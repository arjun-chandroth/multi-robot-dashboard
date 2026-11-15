# Multi-Robot Rover - try11

Tilt detection is added, with separate buzzer and RGB-LED experiments retained alongside the main sketch.

## Features
- Main firmware tracks DHT11, impact, sound, touch, and tilt events.
- Includes standalone buzzer and RGB LED sketches under `firmware/examples/`.
- Retains motor control and sensor reset commands.

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
Adds tilt sensing and two independent sketches for buzzer and RGB indicator outputs. The previous available stage in this history is try10.

## Notes
Example sketches are independent Arduino programs and should be built separately.
