# Multi-Robot Rover - try31

This snapshot focuses the repository on the active dashboard application and its UI assets.

## Features
- Keeps the main dashboard, templates, and static assets.
- Retains gamepad controls, cameras, recording, telemetry, voice, and ROS 2 code in the active app.
- Removes redundant legacy controller scripts and the Arduino sketch from this snapshot.

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
Removes alternate controller scripts, temporary template variants, and the separate Arduino sketch; the active dashboard code is otherwise unchanged. The previous available stage in this history is try30.

## Notes
This source stage has no firmware file; pair it with the matching controller firmware from the hardware setup.
