# Multi-Robot Rover - try38

The next UI/backend revision adds an explicit AI-message path and reorganizes dashboard control events.

## Features
- Retains modular hardware, camera, ROS 2, monitoring, and AI components.
- Adds an AI-message event handler in the application layer.
- Reworks frontend control and recording event wiring.
- Updates dashboard visuals.

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
Adds AI-message routing and changes how control/recording events are wired between browser and server. The previous available stage in this history is try37.

## Notes
AI provider/service availability and credentials are environment-specific; never place API keys in source.
