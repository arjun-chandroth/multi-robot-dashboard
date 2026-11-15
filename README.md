# Multi-Robot Rover - try26

The dashboard adds voice-assistant and network-address experiments to its camera, telemetry, and ROS 2 foundation.

## Features
- Adds voice-control loop and command/response helpers.
- Adds private/public IP and severity helpers for dashboard reporting.
- Retains dual-camera streams/recording, object detection, joystick controls, and ROS 2 LiDAR.
- Includes legacy controller variants beside the active entry point.

## Dependencies and hardware
Python 3 with Flask, Flask-SocketIO, OpenCV, NumPy, psutil, pyserial, pyttsx3, Ultralytics, and Supervision. ROS 2 `rclpy`/`sensor_msgs` must be installed from a compatible ROS distribution. Provide YOLO weights locally; they are not stored here.

## Setup and run
Install Python and ROS 2 dependencies, configure camera/serial/audio devices, provide model weights, and start the active script.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install flask flask-socketio opencv-python numpy psutil pyserial pyttsx3 ultralytics supervision
# Install/source a compatible ROS 2 distribution with rclpy and sensor_msgs.

python car_latest.py
```

## Changes from the previous available try
Adds voice-assistant interaction and network/severity reporting while retaining the prior dashboard features. The previous available stage in this history is try25.

## Notes
Voice output needs a host speech engine; the local YOLO weights file is not tracked.
