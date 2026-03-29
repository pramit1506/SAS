"""
Smart Attendance System - Face Recognition
BALANCED VERSION - Optimized threshold + Manual close
"""

# ─── STARTUP ENVIRONMENT CHECK ───────────────────────────────────────────────
import sys
import os

print("=" * 60)
print(f"🐍 Python executable : {sys.executable}")
print(f"🐍 Python version    : {sys.version.split()[0]}")
print("=" * 60)

# Verify opencv-contrib before anything else
try:
    import cv2
    print(f"✅ cv2 version  : {cv2.__version__}")
    _ = cv2.data.haarcascades          # test cv2.data
    _ = cv2.face.LBPHFaceRecognizer_create  # test cv2.face
    print("✅ cv2.data     : OK")
    print("✅ cv2.face     : OK")
except AttributeError as e:
    print(f"\n❌ OpenCV attribute missing: {e}")
    print("\n👉 Fix: run these commands using THIS Python:")
    print(f"   {sys.executable} -m pip uninstall opencv-python opencv-contrib-python -y")
    print(f"   {sys.executable} -m pip install opencv-contrib-python")
    sys.exit(1)
except ImportError:
    print("\n❌ cv2 not found at all.")
    print(f"   {sys.executable} -m pip install opencv-contrib-python")
    sys.exit(1)

print("=" * 60)
# ─────────────────────────────────────────────────────────────────────────────

import numpy as np
import mysql.connector
import serial
import serial.tools.list_ports
import time
from datetime import datetime
import pandas as pd
import warnings
import logging

# Suppress all warnings and errors
warnings.filterwarnings('ignore')
logging.getLogger('libav').setLevel(logging.ERROR)
logging.getLogger('libavcodec').setLevel(logging.ERROR)
os.environ['OPENCV_FFMPEG_LOGLEVEL'] = '-8'

# Configuration
WEBCAM_URL = "http://10.35.241.7:8080/video"
TRAINER_PATH = "trainer.yml"
LABEL_DICT_PATH = "label_dict.npy"
EXCEL_FILE = "attendance_records.xlsx"
ESP32_BAUDRATE = 115200

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'attendance_system'
}

# Recognition Parameters
CONFIDENCE_THRESHOLD = 55
MIN_CONFIRMATION_FRAMES = 5
CONFIDENCE_VARIANCE_THRESHOLD = 8
RECOGNITION_COOLDOWN = 5


class FaceRecognitionSystem:
    def __init__(self):
        print("\n" + "="*60)
        print("⏳ INITIALIZING SYSTEM")
        print("="*60)

        # ── Load Haar Cascade ─────────────────────────────────────────
        print("📂 Loading face detection...")
        cascade_path = os.path.join(cv2.data.haarcascades,
                                    'haarcascade_frontalface_default.xml')
        if not os.path.exists(cascade_path):
            raise FileNotFoundError(f"❌ Cascade XML not found at: {cascade_path}")
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        if self.face_cascade.empty():
            raise Exception("❌ Cascade loaded but is empty — file may be corrupt.")
        print("   ✅ Loaded")

        # ── Load LBPH model ───────────────────────────────────────────
        print("📂 Loading recognition model...")
        if not os.path.exists(TRAINER_PATH):
            raise FileNotFoundError(
                f"❌ Trainer not found: '{TRAINER_PATH}'\n"
                "   Run add_face.py first to train the model."
            )
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.recognizer.read(TRAINER_PATH)
        print("   ✅ Loaded")

        # ── Load label dict ───────────────────────────────────────────
        print("📂 Loading students...")
        if not os.path.exists(LABEL_DICT_PATH):
            raise FileNotFoundError(
                f"❌ Label dict not found: '{LABEL_DICT_PATH}'\n"
                "   Run add_face.py first to generate it."
            )
        self.label_dict = np.load(LABEL_DICT_PATH, allow_pickle=True).item()
        print(f"   ✅ {len(self.label_dict)} students loaded")

        print(f"\n⚙️  Recognition Settings:")
        print(f"   Confidence Threshold : {CONFIDENCE_THRESHOLD}")
        print(f"   Confirmation Frames  : {MIN_CONFIRMATION_FRAMES}")
        print(f"   Variance Threshold   : {CONFIDENCE_VARIANCE_THRESHOLD}")
        print(f"   Cooldown             : {RECOGNITION_COOLDOWN}s")
        print("="*60)

        # ── ESP32 ─────────────────────────────────────────────────────
        self.esp32 = None
        self.esp32_connected = False
        self.connect_esp32()

        # ── Tracking state ────────────────────────────────────────────
        self.last_recognition = {}
        self.confirmed_faces = {}
        self.confirmation_confidences = {}

    # ─────────────────────────────────────────────────────────────────────
    def find_esp32_port(self):
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            return None
        keywords = ['CH340', 'CH9102', 'CP210', 'USB-SERIAL', 'Enhanced-SERIAL']
        for port in ports:
            for kw in keywords:
                if kw.lower() in port.description.lower():
                    return port.device
        return ports[0].device  # fallback to first available

    def connect_esp32(self):
        print("\n" + "="*60)
        print("🔌 CONNECTING TO ESP32")
        print("="*60)
        port = self.find_esp32_port()
        if port is None:
            print("⚠️  No COM ports found — software-only mode")
            print("="*60 + "\n")
            return
        print(f"📍 Port: {port}")
        try:
            self.esp32 = serial.Serial(port=port, baudrate=ESP32_BAUDRATE, timeout=1)
            time.sleep(2)
            self.esp32.reset_input_buffer()
            self.esp32.reset_output_buffer()
            time.sleep(0.5)
            self.esp32_connected = True
            print("✅ Connected")
            print("🟢 Hardware: ENABLED")
        except serial.SerialException as e:
            print(f"❌ Failed: {e} — software-only mode")
            self.esp32 = None
            self.esp32_connected = False
        print("="*60 + "\n")

    def send_command(self, cmd):
        if self.esp32_connected and self.esp32 and self.esp32.is_open:
            try:
                self.esp32.write(cmd.encode())
            except Exception:
                self.esp32_connected = False

    # ─────────────────────────────────────────────────────────────────────
    def enhance_image(self, gray):
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        enhanced = cv2.GaussianBlur(enhanced, (3, 3), 0)
        return enhanced

    def get_student_name(self, roll_number):
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM students WHERE roll_number = %s",
                           (roll_number,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return result[0] if result else "Unknown"
        except Exception:
            return "Unknown"

    def check_attendance_today(self, roll_number):
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            today = datetime.now().date()
            cursor.execute("""
                SELECT COUNT(*) FROM attendance
                WHERE roll_number = %s AND DATE(date_time) = %s
            """, (roll_number, today))
            count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            return count > 0
        except Exception:
            return False

    def mark_attendance(self, roll_number):
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            now = datetime.now()
            cursor.execute("""
                INSERT INTO attendance (roll_number, date_time)
                VALUES (%s, %s)
            """, (roll_number, now))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"❌ DB error: {e}")
            self.send_command('E')
            return False

    def update_excel(self):
        try:
            from sqlalchemy import create_engine
            engine = create_engine(
                f"mysql+mysqlconnector://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
                f"@{DB_CONFIG['host']}/{DB_CONFIG['database']}"
            )
            query = """
                SELECT a.roll_number, s.name, a.date_time
                FROM attendance a
                JOIN students s ON a.roll_number = s.roll_number
                ORDER BY a.date_time DESC
            """
            df = pd.read_sql(query, engine)
            if not df.empty:
                df['date_time'] = pd.to_datetime(df['date_time']).dt.strftime('%Y-%m-%d %H:%M:%S')
                df.columns = ['Roll Number', 'Name', 'Timestamp']
                df.to_excel(EXCEL_FILE, index=False, engine='openpyxl')
        except Exception:
            # Fallback without SQLAlchemy
            try:
                conn = mysql.connector.connect(**DB_CONFIG)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT a.roll_number, s.name, a.date_time
                    FROM attendance a
                    JOIN students s ON a.roll_number = s.roll_number
                    ORDER BY a.date_time DESC
                """)
                rows = cursor.fetchall()
                cursor.close()
                conn.close()
                if rows:
                    df = pd.DataFrame(rows, columns=['Roll Number', 'Name', 'Timestamp'])
                    df['Timestamp'] = pd.to_datetime(df['Timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
                    df.to_excel(EXCEL_FILE, index=False, engine='openpyxl')
            except Exception:
                pass

    def display_message(self, roll_number, name, status, confidence):
        print("\n" + "="*60)
        if status == "NEW":
            print("✅ NEW ATTENDANCE MARKED!")
        else:
            print("⚠️  ALREADY MARKED TODAY!")
        print(f"📝 Roll: {roll_number} | Name: {name}")
        print(f"🎯 Match: {round(100 - confidence, 1)}%")
        print(f"🕐 {datetime.now().strftime('%I:%M:%S %p')}")
        if self.esp32_connected:
            if status == "NEW":
                print("🟢 Green 1 long + 🔊 1 beep")
            else:
                print("🟢 Green 2 quick + 🔊 2 beeps")
        print("="*60 + "\n")

    # ─────────────────────────────────────────────────────────────────────
    def run_recognition(self):
        print("\n" + "="*60)
        print("🎥 FACE RECOGNITION ACTIVE")
        print("="*60)
        print(f"Hardware: {'🟢 ENABLED' if self.esp32_connected else '🔴 DISABLED'}")
        print("\n⌨️  Controls:")
        print("   'Q' or 'ESC' = Quit anytime")
        print("   'Space'      = Close after attendance marked")
        print("="*60 + "\n")

        cap = cv2.VideoCapture(WEBCAM_URL, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

        if not cap.isOpened():
            print("❌ Cannot connect to webcam. Check the IP/URL.")
            self.send_command('E')
            return

        print("📹 Recognition active...\n")

        window = 'Smart Attendance - Press Q/ESC/SPACE to close'
        cv2.namedWindow(window, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window, 800, 600)
        cv2.setWindowProperty(window, cv2.WND_PROP_TOPMOST, 1)

        marked = False
        close_time = None
        window_raised = False
        frame_skip = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            frame_skip += 1
            if frame_skip % 2 != 0:
                continue

            frame = cv2.resize(frame, (640, 480))
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            enhanced = self.enhance_image(gray)

            faces = self.face_cascade.detectMultiScale(
                enhanced, scaleFactor=1.15, minNeighbors=5, minSize=(120, 120)
            )

            current_time = time.time()

            for (x, y, w, h) in faces:
                face_roi = cv2.resize(enhanced[y:y+h, x:x+w], (200, 200))
                label, confidence = self.recognizer.predict(face_roi)

                if confidence < CONFIDENCE_THRESHOLD:
                    roll_number = self.label_dict[label]
                    name = self.get_student_name(roll_number)

                    if roll_number not in self.confirmation_confidences:
                        self.confirmation_confidences[roll_number] = []
                    self.confirmation_confidences[roll_number].append(confidence)
                    if len(self.confirmation_confidences[roll_number]) > MIN_CONFIRMATION_FRAMES:
                        self.confirmation_confidences[roll_number].pop(0)

                    self.confirmed_faces[roll_number] = \
                        self.confirmed_faces.get(roll_number, 0) + 1

                    last_time = self.last_recognition.get(roll_number, 0)

                    if self.confirmed_faces[roll_number] >= MIN_CONFIRMATION_FRAMES:
                        confs = self.confirmation_confidences[roll_number]
                        avg_conf = sum(confs) / len(confs)
                        variance = sum((c - avg_conf) ** 2 for c in confs) / len(confs)
                        std_dev = variance ** 0.5

                        if (avg_conf < CONFIDENCE_THRESHOLD
                                and std_dev < CONFIDENCE_VARIANCE_THRESHOLD
                                and (current_time - last_time) > RECOGNITION_COOLDOWN):

                            already = self.check_attendance_today(roll_number)
                            if not already:
                                if self.mark_attendance(roll_number):
                                    self.send_command('G')
                                    time.sleep(1.2)
                                    self.update_excel()
                                    self.display_message(roll_number, name, "NEW", avg_conf)
                                    marked = True
                                    close_time = time.time() + 3
                            else:
                                self.send_command('A')
                                time.sleep(0.8)
                                self.display_message(roll_number, name, "ALREADY", avg_conf)
                                marked = True
                                close_time = time.time() + 3

                            self.last_recognition[roll_number] = current_time
                            self.confirmed_faces[roll_number] = 0
                            self.confirmation_confidences[roll_number] = []

                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 3)
                    cv2.putText(frame, f"{name}", (x, y-40),
                                cv2.FONT_HERSHEY_DUPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(frame, f"Roll: {roll_number}", (x, y-15),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.putText(frame, f"Match: {round(100-confidence,1)}%", (x, y+h+25),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    cv2.putText(frame,
                                f"{self.confirmed_faces.get(roll_number,0)}/{MIN_CONFIRMATION_FRAMES}",
                                (x+w-50, y-15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

                else:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 3)
                    cv2.putText(frame, "UNKNOWN", (x, y-15),
                                cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 0, 255), 2)
                    cv2.putText(frame, f"{round(100-confidence,1)}% - TOO LOW", (x, y+h+25),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                    if (current_time - self.last_recognition.get('unknown', 0)) > 3:
                        self.send_command('U')
                        self.last_recognition['unknown'] = current_time

            hw = "HW:ON" if self.esp32_connected else "HW:OFF"
            status_text = "MARKED!" if marked else "SCANNING..."
            cv2.putText(frame, f"{hw} | {status_text}", (10, 30),
                        cv2.FONT_HERSHEY_DUPLEX, 0.7, (0, 255, 255), 2)
            if marked:
                cv2.putText(frame, "Press SPACE to close now", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            cv2.imshow(window, frame)

            if not window_raised:
                cv2.setWindowProperty(window, cv2.WND_PROP_TOPMOST, 0)
                window_raised = True

            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), 27):
                print("\n⚠️  Stopped by user")
                break
            elif key == 32 and marked:
                print("\n⌨️  Manual close")
                break

            if close_time and time.time() >= close_time:
                print("🔒 Auto-closing...")
                break

        cap.release()
        cv2.destroyAllWindows()
        if self.esp32 and self.esp32.is_open:
            self.esp32.close()

        print("\n" + "="*60)
        print("🏁 SESSION ENDED")
        print("="*60 + "\n")


def main():
    try:
        system = FaceRecognitionSystem()
        system.run_recognition()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")


if __name__ == "__main__":
    main()