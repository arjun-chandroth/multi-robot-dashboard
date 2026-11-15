# Multi-Robot Rover - try39

This stage refines the AI controller and dashboard interactions within the modular application.

## Features
- Retains event-driven server and hardware/camera integration.
- Updates AI controller behavior and related dashboard JavaScript/styles.
- Keeps sensor telemetry, camera recording, control modes, and ROS 2 integration.
- Maintains centralized rover configuration.

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
Further revises AI and frontend behavior without changing the overall module boundaries. The previous available stage in this history is try38.

## Notes
Environment-based AI setup arrives in try44; earlier configuration remains code/config driven.
