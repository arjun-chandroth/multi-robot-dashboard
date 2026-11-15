#include <IRremote.h>

// Motor control pins (example pins - adjust to your setup)
#define MOTOR_A_EN 5
#define MOTOR_A_IN1 6
#define MOTOR_A_IN2 7
#define MOTOR_B_EN 10
#define MOTOR_B_IN1 8
#define MOTOR_B_IN2 9

// IR Receiver pin
#define IR_RX_PIN 11

// IR Codes (must match transmitter)
#define IR_CODE_FORWARD 0x10
#define IR_CODE_BACKWARD 0x20
#define IR_CODE_LEFT 0x30
#define IR_CODE_RIGHT 0x40
#define IR_CODE_STOP 0x50

IRrecv irrecv(IR_RX_PIN);
decode_results results;

void setup() {
  Serial.begin(115200);
  Serial.println("IR-TR Receiver Ready");
  
  // Initialize motor control pins
  pinMode(MOTOR_A_EN, OUTPUT);
  pinMode(MOTOR_A_IN1, OUTPUT);
  pinMode(MOTOR_A_IN2, OUTPUT);
  pinMode(MOTOR_B_EN, OUTPUT);
  pinMode(MOTOR_B_IN1, OUTPUT);
  pinMode(MOTOR_B_IN2, OUTPUT);
  
  // Start IR receiver
  irrecv.enableIRIn();
  
  // Stop motors initially
  stopMotors();
}

void loop() {
  if (irrecv.decode(&results)) {
    unsigned long code = results.value;
    
    Serial.print("Received IR Code: 0x");
    Serial.print(code, HEX);
    Serial.print(" - ");
    
    switch(code) {
      case IR_CODE_FORWARD:
        Serial.println("FORWARD");
        moveForward();
        break;
      case IR_CODE_BACKWARD:
        Serial.println("BACKWARD");
        moveBackward();
        break;
      case IR_CODE_LEFT:
        Serial.println("LEFT");
        turnLeft();
        break;
      case IR_CODE_RIGHT:
        Serial.println("RIGHT");
        turnRight();
        break;
      case IR_CODE_STOP:
        Serial.println("STOP");
        stopMotors();
        break;
      default:
        Serial.println("UNKNOWN COMMAND");
    }
    
    irrecv.resume(); // Receive the next value
  }
  delay(10);
}

// Motor control functions
void moveForward() {
  digitalWrite(MOTOR_A_IN1, HIGH);
  digitalWrite(MOTOR_A_IN2, LOW);
  digitalWrite(MOTOR_B_IN1, HIGH);
  digitalWrite(MOTOR_B_IN2, LOW);
  analogWrite(MOTOR_A_EN, 255);
  analogWrite(MOTOR_B_EN, 255);
}

void moveBackward() {
  digitalWrite(MOTOR_A_IN1, LOW);
  digitalWrite(MOTOR_A_IN2, HIGH);
  digitalWrite(MOTOR_B_IN1, LOW);
  digitalWrite(MOTOR_B_IN2, HIGH);
  analogWrite(MOTOR_A_EN, 255);
  analogWrite(MOTOR_B_EN, 255);
}

void turnLeft() {
  digitalWrite(MOTOR_A_IN1, LOW);
  digitalWrite(MOTOR_A_IN2, HIGH);
  digitalWrite(MOTOR_B_IN1, HIGH);
  digitalWrite(MOTOR_B_IN2, LOW);
  analogWrite(MOTOR_A_EN, 200);
  analogWrite(MOTOR_B_EN, 200);
}

void turnRight() {
  digitalWrite(MOTOR_A_IN1, HIGH);
  digitalWrite(MOTOR_A_IN2, LOW);
  digitalWrite(MOTOR_B_IN1, LOW);
  digitalWrite(MOTOR_B_IN2, HIGH);
  analogWrite(MOTOR_A_EN, 200);
  analogWrite(MOTOR_B_EN, 200);
}

void stopMotors() {
  digitalWrite(MOTOR_A_IN1, LOW);
  digitalWrite(MOTOR_A_IN2, LOW);
  digitalWrite(MOTOR_B_IN1, LOW);
  digitalWrite(MOTOR_B_IN2, LOW);
  analogWrite(MOTOR_A_EN, 0);
  analogWrite(MOTOR_B_EN, 0);
}