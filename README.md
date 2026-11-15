# Multi-Robot Rover - try42

This iteration strengthens joystick connection/status reporting and control-mode handling while removing duplicate controller copies.

## Features
- Adds joystick connection handling and a control-mode query route.
- Expands hardware-controller connection, camera, sensor, joystick, and status helpers.
- Updates camera/joystick settings in central configuration.
- Removes duplicate controller source copies while preserving active modules.

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
Adds joystick connection/status and control-mode APIs and consolidates duplicate hardware/camera modules. The previous available stage in this history is try40.

## Notes
Confirm joystick mappings and safe-stop behavior on the target host before operating motors.
