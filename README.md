# Multi-Robot Rover - try15

This stage extends the sensor telemetry with an MQ-2 gas sensor.

## Features
- Adds gas-event counting and threshold status to firmware telemetry.
- Displays gas readings/status in the dashboard.
- Retains accelerometer, camera, serial motor commands, and host metrics.

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
Adds MQ-2 gas detection and its dashboard fields. The previous available stage in this history is try14.

## Notes
MQ-2 readings require warm-up and calibration; the threshold is not a certified safety limit.
