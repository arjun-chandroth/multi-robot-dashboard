# Multi-Robot Rover - try13

The Flask dashboard continues while the Arduino sensor set is revised to include PIR motion and rain detection.

## Features
- Retains the serial-driven rover and web dashboard with camera/system status.
- Adds PIR and rain readings to the main firmware telemetry.
- Keeps periodic DHT, impact, sound, touch, and tilt reporting.

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
arduino-cli lib install "DHT sensor library"
arduino-cli compile --fqbn arduino:avr:mega firmware/rover
arduino-cli upload -p <PORT> --fqbn arduino:avr:mega firmware/rover
```

## Changes from the previous available try
Adds PIR and rain inputs; the previous IR-remote path is absent from the primary sketch. The previous available stage in this history is try12.

## Notes
Review sensor polarity and configured pin numbers before powering the motor driver.
