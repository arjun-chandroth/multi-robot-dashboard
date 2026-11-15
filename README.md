# Multi-Robot Rover - try40

The dashboard restores explicit joystick/control and recording handlers and adds an Arduino diagnostic route.

## Features
- Adds server handlers for joystick packets and recording start/pause/stop events.
- Adds an Arduino test endpoint for checking the serial link.
- Retains modular camera, AI, ROS 2, monitoring, and sensor modules.
- Updates the dashboard template for revised controls.

## Dependencies and hardware
Python 3 with Flask, Flask-SocketIO, OpenCV, NumPy, psutil, pyserial, pyttsx3, requests, and Ultralytics. ROS 2 `rclpy`/`sensor_msgs` are system dependencies. A local YOLO weights file and hardware are needed for those features.

## Setup and run
Install the runtime dependencies, review rover configuration and hardware settings, source ROS 2, and start the application.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install flask flask-socketio opencv-python numpy psutil pyserial pyttsx3 requests ultralytics
# Install/source a compatible ROS 2 distribution with rclpy and sensor_msgs.
python app.py
```

## Changes from the previous available try
Restores explicit control and recording event handlers and adds an Arduino diagnostic action. The previous available stage in this history is try39.

## Notes
Treat test/control endpoints as hardware actions; do not expose the dashboard to untrusted networks.
