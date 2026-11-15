# Multi-Robot Rover - try32

The dashboard removes simulation helpers and keeps the browser gamepad and live telemetry workflow.

## Features
- Retains dashboard, gamepad controls, camera streams/recording, and sensor monitoring.
- Retains ROS 2/LiDAR hooks and location-receive endpoint.
- Removes GPS and movement simulation helpers from the Python app.

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
Drops local movement/GPS simulation helpers; location updates are still accepted from an external client. The previous available stage in this history is try31.

## Notes
This snapshot has no Arduino sketch; pair it with the matching controller firmware. Live hardware/network setup is required for the removed simulation data paths.
