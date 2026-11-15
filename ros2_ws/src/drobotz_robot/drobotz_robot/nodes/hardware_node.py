import json
import math
import time
from datetime import datetime

import rclpy
import serial
from rclpy.node import Node
from std_msgs.msg import String

from drobotz_robot.protocol import normalize_motion_command
from drobotz_robot.status import is_fresh


_SENSOR_FIELDS = (
    "temperature", "humidity", "impact_count", "impact_detected", "sound_count",
    "sound_detected", "touch_count", "touch_detected", "tilt_count",
    "tilt_detected", "pir_count", "pir_detected", "rain_count", "rain_detected",
    "accel_x", "accel_y", "accel_z", "gas_count", "gas_detected",
    "flame_count", "flame_detected", "radar_count", "radar_detected",
)


class HardwareNode(Node):
    """Owns the Arduino serial link and gates all motor commands by control mode."""

    def __init__(self):
        super().__init__("drobotz_hardware")
        self.declare_parameter(
            "serial_ports", ["/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyUSB0", "/dev/ttyUSB1"]
        )
        self.declare_parameter("baudrate", 115200)
        self.declare_parameter("command_timeout_sec", 1.0)
        self.declare_parameter("reconnect_interval_sec", 2.0)
        self.declare_parameter("sensor_timeout_sec", 5.0)

        self._ports = list(self.get_parameter("serial_ports").value)
        self._baudrate = int(self.get_parameter("baudrate").value)
        self._command_timeout = float(self.get_parameter("command_timeout_sec").value)
        self._reconnect_interval = float(self.get_parameter("reconnect_interval_sec").value)
        self._sensor_timeout = float(self.get_parameter("sensor_timeout_sec").value)
        self._serial = None
        self._port_index = 0
        self._rx_buffer = bytearray()
        self._mode = "BUTTONS"
        self._last_connect_attempt = 0.0
        self._last_sensor_received_at = None
        self._last_command_at = 0.0
        self._watchdog_stopped = True
        self._last_command = None
        self._sensor_data = {
            "temperature": None,
            "humidity": None,
            "impact_count": 0,
            "impact_detected": False,
            "sound_count": 0,
            "sound_detected": False,
            "touch_count": 0,
            "touch_detected": False,
            "tilt_count": 0,
            "tilt_detected": False,
            "pir_count": 0,
            "pir_detected": False,
            "rain_count": 0,
            "rain_detected": False,
            "accel_x": 0.0,
            "accel_y": 0.0,
            "accel_z": 0.0,
            "gas_count": 0,
            "gas_detected": False,
            "flame_count": 0,
            "flame_detected": False,
            "radar_count": 0,
            "radar_detected": False,
            "arduino_connected": False,
            "obstacle_avoidance_active": False,
            "control_mode": "BUTTONS",
            "sensor_enabled": {},
            "last_update": None,
        }

        self._sensor_publisher = self.create_publisher(String, "/drobotz/sensors", 10)
        self._status_publisher = self.create_publisher(String, "/drobotz/hardware/status", 10)
        self._location_publisher = self.create_publisher(String, "/drobotz/location", 10)
        self.create_subscription(String, "/drobotz/control_mode", self._mode_callback, 10)
        self.create_subscription(String, "/drobotz/cmd/teleop", self._teleop_callback, 10)
        self.create_subscription(String, "/drobotz/cmd/ai", self._ai_callback, 10)
        self.create_subscription(String, "/drobotz/cmd/autonomy", self._autonomy_callback, 10)
        self.create_subscription(String, "/drobotz/sensors/reset", self._reset_callback, 10)
        self.create_timer(0.05, self._serial_timer)
        self.create_timer(0.1, self._watchdog_timer)
        self.create_timer(1.0, self._status_timer)
        self.get_logger().info("Arduino hardware node ready; waiting for a serial controller.")

    def _mode_callback(self, message):
        mode = message.data.strip().upper()
        if mode == "JOYMODE":
            mode = "JOYSTICK"
        if mode not in {"BUTTONS", "JOYSTICK", "AI", "OBSTACLE"}:
            self.get_logger().warning(f"Ignoring unsupported control mode: {message.data!r}")
            return
        if mode != self._mode:
            self._mode = mode
            self._write_stop()
            self._sensor_data["obstacle_avoidance_active"] = mode == "OBSTACLE"
            self._sensor_data["control_mode"] = mode
            self._publish_sensors()
            self.get_logger().info(f"Control mode changed to {mode}; motors stopped.")

    def _teleop_callback(self, message):
        if self._mode not in {"BUTTONS", "JOYSTICK"}:
            return
        if "," in message.data:
            self.get_logger().warning("Manual control accepts only one movement command at a time.")
            return
        self._accept_command(message.data)

    def _ai_callback(self, message):
        if self._mode == "AI":
            self._accept_command(message.data, require_duration=True)

    def _autonomy_callback(self, message):
        if self._mode == "OBSTACLE":
            if "," in message.data:
                self.get_logger().warning("Obstacle avoidance accepts one movement command at a time.")
                return
            self._accept_command(message.data)

    def _accept_command(self, command, require_duration=False):
        normalized = normalize_motion_command(command, require_duration=require_duration)
        if normalized is None:
            self.get_logger().warning(f"Rejected invalid movement command: {command!r}")
            return
        if not self._write_line(normalized):
            return
        durations = [int(token[1:]) for token in normalized.split(",") if len(token) > 1]
        self._last_command_at = time.monotonic() + sum(durations) / 1000.0
        self._watchdog_stopped = False
        self._last_command = normalized

    def _reset_callback(self, _message):
        self._write_line("X", validate=False)

    def _serial_timer(self):
        if self._serial is None or not self._serial.is_open:
            self._connect_if_due()
            return
        try:
            waiting = self._serial.in_waiting
            if waiting:
                self._rx_buffer.extend(self._serial.read(waiting))
                while b"\n" in self._rx_buffer:
                    line, _, remaining = self._rx_buffer.partition(b"\n")
                    self._rx_buffer = bytearray(remaining)
                    self._handle_serial_line(line.decode("utf-8", errors="replace").strip())
        except (serial.SerialException, OSError) as exc:
            self.get_logger().error(f"Arduino serial read failed: {exc}")
            self._close_serial()

    def _connect_if_due(self):
        now = time.monotonic()
        if now - self._last_connect_attempt < self._reconnect_interval or not self._ports:
            return
        self._last_connect_attempt = now
        for offset in range(len(self._ports)):
            index = (self._port_index + offset) % len(self._ports)
            port = self._ports[index]
            try:
                connection = serial.Serial(port, self._baudrate, timeout=0, write_timeout=0.5)
                self._serial = connection
                self._port_index = index
                self._last_sensor_received_at = None
                time.sleep(2.0)
                self.get_logger().info(f"Arduino connected on {port}")
                self._write_line("D", validate=False)
                return
            except (serial.SerialException, OSError) as exc:
                self.get_logger().debug(f"Could not open Arduino port {port}: {exc}")
        self._sensor_data["arduino_connected"] = False

    def _handle_serial_line(self, line):
        if not line:
            return
        if line.startswith("SENSORS:"):
            self._parse_sensor_data(line[len("SENSORS:"):])
        elif line.count(",") >= 22:
            self._parse_sensor_data(line)
        elif line.startswith("GPS:"):
            try:
                latitude, longitude = (float(part) for part in line[4:].split(",", 1))
                self._sensor_data.update(
                    {"latitude": latitude, "longitude": longitude, "gps_connected": True}
                )
                location = String()
                location.data = json.dumps({"lat": latitude, "lon": longitude})
                self._location_publisher.publish(location)
                self._publish_sensors()
            except ValueError:
                self.get_logger().warning(f"Ignoring malformed GPS frame: {line!r}")
        elif line.startswith("ERROR:"):
            self.get_logger().error(f"Arduino reported: {line[6:]}")

    def _parse_sensor_data(self, payload):
        parts = [part.strip() for part in payload.split(",")]
        while parts and not parts[0]:
            parts.pop(0)
        if len(parts) < len(_SENSOR_FIELDS):
            self.get_logger().warning(f"Ignoring short Arduino sensor frame ({len(parts)} fields).")
            return
        try:
            values = {}
            for name, value in zip(_SENSOR_FIELDS, parts):
                if name.endswith("_detected"):
                    values[name] = bool(int(value))
                elif name.endswith("_count"):
                    values[name] = int(value)
                elif name in {"temperature", "humidity"} and value.lower() == "nan":
                    values[name] = None
                elif name in {"temperature", "humidity", "accel_x", "accel_y", "accel_z"}:
                    parsed = float(value)
                    if math.isfinite(parsed):
                        values[name] = parsed
                    else:
                        values[name] = None if name in {"temperature", "humidity"} else 0.0
                else:
                    values[name] = float(value)
            values["obstacle_avoidance_active"] = self._mode == "OBSTACLE"
            values["control_mode"] = self._mode
            if len(parts) >= 33:
                sensor_names = (
                    "touch", "tilt", "rain", "gas", "flame",
                    "impact", "sound", "pir", "radar",
                )
                values["sensor_enabled"] = {
                    name: bool(int(parts[index + 24]))
                    for index, name in enumerate(sensor_names)
                }
            self._sensor_data.update(values)
            self._sensor_data["arduino_connected"] = True
            self._sensor_data["last_update"] = datetime.now().isoformat(timespec="seconds")
            self._last_sensor_received_at = time.monotonic()
            self._publish_sensors()
        except (ValueError, IndexError) as exc:
            self.get_logger().warning(f"Ignoring malformed Arduino sensor frame: {exc}")

    def _publish_sensors(self):
        message = String()
        message.data = json.dumps(self._sensor_data, allow_nan=False)
        self._sensor_publisher.publish(message)

    def _status_timer(self):
        serial_connected = bool(self._serial is not None and self._serial.is_open)
        sensor_connected = serial_connected and is_fresh(
            self._last_sensor_received_at, self._sensor_timeout
        )
        self._sensor_data["arduino_connected"] = sensor_connected
        sensor_age = (
            time.monotonic() - self._last_sensor_received_at
            if self._last_sensor_received_at is not None
            else None
        )
        message = String()
        message.data = json.dumps(
            {
                "arduino_connected": sensor_connected,
                "serial_connected": serial_connected,
                "sensor_data_age_sec": sensor_age,
                "port": self._serial.port if serial_connected else None,
                "control_mode": self._mode,
                "last_command": self._last_command,
            }
        )
        self._status_publisher.publish(message)

    def _watchdog_timer(self):
        if (
            self._mode in {"BUTTONS", "JOYSTICK", "AI", "OBSTACLE"}
            and not self._watchdog_stopped
            and time.monotonic() - self._last_command_at > self._command_timeout
        ):
            self._write_stop()
            self._watchdog_stopped = True
            self.get_logger().warning("Command timeout; sent a stop command.")

    def _write_stop(self):
        if self._serial is not None and self._serial.is_open:
            self._write_line("S", validate=False)
        self._last_command = "S"
        self._watchdog_stopped = True

    def _write_line(self, command, validate=True):
        if validate:
            command = normalize_motion_command(command)
            if command is None:
                self.get_logger().warning("Rejected invalid Arduino command.")
                return False
        if self._serial is None or not self._serial.is_open:
            return False
        try:
            self._serial.write((command.strip() + "\n").encode("ascii"))
            self._serial.flush()
            return True
        except (serial.SerialException, OSError, UnicodeEncodeError) as exc:
            self.get_logger().error(f"Arduino serial write failed: {exc}")
            self._close_serial()
            return False

    def _close_serial(self):
        if self._serial is not None:
            try:
                self._serial.close()
            except serial.SerialException as exc:
                self.get_logger().warning(f"Error closing Arduino port: {exc}")
        self._serial = None
        self._last_sensor_received_at = None
        self._sensor_data["arduino_connected"] = False

    def destroy_node(self):
        self._write_stop()
        self._close_serial()
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = HardwareNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
