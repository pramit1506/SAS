/*
 * Smart Attendance System - ESP32 Controller
 * FINAL VERSION - Buzzer only for attendance events
 * 
 * Hardware Connections:
 * - Red LED: GPIO 4
 * - Green LED: GPIO 2  
 * - Buzzer: GPIO 13
 * 
 * Behavior:
 * G - New Attendance: Green 1 long blink + 1 long beep ✅
 * A - Already Marked: Green 2 quick blinks + 2 quick beeps ✅
 * U - Unrecognized:   Red 1 long blink (NO BUZZER) 🔇
 * E - Error:          Red 2 quick blinks (NO BUZZER) 🔇
 */

#define RED_LED 4
#define GREEN_LED 2
#define BUZZER 13

void setup() {
  Serial.begin(115200);
  
  pinMode(RED_LED, OUTPUT);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(BUZZER, OUTPUT);
  
  // All OFF
  digitalWrite(RED_LED, LOW);
  digitalWrite(GREEN_LED, LOW);
  digitalWrite(BUZZER, LOW);
  
  delay(1000);
  
  Serial.println("READY");
}

void loop() {
  if (Serial.available() > 0) {
    char command = Serial.read();
    
    switch(command) {
      case 'G':
      case 'g':
        handleNewAttendance();
        break;
        
      case 'A':
      case 'a':
        handleAlreadyMarked();
        break;
        
      case 'U':
      case 'u':
        handleUnrecognized();
        break;
        
      case 'E':
      case 'e':
        handleError();
        break;
    }
  }
}

// G - New Attendance: GREEN 1 LONG BLINK + 1 LONG BEEP
void handleNewAttendance() {
  digitalWrite(GREEN_LED, HIGH);
  digitalWrite(BUZZER, HIGH);
  delay(1000);
  digitalWrite(GREEN_LED, LOW);
  digitalWrite(BUZZER, LOW);
}

// A - Already Marked: GREEN 2 QUICK BLINKS + 2 QUICK BEEPS
void handleAlreadyMarked() {
  // Blink 1
  digitalWrite(GREEN_LED, HIGH);
  digitalWrite(BUZZER, HIGH);
  delay(200);
  digitalWrite(GREEN_LED, LOW);
  digitalWrite(BUZZER, LOW);
  delay(150);
  
  // Blink 2
  digitalWrite(GREEN_LED, HIGH);
  digitalWrite(BUZZER, HIGH);
  delay(200);
  digitalWrite(GREEN_LED, LOW);
  digitalWrite(BUZZER, LOW);
}

// U - Unrecognized: RED 1 LONG BLINK (NO BUZZER)
void handleUnrecognized() {
  digitalWrite(RED_LED, HIGH);
  delay(1000);
  digitalWrite(RED_LED, LOW);
}

// E - Error: RED 2 QUICK BLINKS (NO BUZZER)
void handleError() {
  // Blink 1
  digitalWrite(RED_LED, HIGH);
  delay(200);
  digitalWrite(RED_LED, LOW);
  delay(150);
  
  // Blink 2
  digitalWrite(RED_LED, HIGH);
  delay(200);
  digitalWrite(RED_LED, LOW);
}
