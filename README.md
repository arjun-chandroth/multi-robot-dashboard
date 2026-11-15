# Multi-Robot Rover - try36

The monolithic dashboard is split into modules for routing, hardware, cameras, AI, ROS 2, monitoring, configuration, and utilities.

## Features
- Introduces focused hardware, camera, AI, ROS 2, system-monitor, and utility modules.
- Keeps Flask/Socket.IO routes and shared sensor data in the main app.
- Adds centralized rover configuration and an installer script.
- Retains camera, serial/gamepad controls, object detection, and telemetry.

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
Major architecture refactor from one large Python file into focused modules while preserving dashboard scope. The previous available stage in this history is try32.

## Notes
Review the installer before running it; configuration and hardware assumptions require local review.
