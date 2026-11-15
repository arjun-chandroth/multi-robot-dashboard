# Multi-Robot Rover - try12

The project grows from standalone firmware into a Raspberry Pi/Flask control prototype with an IR-capable Arduino sketch.

## Features
- Adds Flask/Socket.IO dashboard routes for serial sensor data, motor commands, camera streaming, and host status.
- The main Arduino sketch includes IR remote control, DHT11, impact, sound, touch, and tilt paths.
- Includes exploratory firmware sketches and a dashboard template.
- Supports camera and sensor-log/recording routes.

## Dependencies and hardware
Python 3 with Flask, Flask-SocketIO, OpenCV, psutil, and pyserial; This snapshot also requires NumPy. Arduino AVR board and the modules identified in the firmware. No pinned Python dependency manifest is provided.

## Setup and run
Create a virtual environment, install the Python packages, configure the serial port and camera, upload the Arduino sketch, and start the dashboard.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install flask flask-socketio opencv-python psutil pyserial numpy
python car_control.py
```

Build the Arduino sketch separately:

```bash
arduino-cli core install arduino:avr
arduino-cli lib install "DHT sensor library" IRremote
arduino-cli compile --fqbn arduino:avr:mega firmware/rover
arduino-cli upload -p <PORT> --fqbn arduino:avr:mega firmware/rover
```

## Changes from the previous available try
Introduces the Python dashboard and camera/server code, plus an IR remote control path in the firmware. The previous available stage in this history is try11.

## Notes
The server expects camera/serial hardware; run it only on a trusted local network. Multiple alternate firmware sketches are preserved separately.
