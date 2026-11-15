# Multi-Robot Rover - try14

The sensor dashboard gains accelerometer measurements and a browser-side visualization.

## Features
- Adds ADXL345 X/Y/Z readings to rover telemetry.
- Adds an accelerometer plot alongside the sensor and camera panels.
- Retains serial motor commands, camera streaming, and host metrics.

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
Adds an ADXL345 accelerometer to firmware and exposes its axes in the dashboard. The previous available stage in this history is try13.

## Notes
Accelerometer axis orientation depends on board mounting.
