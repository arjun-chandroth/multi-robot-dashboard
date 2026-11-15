# Multi-Robot Rover - try37

The modular backend is retained while the dashboard template, styles, and browser behavior are redesigned.

## Features
- Keeps the try36 backend modules and hardware integration.
- Updates dashboard page, styling, and JavaScript interactions.
- Retains camera, sensor gauges, control modes, recording, AI, and ROS 2 features.

## Dependencies and hardware
Python 3 with Flask, Flask-SocketIO, OpenCV, NumPy, psutil, pyserial, pyttsx3, and Ultralytics. ROS 2 `rclpy`/`sensor_msgs` are system dependencies. A local YOLO weights file and hardware are needed for those features.

## Setup and run
Install the runtime dependencies, review rover configuration and hardware settings, source ROS 2, and start the application.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install flask flask-socketio opencv-python numpy psutil pyserial pyttsx3 ultralytics
# Install/source a compatible ROS 2 distribution with rclpy and sensor_msgs.
python app.py
```

## Changes from the previous available try
Primarily a UI redesign; the Python module set remains the same. The previous available stage in this history is try36.

## Notes
No physical-hardware validation is implied by the updated browser interface.
