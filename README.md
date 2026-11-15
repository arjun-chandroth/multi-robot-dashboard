# Multi-Robot Rover - try6

The rover adds sound-event sensing to the DHT11 and impact-counter baseline.

## Features
- Reads an analog sound sensor and counts threshold events with a cooldown.
- Combines sound and impact flags/counts with DHT11 telemetry.
- Retains motor direction controls and serial sensor reset behavior.

## Dependencies and hardware
Arduino AVR board and the modules listed in the sketch pin map. Install DHT Sensor Library.

## Setup and run
Install the board core/libraries, review pin assignments and hardware polarity, then compile/upload the sketch shown below.

```bash
arduino-cli core install arduino:avr
arduino-cli lib install "DHT sensor library"
arduino-cli compile --fqbn arduino:avr:mega firmware/rover
arduino-cli upload -p <PORT> --fqbn arduino:avr:mega firmware/rover
```

## Changes from the previous available try
Adds sound threshold detection and sound fields to the serial telemetry frame. The previous available stage in this history is try5.

## Notes
Tune the sound threshold and cooldown to the sensor and environment.
