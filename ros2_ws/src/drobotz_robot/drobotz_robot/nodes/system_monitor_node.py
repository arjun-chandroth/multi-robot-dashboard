import json
import os
import socket
from datetime import datetime
from pathlib import Path

import psutil
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


def _read_cpu_temperature():
    for path in ("/sys/class/thermal/thermal_zone0/temp", "/sys/class/hwmon/hwmon0/temp1_input"):
        try:
            value = float(Path(path).read_text().strip())
            return value / 1000.0 if value > 1000 else value
        except (OSError, ValueError):
            continue
    return None


def _severity(value, metric):
    if value is None:
        return "Medium", "P3", f"{metric.capitalize()} data not available."
    thresholds = {
        "temperature": (70, 90),
        "cpu": (70, 90),
        "memory": (70, 90),
        "disk": (70, 90),
        "battery": (20, 50),
    }
    if metric == "battery":
        if value < thresholds[metric][0]:
            return "Critical", "P1", "Battery critically low."
        if value < thresholds[metric][1]:
            return "High", "P2", "Battery level is low."
        return "Low", "P4", "Battery level is sufficient."
    lower, upper = thresholds.get(metric, (None, None))
    if upper is not None and value > upper:
        return "Critical", "P1", f"{metric.capitalize()} level is critically high."
    if lower is not None and value >= lower:
        return "High", "P2", f"{metric.capitalize()} level is high."
    return "Low", "P4", f"{metric.capitalize()} level is within normal range."


class SystemMonitorNode(Node):
    """Publishes system health and appends sensor snapshots to daily JSONL files."""

    def __init__(self):
        super().__init__("drobotz_system_monitor")
        self.declare_parameter(
            "data_directory",
            str(
                Path(os.getenv("DROBOTZ_DATA_DIR", Path.home() / ".ros" / "drobotz"))
                / "sensor_data"
            ),
        )
        self.declare_parameter("update_interval_sec", 5.0)
        self._data_directory = Path(self.get_parameter("data_directory").value).expanduser()
        self._update_interval = float(self.get_parameter("update_interval_sec").value)
        self._sensors = {}
        self._detections = {"front": [], "rear": []}
        self._hardware_status = {}
        self._location = {}
        self._publisher = self.create_publisher(String, "/drobotz/system/status", 10)
        self.create_subscription(String, "/drobotz/sensors", self._sensor_callback, 10)
        self.create_subscription(
            String, "/drobotz/camera/detections", self._detection_callback, 10
        )
        self.create_subscription(
            String, "/drobotz/hardware/status", self._hardware_callback, 10
        )
        self.create_subscription(String, "/drobotz/location", self._location_callback, 10)
        self.create_timer(self._update_interval, self._publish_metrics)
        self.get_logger().info(f"System metrics and JSONL logs: {self._data_directory}")

    def _sensor_callback(self, message):
        try:
            self._sensors = json.loads(message.data)
        except json.JSONDecodeError as exc:
            self.get_logger().warning(f"Ignoring malformed sensor state: {exc}")

    def _detection_callback(self, message):
        try:
            data = json.loads(message.data)
            stream = data.get("camera_type")
            if stream in self._detections:
                self._detections[stream] = data.get("objects", [])
        except (json.JSONDecodeError, AttributeError) as exc:
            self.get_logger().warning(f"Ignoring malformed detection message: {exc}")

    def _hardware_callback(self, message):
        try:
            self._hardware_status = json.loads(message.data)
        except json.JSONDecodeError as exc:
            self.get_logger().warning(f"Ignoring malformed hardware status: {exc}")

    def _location_callback(self, message):
        try:
            self._location = json.loads(message.data)
        except json.JSONDecodeError as exc:
            self.get_logger().warning(f"Ignoring malformed location: {exc}")

    def _publish_metrics(self):
        try:
            metrics = self._collect_metrics()
            payload = {
                **metrics,
                "hostname": socket.gethostname(),
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
            message = String()
            message.data = json.dumps(payload, allow_nan=False)
            self._publisher.publish(message)
            self._append_log(payload)
        except (OSError, psutil.Error, TypeError, ValueError) as exc:
            self.get_logger().error(f"Could not collect/publish system metrics: {exc}")

    def _collect_metrics(self):
        values = {
            "system_temp": _read_cpu_temperature(),
            "cpu_usage": psutil.cpu_percent(interval=None),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage("/").percent,
            "network_bytes_sent": psutil.net_io_counters().bytes_sent,
            "network_bytes_recv": psutil.net_io_counters().bytes_recv,
            "private_ip": self._private_ip(),
            "battery_percent": None,
            "battery_plugged": None,
            "fan_speed_rpm": None,
        }
        try:
            battery = psutil.sensors_battery()
            if battery:
                values["battery_percent"] = battery.percent
                values["battery_plugged"] = battery.power_plugged
        except (AttributeError, OSError) as exc:
            self.get_logger().debug(f"Battery metrics unavailable: {exc}")
        try:
            fans = psutil.sensors_fans()
            if fans:
                values["fan_speed_rpm"] = next(
                    (fan.current for group in fans.values() for fan in group), None
                )
        except (AttributeError, OSError) as exc:
            self.get_logger().debug(f"Fan metrics unavailable: {exc}")

        for key, metric in (
            ("system_temp", "temperature"),
            ("cpu_usage", "cpu"),
            ("memory_usage", "memory"),
            ("disk_usage", "disk"),
            ("battery_percent", "battery"),
        ):
            severity, level, description = _severity(values[key], metric)
            values[f"{metric}_severity"] = severity
            values[f"{metric}_level"] = level
            values[f"{metric}_description"] = description
        return values

    @staticmethod
    def _private_ip():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
                connection.connect(("192.0.2.1", 1))
                return connection.getsockname()[0]
        except OSError:
            return None

    def _append_log(self, metrics):
        self._data_directory.mkdir(parents=True, exist_ok=True)
        filename = datetime.now().strftime("%Y-%m-%d") + ".jsonl"
        entry = {
            "@timestamp": metrics["timestamp"],
            "host": metrics["hostname"],
            "location": self._location,
            "sensors": self._sensors,
            "system": metrics,
            "arduino_connected": self._hardware_status.get("arduino_connected", False),
            "control_mode": self._hardware_status.get("control_mode", "BUTTONS"),
            "yolo_detections_front": self._detections["front"],
            "yolo_detections_rear": self._detections["rear"],
        }
        path = self._data_directory / filename
        with path.open("a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(entry, allow_nan=False) + os.linesep)


def main(args=None):
    rclpy.init(args=args)
    node = SystemMonitorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
