# Multi-Robot Dashboard

A versioned Arduino rover and dashboard project. The early firmware drives a
mobile platform and reports sensor readings over serial. Later snapshots add a
Python web dashboard, camera streaming and object detection, telemetry logging,
voice-control experiments, and optional ROS 2/LiDAR integration.

This repository collects the source snapshots that were available locally.
Missing try numbers are not present in the available files; the numbered
directories below are kept as separate snapshots rather than merged into one
codebase.

## Project contents

- `try3.ino` is the starting Arduino Mega sketch. It controls two motors and
  reads temperature/humidity, impact, sound, touch, tilt, motion, rain, gas,
  flame, radar, and accelerometer sensors.
- `components/gps/GPS.ino` is a standalone GPS module test sketch.
- `versions/tryNN/` contains the source files found in each available later
  snapshot, including try26, try27, try31, try32, try36-try40, and try42-try46.
- `versions/try46/` is the latest full application snapshot available here.
- `versions/try45/` is partial; only its camera-processing module was available.

Later snapshots are experimental and may have different hardware assumptions or
dependencies. They are preserved independently so that earlier work remains
accessible.

## Arduino firmware: try3

### Hardware and libraries

The sketch targets an Arduino Mega-class board and a motor driver. Its sensor
connections are defined near the top of `try3.ino`. Install these Arduino
libraries before compiling:

- DHT sensor library
- Adafruit Unified Sensor
- Adafruit ADXL345

`Wire` is included with the Arduino platform.

Open the sketch in the Arduino IDE, select the board and serial port, then
upload it. The serial interface runs at **115200 baud**.

### Serial commands

Send one character over serial:

| Command | Action |
| --- | --- |
| `F` | Drive forward |
| `B` | Drive backward |
| `L` | Turn left |
| `R` | Turn right |
| `S` | Stop the motors |
| `D` | Send a sensor telemetry frame |
| `X` | Reset sensor event counters |
| `O` | Toggle the obstacle-mode state flag |

The firmware also emits sensor telemetry approximately every two seconds.
Sensor calibration, active levels, and thresholds may need adjustment for the
specific modules and wiring.

## Python dashboard snapshots

The latest complete application snapshot is under `versions/try46/`. It uses
Flask and Socket.IO for the dashboard, serial communication for the Arduino,
OpenCV for camera capture, and Ultralytics for object detection. The application
imports its ROS 2 integration at startup, so a compatible ROS 2 installation
and its Python packages are needed to run this snapshot. Voice-control
providers and hardware also need their own configuration.

From that directory, create an isolated Python environment and install the
listed dependencies:

```bash
cd versions/try46
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Set any needed AI provider values in `.env`; do not commit credentials. Camera,
serial-port, and other hardware settings are in `roverconf.py`. Object
detection expects the YOLO model file configured by that snapshot; model
weights are intentionally not stored in this repository. ROS 2 packages must
be installed from a ROS distribution compatible with the host system. Review
the historical installer script before running it because it installs
software and downloads model files.

This is a hardware project: the application has not been validated against
every snapshot, board, sensor, camera, or ROS 2 setup. Review the wiring and
configuration before connecting motors or deploying it on a network.

## Repository hygiene

Credentials, virtual environments, generated sensor logs, recordings, cache
files, and model weights are excluded. The code may still need configuration
and hardware-specific changes before it runs on a particular rover.

No license file is included yet.
