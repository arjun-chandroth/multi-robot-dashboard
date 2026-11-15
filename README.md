# Multi-Robot Rover - try43

System utility coverage expands to network interfaces, uptime, disk/process data, GPU/host checks, and formatting helpers.

## Features
- Adds network, disk/GPU, uptime, process-count, and camera-connectivity diagnostics.
- Retains the try42 modular dashboard and hardware features.
- Provides safe conversion and formatting helpers used by diagnostics.

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
The principal code change is a broader `utils.py` diagnostics toolkit. The previous available stage in this history is try42.

## Notes
System/GPU metrics depend on operating system and drivers; unsupported metrics are not necessarily hardware failures.
