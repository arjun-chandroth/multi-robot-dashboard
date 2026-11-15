# Multi-Robot Rover - try16

The rover sensor set expands with flame detection while retaining the browser dashboard and accelerometer data.

## Features
- Adds flame sensor state/count telemetry and a dashboard indicator.
- Retains gas, accelerometer, PIR/rain, touch/tilt, sound, and impact readings.
- Continues serial motor control, camera streaming, and host monitoring.

## Dependencies and hardware
Python 3 with Flask, Flask-SocketIO, OpenCV, psutil, and pyserial; No NumPy dependency is needed by this stage. Arduino AVR board and the modules identified in the firmware. No pinned Python dependency manifest is provided.

## Setup and run
Create a virtual environment, install the Python packages, configure the serial port and camera, upload the Arduino sketch, and start the dashboard.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install flask flask-socketio opencv-python psutil pyserial
python car_control.py
```

Build the Arduino sketch separately:

```bash
arduino-cli core install arduino:avr
arduino-cli lib install "DHT sensor library" "Adafruit Unified Sensor" "Adafruit ADXL345"
arduino-cli compile --fqbn arduino:avr:mega firmware/rover
arduino-cli upload -p <PORT> --fqbn arduino:avr:mega firmware/rover
```

## Changes from the previous available try
Adds a flame sensor and its threshold/event fields to firmware and the dashboard. The previous available stage in this history is try15.

## Notes
A hobby flame sensor is not a fire alarm or life-safety device.
