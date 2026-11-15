#include <IRremote.h>

#define IR_TRANSMIT_PIN 3
IRsend irsend;

// Joystick Pins
#define JOY_X_PIN A0
#define JOY_Y_PIN A1
#define MODE_BUTTON_PIN 2

// Command Definitions (Must match receiver)
#define IR_CMD_FORWARD   0x00FF18E7
#define IR_CMD_BACKWARD  0x00FF4AB5
#define IR_CMD_LEFT      0x00FF10EF
#define IR_CMD_RIGHT     0x00FF5AA5
#define IR_CMD_STOP      0x00FF38C7
#define IR_CMD_MODE_SWITCH 0x00FFA25D

void setup() {
  Serial.begin(9600);
  pinMode(MODE_BUTTON_PIN, INPUT_PULLUP);
}

void loop() {
  int xValue = analogRead(JOY_X_PIN);
  int yValue = analogRead(JOY_Y_PIN);
  
  if (digitalRead(MODE_BUTTON_PIN) == LOW) {
    irsend.sendNEC(IR_CMD_MODE_SWITCH, 32);
    delay(200); // Debounce
    return;
  }

  if (yValue > 700) {
    irsend.sendNEC(IR_CMD_FORWARD, 32);
  } else if (yValue < 300) {
    irsend.sendNEC(IR_CMD_BACKWARD, 32);
  } else if (xValue > 700) {
    irsend.sendNEC(IR_CMD_RIGHT, 32);
  } else if (xValue < 300) {
    irsend.sendNEC(IR_CMD_LEFT, 32);
  } else {
    irsend.sendNEC(IR_CMD_STOP, 32);
  }
  
  delay(100); // Reduce IR transmission rate
}