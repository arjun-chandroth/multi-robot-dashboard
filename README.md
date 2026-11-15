# Multi-Robot Rover - try44

AI configuration moves to environment variables, with tests for environment loading and AI settings.

## Features
- Loads provider, key, model, base URL, token, temperature, and timeout values from environment variables.
- Adds tests for AI configuration and environment-variable visibility.
- Retains modular dashboard, utility diagnostics, and hardware integration.
- Includes a blank `.env.example`; credentials are not included.

## Dependencies and hardware
Python 3 with Flask, Flask-SocketIO, OpenCV, NumPy, psutil, pyserial, pyttsx3, requests, Ultralytics, and python-dotenv. ROS 2 `rclpy`/`sensor_msgs` are system dependencies. A local YOLO weights file and hardware are needed for those features.

## Setup and run
Install the runtime dependencies, review rover configuration and hardware settings, source ROS 2, and start the application.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install flask flask-socketio opencv-python numpy psutil pyserial pyttsx3 requests ultralytics python-dotenv
# Install/source a compatible ROS 2 distribution with rclpy and sensor_msgs.
python app.py
```

## Changes from the previous available try
Adds environment-based AI configuration and tests for the configuration path. The previous available stage in this history is try43.

## Notes
Run `python test_env.py` to inspect environment loading. `test_ai.py` makes external API requests and requires valid local credentials; inspect it before running. Never commit `.env` or API keys. The committed example contains blank values only.
