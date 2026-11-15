# Multi-Robot Rover - try3

The first locally available rover firmware snapshot combines a Mega-class motor controller, serial commands, and a broad onboard sensor set.

## Features
- Two-motor drive with forward/reverse/turn/stop and serial telemetry/reset/obstacle-mode commands at 115200 baud.
- Reports DHT11, impact, sound, touch, tilt, PIR, radar, rain, gas, and flame sensor states.
- Reads ADXL345 accelerometer axes and drives indicator LEDs for selected events.
- Includes a separate GPS test sketch.

## Dependencies and hardware
Arduino Mega 2560-class board, motor driver, DHT11, ADXL345, and the listed digital/analog sensors. Install DHT Sensor Library, Adafruit Unified Sensor, and Adafruit ADXL345.

## Setup and run
Install the board core/libraries, review pin assignments and hardware polarity, then compile/upload the sketch shown below.

```bash
arduino-cli core install arduino:avr
arduino-cli lib install "DHT sensor library" "Adafruit Unified Sensor" "Adafruit ADXL345"
arduino-cli compile --fqbn arduino:avr:mega firmware/rover
arduino-cli upload -p <PORT> --fqbn arduino:avr:mega firmware/rover
```

## Changes from the previous available try
Earliest available snapshot; no try1 or try2 source was found, so neither is fabricated.

## Notes
Sensor thresholds and active levels are hardware-dependent. The GPS sketch is independent of the main rover firmware.
