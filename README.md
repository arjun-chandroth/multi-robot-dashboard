# Multi-Robot Rover - try4

A compact Arduino sketch focuses on differential motor movement, DHT11 readings, and interrupt-based impact counting.

## Features
- Controls four motor-driver inputs for forward, reverse, left, right, and stop.
- Reads DHT11 temperature/humidity and emits a serial sensor frame.
- Counts shock events with interrupt, debounce, bounce-window, and cooldown logic.

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
Compared with try3, the sensor set is reduced to DHT11 and impact detection, with a different motor pin map.

## Notes
Review the pin map and motor wiring before applying power.
