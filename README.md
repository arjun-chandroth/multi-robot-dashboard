# Multi-Robot Rover - try46

The latest complete available stage restores the modular dashboard and includes firmware, dependencies, environment template, and AI configuration tests.

## Features
- Runs a Flask/Socket.IO dashboard with modular camera, hardware, ROS 2, AI, and system-monitor components.
- Supports camera streaming/recording, object detection, joystick/button modes, sensor telemetry, and LiDAR hooks.
- Includes Arduino firmware, `requirements.txt`, and blank environment settings.
- Includes tests for AI and environment configuration.

## Dependencies and hardware
Install packages from `requirements.txt`; also install a compatible ROS 2 distribution with `rclpy` and `sensor_msgs`. Camera/serial hardware, local YOLO weights, and optional AI/voice services are needed for their corresponding features.

## Setup and run
Install the manifest dependencies, copy the blank environment template, review hardware configuration, source ROS 2, and provide model weights before starting.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Install/source a compatible ROS 2 distribution with `rclpy` and `sensor_msgs` separately. Build `car_latest.ino` with the AVR core and the sensor libraries it references.

## Changes from the previous available try
Restores the complete application tree after partial try45 and adds the Arduino sketch/dependency manifest; this is the newest selected source stage.

## Notes
`test_ai.py` may send requests to an external provider and requires credentials; inspect it before running. The dashboard may be network-accessible. Restrict it to a trusted LAN; logs, recordings, model weights, and secrets are excluded.
