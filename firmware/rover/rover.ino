#include <DHT.h>
#include <IRremote.h>

// Motor control pins
#define IN1 5
#define IN2 6
#define IN3 9
#define IN4 10

// DHT11 Sensor
#define DHTPIN 2
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

// IR Receiver
#define IR_RECV_PIN 14  // Using A0 as digital pin 14
IRrecv irrecv(IR_RECV_PIN);
decode_results results;

// IR Command Definitions (NEC protocol)
#define IR_CMD_FORWARD   0x00FF18E7
#define IR_CMD_BACKWARD  0x00FF4AB5
#define IR_CMD_LEFT      0x00FF10EF
#define IR_CMD_RIGHT     0x00FF5AA5
#define IR_CMD_STOP      0x00FF38C7
#define IR_CMD_MODE_SWITCH 0x00FFA25D

// Sound Sensor (moved to A1)
#define SOUND_PIN A1
#define SOUND_THRESHOLD 100
unsigned long lastSoundTime = 0;
#define SOUND_COOLDOWN 1000
int soundEvents = 0;
bool soundDetected = false;
unsigned long soundLedStartTime = 0;
bool soundLedActive = false;

// Impact Sensor
#define SHOCK_PIN 3
#define IMPACT_WINDOW_MS 50
#define MIN_BOUNCES 1
#define COOLDOWN_MS 1000
#define DEBOUNCE_MS 2
volatile unsigned long firstTriggerTime = 0;
volatile unsigned long lastTriggerTime = 0;
volatile byte bounceCount = 0;
volatile int confirmedImpacts = 0;
bool impactDetected = false;
unsigned long lastImpactTime = 0;
unsigned long impactLedStartTime = 0;
bool impactLedActive = false;

// Buzzer
#define BUZZER_PIN 8
#define BUZZER_DURATION 1000
bool buzzerActive = false;
unsigned long buzzerStartTime = 0;

// SMD RGB LED
#define LED_RED_PIN 11
#define LED_GREEN_PIN 12
#define LED_BLUE_PIN 13
unsigned long tiltLedStartTime = 0;
bool tiltLedActive = false;

// Touch Sensor
#define TOUCH_PIN 4
bool touchDetected = false;
int touchEvents = 0;
unsigned long lastTouchTime = 0;
#define TOUCH_COOLDOWN 500

// Tilt Sensor
#define TILT_PIN 7
bool tiltDetected = false;
int tiltEvents = 0;
unsigned long lastTiltTime = 0;
#define TILT_COOLDOWN 1000

// Control Mode
enum ControlMode { BUTTON_MODE, JOYSTICK_MODE, IR_TR_MODE };
ControlMode currentMode = BUTTON_MODE;

// Sensor timing
unsigned long lastSensorReadTime = 0;
#define SENSOR_READ_INTERVAL 2000

// Motor state
char currentMotorState = 'S';

void setupLEDs() {
  pinMode(LED_RED_PIN, OUTPUT);
  pinMode(LED_GREEN_PIN, OUTPUT);
  pinMode(LED_BLUE_PIN, OUTPUT);
  digitalWrite(LED_RED_PIN, LOW);
  digitalWrite(LED_GREEN_PIN, LOW);
  digitalWrite(LED_BLUE_PIN, LOW);
}

void handleBuzzer() {
  if (buzzerActive && (millis() - buzzerStartTime >= BUZZER_DURATION)) {
    digitalWrite(BUZZER_PIN, LOW);
    buzzerActive = false;
  }
}

void handleLEDs() {
  if (soundLedActive && (millis() - soundLedStartTime >= 1000)) {
    digitalWrite(LED_BLUE_PIN, LOW);
    soundLedActive = false;
  }
  if (impactLedActive && (millis() - impactLedStartTime >= 1000)) {
    digitalWrite(LED_RED_PIN, LOW);
    impactLedActive = false;
  }
  if (tiltLedActive && (millis() - tiltLedStartTime >= 1000)) {
    digitalWrite(LED_GREEN_PIN, LOW);
    tiltLedActive = false;
  }
}

void triggerBuzzer() {
  digitalWrite(BUZZER_PIN, HIGH);
  buzzerActive = true;
  buzzerStartTime = millis();
}

void triggerSoundLED() {
  digitalWrite(LED_BLUE_PIN, HIGH);
  soundLedActive = true;
  soundLedStartTime = millis();
}

void triggerImpactLED() {
  digitalWrite(LED_RED_PIN, HIGH);
  impactLedActive = true;
  impactLedStartTime = millis();
}

void triggerTiltLED() {
  digitalWrite(LED_GREEN_PIN, HIGH);
  tiltLedActive = true;
  tiltLedStartTime = millis();
}

void handleImpact() {
  unsigned long currentTime = millis();
  if (currentTime - lastTriggerTime < DEBOUNCE_MS) return;
  if (currentTime - lastImpactTime < COOLDOWN_MS) return;
  
  if (currentTime - lastTriggerTime > IMPACT_WINDOW_MS) {
    firstTriggerTime = currentTime;
    bounceCount = 1;
  } else {
    bounceCount++;
  }
  
  lastTriggerTime = currentTime;

  if (bounceCount >= MIN_BOUNCES && currentTime - firstTriggerTime <= IMPACT_WINDOW_MS) {
    confirmedImpacts++;
    impactDetected = true;
    lastImpactTime = currentTime;
    bounceCount = 0;
    if (!buzzerActive) triggerBuzzer();
    if (!impactLedActive) triggerImpactLED();
  }
}

void checkSoundSensor() {
  int soundValue = analogRead(SOUND_PIN);
  if (soundValue > SOUND_THRESHOLD && millis() - lastSoundTime > SOUND_COOLDOWN) {
    soundEvents++;
    soundDetected = true;
    lastSoundTime = millis();
    if (!soundLedActive) triggerSoundLED();
  }
}

void checkTouchSensor() {
  int touchValue = digitalRead(TOUCH_PIN);
  if (touchValue == HIGH && millis() - lastTouchTime > TOUCH_COOLDOWN) {
    touchEvents++;
    touchDetected = true;
    lastTouchTime = millis();
  }
}

void checkTiltSensor() {
  int tiltValue = digitalRead(TILT_PIN);
  if (tiltValue == LOW && millis() - lastTiltTime > TILT_COOLDOWN) {
    tiltEvents++;
    tiltDetected = true;
    lastTiltTime = millis();
    if (!tiltLedActive) triggerTiltLED();
  }
}

void resetAllSensors() {
  confirmedImpacts = 0;
  soundEvents = 0;
  touchEvents = 0;
  tiltEvents = 0;
  impactDetected = false;
  soundDetected = false;
  touchDetected = false;
  tiltDetected = false;
  digitalWrite(LED_RED_PIN, LOW);
  digitalWrite(LED_GREEN_PIN, LOW);
  digitalWrite(LED_BLUE_PIN, LOW);
  soundLedActive = false;
  impactLedActive = false;
  tiltLedActive = false;
}

bool readDHTData(float &temperature, float &humidity) {
  temperature = dht.readTemperature();
  humidity = dht.readHumidity();
  if (isnan(temperature) || isnan(humidity)) {
    delay(100);
    temperature = dht.readTemperature();
    humidity = dht.readHumidity();
  }
  return !(isnan(temperature) || isnan(humidity));
}

void sendSensorData() {
  float temperature, humidity;
  bool dhtSuccess = readDHTData(temperature, humidity);
  
  Serial.print("SENSORS:");
  Serial.print(dhtSuccess ? String(temperature) : "NaN");
  Serial.print(",");
  Serial.print(dhtSuccess ? String(humidity) : "NaN");
  Serial.print(",");
  Serial.print(confirmedImpacts);
  Serial.print(",");
  Serial.print(impactDetected ? "1" : "0");
  Serial.print(",");
  Serial.print(soundEvents);
  Serial.print(",");
  Serial.print(soundDetected ? "1" : "0");
  Serial.print(",");
  Serial.print(touchEvents);
  Serial.print(",");
  Serial.print(touchDetected ? "1" : "0");
  Serial.print(",");
  Serial.print(tiltEvents);
  Serial.print(",");
  Serial.print(tiltDetected ? "1" : "0");
  Serial.println();
  
  impactDetected = false;
  soundDetected = false;
  touchDetected = false;
  tiltDetected = false;
}

void forward() {
  digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
  digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);
  currentMotorState = 'F';
  Serial.println("Moving Forward");
}

void backward() {
  digitalWrite(IN1, LOW); digitalWrite(IN2, HIGH);
  digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH);
  currentMotorState = 'B';
  Serial.println("Moving Backward");
}

void left() {
  digitalWrite(IN1, LOW); digitalWrite(IN2, HIGH);
  digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);
  currentMotorState = 'L';
  Serial.println("Turning Left");
}

void right() {
  digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH);
  currentMotorState = 'R';
  Serial.println("Turning Right");
}

void stopMotors() {
  digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW); digitalWrite(IN4, LOW);
  currentMotorState = 'S';
  Serial.println("Stopped");
}

void processIRCommand() {
  if (irrecv.decode(&results)) {
    if (currentMode == IR_TR_MODE) {
      switch(results.value) {
        case IR_CMD_FORWARD: forward(); break;
        case IR_CMD_BACKWARD: backward(); break;
        case IR_CMD_LEFT: left(); break;
        case IR_CMD_RIGHT: right(); break;
        case IR_CMD_STOP: stopMotors(); break;
        case IR_CMD_MODE_SWITCH:
          currentMode = BUTTON_MODE;
          Serial.println("Mode switched to BUTTON");
          break;
      }
    }
    irrecv.resume();
  }
}

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    ; // wait for serial port to connect
  }
  
  // Initialize motor control pins
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  stopMotors();
  
  // Initialize sensors
  dht.begin();
  pinMode(SOUND_PIN, INPUT);
  pinMode(SHOCK_PIN, INPUT_PULLUP);
  pinMode(TOUCH_PIN, INPUT);
  pinMode(TILT_PIN, INPUT_PULLUP);
  
  // Initialize buzzer and LEDs
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
  setupLEDs();
  
  // Initialize IR receiver
  irrecv.enableIRIn();
  
  attachInterrupt(digitalPinToInterrupt(SHOCK_PIN), handleImpact, FALLING);
  
  Serial.println("System initialized");
}

void loop() {
  handleBuzzer();
  handleLEDs();
  processIRCommand();

  if (Serial.available() > 0) {
    char command = Serial.read();
    switch(command) {
      case 'F': if (currentMode == BUTTON_MODE) forward(); break;
      case 'B': if (currentMode == BUTTON_MODE) backward(); break;
      case 'L': if (currentMode == BUTTON_MODE) left(); break;
      case 'R': if (currentMode == BUTTON_MODE) right(); break;
      case 'S': stopMotors(); break;
      case 'X': resetAllSensors(); break;
      case 'D': sendSensorData(); break;
      case 'M': 
        currentMode = (ControlMode)((currentMode + 1) % 3);
        Serial.print("Mode switched to ");
        switch(currentMode) {
          case BUTTON_MODE: Serial.println("BUTTON"); break;
          case JOYSTICK_MODE: Serial.println("JOYSTICK"); break;
          case IR_TR_MODE: Serial.println("IR-TR"); break;
        }
        break;
      default: 
        Serial.print("Unknown command: ");
        Serial.println(command);
        break;
    }
  }

  checkSoundSensor();
  checkTouchSensor();
  checkTiltSensor();
  
  if (millis() - lastSensorReadTime > SENSOR_READ_INTERVAL) {
    sendSensorData();
    lastSensorReadTime = millis();
  }
}