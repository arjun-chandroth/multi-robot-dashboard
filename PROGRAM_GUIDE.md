# DROBOTZ Program Guide

This guide explains the idea behind the program, how to start it, and how its
parts exchange commands and information. It covers both the **physical robot**
and the **Gazebo simulation**.

## 1. The idea: one dashboard, two kinds of robot

DROBOTZ is a group of small programs that work together:

- The **dashboard** is the web page an operator uses.
- **ROS 2** carries commands and information between the programs.
- The **robot interface** sends commands to either a real Arduino or a Gazebo
  model.
- Other programs handle cameras, AI, obstacle avoidance, and computer health.

There are two robot interfaces:

1. **Physical robot:** `drobotz_hardware` exchanges text messages with an
   Arduino over USB/serial.
2. **Gazebo simulation:** `drobotz_simulation_hardware` exchanges speed
   commands with Gazebo through a ROS-Gazebo bridge.

The dashboard and most other ROS 2 programs are shared by both modes. Choose
one robot interface at a time. **Do not start the physical and simulation
launch files together.**

### A few ROS 2 words

- A **node** is a running program, such as the camera node.
- A **topic** is a named message stream. One node publishes messages; other
  nodes subscribe to that topic and receive them. Topics are used for commands,
  sensor readings, status, and images in this project.
- A **service** is a request that expects one reply.
- An **action** is a longer task with progress and a result.
- A **launch file** starts several nodes and gives them settings.

This project uses ROS 2 **topics** for communication between its nodes. It
does not define ROS 2 services or actions. The dashboard also uses normal web
HTTP and Socket.IO messages; those are not ROS services or actions.

## 2. How to build and start the program

### First-time setup

Install ROS 2 Jazzy and the project's Python and ROS dependencies. Then build
the ROS 2 workspace. The complete installation instructions are in
[`README.md`](README.md). The basic ROS build steps are:

```bash
source /opt/ros/jazzy/setup.bash
cd /path/to/try47/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

Replace `/path/to/try47` with the location of the project. The project path
should not contain spaces; generated ROS 2 setup files and commands can have
trouble with spaces in paths. If the Python dependencies have not been
installed yet, follow the full setup in `README.md` too.

### Every time you start it

Open a terminal and source ROS 2 and the built workspace:

```bash
source /opt/ros/jazzy/setup.bash
cd /path/to/try47/ros2_ws
source install/setup.bash
```

If you created the optional `.venv` described in `README.md`, activate it
before sourcing the workspace:

```bash
source /path/to/try47/.venv/bin/activate
```

Then run **one** of these launch commands:

| What you want to run | Command |
| --- | --- |
| Physical robot | `ros2 launch drobotz_robot drobotz.launch.py` |
| Gazebo robot | `ros2 launch drobotz_robot simulation.launch.py` |

Keep that terminal open. The launch command starts the required programs and
shows their log messages. When the dashboard node is running, open
**http://localhost:5001** in a browser. Press **Ctrl+C** in the launch terminal
to stop the launched programs.

The physical launch can skip optional camera and AI nodes:

```bash
ros2 launch drobotz_robot drobotz.launch.py enable_camera:=false enable_ai:=false
```

The simulation can run without a graphical Gazebo window:

```bash
ros2 launch drobotz_robot simulation.launch.py gui:=false
```

### What happens during startup

1. The ROS 2 launch system reads the selected launch file.
2. It starts the nodes listed in that file. They run at the same time and
   connect to one another through topics.
3. The physical hardware node starts looking for an Arduino. The simulation
   launch starts Gazebo and the ROS-Gazebo bridge instead.
4. The dashboard node starts its web server on port `5001`.
5. Open the dashboard in a browser. Select Manual, ROV, AI, or Autonomous mode
   and use the controls.

The dashboard server listens on `0.0.0.0:5001` by default, so other computers
on the network may be able to reach it. It has no login. Restrict network
access or set the host to `127.0.0.1` in
[`drobotz.yaml`](ros2_ws/src/drobotz_robot/config/drobotz.yaml) for local-only
use.

## 3. Physical robot

### What the physical robot needs

The physical launch expects an Arduino running compatible firmware and wired
to the motor drivers and sensors. The included
[`car_latest.ino`](ros2_ws/src/drobotz_robot/firmware/car_latest.ino) is the
firmware for this project's current wiring and command format.

The hardware node checks these serial ports:

- `/dev/ttyACM0`
- `/dev/ttyACM1`
- `/dev/ttyUSB0`
- `/dev/ttyUSB1`

It uses **115200 baud** and retries the ports every two seconds. These
settings are in `drobotz.yaml`. The Arduino sends newline-ended text over
serial. The hardware node reads sensor and GPS lines and writes movement
letters such as `F`, `B`, `L`, `R`, and `S`.

The dashboard's Arduino status should become **Connected** only when valid
sensor messages are arriving as well as the serial port being open. If it
stays disconnected, check the board, firmware, USB port, baud rate, and Linux
serial-port permissions.

### Physical launch: nodes and their ROS topics

The default physical launch starts these nodes:

| Node | Publishes (ROS topics) | Subscribes to (ROS topics) | Other work |
| --- | --- | --- | --- |
| `drobotz_web_dashboard` | `/drobotz/control_mode`, `/drobotz/cmd/teleop`, `/drobotz/ai/prompt`, `/drobotz/sensors/reset`, `/drobotz/location`, `/drobotz/camera/recording/start`, `/drobotz/camera/recording/stop` | `/drobotz/sensors`, `/drobotz/hardware/status`, `/drobotz/system/status`, `/drobotz/camera/status`, `/drobotz/ai/response`, `/drobotz/location`, `/drobotz/camera/detections`, `/drobotz/camera/recording/status`, `/scan`, and four camera-image topics | Serves the browser using HTTP and Socket.IO. |
| `drobotz_hardware` | `/drobotz/sensors`, `/drobotz/hardware/status`, `/drobotz/location` | `/drobotz/control_mode`, `/drobotz/cmd/teleop`, `/drobotz/cmd/ai`, `/drobotz/cmd/autonomy`, `/drobotz/sensors/reset` | Reads from and writes to the Arduino over USB/serial. |
| `drobotz_camera` | Four camera-image topics, `/drobotz/camera/detections`, `/drobotz/camera/status`, `/drobotz/camera/recording/status` | `/drobotz/camera/recording/start`, `/drobotz/camera/recording/stop` | Reads cameras; object detection is optional. |
| `drobotz_ai_controller` | `/drobotz/cmd/ai`, `/drobotz/ai/response` | `/drobotz/control_mode`, `/drobotz/ai/prompt` | Sends an HTTP request to the configured AI provider. |
| `drobotz_obstacle_avoidance` | `/drobotz/cmd/autonomy` | `/scan`, `/drobotz/control_mode` | Uses forward LiDAR readings when Autonomous mode is selected. |
| `drobotz_system_monitor` | `/drobotz/system/status` | `/drobotz/sensors`, `/drobotz/camera/detections`, `/drobotz/hardware/status`, `/drobotz/location` | Reads computer health and saves sensor-history files. |

The physical launch starts the camera, AI, and dashboard nodes by default.
They can be disabled with launch arguments. The hardware, obstacle-avoidance,
and system-monitor nodes are always started by this launch file.

### Physical movement and sensor flow

```text
Dashboard button
  → browser Socket.IO message
  → dashboard node publishes /drobotz/cmd/teleop (ROS topic)
  → hardware node checks the mode and command
  → USB/serial text command
  → Arduino firmware
  → motor drivers and motors

Arduino sensor/GPS text
  → USB/serial
  → hardware node
  → /drobotz/sensors or /drobotz/location (ROS topics)
  → dashboard and system monitor
```

Manual movement commands are `std_msgs/msg/String` ROS messages. The hardware
node validates them and sends the matching letter over serial. The firmware
controls the motors. In the included firmware, left/right turns run the two
drive motors in opposite directions, so the robot pivots; this is not
Ackermann steering with a steering servo.

The camera node uses the configured front and rear camera indices. It publishes
raw and processed compressed images. If optional YOLO detection is available,
the processed image can include detections. If a camera is missing, the node
can publish a placeholder instead.

The physical launch does **not** start a LiDAR driver. For physical Autonomous
mode, a separate ROS 2 LiDAR driver must publish `sensor_msgs/msg/LaserScan`
messages on `/scan`. With the default settings, the obstacle node examines the
front 60 degrees: it requests a left turn if something is closer than 0.5 m,
moves forward when the path is clear, and requests stop if it has no valid
forward readings.

## 4. Gazebo simulation

Start the simulation with:

```bash
ros2 launch drobotz_robot simulation.launch.py
```

This opens Gazebo with the four-wheel car and its simulated LiDAR. The same
dashboard is available at **http://localhost:5001**. The simulation launch
does not start the real Arduino hardware node or the physical camera node.
Instead, `drobotz_simulation_hardware` takes the place of
`drobotz_hardware`.

### Simulation launch: nodes and their ROS topics

| Node or program | Publishes (ROS topics) | Subscribes to (ROS topics) | Other work |
| --- | --- | --- | --- |
| Gazebo | Simulated sensor data is carried into ROS by the bridge. | Receives drive commands through the bridge. | Runs the virtual world, car, and LiDAR sensor. |
| `ros_gz_bridge` (`parameter_bridge`) | `/scan` as `sensor_msgs/msg/LaserScan` | `/cmd_vel` as `geometry_msgs/msg/Twist` | Converts between ROS messages and Gazebo Transport messages. |
| `drobotz_simulation_hardware` | `/cmd_vel`, `/drobotz/hardware/status`, `/drobotz/sensors` | `/drobotz/control_mode`, `/drobotz/cmd/teleop`, `/drobotz/cmd/ai`, `/drobotz/cmd/autonomy`, `/scan` | Converts the project's command letters into simulated speed and steering. It does not use serial. |
| `drobotz_web_dashboard` | Same dashboard command and recording topics as in the physical launch | Same dashboard status, sensor, camera, AI, location, and `/scan` topics as in the physical launch | Serves the same browser dashboard. |
| `drobotz_ai_controller` | `/drobotz/cmd/ai`, `/drobotz/ai/response` | `/drobotz/control_mode`, `/drobotz/ai/prompt` | Optional; same as in the physical launch. |
| `drobotz_obstacle_avoidance` | `/drobotz/cmd/autonomy` | `/scan`, `/drobotz/control_mode` | Uses the simulated LiDAR in Autonomous mode. |
| `drobotz_system_monitor` | `/drobotz/system/status` | `/drobotz/sensors`, `/drobotz/camera/detections`, `/drobotz/hardware/status`, `/drobotz/location` | Optional in simulation; saves system and sensor history. |

The simulation launch starts Gazebo, the bridge, the simulation hardware
adapter, and obstacle avoidance. It also starts AI, the dashboard, and the
system monitor by default. AI, dashboard, and system monitor can be disabled
with their launch arguments. The physical camera node is not part of this
launch.

### Simulation movement and LiDAR flow

```text
Dashboard button
  → dashboard node publishes /drobotz/cmd/teleop (ROS String topic)
  → simulation hardware adapter checks the mode and command
  → adapter publishes /cmd_vel (ROS Twist topic)
  → ros_gz_bridge converts it to a Gazebo drive message
  → Gazebo moves the virtual car

Gazebo LiDAR
  → ros_gz_bridge publishes /scan (ROS LaserScan topic)
  → simulation adapter, dashboard, and obstacle node
```

In the simulation, `/cmd_vel` is a `geometry_msgs/msg/Twist` message. Its
`linear.x` value is forward/backward speed; its `angular.z` value is turning
speed. The bridge maps that ROS topic to Gazebo's drive topic. The bridge also
maps Gazebo's LiDAR output to the ROS `/scan` topic.

The simulation's Forward and Backward commands drive straight. Left and Right
drive forward while steering the car in an arc. This differs from the
included physical Arduino firmware, where left and right pivot the robot.

The simulation adapter publishes status with `"simulated": true`. It reports
the simulated robot as connected while fresh LiDAR scans arrive. Its sensor
values are placeholders; they are not readings from physical sensors.

The simulation adapter's default drive speeds are 0.25 m/s forward/backward
and 0.25 rad/s turning. It stops if command messages stop arriving for one
second, or if fresh LiDAR scans stop arriving for three seconds.

## 5. All ROS topics and message types

Every item in this table is a **ROS topic**. A publisher sends messages; any
listed subscribers receive them. `String` means `std_msgs/msg/String`; JSON
topics are JSON text inside that String message.

| Topic | ROS message type | Publisher → subscriber(s) | Used by |
| --- | --- | --- | --- |
| `/drobotz/control_mode` | `std_msgs/msg/String` | Dashboard → hardware or simulation adapter, AI, obstacle node | Both |
| `/drobotz/cmd/teleop` | `std_msgs/msg/String` | Dashboard → hardware or simulation adapter | Both |
| `/drobotz/cmd/ai` | `std_msgs/msg/String` | AI controller → hardware or simulation adapter | Both |
| `/drobotz/cmd/autonomy` | `std_msgs/msg/String` | Obstacle node → hardware or simulation adapter | Both |
| `/drobotz/ai/prompt` | `std_msgs/msg/String` | Dashboard → AI controller | Both |
| `/drobotz/ai/response` | `std_msgs/msg/String` (JSON) | AI controller → dashboard | Both |
| `/drobotz/sensors/reset` | `std_msgs/msg/String` | Dashboard → physical hardware node | Physical |
| `/drobotz/sensors` | `std_msgs/msg/String` (JSON) | Hardware node or simulation adapter → dashboard and monitor | Both |
| `/drobotz/hardware/status` | `std_msgs/msg/String` (JSON) | Hardware node or simulation adapter → dashboard and monitor | Both |
| `/drobotz/location` | `std_msgs/msg/String` (JSON) | Hardware node or dashboard → dashboard and monitor | Both |
| `/drobotz/system/status` | `std_msgs/msg/String` (JSON) | System monitor → dashboard | Both |
| `/scan` | `sensor_msgs/msg/LaserScan` | Physical LiDAR driver or Gazebo bridge → obstacle node and dashboard; also simulation adapter in Gazebo | Both |
| `/drobotz/camera/fpv/raw/compressed` | `sensor_msgs/msg/CompressedImage` | Camera node → dashboard | Physical |
| `/drobotz/camera/fpv/processed/compressed` | `sensor_msgs/msg/CompressedImage` | Camera node → dashboard | Physical |
| `/drobotz/camera/rear/raw/compressed` | `sensor_msgs/msg/CompressedImage` | Camera node → dashboard | Physical |
| `/drobotz/camera/rear/processed/compressed` | `sensor_msgs/msg/CompressedImage` | Camera node → dashboard | Physical |
| `/drobotz/camera/detections` | `std_msgs/msg/String` (JSON) | Camera node → dashboard and monitor | Physical |
| `/drobotz/camera/status` | `std_msgs/msg/String` (JSON) | Camera node → dashboard | Physical |
| `/drobotz/camera/recording/start` | `std_msgs/msg/String` | Dashboard → camera node | Physical |
| `/drobotz/camera/recording/stop` | `std_msgs/msg/String` | Dashboard → camera node | Physical |
| `/drobotz/camera/recording/status` | `std_msgs/msg/String` (JSON) | Camera node → dashboard | Physical |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | Simulation adapter → ROS-Gazebo bridge → Gazebo | Simulation |

Most regular ROS topics use a queue depth of 10. Camera and LiDAR topics use a
sensor-data quality-of-service setting that is suitable for frequent updates.

## 6. Settings and optional features

The main settings are in
[`drobotz.yaml`](ros2_ws/src/drobotz_robot/config/drobotz.yaml). Important
defaults are:

| Part | Default |
| --- | --- |
| Arduino serial | Candidate ports listed above, 115200 baud; retry every 2 seconds. |
| Physical command watchdog | Stop after 1 second without a fresh command. Sensor data is considered stale after 5 seconds. |
| Cameras | Front indices `0, 1, 2`; rear indices `2, 1, 3, 4`; 1280×720 at 20 frames per second. A camera is considered stale after 4 seconds without a frame. |
| Obstacle avoidance | Read `/scan`; inspect the front 60 degrees; turn if something is nearer than 0.5 m. |
| System monitor | Publish computer health and save a sensor record every 5 seconds. |
| Dashboard | Listen on `0.0.0.0:5001`. |
| Simulation drive | 0.25 m/s linear speed; 0.25 rad/s turn speed. |

The AI node starts by default but needs an AI provider configured to answer
prompts. Hosted providers usually need an `AI_API_KEY`; see `README.md` for
provider settings. Hosted AI sends the operator's prompt to that provider.
The camera node can show video without object detection; detection needs the
optional model and dependencies. Physical Autonomous mode requires a separate
LiDAR driver. Gazebo supplies its own simulated LiDAR.

## 7. Topics, services, actions, and other connections

The ROS 2 nodes in this project use **publishers and subscribers on topics**.
There are no project-defined ROS 2 services, service clients, action servers,
or action clients. Camera recording may sound like a long-running action, but
in this code it is requested with the `/drobotz/camera/recording/start` and
`/stop` topics and reported on `/drobotz/camera/recording/status`.

Some connections are not ROS topics:

| Connection | What it is used for |
| --- | --- |
| Browser ↔ dashboard | HTTP loads the page and video routes. Socket.IO carries button, joystick, AI, and recording events. The dashboard node converts these to ROS topics. |
| Hardware node ↔ Arduino | USB/serial text messages at 115200 baud. This is not a ROS service or action. |
| AI controller ↔ AI provider | An HTTP request to an OpenAI-compatible API. Hosted providers receive the prompt outside the robot computer; a local Ollama server can be used instead. |
| ROS ↔ Gazebo | `ros_gz_bridge` converts ROS topics to and from Gazebo Transport messages. |

## 8. Control modes and stopping

The default mode is Manual (`BUTTONS`).

| Dashboard mode | ROS mode value | What can send movement |
| --- | --- | --- |
| Manual | `BUTTONS` | Dashboard buttons |
| ROV | `JOYSTICK` | Dashboard joystick |
| Joy Mode | `JOYMODE` (treated internally as `JOYSTICK`) | Connected browser gamepad |
| AI | `AI` | AI controller, after a prompt |
| Autonomous | `OBSTACLE` | Obstacle-avoidance node |

The hardware and simulation nodes ignore movement commands from the wrong
mode. A mode change asks the robot to stop. Manual buttons refresh their
command while held and send stop on release. The hardware and simulation
adapters also stop if command messages stop arriving; their default timeout
is one second. Timed AI movements are validated and limited to a few seconds
per movement (at most 5 seconds).

Software stopping is not a replacement for an emergency stop. Test physical
hardware with the wheels raised, the area clear, and a way to cut motor power
immediately.

## 9. Checking status and finding saved data

In another terminal, source ROS 2 and the workspace, then run:

```bash
ros2 node list
ros2 topic list
ros2 topic echo /drobotz/hardware/status
```

For physical hardware, look for `"arduino_connected": true` and a serial port.
For simulation, look for `"simulated": true`; the status becomes connected
while fresh LiDAR messages arrive. To inspect motion and LiDAR in simulation,
also try:

```bash
ros2 topic echo /cmd_vel
ros2 topic echo /scan
```

Sensor history and recordings are stored under `~/.ros/drobotz/` by default.
Set `DROBOTZ_DATA_DIR` to choose another folder. AI control needs a configured
AI provider; object detection needs its optional model and dependencies.
