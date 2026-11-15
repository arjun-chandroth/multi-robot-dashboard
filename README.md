# Multi-Robot Rover - try8

A standalone joystick-to-serial experiment replaces the rover sensor sketch for this stage.

## Features
- Reads X/Y axes and a mode button from an analog joystick module.
- Maps axes to a signed range, applies a center deadzone, and transmits at about 20 Hz.
- Sends `JOY:x,y` packets and button-driven `MODE:` updates.

## Dependencies and hardware
Arduino AVR board, two-axis analog joystick module, and a momentary mode button.

## Setup and run
Install the board core/libraries, review pin assignments and hardware polarity, then compile/upload the sketch shown below.

```bash
arduino-cli core install arduino:avr
arduino-cli compile --fqbn arduino:avr:mega firmware/joystick
arduino-cli upload -p <PORT> --fqbn arduino:avr:mega firmware/joystick
```

## Changes from the previous available try
Switches from try7 rover sensor firmware to a focused joystick input test.

## Notes
This is an input protocol experiment, not a complete motor-control firmware.
