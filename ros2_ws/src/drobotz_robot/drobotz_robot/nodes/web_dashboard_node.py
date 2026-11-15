import json
import math
import os
import threading
import time
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path

import rclpy
from ament_index_python.packages import get_package_share_directory
from flask import Flask, Response, jsonify, render_template, request, send_from_directory
from flask_socketio import SocketIO
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CompressedImage, LaserScan
from std_msgs.msg import String

from drobotz_robot.protocol import normalize_motion_command
from drobotz_robot.status import is_fresh


_CONTROL_MODES = {"BUTTONS", "JOYSTICK", "AI", "OBSTACLE"}


class WebDashboardNode(Node):
    """Bridges the preserved Flask/Socket.IO dashboard to the ROS 2 topic graph."""

    def __init__(self):
        super().__init__("drobotz_web_dashboard")
        self.declare_parameter("host", "0.0.0.0")
        self.declare_parameter("port", 5001)
        self.declare_parameter(
            "data_directory", os.getenv("DROBOTZ_DATA_DIR", str(Path.home() / ".ros" / "drobotz"))
        )
        self._data_directory = Path(self.get_parameter("data_directory").value).expanduser()
        self._recordings_directory = self._data_directory / "recordings"
        self._sensor_data_directory = self._data_directory / "sensor_data"
        self._state_lock = threading.Lock()
        self._state = {
            "control_mode": "BUTTONS",
            "arduino_connected": False,
            "camera_connected": False,
            "rear_camera_connected": False,
            "lidar_connected": False,
            "gps_connected": False,
            "joystick_connected": False,
            "sensor_enabled": {},
            "location": {},
        }
        self._images = {
            "fpv_raw": None,
            "fpv_processed": None,
            "rear_raw": None,
            "rear_processed": None,
        }
        self._image_lock = threading.Lock()
        self._hardware_status_received_at = None
        self._camera_status_received_at = None

        self._teleop_publisher = self.create_publisher(String, "/drobotz/cmd/teleop", 10)
        self._mode_publisher = self.create_publisher(String, "/drobotz/control_mode", 10)
        self._ai_prompt_publisher = self.create_publisher(String, "/drobotz/ai/prompt", 10)
        self._sensor_reset_publisher = self.create_publisher(String, "/drobotz/sensors/reset", 10)
        self._location_publisher = self.create_publisher(String, "/drobotz/location", 10)
        self._record_start_publisher = self.create_publisher(
            String, "/drobotz/camera/recording/start", 10
        )
        self._record_stop_publisher = self.create_publisher(
            String, "/drobotz/camera/recording/stop", 10
        )

        self.create_subscription(String, "/drobotz/sensors", self._sensor_callback, 10)
        self.create_subscription(
            String, "/drobotz/hardware/status", self._hardware_callback, 10
        )
        self.create_subscription(String, "/drobotz/system/status", self._system_callback, 10)
        self.create_subscription(String, "/drobotz/camera/status", self._camera_status_callback, 10)
        self.create_subscription(String, "/drobotz/ai/response", self._ai_response_callback, 10)
        self.create_subscription(String, "/drobotz/location", self._location_callback, 10)
        self.create_subscription(
            String, "/drobotz/camera/detections", self._detection_callback, 10
        )
        self.create_subscription(
            String, "/drobotz/camera/recording/status", self._recording_callback, 10
        )
        self.create_subscription(
            LaserScan, "/scan", self._lidar_callback, qos_profile_sensor_data
        )
        self.create_timer(1.0, self._publish_connection_status)
        for stream in ("fpv", "rear"):
            for kind in ("raw", "processed"):
                topic = f"/drobotz/camera/{stream}/{kind}/compressed"
                self.create_subscription(
                    CompressedImage,
                    topic,
                    lambda message, name=f"{stream}_{kind}": self._image_callback(name, message),
                    qos_profile_sensor_data,
                )

        self._configure_web_app()
        self._recordings_directory.mkdir(parents=True, exist_ok=True)
        self._sensor_data_directory.mkdir(parents=True, exist_ok=True)
        self._server_thread = threading.Thread(target=self._serve, daemon=True)
        self._server_thread.start()
        self.get_logger().info(
            f"Dashboard listening on http://{self.get_parameter('host').value}:"
            f"{self.get_parameter('port').value}"
        )

    def _configure_web_app(self):
        web_root = Path(get_package_share_directory("drobotz_robot")) / "web"
        self._app = Flask(
            __name__,
            template_folder=str(web_root / "templates"),
            static_folder=str(web_root / "static"),
        )
        self._socketio = SocketIO(self._app, async_mode="threading")

        @self._app.get("/")
        def index():
            return render_template("index.html", recordings=self._recordings())

        @self._app.get("/video_feed_raw")
        def fpv_raw():
            return self._video_stream("fpv_raw")

        @self._app.get("/video_feed_processed")
        def fpv_processed():
            return self._video_stream("fpv_processed")

        @self._app.get("/rear_video_feed_raw")
        def rear_raw():
            return self._video_stream("rear_raw")

        @self._app.get("/rear_video_feed_processed")
        def rear_processed():
            return self._video_stream("rear_processed")

        @self._app.post("/location")
        def receive_location():
            payload = request.get_json(silent=True) or {}
            try:
                location = {
                    "lat": float(payload["lat"]),
                    "lon": float(payload["lon"]),
                    "city": payload.get("city"),
                    "country": payload.get("country"),
                }
                if not -90 <= location["lat"] <= 90 or not -180 <= location["lon"] <= 180:
                    raise ValueError("latitude/longitude out of range")
            except (KeyError, TypeError, ValueError) as exc:
                return jsonify({"status": "Error", "error": str(exc)}), 400
            with self._state_lock:
                self._state["location"] = location
                self._state["gps_connected"] = True
            self._publish(self._location_publisher, json.dumps(location))
            self._socketio.emit("gps_update", location)
            return jsonify({"status": "Location received", "location": location})

        @self._app.post("/start_recording/<stream>")
        def start_recording(stream):
            return self._recording_request(stream, True)

        @self._app.post("/stop_recording/<stream>")
        def stop_recording(stream):
            return self._recording_request(stream, False)

        @self._app.get("/download/<path:filename>")
        def download_recording(filename):
            return send_from_directory(self._recordings_directory, filename, as_attachment=True)

        @self._app.get("/download_sensor_logs")
        def download_sensor_logs():
            memory_file = BytesIO()
            with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as archive:
                for path in self._sensor_data_directory.glob("*.jsonl"):
                    archive.write(path, path.name)
            memory_file.seek(0)
            return Response(
                memory_file.getvalue(),
                mimetype="application/zip",
                headers={"Content-Disposition": "attachment;filename=sensor_logs.zip"},
            )

        @self._app.post("/reset_sensors")
        @self._app.post("/reset_shock_count")
        def reset_sensors():
            with self._state_lock:
                connected = self._state.get("arduino_connected", False)
            if not connected:
                return jsonify({"status": "Arduino is not connected"}), 503
            self._publish(self._sensor_reset_publisher, "X")
            return jsonify({"status": "Sensor reset requested"})

        @self._app.post("/set_control_mode/<mode>")
        def set_control_mode(mode):
            if not self._set_mode(mode):
                return jsonify({"status": "Invalid mode"}), 400
            return jsonify({"status": f"Control mode set to {self._current_mode()}"})

        @self._app.post("/set_obstacle_mode/<state>")
        def set_obstacle_mode(state):
            if state not in {"on", "off"}:
                return jsonify({"status": "Invalid obstacle mode state"}), 400
            mode = "OBSTACLE" if state == "on" else "BUTTONS"
            self._set_mode(mode)
            return jsonify(
                {
                    "status": "Obstacle avoidance mode activated"
                    if state == "on"
                    else "Obstacle avoidance mode deactivated"
                }
            )

        @self._app.get("/get_control_mode")
        def get_control_mode():
            return jsonify(
                {"current_mode": self._current_mode(), "available_modes": sorted(_CONTROL_MODES)}
            )

        @self._app.post("/record")
        def toggle_recording():
            with self._state_lock:
                is_recording = bool(self._state.get("recording", {}).get("fpv", False))
            self._recording_request("fpv", not is_recording)
            return jsonify(
                {"status": "Recording started" if not is_recording else "Recording stopped"}
            )

        @self._app.get("/test_arduino/<command>")
        def test_arduino(command):
            with self._state_lock:
                connected = self._state.get("arduino_connected", False)
            normalized = normalize_motion_command(command)
            if not connected:
                return jsonify({"status": "Arduino is not connected"}), 503
            if normalized is None or "," in normalized:
                return jsonify({"status": "Command was not accepted"}), 400
            if not self._publish(self._teleop_publisher, normalized):
                return jsonify({"status": "Command was not accepted"}), 400
            return jsonify({"status": f"Command {normalized} sent"})

        @self._socketio.on("control")
        def control(command):
            if self._current_mode() != "BUTTONS":
                self._socketio.emit("control_error", {"message": "Select Manual mode first."})
                return
            normalized = normalize_motion_command(command) if isinstance(command, str) else None
            if normalized is None or "," in normalized:
                self._socketio.emit("control_error", {"message": "Invalid movement command."})
                return
            if not self._publish(self._teleop_publisher, normalized):
                self._socketio.emit("control_error", {"message": "Invalid movement command."})

        @self._socketio.on("joystick_input")
        def joystick_input(payload):
            if self._current_mode() != "JOYSTICK":
                return
            axes = payload.get("axes", []) if isinstance(payload, dict) else []
            if len(axes) < 4:
                return
            try:
                raw_x = float(axes[3])
                raw_y = float(axes[1])
            except (TypeError, ValueError):
                self._socketio.emit("control_error", {"message": "Invalid joystick axes."})
                return
            if not math.isfinite(raw_x) or not math.isfinite(raw_y):
                self._socketio.emit("control_error", {"message": "Invalid joystick axes."})
                return
            x = max(-1.0, min(1.0, raw_x))
            y = max(-1.0, min(1.0, raw_y))
            deadzone = 0.2
            command = (
                "F" if y > deadzone else
                "B" if y < -deadzone else
                "R" if x > deadzone else
                "L" if x < -deadzone else "S"
            )
            self._publish(self._teleop_publisher, command)
            self._socketio.emit(
                "joystick_status", {"x": round(x, 1), "y": round(y, 1), "command": command, "deadzone": deadzone}
            )

        @self._socketio.on("joystick")
        def legacy_joystick(payload):
            if self._current_mode() != "JOYSTICK" or not isinstance(payload, str):
                return
            try:
                x, y = (int(value) for value in payload.split(",", 1))
            except (ValueError, TypeError):
                self._socketio.emit("control_error", {"message": "Invalid joystick payload."})
                return
            deadzone = 50
            command = (
                "F" if abs(y) > abs(x) and y > deadzone else
                "B" if abs(y) > abs(x) and y < -deadzone else
                "R" if x > deadzone else
                "L" if x < -deadzone else "S"
            )
            self._publish(self._teleop_publisher, command)
            self._socketio.emit("joystick_status", {"x": x, "y": y, "command": command, "deadzone": deadzone})

        @self._socketio.on("ai_message")
        def ai_message(payload):
            if self._current_mode() != "AI":
                self._socketio.emit(
                    "ai_response", {"action": "error", "text": "AI mode is not active."}
                )
                return
            prompt = payload.get("text", "").strip() if isinstance(payload, dict) else ""
            if not prompt:
                self._socketio.emit(
                    "ai_response", {"action": "error", "text": "Enter a message first."}
                )
                return
            self._socketio.emit("ai_response", {"action": "start", "text": ""})
            self._publish(self._ai_prompt_publisher, prompt)

        @self._socketio.on("start_recording")
        def start_recording_event(payload):
            stream = payload.get("stream") if isinstance(payload, dict) else None
            self._recording_request(stream, True)

        @self._socketio.on("stop_recording")
        @self._socketio.on("pause_recording")
        def stop_recording_event(payload):
            stream = payload.get("stream") if isinstance(payload, dict) else None
            self._recording_request(stream, False)

        @self._socketio.on("joystick_connect")
        def joystick_connect(payload):
            connected = bool(payload.get("connected", False)) if isinstance(payload, dict) else False
            with self._state_lock:
                self._state["joystick_connected"] = connected
            self._socketio.emit("joystick_connection_update", {"connected": connected})

    def _serve(self):
        try:
            self._socketio.run(
                self._app,
                host=str(self.get_parameter("host").value),
                port=int(self.get_parameter("port").value),
                debug=False,
                use_reloader=False,
                allow_unsafe_werkzeug=True,
            )
        except OSError as exc:
            self.get_logger().error(f"Could not start dashboard server: {exc}")

    def _video_stream(self, name):
        def generate():
            while rclpy.ok():
                with self._image_lock:
                    frame = self._images[name]
                if frame:
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                else:
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n\r\n"
                threading.Event().wait(0.05)

        return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

    def _recordings(self):
        result = []
        if not self._recordings_directory.exists():
            return result
        for path in sorted(self._recordings_directory.iterdir(), reverse=True):
            if path.is_file() and path.suffix.lower() in {".mp4", ".avi", ".mov"}:
                try:
                    modified = datetime.fromtimestamp(path.stat().st_mtime)
                    result.append(
                        {
                            "name": path.name,
                            "size": f"{path.stat().st_size // 1024} KB",
                            "date": modified.strftime("%Y-%m-%d %H:%M"),
                        }
                    )
                except OSError as exc:
                    self.get_logger().warning(f"Could not read recording {path}: {exc}")
        return result

    def _recording_request(self, stream, start):
        if stream not in {"fpv", "rear"}:
            return jsonify({"status": "Invalid stream type"}), 400
        if start:
            with self._state_lock:
                connected = self._state.get(
                    "camera_connected" if stream == "fpv" else "rear_camera_connected",
                    False,
                )
            if not connected:
                status = {"stream": stream, "recording": False, "detail": "camera unavailable"}
                self._socketio.emit("recording_status", status)
                return jsonify({"status": "Camera is not connected"}), 503
        publisher = self._record_start_publisher if start else self._record_stop_publisher
        self._publish(publisher, stream)
        return jsonify({"status": "recording requested" if start else "recording stop requested"})

    @staticmethod
    def _publish(publisher, value):
        if not isinstance(value, str) or not value.strip():
            return False
        message = String()
        message.data = value.strip()
        publisher.publish(message)
        return True

    def _set_mode(self, mode):
        normalized = str(mode).upper()
        if normalized == "JOYMODE":
            normalized = "JOYSTICK"
        if normalized not in _CONTROL_MODES:
            return False
        with self._state_lock:
            self._state["control_mode"] = normalized
        self._publish(self._mode_publisher, normalized)
        self._socketio.emit("control_mode_update", {"mode": normalized})
        return True

    def _current_mode(self):
        with self._state_lock:
            return self._state["control_mode"]

    def _sensor_callback(self, message):
        try:
            sensors = json.loads(message.data)
        except json.JSONDecodeError as exc:
            self.get_logger().warning(f"Ignoring malformed sensor state: {exc}")
            return
        with self._state_lock:
            self._state.update(sensors)
        self._socketio.emit("sensor_update", self._format_sensor_update(sensors))
        if all(key in sensors for key in ("accel_x", "accel_y", "accel_z")):
            self._socketio.emit(
                "accel_update",
                {"x": sensors["accel_x"], "y": sensors["accel_y"], "z": sensors["accel_z"]},
            )
        if sensors.get("latitude") is not None and sensors.get("longitude") is not None:
            location = {
                "lat": sensors["latitude"],
                "lon": sensors["longitude"],
                "city": sensors.get("city"),
                "country": sensors.get("country"),
            }
            self._socketio.emit("gps_update", location)

    def _format_sensor_update(self, sensors):
        with self._state_lock:
            combined = {**self._state, **sensors}
        temperature = combined.get("temperature")
        humidity = combined.get("humidity")
        for key in ("temperature", "humidity"):
            value = combined.get(key)
            combined[key] = f"{value:.1f}{'°C' if key == 'temperature' else '%'}" if value is not None else "--"
        combined["system_temp"] = (
            f"{combined['system_temp']:.1f}°C"
            if isinstance(combined.get("system_temp"), (int, float))
            else "--"
        )
        combined["cpu_usage"] = (
            f"{combined['cpu_usage']:.0f}%"
            if isinstance(combined.get("cpu_usage"), (int, float))
            else "--"
        )
        combined["memory_usage"] = (
            f"{combined['memory_usage']:.0f}%"
            if isinstance(combined.get("memory_usage"), (int, float))
            else "--"
        )
        for axis in ("accel_x", "accel_y", "accel_z"):
            combined[axis] = f"{combined.get(axis, 0.0):.2f}"
        combined.setdefault("sensor_enabled", {})
        combined.setdefault("wifi_strength", "--")
        combined.setdefault("battery_level", combined.get("battery_percent", "--"))
        combined.setdefault("obstacle_avoidance_active", combined.get("control_mode") == "OBSTACLE")
        return combined

    def _hardware_callback(self, message):
        try:
            status = json.loads(message.data)
        except json.JSONDecodeError as exc:
            self.get_logger().warning(f"Ignoring malformed hardware status: {exc}")
            return
        with self._state_lock:
            self._state.update(status)
            self._hardware_status_received_at = time.monotonic()
        self._publish_connection_status()

    def _system_callback(self, message):
        try:
            metrics = json.loads(message.data)
        except json.JSONDecodeError as exc:
            self.get_logger().warning(f"Ignoring malformed system metrics: {exc}")
            return
        with self._state_lock:
            self._state.update(metrics)
            snapshot = dict(self._state)
        self._socketio.emit("sensor_update", self._format_sensor_update(snapshot))
        self._socketio.emit("status", metrics)

    def _camera_status_callback(self, message):
        try:
            status = json.loads(message.data)
        except json.JSONDecodeError as exc:
            self.get_logger().warning(f"Ignoring malformed camera status: {exc}")
            return
        with self._state_lock:
            self._camera_status_received_at = time.monotonic()
            self._state["camera_connected"] = status.get("fpv_connected", False)
            self._state["rear_camera_connected"] = status.get("rear_connected", False)
            self._state["recording"] = status.get("recording", self._state.get("recording", {}))
        self._publish_connection_status()

    def _publish_connection_status(self):
        now = time.monotonic()
        with self._state_lock:
            arduino_connected = is_fresh(
                self._hardware_status_received_at, 3.0, now
            ) and bool(self._state.get("arduino_connected", False))
            camera_status_fresh = is_fresh(self._camera_status_received_at, 5.0, now)
            camera_connected = camera_status_fresh and bool(
                self._state.get("camera_connected", False)
            )
            rear_camera_connected = camera_status_fresh and bool(
                self._state.get("rear_camera_connected", False)
            )
            self._state["arduino_connected"] = arduino_connected
            self._state["camera_connected"] = camera_connected
            self._state["rear_camera_connected"] = rear_camera_connected
            connection = {
                "arduino_connected": arduino_connected,
                "camera_connected": camera_connected,
                "rear_camera_connected": rear_camera_connected,
                "joystick_connected": self._state.get("joystick_connected", False),
            }
        self._socketio.emit("connection_update", connection)

    def _detection_callback(self, message):
        try:
            detections = json.loads(message.data)
        except json.JSONDecodeError as exc:
            self.get_logger().warning(f"Ignoring malformed detections: {exc}")
            return
        self._socketio.emit("detection_update", detections)

    def _location_callback(self, message):
        try:
            location = json.loads(message.data)
        except json.JSONDecodeError as exc:
            self.get_logger().warning(f"Ignoring malformed location: {exc}")
            return
        with self._state_lock:
            self._state["location"] = location
            self._state["gps_connected"] = True
        self._socketio.emit("gps_update", location)

    def _recording_callback(self, message):
        try:
            status = json.loads(message.data)
        except json.JSONDecodeError as exc:
            self.get_logger().warning(f"Ignoring malformed recording status: {exc}")
            return
        with self._state_lock:
            recording = dict(self._state.get("recording", {}))
            recording[status.get("stream")] = bool(status.get("recording"))
            self._state["recording"] = recording
        self._socketio.emit("recording_status", status)

    def _ai_response_callback(self, message):
        try:
            payload = json.loads(message.data)
        except json.JSONDecodeError as exc:
            self.get_logger().warning(f"Ignoring malformed AI response: {exc}")
            return
        status = payload.get("status", "done")
        if status == "error":
            self._socketio.emit("ai_response", {**payload, "action": "error"})
        elif status == "done":
            self._socketio.emit(
                "ai_response", {"action": "stream", "text": payload.get("text", "")}
            )
            self._socketio.emit("ai_response", {"action": "end", "text": ""})
        else:
            self._socketio.emit("ai_response", {**payload, "action": "end"})

    def _image_callback(self, name, message):
        with self._image_lock:
            self._images[name] = bytes(message.data)

    def _lidar_callback(self, scan):
        ranges = [float(value) if math.isfinite(value) else 0.0 for value in scan.ranges]
        self._socketio.emit(
            "lidar_update",
            {
                "angle_min": scan.angle_min,
                "angle_max": scan.angle_max,
                "angle_increment": scan.angle_increment,
                "time_increment": scan.time_increment,
                "scan_time": scan.scan_time,
                "range_min": scan.range_min,
                "range_max": scan.range_max,
                "ranges": ranges,
                "intensities": [
                    float(value) if math.isfinite(value) else 0.0 for value in scan.intensities
                ],
            },
        )


def main(args=None):
    rclpy.init(args=args)
    node = WebDashboardNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
