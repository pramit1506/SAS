"""
Smart Attendance System - Optimized Face Capture Module
✅ Fast cascade loading
✅ Live preview window with alignment guides
✅ Real-time counter display
✅ Optimized for speed and accuracy
"""

import cv2
import os
import numpy as np
import mysql.connector
from datetime import datetime
import time

# Configuration
WEBCAM_URL = "http://10.35.241.7:8080/video"
FACE_DATA_PATH = "face_data"
TRAINER_PATH = "trainer.yml"

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'attendance_system'
}

class OptimizedFaceCapture:
    def __init__(self):
        print("⏳ Loading face detection model...")
        
        # Load cascade ONCE - faster method
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        if self.face_cascade.empty():
            raise Exception("❌ Failed to load Haar Cascade!")
        
        print("✅ Face detection model loaded!")
        
        # Optimized parameters
        self.num_samples = 30  # 30 is sufficient with good preprocessing
        self.min_face_size = (100, 100)
        self.quality_threshold = 15
        
    def enhance_image(self, gray_image):
        """
        Fast preprocessing with CLAHE
        """
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8,8))
        enhanced = clahe.apply(gray_image)
        return enhanced
    
    def check_quality(self, gray_image):
        """
        Quick blur detection
        """
        laplacian = cv2.Laplacian(gray_image, cv2.CV_64F).var()
        return laplacian > self.quality_threshold
    
    def draw_ui(self, frame, count, total, rejected, face_detected, face_coords=None):
        """
        Draw professional UI overlay
        """
        h, w = frame.shape[:2]
        
        # Semi-transparent overlay for header
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 80), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)
        
        # Title
        cv2.putText(frame, "FACE CAPTURE SYSTEM", (10, 30),
                   cv2.FONT_HERSHEY_DUPLEX, 0.9, (255, 255, 255), 2)
        
        # Counter with progress bar
        progress_text = f"Captured: {count}/{total}"
        cv2.putText(frame, progress_text, (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Progress bar
        bar_width = 300
        bar_x = w - bar_width - 10
        bar_y = 45
        bar_height = 20
        
        # Background bar
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height),
                     (50, 50, 50), -1)
        
        # Progress fill
        progress = int((count / total) * bar_width)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + progress, bar_y + bar_height),
                     (0, 255, 0), -1)
        
        # Percentage
        percent = int((count / total) * 100)
        cv2.putText(frame, f"{percent}%", (bar_x + bar_width + 10, bar_y + 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        # Draw face detection box and guides
        if face_detected and face_coords:
            x, y, w_face, h_face = face_coords
            
            # Green box for detected face
            cv2.rectangle(frame, (x, y), (x+w_face, y+h_face), (0, 255, 0), 3)
            
            # Corner markers for alignment
            corner_length = 20
            # Top-left
            cv2.line(frame, (x, y), (x + corner_length, y), (0, 255, 255), 3)
            cv2.line(frame, (x, y), (x, y + corner_length), (0, 255, 255), 3)
            # Top-right
            cv2.line(frame, (x+w_face, y), (x+w_face - corner_length, y), (0, 255, 255), 3)
            cv2.line(frame, (x+w_face, y), (x+w_face, y + corner_length), (0, 255, 255), 3)
            # Bottom-left
            cv2.line(frame, (x, y+h_face), (x + corner_length, y+h_face), (0, 255, 255), 3)
            cv2.line(frame, (x, y+h_face), (x, y+h_face - corner_length), (0, 255, 255), 3)
            # Bottom-right
            cv2.line(frame, (x+w_face, y+h_face), (x+w_face - corner_length, y+h_face), (0, 255, 255), 3)
            cv2.line(frame, (x+w_face, y+h_face), (x+w_face, y+h_face - corner_length), (0, 255, 255), 3)
            
            # Center crosshair
            center_x = x + w_face // 2
            center_y = y + h_face // 2
            cv2.circle(frame, (center_x, center_y), 5, (0, 255, 255), -1)
            cv2.circle(frame, (center_x, center_y), 3, (0, 0, 255), -1)
            
            # Status text on face
            cv2.putText(frame, "FACE DETECTED", (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        else:
            # Center guide when no face
            center_x, center_y = w // 2, h // 2
            guide_size = 150
            
            # Draw center box guide
            cv2.rectangle(frame, 
                         (center_x - guide_size, center_y - guide_size),
                         (center_x + guide_size, center_y + guide_size),
                         (0, 0, 255), 2)
            
            cv2.putText(frame, "Position face in center box", (center_x - 150, center_y - guide_size - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Instructions at bottom
        instructions = [
            "Keep face centered | Look at camera | Good lighting",
            f"Rejected (blur): {rejected} | Press 'Q' to quit"
        ]
        
        y_offset = h - 60
        for instruction in instructions:
            cv2.putText(frame, instruction, (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset += 25
        
        return frame
    
    def capture_faces(self, roll_number, student_name):
        """
        Optimized face capture with live preview
        """
        print("\n" + "="*60)
        print("📸 FACE CAPTURE - LIVE PREVIEW MODE")
        print("="*60)
        print(f"Student: {student_name} (Roll: {roll_number})")
        print(f"Images to capture: {self.num_samples}")
        print("\n✨ PREVIEW WINDOW OPENING...")
        print("="*60 + "\n")
        
        # Create directory
        student_dir = os.path.join(FACE_DATA_PATH, str(roll_number))
        os.makedirs(student_dir, exist_ok=True)
        
        # Connect to webcam
        cap = cv2.VideoCapture(WEBCAM_URL)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer for lower latency
        
        if not cap.isOpened():
            print("❌ Cannot connect to IP webcam!")
            return False
        
        print("🎥 Camera connected! Preview active...\n")
        
        # Create fullscreen window
        window_name = 'Face Capture - Live Preview'
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 800, 600)
        
        count = 0
        rejected = 0
        last_save_time = 0
        save_interval = 0.25  # Faster capture
        
        while count < self.num_samples:
            ret, frame = cap.read()
            if not ret:
                print("❌ Failed to grab frame")
                break
            
            # Resize for speed
            frame = cv2.resize(frame, (640, 480))
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Fast enhancement
            enhanced = self.enhance_image(gray)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                enhanced,
                scaleFactor=1.2,
                minNeighbors=4,
                minSize=self.min_face_size
            )
            
            current_time = time.time()
            face_detected = False
            face_coords = None
            
            # Process only if single face
            if len(faces) == 1:
                x, y, w, h = faces[0]
                face_detected = True
                face_coords = (x, y, w, h)
                
                # Capture logic
                if (current_time - last_save_time) > save_interval:
                    face_roi = enhanced[y:y+h, x:x+w]
                    
                    if self.check_quality(face_roi):
                        # Resize and save
                        face_roi = cv2.resize(face_roi, (200, 200))
                        img_path = os.path.join(student_dir, f"{roll_number}_{count}.jpg")
                        cv2.imwrite(img_path, face_roi)
                        
                        count += 1
                        last_save_time = current_time
                        print(f"✓ Captured: {count}/{self.num_samples}")
                    else:
                        rejected += 1
            
            # Draw UI
            frame = self.draw_ui(frame, count, self.num_samples, rejected, 
                               face_detected, face_coords)
            
            cv2.imshow(window_name, frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\n⚠️  Capture cancelled")
                break
        
        cap.release()
        cv2.destroyAllWindows()
        
        if count >= self.num_samples:
            print(f"\n✅ Successfully captured {count} images!")
            return True
        else:
            print(f"\n⚠️  Only {count}/{self.num_samples} captured")
            return False
    
    def train_model(self):
        """
        Fast training with optimized LBPH
        """
        print("\n" + "="*60)
        print("🧠 TRAINING MODEL")
        print("="*60)
        
        faces = []
        labels = []
        label_dict = {}
        current_label = 0
        
        if not os.path.exists(FACE_DATA_PATH):
            print("❌ No face data found!")
            return False
        
        print("\n📂 Loading images...")
        
        for student_folder in os.listdir(FACE_DATA_PATH):
            folder_path = os.path.join(FACE_DATA_PATH, student_folder)
            
            if not os.path.isdir(folder_path):
                continue
            
            roll_number = int(student_folder)
            label_dict[current_label] = roll_number
            
            img_count = 0
            for img_name in os.listdir(folder_path):
                if not img_name.endswith('.jpg'):
                    continue
                
                img_path = os.path.join(folder_path, img_name)
                gray = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                
                if gray is None:
                    continue
                
                # Apply same enhancement
                enhanced = self.enhance_image(gray)
                faces.append(enhanced)
                labels.append(current_label)
                img_count += 1
            
            print(f"   ✓ Roll {roll_number}: {img_count} images")
            current_label += 1
        
        if len(faces) == 0:
            print("❌ No valid images!")
            return False
        
        print(f"\n📊 Total: {len(label_dict)} students, {len(faces)} images")
        print("⏳ Training...")
        
        # Optimized LBPH parameters
        recognizer = cv2.face.LBPHFaceRecognizer_create(
            radius=1,
            neighbors=8,
            grid_x=8,
            grid_y=8,
            threshold=100.0
        )
        
        recognizer.train(faces, np.array(labels))
        recognizer.save(TRAINER_PATH)
        np.save("label_dict.npy", label_dict)
        
        print(f"✅ Training complete!")
        print(f"📁 Saved: {TRAINER_PATH}")
        print("="*60 + "\n")
        
        return True
    
    def add_to_database(self, roll_number, student_name):
        """
        Add to MySQL
        """
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM students WHERE roll_number = %s", (roll_number,))
            if cursor.fetchone():
                cursor.execute(
                    "UPDATE students SET name = %s WHERE roll_number = %s",
                    (student_name, roll_number)
                )
            else:
                cursor.execute(
                    "INSERT INTO students (roll_number, name) VALUES (%s, %s)",
                    (roll_number, student_name)
                )
            
            conn.commit()
            cursor.close()
            conn.close()
            print("✅ Added to database")
            return True
            
        except mysql.connector.Error as err:
            print(f"❌ Database error: {err}")
            return False

def main():
    print("\n" + "="*60)
    print("🎓 ADD NEW STUDENT")
    print("="*60)
    
    try:
        roll_number = int(input("\nRoll Number: "))
        if roll_number <= 0:
            print("❌ Invalid roll number!")
            return
    except ValueError:
        print("❌ Enter a valid number!")
        return
    
    student_name = input("Student Name: ").strip()
    if not student_name:
        print("❌ Name cannot be empty!")
        return
    
    print(f"\n📝 Roll: {roll_number} | Name: {student_name}")
    confirm = input("Proceed? (y/n): ")
    
    if confirm.lower() != 'y':
        print("❌ Cancelled")
        return
    
    try:
        capture_system = OptimizedFaceCapture()
        
        if capture_system.capture_faces(roll_number, student_name):
            if capture_system.train_model():
                capture_system.add_to_database(roll_number, student_name)
                print("\n" + "="*60)
                print("🎉 STUDENT ADDED SUCCESSFULLY!")
                print("="*60)
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
