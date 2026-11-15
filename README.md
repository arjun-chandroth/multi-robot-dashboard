# Multi-Robot Rover - try17

The latest early dashboard stage adds radar/proximity event reporting to rover telemetry.

## Features
- Adds radar sensor event counting/status to firmware and dashboard.
- Retains flame/gas, accelerometer, PIR/rain, and earlier event sensors.
- Provides Flask/Socket.IO controls, camera streaming, serial telemetry, and host metrics.

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
Adds radar/proximity detection and displays the new event fields. The previous available stage in this history is try16.

## Notes
This is the last available early dashboard stage before the later dual-camera/ROS 2 experiments.
