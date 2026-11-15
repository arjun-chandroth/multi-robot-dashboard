# Multi-Robot Rover - try28

The dashboard backend remains stable while browser-side control and initialization code receives another revision.

## Features
- Retains camera, recording, detection, telemetry, voice, joystick, and ROS 2 features.
- Updates the main JavaScript dashboard interaction code.
- Keeps the Arduino firmware and active Python entry point from try27.

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
Primarily a front-end revision; the main Python feature set is unchanged. The previous available stage in this history is try27.

## Notes
Only the primary frontend revision is used; generated recordings and logs are not tracked.
