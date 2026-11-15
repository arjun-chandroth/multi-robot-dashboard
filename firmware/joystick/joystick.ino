// Joystick Controller for Raspberry Pi Car
// Connect to Ubuntu laptop via USB

#define JOYSTICK_X A0
#define JOYSTICK_Y A1
#define BUTTON_PIN 2  // Mode switch button

void setup() {
  Serial.begin(115200);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
}

void loop() {
  static bool joystickMode = true;
  static unsigned long lastSendTime = 0;
  
  // Check mode switch button
  if (digitalRead(BUTTON_PIN) == LOW) {
    delay(50);  // Debounce
    if (digitalRead(BUTTON_PIN) == LOW) {
      joystickMode = !joystickMode;
      Serial.print("MODE:");
      Serial.println(joystickMode ? "JOYSTICK" : "BUTTONS");
      while (digitalRead(BUTTON_PIN) == LOW);  // Wait for release
    }
  }
  
  // Send joystick data at 20Hz
  if (joystickMode && millis() - lastSendTime > 50) {
    int x = analogRead(JOYSTICK_X);
    int y = analogRead(JOYSTICK_Y);
    
    // Map to -500 to 500 range (center at 0)
    x = map(x, 0, 1023, -500, 500);
    y = map(y, 0, 1023, -500, 500);
    
    // Apply deadzone
    if (abs(x) < 50) x = 0;
    if (abs(y) < 50) y = 0;
    
    Serial.print("JOY:");
    Serial.print(x);
    Serial.print(",");
    Serial.println(y);
    
    lastSendTime = millis();
  }
  
  delay(10);
}