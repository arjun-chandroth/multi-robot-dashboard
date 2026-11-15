# Multi-Robot Rover - try7

The sound/impact firmware adds a retry path for unreliable DHT11 readings.

## Features
- Retains motor control, impact counting, and sound threshold events.
- Retries a failed temperature/humidity read once after a short delay.
- Reports sensor values and event states in a periodic serial frame.

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
Adds a one-retry DHT read helper and explicit handling for failed sensor values. The previous available stage in this history is try6.

## Notes
This source came from a locally named best-version folder; this history labels it sequentially as try7.
