#include <DHT.h>

// Motor control pins
#define IN1 5
#define IN2 6
#define IN3 9
#define IN4 10

// DHT11 Sensor
#define DHTPIN 2
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

// Sound Sensor
#define SOUND_PIN A0
#define SOUND_THRESHOLD 100
unsigned long lastSoundTime = 0;
#define SOUND_COOLDOWN 1000
int soundEvents = 0;
bool soundDetected = false;

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

// Buzzer
#define BUZZER_PIN 8
#define BUZZER_DURATION 1000  // 1 second beep
bool buzzerActive = false;
unsigned long buzzerStartTime = 0;

// Touch Sensor
#define TOUCH_PIN 4
bool touchDetected = false;
int touchEvents = 0;
unsigned long lastTouchTime = 0;
#define TOUCH_COOLDOWN 500

// Tilt Sensor (HW-505)
#define TILT_PIN 7
bool tiltDetected = false;
int tiltEvents = 0;
unsigned long lastTiltTime = 0;
#define TILT_COOLDOWN 1000

// Sensor timing
unsigned long lastSensorReadTime = 0;
#define SENSOR_READ_INTERVAL 2000

// Motor state
char currentMotorState = 'S';

void handleBuzzer() {
  if (buzzerActive && (millis() - buzzerStartTime >= BUZZER_DURATION)) {
    digitalWrite(BUZZER_PIN, LOW);
    buzzerActive = false;
  }
}

void triggerBuzzer() {
  digitalWrite(BUZZER_PIN, HIGH);
  buzzerActive = true;
  buzzerStartTime = millis();
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
    if (!buzzerActive) {
      triggerBuzzer();
    }
  }
}

void checkSoundSensor() {
  int soundValue = analogRead(SOUND_PIN);
  if (soundValue > SOUND_THRESHOLD && millis() - lastSoundTime > SOUND_COOLDOWN) {
    soundEvents++;
    soundDetected = true;
    lastSoundTime = millis();
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
  
  // Initialize buzzer
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
  
  attachInterrupt(digitalPinToInterrupt(SHOCK_PIN), handleImpact, FALLING);
  
  Serial.println("System initialized");
}

void loop() {
  // Handle buzzer timing
  handleBuzzer();

  // Handle serial commands
  if (Serial.available() > 0) {
    char command = Serial.read();
    switch(command) {
      case 'F': forward(); break;
      case 'B': backward(); break;
      case 'L': left(); break;
      case 'R': right(); break;
      case 'S': stopMotors(); break;
      case 'X': resetAllSensors(); break;
      case 'D': sendSensorData(); break;
      default: 
        Serial.print("Unknown command: ");
        Serial.println(command);
        break;
    }
  }

  // Check sensors
  checkSoundSensor();
  checkTouchSensor();
  checkTiltSensor();
  
  // Send sensor data at regular intervals
  if (millis() - lastSensorReadTime > SENSOR_READ_INTERVAL) {
    sendSensorData();
    lastSensorReadTime = millis();
  }
}