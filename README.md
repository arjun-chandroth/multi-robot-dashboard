# Multi-Robot Rover - try5

This snapshot preserves the compact DHT11, impact-counter, and motor-control sketch.

## Features
- Retains four-direction motor control, DHT11 telemetry, and interrupt-driven impact counting.
- Keeps the same pin assignments and serial protocol as try4.

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
The selected try5 sketch is byte-for-byte identical to try4; no firmware behavior change is detectable. This commit preserves the available stage and gives it its own documentation.

## Notes
No additional behavior is inferred beyond the source.
