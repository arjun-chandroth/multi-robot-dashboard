# Multi-Robot Rover - try25

A later dashboard prototype brings camera processing, object detection, joystick controls, recording, telemetry, and ROS 2 LiDAR into one Python application.

## Features
- Streams front and rear camera feeds and supports recording/download routes.
- Runs Ultralytics object detection and perspective-based tracking.
- Includes joystick and web-button control, sensor logging, location updates, and system metrics.
- Defines ROS 2 LiDAR subscriber and obstacle-avoidance helpers.

## Dependencies and hardware
Python 3 with Flask, Flask-SocketIO, OpenCV, NumPy, psutil, pyserial, Ultralytics, and Supervision. ROS 2 `rclpy`/`sensor_msgs` must be installed from a compatible ROS distribution. Provide YOLO weights locally; they are not stored here.

## Setup and run
Install Python and ROS 2 dependencies, configure camera/serial/audio devices, provide model weights, and start the active script.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install flask flask-socketio opencv-python numpy psutil pyserial ultralytics supervision
# Install/source a compatible ROS 2 distribution with rclpy and sensor_msgs.

python car_control.py
```

## Changes from the previous available try
Major expansion over try17: camera recording/object detection, joystick support, and ROS 2/LiDAR are introduced in the available source.

## Notes
Review camera/serial settings. Runtime recordings, logs, and model weights are excluded; restrict server access to a trusted network.
