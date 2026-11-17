import json
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String

from drobotz_robot.protocol import normalize_motion_command


_VALID_MODES = {"BUTTONS", "JOYSTICK", "AI", "OBSTACLE"}


def action_to_velocity(action, linear_speed, angular_speed):
    """Map controls to velocity commands for the car-like Ackermann model."""
    velocities = {
        "F": (linear_speed, 0.0),
        "B": (-linear_speed, 0.0),
        "L": (linear_speed, angular_speed),
        "R": (linear_speed, -angular_speed),
        "S": (0.0, 0.0),
    }
    try:
        return velocities[action]
    except KeyError as exc:
        raise ValueError(f"Unsupported movement action: {action}") from exc


class SimulationHardwareNode(Node):
    """Replaces the Arduino node with a guarded Gazebo Twist command interface."""

    def __init__(self):
        super().__init__("drobotz_simulation_hardware")
        self.declare_parameter("linear_speed_mps", 0.25)
        self.declare_parameter("angular_speed_rps", 0.25)
        self.declare_parameter("command_timeout_sec", 1.0)
        self.declare_parameter("scan_timeout_sec", 3.0)

        self._linear_speed = float(self.get_parameter("linear_speed_mps").value)
        self._angular_speed = float(self.get_parameter("angular_speed_rps").value)
        self._command_timeout = float(self.get_parameter("command_timeout_sec").value)
        self._scan_timeout = float(self.get_parameter("scan_timeout_sec").value)
        self._mode = "BUTTONS"
        self._last_scan_at = None
        self._last_command_at = None
        self._last_command = "S"
        self._velocity = (0.0, 0.0)
        self._sequence = []
        self._sequence_deadline = None
        self._sensor_values = self._empty_sensor_values()

        self._cmd_publisher = self.create_publisher(Twist, "/cmd_vel", 10)
        self._status_publisher = self.create_publisher(
            String, "/drobotz/hardware/status", 10
        )
        self._sensor_publisher = self.create_publisher(String, "/drobotz/sensors", 10)
        self.create_subscription(
            String, "/drobotz/control_mode", self._mode_callback, 10
        )
        self.create_subscription(
            String, "/drobotz/cmd/teleop", self._teleop_callback, 10
        )
        self.create_subscription(String, "/drobotz/cmd/ai", self._ai_callback, 10)
        self.create_subscription(
            String, "/drobotz/cmd/autonomy", self._autonomy_callback, 10
        )
        self.create_subscription(
            LaserScan, "/scan", self._scan_callback, qos_profile_sensor_data
        )
        self.create_timer(0.05, self._control_timer)
        self.create_timer(1.0, self._status_timer)
        self.get_logger().info(
            "Simulation hardware adapter ready; waiting for Gazebo LiDAR on /scan."
        )

    @staticmethod
    def _empty_sensor_values():
        values = {
            "temperature": None,
            "humidity": None,
            "accel_x": 0.0,
            "accel_y": 0.0,
            "accel_z": 0.0,
            "sensor_enabled": {},
        }
        for name in (
            "impact", "sound", "touch", "tilt", "pir",
            "rain", "gas", "flame", "radar",
        ):
            values[f"{name}_count"] = 0
            values[f"{name}_detected"] = False
        return values

    def _mode_callback(self, message):
        mode = message.data.strip().upper()
        if mode == "JOYMODE":
            mode = "JOYSTICK"
        if mode not in _VALID_MODES:
            self.get_logger().warning(f"Ignoring unsupported control mode: {message.data!r}")
            return
        if mode != self._mode:
            self._mode = mode
            self._stop()
            self.get_logger().info(f"Simulation control mode changed to {mode}.")

    def _teleop_callback(self, message):
        if self._mode not in {"BUTTONS", "JOYSTICK"}:
            return
        self._accept_command(message.data, allow_sequence=False)

    def _ai_callback(self, message):
        if self._mode != "AI":
            return
        self._accept_command(message.data, allow_sequence=True)

    def _autonomy_callback(self, message):
        if self._mode != "OBSTACLE":
            return
        self._accept_command(message.data, allow_sequence=False)

    def _accept_command(self, command, *, allow_sequence):
        normalized = normalize_motion_command(
            command, require_duration=allow_sequence
        )
        if normalized is None:
            self.get_logger().warning(f"Rejected invalid simulation command: {command!r}")
            return
        if not allow_sequence and "," in normalized:
            self.get_logger().warning("Manual/autonomy commands must contain one action.")
            return

        self._sequence.clear()
        self._sequence_deadline = None
        self._last_command = normalized
        self._last_command_at = time.monotonic()

        tokens = normalized.split(",")
        has_durations = any(len(token) > 1 for token in tokens)
        if allow_sequence or has_durations:
            self._sequence = [
                (token[0], int(token[1:]) if len(token) > 1 else 0)
                for token in tokens
            ]
            self._advance_sequence()
            return

        self._set_action(normalized[0])

    def _advance_sequence(self):
        now = time.monotonic()
        while self._sequence:
            action, duration_ms = self._sequence.pop(0)
            self._set_action(action)
            if action != "S" and duration_ms > 0:
                self._sequence_deadline = now + duration_ms / 1000.0
                return
        self._sequence_deadline = None
        self._set_action("S")

    def _set_action(self, action):
        self._velocity = action_to_velocity(
            action, self._linear_speed, self._angular_speed
        )

    def _stop(self):
        self._sequence.clear()
        self._sequence_deadline = None
        self._velocity = (0.0, 0.0)
        self._last_command = "S"
        self._last_command_at = None
        self._publish_twist()

    def _scan_callback(self, _message):
        self._last_scan_at = time.monotonic()

    def _control_timer(self):
        now = time.monotonic()
        if (
            self._sequence_deadline is not None
            and now >= self._sequence_deadline
        ):
            self._sequence_deadline = None
            self._advance_sequence()
        elif (
            self._sequence_deadline is None
            and self._velocity != (0.0, 0.0)
            and self._last_command_at is not None
            and now - self._last_command_at > self._command_timeout
        ):
            self.get_logger().warning("Simulation command timeout; stopping.")
            self._stop()
        self._publish_twist()

    def _publish_twist(self):
        message = Twist()
        message.linear.x, message.angular.z = self._velocity
        self._cmd_publisher.publish(message)

    def _status_timer(self):
        now = time.monotonic()
        connected = (
            self._last_scan_at is not None
            and 0.0 <= now - self._last_scan_at <= self._scan_timeout
        )
        status = String()
        status.data = json.dumps(
            {
                "arduino_connected": connected,
                "serial_connected": False,
                "simulated": True,
                "control_mode": self._mode,
                "last_command": self._last_command,
            }
        )
        self._status_publisher.publish(status)

        sensor_values = {
            **self._sensor_values,
            "arduino_connected": connected,
            "control_mode": self._mode,
            "obstacle_avoidance_active": self._mode == "OBSTACLE",
            "last_update": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        sensors = String()
        sensors.data = json.dumps(sensor_values, allow_nan=False)
        self._sensor_publisher.publish(sensors)

    def destroy_node(self):
        self._velocity = (0.0, 0.0)
        self._publish_twist()
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = SimulationHardwareNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
