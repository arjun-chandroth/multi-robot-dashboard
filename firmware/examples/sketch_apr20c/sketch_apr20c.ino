#include <DHT.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_ADXL345_U.h>

// Motor control pins (adjusted for Mega)
#define IN1 22
#define IN2 24
#define IN3 26
#define IN4 28

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

// SMD RGB LED (Common Cathode)
#define LED_RED_PIN 9
#define LED_GREEN_PIN 10
#define LED_BLUE_PIN 11
unsigned long tiltLedStartTime = 0;
bool tiltLedActive = false;

// Touch Sensor
#define TOUCH_PIN 4
bool touchDetected = false;
int touchEvents = 0;
unsigned long lastTouchTime = 0;
#define TOUCH_COOLDOWN 500

// Tilt Sensor (HW-505)
#define TILT_PIN 5
bool tiltDetected = false;
int tiltEvents = 0;
unsigned long lastTiltTime = 0;
#define TILT_COOLDOWN 1000

// PIR Motion Sensor
#define PIR_PIN 6
bool pirDetected = false;
int pirEvents = 0;
unsigned long lastPirTime = 0;
#define PIR_COOLDOWN 2000

// Rain Drop Sensor
#define RAIN_PIN A1
#define RAIN_THRESHOLD 500
bool rainDetected = false;
int rainEvents = 0;
unsigned long lastRainTime = 0;
#define RAIN_COOLDOWN 2000

// MQ2 Gas Sensor
#define MQ2_PIN A2
#define MQ2_THRESHOLD 300
bool gasDetected = false;
int gasEvents = 0;
unsigned long lastGasTime = 0;
#define GAS_COOLDOWN 2000

// Flame Sensor
#define FLAME_PIN A3
#define FLAME_THRESHOLD 200
bool flameDetected = false;
int flameEvents = 0;
unsigned long lastFlameTime = 0;
#define FLAME_COOLDOWN 2000

// ADXL345 Accelerometer
Adafruit_ADXL345_Unified accel = Adafruit_ADXL345_Unified(12345);
float accelX = 0, accelY = 0, accelZ = 0;

// 2-Color LED Module (Common Cathode)
#define LED_COLOR1_PIN 30  // e.g., Green for rain
#define LED_COLOR2_PIN 31  // e.g., Red for touch
unsigned long colorLedStartTime = 0;
bool colorLedActive = false;
#define COLOR_LED_DURATION 2000  // 2 seconds

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
  
  // Initialize 2-color LED
  pinMode(LED_COLOR1_PIN, OUTPUT);
  pinMode(LED_COLOR2_PIN, OUTPUT);
  digitalWrite(LED_COLOR1_PIN, LOW);
  digitalWrite(LED_COLOR2_PIN, LOW);
}

void handleBuzzer() {
  if (buzzerActive && (millis() - buzzerStartTime >= BUZZER_DURATION)) {
    digitalWrite(BUZZER_PIN, LOW);
    buzzerActive = false;
  }
}

void handleLEDs() {
  // Handle sound LED (Blue)
  if (soundLedActive && (millis() - soundLedStartTime >= 1000)) {
    digitalWrite(LED_BLUE_PIN, LOW);
    soundLedActive = false;
  }
  
  // Handle impact LED (Red)
  if (impactLedActive && (millis() - impactLedStartTime >= 1000)) {
    digitalWrite(LED_RED_PIN, LOW);
    impactLedActive = false;
  }
  
  // Handle tilt LED (Green)
  if (tiltLedActive && (millis() - tiltLedStartTime >= 1000)) {
    digitalWrite(LED_GREEN_PIN, LOW);
    tiltLedActive = false;
  }
  
  // Handle 2-color LED
  if (colorLedActive && (millis() - colorLedStartTime >= COLOR_LED_DURATION)) {
    digitalWrite(LED_COLOR1_PIN, LOW);
    digitalWrite(LED_COLOR2_PIN, LOW);
    colorLedActive = false;
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

void triggerColorLED(int color) {
  // Turn off both colors first
  digitalWrite(LED_COLOR1_PIN, LOW);
  digitalWrite(LED_COLOR2_PIN, LOW);
  
  // Turn on the selected color
  if (color == 1) {
    digitalWrite(LED_COLOR1_PIN, HIGH);  // Color 1 (e.g., Green for rain)
  } else if (color == 2) {
    digitalWrite(LED_COLOR2_PIN, HIGH);  // Color 2 (e.g., Red for touch)
  }
  
  colorLedActive = true;
  colorLedStartTime = millis();
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
    if (!impactLedActive) {
      triggerImpactLED();
    }
  }
}

void readAccelerometer() {
  sensors_event_t event; 
  accel.getEvent(&event);
  accelX = event.acceleration.x;
  accelY = event.acceleration.y;
  accelZ = event.acceleration.z;
}

void checkSoundSensor() {
  int soundValue = analogRead(SOUND_PIN);
  if (soundValue > SOUND_THRESHOLD && millis() - lastSoundTime > SOUND_COOLDOWN) {
    soundEvents++;
    soundDetected = true;
    lastSoundTime = millis();
    if (!soundLedActive) {
      triggerSoundLED();
    }
  }
}

void checkTouchSensor() {
  int touchValue = digitalRead(TOUCH_PIN);
  if (touchValue == HIGH && millis() - lastTouchTime > TOUCH_COOLDOWN) {
    touchEvents++;
    touchDetected = true;
    lastTouchTime = millis();
    // Trigger color LED for touch
    if (!colorLedActive) {
      triggerColorLED(2);  // Color 2 for touch
    }
  }
}

void checkTiltSensor() {
  int tiltValue = digitalRead(TILT_PIN);
  if (tiltValue == LOW && millis() - lastTiltTime > TILT_COOLDOWN) {
    tiltEvents++;
    tiltDetected = true;
    lastTiltTime = millis();
    if (!tiltLedActive) {
      triggerTiltLED();
    }
  }
}

void checkPirSensor() {
  int pirValue = digitalRead(PIR_PIN);
  if (pirValue == HIGH && millis() - lastPirTime > PIR_COOLDOWN) {
    pirEvents++;
    pirDetected = true;
    lastPirTime = millis();
  }
}

void checkRainSensor() {
  int rainValue = analogRead(RAIN_PIN);
  if (rainValue < RAIN_THRESHOLD && millis() - lastRainTime > RAIN_COOLDOWN) {
    rainEvents++;
    rainDetected = true;
    lastRainTime = millis();
    // Trigger color LED for rain
    if (!colorLedActive) {
      triggerColorLED(1);  // Color 1 for rain
    }
  }
}

void checkGasSensor() {
  int gasValue = analogRead(MQ2_PIN);
  if (gasValue > MQ2_THRESHOLD && millis() - lastGasTime > GAS_COOLDOWN) {
    gasEvents++;
    gasDetected = true;
    lastGasTime = millis();
  }
}

void checkFlameSensor() {
  int flameValue = analogRead(FLAME_PIN);
  if (flameValue < FLAME_THRESHOLD && millis() - lastFlameTime > FLAME_COOLDOWN) {
    flameEvents++;
    flameDetected = true;
    lastFlameTime = millis();
  }
}

void resetAllSensors() {
  confirmedImpacts = 0;
  soundEvents = 0;
  touchEvents = 0;
  tiltEvents = 0;
  pirEvents = 0;
  rainEvents = 0;
  gasEvents = 0;
  flameEvents = 0;
  impactDetected = false;
  soundDetected = false;
  touchDetected = false;
  tiltDetected = false;
  pirDetected = false;
  rainDetected = false;
  gasDetected = false;
  flameDetected = false;
  
  // Turn off all LEDs
  digitalWrite(LED_RED_PIN, LOW);
  digitalWrite(LED_GREEN_PIN, LOW);
  digitalWrite(LED_BLUE_PIN, LOW);
  digitalWrite(LED_COLOR1_PIN, LOW);
  digitalWrite(LED_COLOR2_PIN, LOW);
  soundLedActive = false;
  impactLedActive = false;
  tiltLedActive = false;
  colorLedActive = false;
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
  
  readAccelerometer(); // Read accelerometer data
  
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
  Serial.print(",");
  Serial.print(pirEvents);
  Serial.print(",");
  Serial.print(pirDetected ? "1" : "0");
  Serial.print(",");
  Serial.print(rainEvents);
  Serial.print(",");
  Serial.print(rainDetected ? "1" : "0");
  Serial.print(",");
  Serial.print(accelX);
  Serial.print(",");
  Serial.print(accelY);
  Serial.print(",");
  Serial.print(accelZ);
  Serial.print(",");
  Serial.print(gasEvents);
  Serial.print(",");
  Serial.print(gasDetected ? "1" : "0");
  Serial.print(",");
  Serial.print(flameEvents);
  Serial.print(",");
  Serial.print(flameDetected ? "1" : "0");
  Serial.println();
  
  impactDetected = false;
  soundDetected = false;
  touchDetected = false;
  tiltDetected = false;
  pirDetected = false;
  rainDetected = false;
  gasDetected = false;
  flameDetected = false;
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
  pinMode(PIR_PIN, INPUT);
  pinMode(RAIN_PIN, INPUT);
  pinMode(MQ2_PIN, INPUT);
  pinMode(FLAME_PIN, INPUT);
  
  // Initialize buzzer
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
  
  // Initialize LEDs
  setupLEDs();
  
  // Initialize accelerometer
  if(!accel.begin()) {
    Serial.println("Could not find ADXL345 accelerometer");
  } else {
    accel.setRange(ADXL345_RANGE_16_G);
    Serial.println("ADXL345 accelerometer initialized");
  }
  
  // Attach interrupt
  attachInterrupt(digitalPinToInterrupt(SHOCK_PIN), handleImpact, FALLING);
  
  Serial.println("System initialized - Mega Version with MQ2 Gas and Flame Sensors");
}

void loop() {
  // Handle buzzer timing
  handleBuzzer();
  
  // Handle LED timing
  handleLEDs();

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
  checkPirSensor();
  checkRainSensor();
  checkGasSensor();
  checkFlameSensor();
  
  // Send sensor data at regular intervals
  if (millis() - lastSensorReadTime > SENSOR_READ_INTERVAL) {
    sendSensorData();
    lastSensorReadTime = millis();
  }
}