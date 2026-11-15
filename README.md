# Multi-Robot Rover - try27

This iteration pairs the dashboard with an Arduino firmware snapshot and updates the browser interface.

## Features
- Includes an Arduino motor/sensor sketch to accompany serial dashboard control.
- Retains cameras, recording, YOLO processing, telemetry, voice features, and ROS 2/LiDAR.
- Updates dashboard JavaScript and template content.
- Preserves alternate controller scripts as reference source files.

## Dependencies and hardware
Python 3 with Flask, Flask-SocketIO, OpenCV, NumPy, psutil, pyserial, pyttsx3, Ultralytics, and Supervision. ROS 2 `rclpy`/`sensor_msgs` must be installed from a compatible ROS distribution. Provide YOLO weights locally; they are not stored here.

## Setup and run
Install Python and ROS 2 dependencies, configure camera/serial/audio devices, provide model weights, and start the active script.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install flask flask-socketio opencv-python numpy psutil pyserial pyttsx3 ultralytics supervision
# Install/source a compatible ROS 2 distribution with rclpy and sensor_msgs.
arduino-cli core install arduino:avr
arduino-cli compile --fqbn arduino:avr:mega firmware/rover
python car_latest.py
```

## Changes from the previous available try
Adds the rover Arduino sketch and adjusts dashboard-side controls/layout. The previous available stage in this history is try26.

## Notes
Confirm motor wiring and stop behavior before testing controls.
