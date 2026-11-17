# DROBOTZ ROS 2 Jazzy

This is the ROS 2 Jazzy reorganization of `try46`. Each runtime responsibility is an independent ROS node in the `drobotz_robot` package. The existing Flask/Socket.IO dashboard and Arduino firmware are retained, but all robot state and commands cross ROS topics.

For a plain-language explanation of the ROS 2 nodes, topics, hardware flow, and control modes, see [PROGRAM_GUIDE.md](PROGRAM_GUIDE.md).

For details on the included Gazebo Sim robot, dashboard integration, and launch file, see [GAZEBO_SIM_GUIDE.md](GAZEBO_SIM_GUIDE.md).

## Project layout

```text
try47/
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
        │   ├── simulation_hardware_node.py
        │   ├── system_monitor_node.py
        │   └── web_dashboard_node.py
        ├── firmware/car_latest.ino
        ├── launch/drobotz.launch.py
        ├── launch/simulation.launch.py
        ├── models/yolov8n.pt
        ├── worlds/drobotz_sim.sdf
        └── web/                    # Original dashboard UI
```

`.env` files, virtual environments, cached Python bytecode, sensor-history logs, and old recordings were deliberately not copied. API credentials should stay in the operator's environment and must not be added to ROS parameter files.

## Install

Place the project in a directory path without spaces; generated ROS setup
scripts and Python entry points may not work correctly when their paths
contain spaces.

Use the system Python that matches ROS 2 Jazzy, or a virtual environment that can see ROS's system packages:

```bash
cd ~/Downloads/try47
export DROBOTZ_DATA_DIR="$PWD/data"
source /opt/ros/jazzy/setup.bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

cd ros2_ws
rosdep install --from-paths src --ignore-src -r -y
python -m colcon build --symlink-install
source install/setup.bash
```

For the Gazebo Sim integration on ROS 2 Jazzy, also install
`ros-jazzy-ros-gz` (`sudo apt install ros-jazzy-ros-gz`).

To enable YOLO detection and text-to-speech, install the optional AI/vision dependencies before building:

```bash
python -m pip install -r ../requirements-ai.txt
```

The camera node continues to publish raw video if Ultralytics or the model is unavailable. Set `enable_object_detection: false` in `config/drobotz.yaml` to disable inference explicitly. Speech is best-effort and can be disabled with `enable_tts: false`.

## Configure and run

Edit `ros2_ws/src/drobotz_robot/config/drobotz.yaml` for the serial ports, camera indices, LiDAR topic, and dashboard port. Runtime recordings and sensor logs are written under `~/.ros/drobotz/` by default.
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

Start the Gazebo simulation with the dashboard and obstacle avoidance:

```bash
ros2 launch drobotz_robot simulation.launch.py
```

This simulation launch uses a car-like Gazebo robot with four wheels and front
Ackermann steering, starts a simulation hardware adapter instead of the
Arduino node, and serves the dashboard at `http://localhost:5001`. Manual
forward/reverse drives straight; left/right drives a steering arc. Held
dashboard controls refresh their command until released. The simulation does
not start the physical-camera node. The same optional AI and dashboard flags
are available:

```bash
ros2 launch drobotz_robot simulation.launch.py enable_ai:=false
```

If Gazebo's graphical renderer is unavailable, the headless simulation still
runs robot physics, simulated LiDAR, the ROS bridge, and the dashboard:

```bash
ros2 launch drobotz_robot simulation.launch.py gui:=false
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

The app also supports `python -m colcon test --packages-select drobotz_robot`.
