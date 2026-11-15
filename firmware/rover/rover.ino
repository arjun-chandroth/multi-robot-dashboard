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
#define SOUND_THRESHOLD 100  // Adjust based on testing
unsigned long lastSoundTime = 0;
#define SOUND_COOLDOWN 1000  // 1 second cooldown
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

// Sensor timing
unsigned long lastSensorReadTime = 0;
#define SENSOR_READ_INTERVAL 2000

// Motor state
char currentMotorState = 'S';

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

void resetAllSensors() {
  confirmedImpacts = 0;
  soundEvents = 0;
  impactDetected = false;
  soundDetected = false;
}

bool readDHTData(float &temperature, float &humidity) {
  temperature = dht.readTemperature();
  humidity = dht.readHumidity();
  
  // Retry once if readings failed
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
  Serial.println();
  
  impactDetected = false;
  soundDetected = false;
}

// Motor control functions
void forward() {
  digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
  digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);
  currentMotorState = 'F';
}

void backward() {
  digitalWrite(IN1, LOW); digitalWrite(IN2, HIGH);
  digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH);
  currentMotorState = 'B';
}

void left() {
  digitalWrite(IN1, LOW); digitalWrite(IN2, HIGH);
  digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);
  currentMotorState = 'L';
}

void right() {
  digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH);
  currentMotorState = 'R';
}

void stopMotors() {
  digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW); digitalWrite(IN4, LOW);
  currentMotorState = 'S';
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
  attachInterrupt(digitalPinToInterrupt(SHOCK_PIN), handleImpact, FALLING);
  
  Serial.println("System initialized");
}

void loop() {
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
      default: break;
    }
  }

  // Check sound sensor
  checkSoundSensor();
  
  // Send sensor data at regular intervals
  if (millis() - lastSensorReadTime > SENSOR_READ_INTERVAL) {
    sendSensorData();
    lastSensorReadTime = millis();
  }
}