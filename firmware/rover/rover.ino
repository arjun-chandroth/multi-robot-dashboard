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

// Extreme impact detection settings
#define SHOCK_PIN 3
#define IMPACT_WINDOW_MS 30       // Time window to detect multiple bounces (ms)
#define MIN_BOUNCES 4             // Minimum bounces to confirm real impact
#define COOLDOWN_MS 1000          // Ignore new hits after detection (ms)
#define DEBOUNCE_MS 5             // Minimum time between interrupts (ms)

// Impact detection variables
volatile unsigned long firstTriggerTime = 0;
volatile unsigned long lastTriggerTime = 0;
volatile byte bounceCount = 0;
volatile int confirmedImpacts = 0;
bool impactDetected = false;
unsigned long lastImpactTime = 0;

void handleImpact() {
  unsigned long currentTime = millis();
  
  // Hardware debounce check
  if (currentTime - lastTriggerTime < DEBOUNCE_MS) return;
  
  // Check if we're in cooldown period
  if (currentTime - lastImpactTime < COOLDOWN_MS) return;
  
  // If first impact in new series
  if (currentTime - lastTriggerTime > IMPACT_WINDOW_MS) {
    firstTriggerTime = currentTime;
    bounceCount = 1;
  } 
  else {
    bounceCount++;
  }
  
  lastTriggerTime = currentTime;

  // Check if we got enough bounces in the time window
  if (bounceCount >= MIN_BOUNCES && 
      currentTime - firstTriggerTime <= IMPACT_WINDOW_MS) {
    confirmedImpacts++;
    impactDetected = true;
    lastImpactTime = currentTime;
    bounceCount = 0;
    Serial.print("!!!EXTREME IMPACT CONFIRMED!!! Total: ");
    Serial.println(confirmedImpacts);
  }
}

void resetImpactCount() {
  confirmedImpacts = 0;
  impactDetected = false;
  Serial.println("Impact counter reset");
}

void setup() {
  Serial.begin(115200);
  
  // Initialize motor pins
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  stopMotors();
  
  // Initialize DHT sensor
  dht.begin();
  
  // Configure shock sensor with hardware debouncing
  pinMode(SHOCK_PIN, INPUT_PULLUP);
  // Add 0.1μF capacitor between signal and ground
  attachInterrupt(digitalPinToInterrupt(SHOCK_PIN), handleImpact, FALLING);
}

void sendSensorData() {
  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();
  
  if (!isnan(humidity) && !isnan(temperature)) {
    Serial.print("SENSORS:");
    Serial.print(temperature);
    Serial.print(",");
    Serial.print(humidity);
    Serial.print(",");
    Serial.print(confirmedImpacts);
    Serial.print(",");
    Serial.print(impactDetected ? "1" : "0");
    Serial.println();
  } else {
    Serial.println("SENSORS:NaN,NaN,0,0");
  }
  impactDetected = false;
}

// Motor control functions (unchanged)
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
    Serial.print("Received: ");
    Serial.println(command);
    
    switch(command) {
      case 'F': forward(); break;
      case 'B': backward(); break;
      case 'L': left(); break;
      case 'R': right(); break;
      case 'S': stopMotors(); break;
      case 'X': resetImpactCount(); break;
      case 'D': sendSensorData(); break;
    }
  }
  
  // Regular sensor updates
  static unsigned long lastSensorUpdate = 0;
  if (millis() - lastSensorUpdate > 2000) {
    sendSensorData();
    lastSensorUpdate = millis();
  }
}