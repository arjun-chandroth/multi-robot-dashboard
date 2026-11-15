# Multi-Robot Rover - try30

This stage adds a browser gamepad path to the joystick-enabled rover dashboard.

## Features
- Adds gamepad polling/activation in the browser UI.
- Adds server handling for joystick input packets.
- Retains camera, recording, sensor telemetry, voice, object detection, and ROS 2/LiDAR.
- Includes the Arduino sketch and active Python app.

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
Adds a new joystick/gamepad control path in both the browser and Python server. The previous available stage in this history is try28.

## Notes
Verify deadzone and safe-stop behavior before using a gamepad to drive motors.
