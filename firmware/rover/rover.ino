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

// Big Sound Sensor
#define SOUND_PIN A0
#define SOUND_THRESHOLD 100  // Adjust based on testing
unsigned long lastSoundTime = 0;
#define SOUND_COOLDOWN 1000  // 1 second cooldown
int soundEvents = 0;
bool soundDetected = false;

// Impact Sensor
#define SHOCK_PIN 3
#define IMPACT_WINDOW_MS 25
#define MIN_BOUNCES 5
#define COOLDOWN_MS 1500
#define DEBOUNCE_MS 2
volatile unsigned long firstTriggerTime = 0;
volatile unsigned long lastTriggerTime = 0;
volatile byte bounceCount = 0;
volatile int confirmedImpacts = 0;
bool impactDetected = false;
unsigned long lastImpactTime = 0;

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

void setup() {
  Serial.begin(115200);
  
  // Motor control
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  stopMotors();
  
  // Sensors
  dht.begin();
  pinMode(SOUND_PIN, INPUT);
  pinMode(SHOCK_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(SHOCK_PIN), handleImpact, FALLING);
}

void sendSensorData() {
  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();
  
  Serial.print("SENSORS:");
  Serial.print(isnan(temperature) ? "NaN" : String(temperature));
  Serial.print(",");
  Serial.print(isnan(humidity) ? "NaN" : String(humidity));
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
}

void backward() {
  digitalWrite(IN1, LOW); digitalWrite(IN2, HIGH);
  digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH);
}

void left() {
  digitalWrite(IN1, LOW); digitalWrite(IN2, HIGH);
  digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);
}

void right() {
  digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH);
}

void stopMotors() {
  digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW); digitalWrite(IN4, LOW);
}

void loop() {
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
    }
  }

  checkSoundSensor();
  
  static unsigned long lastUpdate = 0;
  if (millis() - lastUpdate > 2000) {
    sendSensorData();
    lastUpdate = millis();
  }
}