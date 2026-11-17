# Using DROBOTZ with a Robot in Gazebo Sim

This guide explains how to connect this project to a robot model running in
Gazebo Sim. It is written for the project's ROS 2 Jazzy workspace.

Keep the checkout and Python environment paths free of spaces. ROS 2's
generated setup scripts and Python entry points may not work correctly when
their installation paths contain spaces.

## Included simulation

The project now includes a small car-like Gazebo vehicle with four wheels and
front Ackermann steering, an obstacle world, a ROS-Gazebo bridge, and a
simulation adapter that connects to the existing dashboard and control topics.
Its regular
[`drobotz.launch.py`](ros2_ws/src/drobotz_robot/launch/drobotz.launch.py)
always starts `hardware_node`, which talks to a real Arduino over serial.
Use the separate `simulation.launch.py` file for Gazebo; it intentionally
does not start that Arduino node.

Install Gazebo's ROS integration if it is not already present:

```bash
sudo apt install ros-jazzy-ros-gz
```

Build and source the workspace, then launch Gazebo, the robot, LiDAR,
dashboard, and obstacle avoidance together:

```bash
cd ros2_ws
colcon build --symlink-install
source install/setup.bash
ros2 launch drobotz_robot simulation.launch.py
```

Open `http://localhost:5001` to use the dashboard. Wait for the simulated
LiDAR to connect; the adapter reports the simulated robot as connected only
while `/scan` messages are arriving. Use the dashboard's Manual or Obstacle
mode, or AI mode if an AI provider is configured.

In Manual mode, hold the forward or reverse arrow to drive straight. Hold
left or right to drive in a forward arc with the front wheels steering; release
the control or press Stop to stop. A held button periodically refreshes its
command, while a one-second watchdog still stops the car if command traffic is
lost.

If Gazebo's graphical renderer is not supported by the current display or
graphics driver, start the simulation without the GUI:

```bash
ros2 launch drobotz_robot simulation.launch.py gui:=false
```

The headless mode still runs robot physics, simulated LiDAR, the ROS bridge, and the
dashboard.

Do **not** launch `drobotz.launch.py` alongside the simulation. That launch
starts the real Arduino serial node, which could send movement commands to a
physical robot if one is connected.

## How the parts fit together

```text
Dashboard / AI / obstacle avoidance
        │
        ├── /drobotz/cmd/teleop
        ├── /drobotz/cmd/ai
        └── /drobotz/cmd/autonomy
                    │
                    ▼
       Simulation hardware adapter
       (mode checks, stop, status)
                    │
                    ▼
             /cmd_vel (Twist)
                    │
         ros_gz_bridge (ROS → Gazebo)
                    │
                    ▼
             Gazebo drive plugin

Gazebo LiDAR ── ros_gz_bridge (Gazebo → ROS) ── /scan
                                                   │
                                      obstacle-avoidance node
```

In the diagram, `/cmd_vel` is a ROS `geometry_msgs/msg/Twist` topic. The
Gazebo drive plugin turns its forward and turning speeds into wheel motion.
The existing project command topics use `std_msgs/msg/String`, so they need
the adapter between them; `ros_gz_bridge` does not convert those strings into
movement commands by itself.

## 1. Install the matching Gazebo/ROS integration

For ROS 2 Jazzy on Ubuntu 24.04, Gazebo Harmonic is the recommended matching
Gazebo release. With ROS Jazzy and its package repository already installed:

```bash
sudo apt update
sudo apt install ros-jazzy-ros-gz
```

The `ros_gz` packages provide tools such as `ros_gz_sim` for starting Gazebo
and spawning models, and `ros_gz_bridge` for passing supported messages
between ROS and Gazebo Transport.

Source ROS in each terminal:

```bash
source /opt/ros/jazzy/setup.bash
```

Check that the commands are available:

```bash
ros2 pkg executables ros_gz_sim
ros2 pkg executables ros_gz_bridge
gz sim --help
```

If these packages are missing, check that the machine is using the Jazzy
package repository and the supported Ubuntu release before trying to install
packages from a different ROS/Gazebo version.

## 2. The included robot and world

The simulation model and test world are in
[`drobotz_sim.sdf`](ros2_ws/src/drobotz_robot/worlds/drobotz_sim.sdf). The
world includes a four-wheel car body, driven rear wheels, steerable front
wheels, a 360-degree simulated LiDAR, a floor, and an obstacle wall in front
of the robot. The `gz-sim-ackermann-steering-system` plugin listens for
velocity commands on Gazebo's `/cmd_vel` topic.

These are starter simulation dimensions, not a measured model of the physical
robot. If your robot uses different wheel positions, wheel radius, mass, or
sensor placement, edit the SDF and retest drive direction and collision
behavior.

The simulation launch starts this world directly, so you do not need to
separately start an empty world or spawn the robot. To open only Gazebo for
testing, you can use:

```bash
ros2 launch ros_gz_sim gz_sim.launch.py \
  gz_args:="-r /absolute/path/to/ros2_ws/src/drobotz_robot/worlds/drobotz_sim.sdf"
```

In normal use, prefer `ros2 launch drobotz_robot simulation.launch.py`; it
starts the world, bridges, adapter, and project nodes together.

## 3. How the Gazebo topics reach ROS

The simulation launch starts `ros_gz_bridge` with the two topic connections
used by this world:

- ROS `/cmd_vel` (`geometry_msgs/msg/Twist`) to Gazebo `/cmd_vel`
  (`gz.msgs.Twist`).
- Gazebo `/scan` (`gz.msgs.LaserScan`) to ROS `/scan`
  (`sensor_msgs/msg/LaserScan`).

The launch file configures this bridge automatically. If you edit the SDF
topic names, edit the bridge arguments in
[`simulation.launch.py`](ros2_ws/src/drobotz_robot/launch/simulation.launch.py)
to match. Inspect Gazebo's topic names with `gz topic -l` and check ROS topics
with `ros2 topic list`.

The bridge direction characters are `]` for ROS-to-Gazebo and `[` for
Gazebo-to-ROS. For a different model, an equivalent manual bridge looks like:

```bash
ros2 run ros_gz_bridge parameter_bridge \
  '/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist' \
  '/world/default/model/drobotz/link/chassis/sensor/lidar/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan'
```

In the bridge syntax:

- `]` means ROS publishes to Gazebo. That is the direction for `/cmd_vel`.
- `[` means Gazebo publishes to ROS. That is the direction for the LiDAR scan.
- `@` in place of either direction marker requests a bidirectional bridge.

If the bridge reports an unsupported message type or no messages arrive,
check the installed `ros_gz_bridge` Jazzy documentation and the exact Gazebo
topic and message type.

The project expects the ROS-side scan topic to be `/scan` by default. If the
bridge publishes the scan on another ROS topic, set the
`scan_topic` parameter on `obstacle_avoidance_node` to match.

## 4. How the included simulation adapter works

[`simulation_hardware_node.py`](ros2_ws/src/drobotz_robot/drobotz_robot/nodes/simulation_hardware_node.py)
takes the place of `hardware_node`; it uses the same command topics as the real
robot and publishes velocity commands to `/cmd_vel`. The launch file bridges
that ROS topic to Gazebo's Ackermann steering plugin and brings the simulated LiDAR
back to ROS as `/scan`.

The adapter:

1. Subscribes to `/drobotz/control_mode`, `/drobotz/cmd/teleop`,
   `/drobotz/cmd/ai`, and `/drobotz/cmd/autonomy`.
2. Accepts commands only from the source allowed by the current mode:
   teleoperation in `BUTTONS`/`JOYSTICK`, AI in `AI`, and autonomy in
   `OBSTACLE`.
3. Validates commands with the project's
   [`normalize_motion_command`](ros2_ws/src/drobotz_robot/drobotz_robot/protocol.py)
   helper before using them.
4. Publishes `geometry_msgs/msg/Twist` on `/cmd_vel`. `F` and `B` drive
   straight forward and backward; `L` and `R` drive forward while steering
   left and right; `S` sets both speeds to zero.
5. Executes AI command sequences in order for their requested durations. Stops
   between/after sequences as appropriate. Do not treat a string such as
   `F1000,L500,S` as one direction.
6. Publishes a zero `Twist` when the mode changes, a stop command arrives,
   commands time out, or the adapter shuts down.
7. Publishes JSON on `/drobotz/hardware/status` periodically, with at least
   `arduino_connected: true` and the current `control_mode`. In simulation,
   this field means “the simulated drive is available.” The dashboard checks
   this status before sending button commands. This adapter marks the robot
   connected only while simulated scans are fresh.

The speed defaults are 0.25 m/s forward/back and 0.25 rad/s yaw while turning.
The dashboard refreshes a held movement command every 250 ms; the adapter's
one-second timeout still stops the car if command traffic is lost. It also
publishes zeroed, Arduino-shaped sensor JSON so the dashboard and system
monitor have a consistent simulated sensor message.

The world is an example, not a dimensionally accurate reconstruction of the
physical robot. Adjust its wheel geometry, speed, and sensor placement to
match your own model or hardware.

## 5. Start the existing ROS nodes without the Arduino node

The `simulation.launch.py` file starts Gazebo Sim with the included world,
bridges `/cmd_vel` and `/scan`, and starts the simulation adapter, obstacle
avoidance, system monitor, and (by default) AI controller and dashboard.
It intentionally does not start the physical-camera node. Build and source
the workspace as described in [`README.md`](README.md); then run:

```bash
ros2 launch drobotz_robot simulation.launch.py
```

The AI and dashboard can be disabled:

```bash
ros2 launch drobotz_robot simulation.launch.py enable_ai:=false enable_dashboard:=false
```

The existing camera node uses physical camera indices through OpenCV; it does
not consume Gazebo camera images. Leave it stopped unless you have real
cameras. To show simulated camera images in the dashboard, add a separate
Gazebo camera bridge and a ROS node that converts the bridged image message to
the dashboard's expected `sensor_msgs/msg/CompressedImage` topics:

- `/drobotz/camera/fpv/raw/compressed`
- `/drobotz/camera/fpv/processed/compressed`
- (and the equivalent `rear` topics if you have a rear camera)

The simulation adapter publishes zero/default values on `/drobotz/sensors`.
GPS and other optional dashboard panels need their own simulated data
publishers if you want them populated.

## 6. Check each link in the chain

Run these checks in sourced terminals:

```bash
gz topic -l
ros2 topic list
ros2 topic info /scan
ros2 topic echo /scan
ros2 topic echo /drobotz/hardware/status
```

To test the final ROS-to-Gazebo command bridge without the dashboard, publish a
`Twist` directly. This tests the bridge and Gazebo drive plugin, not the
project's adapter:

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 0.1}, angular: {z: 0.0}}'
```

Send a zero `Twist` to stop it:

```bash
ros2 topic pub --once /model/drobotz/cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 0.0}, angular: {z: 0.0}}'
```

Then test the project side in order:

1. Confirm the adapter reports simulated hardware as connected.
2. Select `BUTTONS` mode and publish or send one teleop command.
3. Confirm the adapter publishes the expected `Twist` and the model moves.
4. Confirm Gazebo scans arrive on ROS `/scan`.
5. Select `OBSTACLE` mode and check that `/drobotz/cmd/autonomy` receives
   `F`, `L`, or `S` when the scan changes.
6. Use the dashboard at `http://localhost:5001` after its status is connected.

If the robot turns the wrong way or moves backward for a forward command,
check wheel joint orientation and the adapter's sign mapping. If obstacle
avoidance always stops, inspect the scan topic name, QoS, frame orientation,
and valid scan range values.

## 7. Recommended simulation launch structure

The included simulation launch file starts:

- Gazebo Sim and the chosen world.
- The robot model.
- `ros_gz_bridge` with the drive and sensor topic mappings.
- The simulation hardware adapter (instead of `hardware_node`).
- The existing obstacle-avoidance node, dashboard, and optional AI/monitor.
- Any simulated camera or sensor conversion nodes you add.

Keeping this separate from the real-robot launch makes it harder to
accidentally send simulation commands to physical hardware.

## References

- [Gazebo Harmonic with ROS 2 integration](https://gazebosim.org/docs/harmonic/ros2_integration/)
- [Installing Gazebo with ROS and supported ROS/Gazebo pairings](https://gazebosim.org/docs/harmonic/ros_installation/)
- [Gazebo Harmonic: moving a differential-drive robot](https://gazebosim.org/docs/harmonic/moving_robot/)
- [Gazebo Sim and ROS project template guide](https://gazebosim.org/docs/harmonic/ros_gz_project_template_guide/)
