# DROBOTZ Robot Dashboard - try47

try47 is the ROS 2 Jazzy evolution of try46. It keeps the rover dashboard and Arduino capabilities while moving runtime responsibilities into separate ROS 2 nodes connected by topics.

## Features

- Flask and Socket.IO dashboard for vehicle controls, sensors, GPS, LiDAR, camera streams, recordings, and AI interaction.
- Responsive dashboard layout for phone, tablet, and desktop screens; the Plotly accelerometer view resizes with its panel.
- Independent nodes for hardware, camera, system monitoring, obstacle avoidance, AI control, and the web dashboard.
- Raw and processed FPV/rear camera topics, with optional YOLO annotations and a detections topic.
- Arduino serial telemetry and motor control, plus LiDAR-based obstacle avoidance.
- Optional AI providers (OpenAI-compatible APIs, Groq, or Ollama) and optional text-to-speech.

## Changes from try46

- Replaces try46's single Flask application, shared in-process state, and manually coordinated component threads with an `ament_python` ROS 2 package and independently launched nodes.
- Moves robot communication to ROS topics, including dedicated command sources, status streams, compressed camera images, and object detections.
- Moves hardware and dashboard settings into `config/drobotz.yaml`, and adds a ROS 2 launch file with switches for the camera, AI, and dashboard nodes.
- Keeps the browser dashboard and Arduino firmware, while updating camera streaming and the responsive dashboard behavior for try47.
- Splits Python dependencies into core dashboard/hardware requirements and optional AI/YOLO dependencies, so inference packages are not required when detection is unused.

## Project layout

```text
multi-robot-dashboard/
├── data/                          # Runtime recordings and JSONL sensor logs
├── requirements.txt               # Dashboard and hardware Python dependencies
├── requirements-ai.txt            # Optional YOLO object-detection dependencies
└── ros2_ws/
    └── src/drobotz_robot/
        ├── config/drobotz.yaml
        ├── drobotz_robot/nodes/
        │   ├── ai_controller_node.py
        │   ├── camera_node.py
        │   ├── hardware_node.py
        │   ├── obstacle_avoidance_node.py
        │   ├── system_monitor_node.py
        │   └── web_dashboard_node.py
        ├── firmware/car_latest.ino
        ├── launch/drobotz.launch.py
        ├── models/yolov8n.pt
        └── web/                    # Original dashboard UI
```

`.env` files, virtual environments, cached Python bytecode, sensor-history logs, and old recordings were deliberately not copied. API credentials should stay in the operator's environment and must not be added to ROS parameter files.

## Install

Use Ubuntu with ROS 2 Jazzy. Use the system Python that matches ROS, or a virtual environment that can see ROS's system packages:

```bash
git clone https://github.com/arjun-chandroth/multi-robot-dashboard.git
cd multi-robot-dashboard
export DROBOTZ_DATA_DIR="$PWD/data"
source /opt/ros/jazzy/setup.bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

cd ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

To enable YOLO detection and text-to-speech, install the optional dependencies before launching:

```bash
python -m pip install -r ../requirements-ai.txt
```

The camera node continues to publish raw video if Ultralytics or the model is unavailable. Set `enable_object_detection: false` in `config/drobotz.yaml` to disable inference explicitly. Speech is best-effort and can be disabled with `enable_tts: false`.

## Configure and run

From the repository root, edit `ros2_ws/src/drobotz_robot/config/drobotz.yaml` for the serial ports, camera indices, LiDAR topic, and dashboard port. Runtime recordings and sensor logs are written under `~/.ros/drobotz/` by default.
The install example above sets `DROBOTZ_DATA_DIR` to keep runtime output in the copied project's `data/` folder; remove that export to use the default location.

AI control is optional. For OpenAI:

```bash
export AI_PROVIDER=openai
export AI_API_KEY='your-key'
export AI_MODEL=gpt-4o-mini
```

For Groq set `AI_PROVIDER=groq` and `AI_API_KEY`; for Ollama set `AI_PROVIDER=ollama` and start the Ollama service. Set `AI_BASE_URL` when using a different OpenAI-compatible endpoint. Do not put keys in `drobotz.yaml`.

Start the full system:

```bash
ros2 launch drobotz_robot drobotz.launch.py
```

The dashboard is available at `http://localhost:5001`. You may disable optional components:

```bash
ros2 launch drobotz_robot drobotz.launch.py enable_camera:=false enable_ai:=false
```

The robot starts in `BUTTONS` mode. Motor publishers are separated by source and the hardware node enforces the active mode, rejects malformed commands, bounds timed movement to 5 seconds per action, and sends a stop when command traffic expires or the mode changes. Obstacle avoidance activates only in `OBSTACLE` mode and stops if the forward LiDAR sector has no valid readings.

The system can launch with no Arduino, sensors, cameras, or LiDAR attached. Arduino sensor data becomes disconnected after 5 seconds without a valid frame; cameras require a frame within 4 seconds; GPS and LiDAR are marked disconnected after 7 seconds without dashboard updates. Camera streams show a placeholder, system monitoring continues, and ROS nodes do not repeatedly restart if an optional process exits.

The dashboard defaults to `0.0.0.0:5001` to preserve LAN access and does not provide authentication. Restrict access with a firewall or set `host` to `127.0.0.1` when using it only locally.

## ROS topic map

| Topic | Type | Purpose |
| --- | --- | --- |
| `/scan` | `sensor_msgs/msg/LaserScan` | Input from a ROS-compatible LiDAR driver |
| `/drobotz/control_mode` | `std_msgs/msg/String` | `BUTTONS`, `JOYSTICK`, `AI`, or `OBSTACLE` |
| `/drobotz/cmd/teleop` | `std_msgs/msg/String` | Manual and joystick motor commands |
| `/drobotz/cmd/ai` | `std_msgs/msg/String` | Validated AI motor sequences |
| `/drobotz/cmd/autonomy` | `std_msgs/msg/String` | LiDAR obstacle-avoidance commands |
| `/drobotz/sensors` | `std_msgs/msg/String` | JSON Arduino sensor data |
| `/drobotz/location` | `std_msgs/msg/String` | GPS and dashboard location JSON |
| `/drobotz/hardware/status` | `std_msgs/msg/String` | Arduino and control-mode status |
| `/drobotz/camera/{fpv,rear}/{raw,processed}/compressed` | `sensor_msgs/msg/CompressedImage` | Camera streams |
| `/drobotz/camera/detections` | `std_msgs/msg/String` | Per-camera JSON detections |
| `/drobotz/system/status` | `std_msgs/msg/String` | System health metrics |
| `/drobotz/ai/prompt` | `std_msgs/msg/String` | Dashboard AI prompts |
| `/drobotz/ai/response` | `std_msgs/msg/String` | AI responses and command status |

## Check the running graph

```bash
ros2 node list
ros2 topic list
ros2 topic echo /drobotz/hardware/status
ros2 topic echo /drobotz/sensors
```

## Tests

From `ros2_ws/src/drobotz_robot`, run the protocol and safety tests with:

```bash
python3 -m unittest discover -s test -v
```

The app also supports `colcon test --packages-select drobotz_robot` from `ros2_ws`, followed by `colcon test-result --verbose`.
