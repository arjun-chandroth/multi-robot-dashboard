# Multi-Robot Rover - try10

The rover firmware resumes with DHT11, sound, and impact sensing and adds touch-event detection.

## Features
- Controls the motor driver and periodically reports sensor state.
- Counts impact, sound, and touch events with per-sensor cooldowns.
- Provides reset-all-sensors behavior and retries unsuccessful DHT11 readings.

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
Returns to rover motor/sensor firmware and adds a touch sensor to the earlier combination. The previous available stage in this history is try8.

## Notes
The try8 joystick sketch is not included in this stage snapshot.
