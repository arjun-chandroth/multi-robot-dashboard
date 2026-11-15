#include <TinyGPS++.h>             // TinyGPS++ parsing library
#include <DHT.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_ADXL345_U.h>

// Motor control pins for BTS7960 (IBT-2) drivers
// Left motor (M1)
#define M1_RPWM 22  // Right PWM (forward)
#define M1_LPWM 24  // Left PWM (reverse)
#define M1_EN 23    // Enable pin (optional, can be tied HIGH)

// Right motor (M2)
#define M2_RPWM 26  // Right PWM (forward)
#define M2_LPWM 28  // Left PWM (reverse)
#define M2_EN 27    // Enable pin (optional, can be tied HIGH)

// DHT11
#define DHTPIN 2
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

// Sound sensor
// FIX: raised threshold to 1000+ to effectively disable (not connected)
#define SOUND_PIN A0
#define SOUND_THRESHOLD 1100
#define SOUND_REARM_THRESHOLD 1000
unsigned long lastSoundTime = 0;
#define SOUND_COOLDOWN 1000
int soundEvents = 0;
bool soundDetected = false;
unsigned long soundLedStartTime = 0;
bool soundLedActive = false;
bool soundArmed = false;

// Impact sensor (disabled - not connected)
#define SHOCK_PIN 3
#define IMPACT_WINDOW_MS 50
#define MIN_BOUNCES 5
#define COOLDOWN_MS 5000
#define DEBOUNCE_MS 10
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

// RGB LED
#define LED_RED_PIN 9
#define LED_GREEN_PIN 10
#define LED_BLUE_PIN 11
unsigned long tiltLedStartTime = 0;
bool tiltLedActive = false;

// Touch
#define TOUCH_PIN 4
#define TOUCH_ACTIVE_HIGH true
bool touchDetected = false;
int touchEvents = 0;
unsigned long lastTouchTime = 0;
#define TOUCH_COOLDOWN 500
bool touchSeenInactive = false;

// Tilt (disabled - not connected)
#define TILT_PIN 5
bool tiltDetected = false;
int tiltEvents = 0;
unsigned long lastTiltTime = 0;
#define TILT_COOLDOWN 5000

// PIR
#define PIR_PIN 6
bool pirDetected = false;
int pirEvents = 0;
unsigned long lastPirTime = 0;
#define PIR_COOLDOWN 2000
// Track PIR state transitions so detection works for both active-high and active-low modules.
int lastPirState = LOW;

// Radar (disabled - not connected)
#define RADAR_PIN 7
bool radarDetected = false;
int radarEvents = 0;
unsigned long lastRadarTime = 0;
#define RADAR_COOLDOWN 2000
#define RADAR_DISABLED true

// Rain sensor (disabled - not connected)
// FIX: raised threshold to 1024+ to effectively disable
#define RAIN_PIN A1
#define RAIN_THRESHOLD 1024
bool rainDetected = false;
int rainEvents = 0;
unsigned long lastRainTime = 0;
#define RAIN_COOLDOWN 2000

// Gas (MQ2) (disabled - not connected)
// FIX: raised threshold to 1000+ to effectively disable
#define MQ2_PIN A2
#define MQ2_THRESHOLD 1000
#define MQ2_REARM_THRESHOLD 900
bool gasDetected = false;
int gasEvents = 0;
unsigned long lastGasTime = 0;
#define GAS_COOLDOWN 2000
bool gasArmed = false;

// Flame (connected - keep as is)
#define FLAME_PIN A3
#define FLAME_THRESHOLD 30
bool flameDetected = false;
int flameEvents = 0;
unsigned long lastFlameTime = 0;
#define FLAME_COOLDOWN 2000

// Accelerometer
// FIX: track init success so readAccelerometer() returns 0,0,0 when sensor absent
Adafruit_ADXL345_Unified accel = Adafruit_ADXL345_Unified(12345);
float accelX = 0, accelY = 0, accelZ = 0;
bool accelInitialized = false;

// 2‑color LED
#define LED_COLOR1_PIN 30
#define LED_COLOR2_PIN 31
unsigned long colorLedStartTime = 0;
bool colorLedActive = false;
#define COLOR_LED_DURATION 2000

// Timing
unsigned long lastSensorReadTime = 0;
#define SENSOR_READ_INTERVAL 2000

// Motor state
char currentMotorState = 'S';
bool obstacleAvoidanceMode = false;
bool executingTimedCommand = false;
unsigned long commandEndTime = 0;
String commandQueue = "";
bool processingQueue = false;

// GPS objects
TinyGPSPlus gps;

// ——————————————————————————————————
// Helper functions for LEDs & buzzer
// ——————————————————————————————————
void setupLEDs() {
  pinMode(LED_RED_PIN, OUTPUT);
  pinMode(LED_GREEN_PIN, OUTPUT);
  pinMode(LED_BLUE_PIN, OUTPUT);
  digitalWrite(LED_RED_PIN, LOW);
  digitalWrite(LED_GREEN_PIN, LOW);
  digitalWrite(LED_BLUE_PIN, LOW);
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
  digitalWrite(LED_COLOR1_PIN, LOW);
  digitalWrite(LED_COLOR2_PIN, LOW);
  if (color == 1) digitalWrite(LED_COLOR1_PIN, HIGH);
  if (color == 2) digitalWrite(LED_COLOR2_PIN, HIGH);
  colorLedActive = true;
  colorLedStartTime = millis();
}

// Impact ISR
void handleImpact() {
  unsigned long now = millis();
  if (now - lastTriggerTime < DEBOUNCE_MS) return;
  if (now - lastImpactTime < COOLDOWN_MS) return;
  if (now - lastTriggerTime > IMPACT_WINDOW_MS) {
    firstTriggerTime = now;
    bounceCount = 1;
  } else {
    bounceCount++;
  }
  lastTriggerTime = now;
  if (bounceCount >= MIN_BOUNCES && now - firstTriggerTime <= IMPACT_WINDOW_MS) {
    confirmedImpacts++;
    impactDetected = true;
    lastImpactTime = now;
    bounceCount = 0;
    if (!buzzerActive) triggerBuzzer();
    if (!impactLedActive) triggerImpactLED();
  }
}

// FIX: guard against uninitialized ADXL345 — returns 0,0,0 when sensor absent
void readAccelerometer() {
  if (!accelInitialized) {
    accelX = accelY = accelZ = 0;
    return;
  }
  sensors_event_t evt;
  accel.getEvent(&evt);
  accelX = evt.acceleration.x;
  accelY = evt.acceleration.y;
  accelZ = evt.acceleration.z;
}

// ——————————————————————————————————
// Sensor check routines
// ——————————————————————————————————
void checkSoundSensor() {
  // Edge-trigger with hysteresis: only count when rising through high threshold.
  int highHits = 0;
  int lowHits = 0;
  for (int i = 0; i < 5; i++) {
    int v = analogRead(SOUND_PIN);
    if (v > SOUND_THRESHOLD) highHits++;
    if (v < SOUND_REARM_THRESHOLD) lowHits++;
    delayMicroseconds(200);
  }

  if (lowHits >= 4) {
    soundArmed = true;
  }

  if (soundArmed && highHits >= 4 && millis() - lastSoundTime > SOUND_COOLDOWN) {
    soundEvents++;
    soundDetected = true;
    lastSoundTime = millis();
    soundArmed = false;
    if (!soundLedActive) triggerSoundLED();
  }
}

void checkTouchSensor() {
  bool isActive = TOUCH_ACTIVE_HIGH ? (digitalRead(TOUCH_PIN) == HIGH) : (digitalRead(TOUCH_PIN) == LOW);

  if (!isActive) {
    touchSeenInactive = true;
  }

  // Edge-trigger touch: only count inactive->active transitions.
  // This blocks continuous false counts when the line is stuck active.
  if (isActive && touchSeenInactive && millis() - lastTouchTime > TOUCH_COOLDOWN) {
    touchSeenInactive = false;
    touchEvents++;
    touchDetected = true;
    lastTouchTime = millis();
    if (!colorLedActive) triggerColorLED(2);
  }
}

void checkTiltSensor() {
  if (digitalRead(TILT_PIN) == LOW && millis() - lastTiltTime > TILT_COOLDOWN) {
    tiltEvents++;
    tiltDetected = true;
    lastTiltTime = millis();
    if (!tiltLedActive) triggerTiltLED();
  }
}

// FIX: PIR requires LOW->HIGH transition before counting motion.
// Count only stable transitions (either edge) so connected PIR modules detect
// motion regardless of polarity, while a stuck level does not spam events.
void checkPirSensor() {
  int s1 = digitalRead(PIR_PIN);
  delayMicroseconds(200);
  int s2 = digitalRead(PIR_PIN);
  if (s1 != s2) {
    return; // reject very short glitches
  }

  int state = s1;
  if (state != lastPirState && millis() - lastPirTime > PIR_COOLDOWN) {
    pirEvents++;
    pirDetected = true;
    lastPirTime = millis();
  }
  lastPirState = state;
}

void checkRadarSensor() {
  // Radar disabled - not connected
  if (false && digitalRead(RADAR_PIN) == HIGH && millis() - lastRadarTime > RADAR_COOLDOWN) {
    radarEvents++;
    radarDetected = true;
    lastRadarTime = millis();
  }
}

void checkRainSensor() {
  // Rain sensor disabled - not connected
  if (false && analogRead(RAIN_PIN) < RAIN_THRESHOLD && millis() - lastRainTime > RAIN_COOLDOWN) {
    rainEvents++;
    rainDetected = true;
    lastRainTime = millis();
    if (!colorLedActive) triggerColorLED(1);
  }
}

void checkGasSensor() {
  // Edge-trigger with hysteresis: only count when rising through high threshold.
  int highHits = 0;
  int lowHits = 0;
  for (int i = 0; i < 5; i++) {
    int v = analogRead(MQ2_PIN);
    if (v > MQ2_THRESHOLD) highHits++;
    if (v < MQ2_REARM_THRESHOLD) lowHits++;
    delayMicroseconds(200);
  }

  if (lowHits >= 4) {
    gasArmed = true;
  }

  if (gasArmed && highHits >= 4 && millis() - lastGasTime > GAS_COOLDOWN) {
    gasEvents++;
    gasDetected = true;
    lastGasTime = millis();
    gasArmed = false;
  }
}

void checkFlameSensor() {
  if (analogRead(FLAME_PIN) < FLAME_THRESHOLD && millis() - lastFlameTime > FLAME_COOLDOWN) {
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
  radarEvents = 0;
  rainEvents = 0;
  gasEvents = 0;
  flameEvents = 0;
  impactDetected = soundDetected = touchDetected = tiltDetected =
    pirDetected = radarDetected = rainDetected = gasDetected = flameDetected = false;
  lastPirState = digitalRead(PIR_PIN);
  touchSeenInactive = false;
  soundArmed = false;
  gasArmed = false;
  digitalWrite(LED_RED_PIN, LOW);
  digitalWrite(LED_GREEN_PIN, LOW);
  digitalWrite(LED_BLUE_PIN, LOW);
  digitalWrite(LED_COLOR1_PIN, LOW);
  digitalWrite(LED_COLOR2_PIN, LOW);
  soundLedActive = impactLedActive = tiltLedActive = colorLedActive = false;
}

// ——————————————————————————————————
// Read DHT
// ——————————————————————————————————
bool readDHTData(float &T, float &H) {
  T = dht.readTemperature();
  H = dht.readHumidity();
  // DHT11 not connected - skip retry
  return !isnan(T) && !isnan(H);
}

// ——————————————————————————————————
// Send everything over Serial USB
// ——————————————————————————————————
void sendSensorData() {
  float T, H;
  bool ok = readDHTData(T, H);
  readAccelerometer();
  Serial.print("SENSORS:");
  Serial.print(ok ? String(T) : "NaN"); Serial.print(",");
  Serial.print(ok ? String(H) : "NaN"); Serial.print(",");
  Serial.print(confirmedImpacts); Serial.print(",");
  Serial.print(impactDetected ? 1 : 0); Serial.print(",");
  Serial.print(soundEvents); Serial.print(",");
  Serial.print(soundDetected ? 1 : 0); Serial.print(",");
  Serial.print(touchEvents); Serial.print(",");
  Serial.print(touchDetected ? 1 : 0); Serial.print(",");
  Serial.print(tiltEvents); Serial.print(",");
  Serial.print(tiltDetected ? 1 : 0); Serial.print(",");
  Serial.print(pirEvents); Serial.print(",");
  Serial.print(pirDetected ? 1 : 0); Serial.print(",");
  Serial.print(rainEvents); Serial.print(",");
  Serial.print(rainDetected ? 1 : 0); Serial.print(",");
  Serial.print(accelX); Serial.print(",");
  Serial.print(accelY); Serial.print(",");
  Serial.print(accelZ); Serial.print(",");
  Serial.print(gasEvents); Serial.print(",");
  Serial.print(gasDetected ? 1 : 0); Serial.print(",");
  Serial.print(flameEvents); Serial.print(",");
  Serial.print(flameDetected ? 1 : 0); Serial.print(",");
  Serial.print(radarEvents); Serial.print(",");
  Serial.print(radarDetected ? 1 : 0); Serial.print(",");
  Serial.print(obstacleAvoidanceMode ? 1 : 0);
  Serial.println();
  impactDetected = soundDetected = touchDetected = tiltDetected =
    pirDetected = radarDetected = rainDetected = gasDetected = flameDetected = false;
}

// ——————————————————————————————————
// Motor control (updated for BTS7960)
// ——————————————————————————————————
void forward() {
  // Both motors forward
  digitalWrite(M1_RPWM, HIGH); digitalWrite(M1_LPWM, LOW);
  digitalWrite(M2_RPWM, HIGH); digitalWrite(M2_LPWM, LOW);
  currentMotorState = 'F'; 
  Serial.println("Moving Forward");
}

void backward() {
  // Both motors backward
  digitalWrite(M1_RPWM, LOW); digitalWrite(M1_LPWM, HIGH);
  digitalWrite(M2_RPWM, LOW); digitalWrite(M2_LPWM, HIGH);
  currentMotorState = 'B'; 
  Serial.println("Moving Backward");
}

void left() {
  // Right motor forward, left motor backward
  digitalWrite(M1_RPWM, LOW); digitalWrite(M1_LPWM, HIGH);
  digitalWrite(M2_RPWM, HIGH); digitalWrite(M2_LPWM, LOW);
  currentMotorState = 'L'; 
  Serial.println("Turning Left");
}

void right() {
  // Left motor forward, right motor backward
  digitalWrite(M1_RPWM, HIGH); digitalWrite(M1_LPWM, LOW);
  digitalWrite(M2_RPWM, LOW); digitalWrite(M2_LPWM, HIGH);
  currentMotorState = 'R'; 
  Serial.println("Turning Right");
}

void stopMotors() {
  // Both motors stop
  digitalWrite(M1_RPWM, LOW); digitalWrite(M1_LPWM, LOW);
  digitalWrite(M2_RPWM, LOW); digitalWrite(M2_LPWM, LOW);
  currentMotorState = 'S'; 
  Serial.println("Stopped");
}

// ——————————————————————————————————
// Timed Command Execution (FIXED)
// ——————————————————————————————————
void executeTimedCommand(char command, int duration) {
  Serial.print("Executing timed command: ");
  Serial.print(command);
  Serial.print(" for ");
  Serial.print(duration);
  Serial.println("ms");
  
  switch(command) {
    case 'F': forward(); break;
    case 'B': backward(); break;
    case 'L': left(); break;
    case 'R': right(); break;
    case 'S': stopMotors(); break;
  }
  
  if (command != 'S') {
    executingTimedCommand = true;
    commandEndTime = millis() + duration;
  } else {
    executingTimedCommand = false;
  }
}

void handleTimedCommands() {
  if (executingTimedCommand && millis() >= commandEndTime) {
    stopMotors();
    executingTimedCommand = false;
    Serial.println("Timed command completed");
  }
}

// ——————————————————————————————————
// Command Parser for AI Commands (FIXED)
// ——————————————————————————————————
void processCommandQueue() {
  if (commandQueue.length() == 0 || processingQueue) return;
  
  processingQueue = true;
  Serial.print("Processing command queue: ");
  Serial.println(commandQueue);
  
  int startIndex = 0;
  for (int i = 0; i <= commandQueue.length(); i++) {
    if (i == commandQueue.length() || commandQueue[i] == ',') {
      String cmd = commandQueue.substring(startIndex, i);
      startIndex = i + 1;
      
      if (cmd.length() > 0) {
        // Parse command and duration
        char dir = cmd[0];
        int duration = 0;
        
        if (cmd.length() > 1) {
          duration = cmd.substring(1).toInt();
        }
        
        // Set default durations if not specified
        if (duration == 0) {
          if (dir == 'F' || dir == 'B') duration = 500;
          else if (dir == 'L' || dir == 'R') duration = 300;
        }
        
        // Validate and execute command
        if (dir == 'F' || dir == 'B' || dir == 'L' || dir == 'R' || dir == 'S') {
          executeTimedCommand(dir, duration);
          
          // Wait for this command to complete
          while (executingTimedCommand) {
            handleTimedCommands();
            delay(50); // Small delay to prevent blocking
          }
          delay(200); // Pause between commands
        }
      }
    }
  }
  
  commandQueue = "";
  processingQueue = false;
  Serial.println("Command queue processing completed");
}

void parseAICommand(String input) {
  input.trim();
  Serial.print("Received AI command: ");
  Serial.println(input);
  
  // Handle single character commands (legacy support)
  if (input.length() == 1) {
    char c = input[0];
    switch (c) {
      case 'F': executeTimedCommand('F', 500); break;
      case 'B': executeTimedCommand('B', 500); break;
      case 'L': executeTimedCommand('L', 300); break;
      case 'R': executeTimedCommand('R', 300); break;
      case 'S': stopMotors(); break;
      case 'X': resetAllSensors(); break;
      case 'D': sendSensorData(); break;
      case 'O':
        obstacleAvoidanceMode = !obstacleAvoidanceMode;
        Serial.println(obstacleAvoidanceMode ? "Obstacle mode ON" : "Obstacle mode OFF");
        break;
      default:
        Serial.print("Unknown single char cmd: ");
        Serial.println(c);
    }
    return;
  }
  
  // Queue the multi-command for processing
  commandQueue = input;
}

// ——————————————————————————————————
// Arduino setup
// ——————————————————————————————————
void setup() {
  Serial.begin(115200);
  Serial1.begin(9600);                // GPS on Serial1
  while (!Serial) {}

  // Motors - BTS7960 setup
  pinMode(M1_RPWM, OUTPUT); pinMode(M1_LPWM, OUTPUT);
  pinMode(M2_RPWM, OUTPUT); pinMode(M2_LPWM, OUTPUT);
  // Enable pins (optional - can be permanently enabled by connecting to VCC)
  pinMode(M1_EN, OUTPUT); digitalWrite(M1_EN, HIGH);
  pinMode(M2_EN, OUTPUT); digitalWrite(M2_EN, HIGH);
  stopMotors();

  // Sensors
  dht.begin();
  pinMode(SOUND_PIN, INPUT);
  pinMode(SHOCK_PIN, INPUT_PULLUP);
  pinMode(TOUCH_PIN, INPUT);
  pinMode(TILT_PIN, INPUT_PULLUP);
  // Use pull-up so PIR line is never floating and open-collector outputs can be read.
  pinMode(PIR_PIN, INPUT_PULLUP);
  pinMode(RADAR_PIN, INPUT);
  // FIX: INPUT_PULLUP on A1/A3 — pulls floating pin to ~1023 (dry/no-flame),
  // preventing false triggers. Real sensor modules override the weak pull-up.
  pinMode(RAIN_PIN, INPUT_PULLUP);
  pinMode(MQ2_PIN, INPUT);
  pinMode(FLAME_PIN, INPUT_PULLUP);

  // Initialize arming state from current baseline so lines stuck high at boot do not auto-trigger.
  lastPirState = digitalRead(PIR_PIN);
  touchSeenInactive = !(TOUCH_ACTIVE_HIGH ? (digitalRead(TOUCH_PIN) == HIGH) : (digitalRead(TOUCH_PIN) == LOW));
  soundArmed = analogRead(SOUND_PIN) < SOUND_REARM_THRESHOLD;
  gasArmed = analogRead(MQ2_PIN) < MQ2_REARM_THRESHOLD;

  // Buzzer/LEDs
  pinMode(BUZZER_PIN, OUTPUT); digitalWrite(BUZZER_PIN, LOW);
  setupLEDs();

  // Accelerometer
  // FIX: only set accelInitialized=true on successful init
  if (!accel.begin()) {
    Serial.println("Could not find ADXL345 accelerometer — accel will report 0,0,0");
  } else {
    accel.setRange(ADXL345_RANGE_16_G);
    accelInitialized = true;
    Serial.println("ADXL345 initialized");
  }
  attachInterrupt(digitalPinToInterrupt(SHOCK_PIN), handleImpact, FALLING);

  Serial.println("System initialized with BTS7960 motor drivers and FIXED AI command support!");
  Serial.println("Supported commands:");
  Serial.println("  Single: F, B, L, R, S, X, D, O");
  Serial.println("  Timed: F1000, L500,R500, B1000,S, etc.");
}

// ——————————————————————————————————
// Main loop (FIXED)
// ——————————————————————————————————
void loop() {
  // 1) GPS parsing & printing
  while (Serial1.available()) {
    gps.encode(Serial1.read());
  }
  if (gps.location.isUpdated()) {
    double lat = gps.location.lat();
    double lon = gps.location.lng();
    Serial.print("GPS:"); Serial.print(lat, 6); Serial.print(","); Serial.println(lon, 6);
  }

  // 2) handle timing for buzzer, LEDs, and timed commands
  handleBuzzer();
  handleLEDs();
  handleTimedCommands();

  // 3) Process command queue (non-blocking)
  if (commandQueue.length() > 0 && !processingQueue) {
    processCommandQueue();
  }

  // 4) read commands from USB (AI commands)
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    parseAICommand(input);
  }

  // 5) sample all sensors
  checkSoundSensor();
  checkTouchSensor();
  checkTiltSensor();
  checkPirSensor();
  checkRadarSensor();
  checkRainSensor();
  checkGasSensor();
  checkFlameSensor();

  // 6) periodic send
  if (millis() - lastSensorReadTime > SENSOR_READ_INTERVAL) {
    sendSensorData();
    lastSensorReadTime = millis();
  }
}
