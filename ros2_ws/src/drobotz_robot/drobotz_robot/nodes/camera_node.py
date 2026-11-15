import json
import os
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import rclpy
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CompressedImage
from std_msgs.msg import String

from drobotz_robot.status import is_fresh


class CameraNode(Node):
    """Captures front/rear cameras, optionally annotates YOLO detections and records video."""

    def __init__(self):
        super().__init__("drobotz_camera")
        self.declare_parameter("front_camera_indices", [0, 1, 2])
        self.declare_parameter("rear_camera_indices", [2, 1, 3, 4])
        self.declare_parameter("width", 1280)
        self.declare_parameter("height", 720)
        self.declare_parameter("fps", 20.0)
        self.declare_parameter("jpeg_quality", 75)
        self.declare_parameter("frame_timeout_sec", 4.0)
        self.declare_parameter("enable_object_detection", True)
        self.declare_parameter(
            "model_path",
            str(Path(get_package_share_directory("drobotz_robot")) / "models" / "yolov8n.pt"),
        )
        self.declare_parameter(
            "recordings_directory",
            str(
                Path(os.getenv("DROBOTZ_DATA_DIR", Path.home() / ".ros" / "drobotz"))
                / "recordings"
            ),
        )

        self._width = int(self.get_parameter("width").value)
        self._height = int(self.get_parameter("height").value)
        self._fps = max(1.0, float(self.get_parameter("fps").value))
        self._frame_timeout = float(self.get_parameter("frame_timeout_sec").value)
        self._jpeg_quality = min(100, max(1, int(self.get_parameter("jpeg_quality").value)))
        self._recordings_directory = Path(
            self.get_parameter("recordings_directory").value
        ).expanduser()
        self._model = None
        self._model_error_reported = False
        self._cameras = {"fpv": None, "rear": None}
        self._camera_indices = {"fpv": None, "rear": None}
        self._writers = {"fpv": None, "rear": None}
        self._last_open_attempt = {"fpv": 0.0, "rear": 0.0}
        self._last_frame_at = {"fpv": None, "rear": None}
        self._frame_sizes = {
            "fpv": (self._width, self._height),
            "rear": (self._width, self._height),
        }
        self._placeholder = self._load_placeholder()

        self._raw_publishers = {}
        self._processed_publishers = {}
        for stream in ("fpv", "rear"):
            self._raw_publishers[stream] = self.create_publisher(
                CompressedImage,
                f"/drobotz/camera/{stream}/raw/compressed",
                qos_profile_sensor_data,
            )
            self._processed_publishers[stream] = self.create_publisher(
                CompressedImage,
                f"/drobotz/camera/{stream}/processed/compressed",
                qos_profile_sensor_data,
            )
        self._detections_publisher = self.create_publisher(
            String, "/drobotz/camera/detections", 10
        )
        self._status_publisher = self.create_publisher(
            String, "/drobotz/camera/status", 10
        )
        self._recording_status_publisher = self.create_publisher(
            String, "/drobotz/camera/recording/status", 10
        )
        self.create_subscription(
            String, "/drobotz/camera/recording/start", self._start_recording, 10
        )
        self.create_subscription(
            String, "/drobotz/camera/recording/stop", self._stop_recording, 10
        )
        self.create_timer(1.0 / self._fps, self._capture_timer)
        self.create_timer(2.0, self._status_timer)
        self._open_cameras()
        self._load_model()
        self.get_logger().info("Camera node ready; compressed images are published on ROS topics.")

    def _load_placeholder(self):
        path = Path(get_package_share_directory("drobotz_robot")) / "web" / "static" / "placeholder.jpg"
        image = cv2.imread(str(path))
        if image is None:
            image = np.zeros((self._height, self._width, 3), dtype=np.uint8)
            cv2.putText(image, "Camera unavailable", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        success, encoded = cv2.imencode(".jpg", image)
        if not success:
            raise RuntimeError(f"Unable to encode camera placeholder: {path}")
        return encoded.tobytes()

    def _open_cameras(self):
        front_indices = list(self.get_parameter("front_camera_indices").value)
        rear_indices = list(self.get_parameter("rear_camera_indices").value)
        for stream, candidates in (("fpv", front_indices), ("rear", rear_indices)):
            self._try_open_camera(stream, candidates)

    def _try_open_camera(self, stream, candidates):
        other_index = self._camera_indices["rear" if stream == "fpv" else "fpv"]
        for index in candidates:
            index = int(index)
            if index == other_index:
                continue
            capture = cv2.VideoCapture(index, cv2.CAP_V4L2)
            if not capture.isOpened():
                capture.release()
                continue
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
            capture.set(cv2.CAP_PROP_FPS, self._fps)
            capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self._cameras[stream] = capture
            self._camera_indices[stream] = index
            self.get_logger().info(f"{stream} camera opened at index {index}.")
            return
        self.get_logger().warning(f"No {stream} camera found in candidates {candidates}.")

    def _load_model(self):
        if not self.get_parameter("enable_object_detection").value:
            self.get_logger().info("Object detection is disabled.")
            return
        model_path = Path(self.get_parameter("model_path").value).expanduser()
        if not model_path.is_file():
            self.get_logger().warning(
                f"YOLO model not found at {model_path}; camera streaming will remain available."
            )
            return
        try:
            from ultralytics import YOLO

            self._model = YOLO(str(model_path))
            self.get_logger().info(f"YOLO model loaded from {model_path}.")
        except ImportError:
            self.get_logger().warning(
                "Ultralytics is not installed; install requirements-ai.txt to enable YOLO."
            )
        except (OSError, RuntimeError, ValueError) as exc:
            self.get_logger().error(f"Could not load YOLO model {model_path}: {exc}")

    def _capture_timer(self):
        for stream in ("fpv", "rear"):
            capture = self._cameras[stream]
            if capture is None or not capture.isOpened():
                self._retry_camera(stream)
                self._publish_frame(stream, self._placeholder, self._placeholder)
                continue
            success, frame = capture.read()
            if not success:
                capture.release()
                self._cameras[stream] = None
                self._camera_indices[stream] = None
                self._last_frame_at[stream] = None
                self._publish_frame(stream, self._placeholder, self._placeholder)
                continue

            self._last_frame_at[stream] = time.monotonic()
            self._frame_sizes[stream] = (frame.shape[1], frame.shape[0])
            raw_bytes = self._encode(frame)
            processed = frame.copy()
            objects = self._detect_objects(stream, processed)
            processed_bytes = self._encode(processed)
            self._publish_frame(stream, raw_bytes, processed_bytes)
            writer = self._writers[stream]
            if writer is not None:
                writer.write(processed)
            detection_message = String()
            detection_message.data = json.dumps(
                {
                    "camera_type": stream,
                    "timestamp": datetime.now().isoformat(timespec="milliseconds"),
                    "objects": objects,
                },
                allow_nan=False,
            )
            self._detections_publisher.publish(detection_message)

    def _detect_objects(self, stream, frame):
        if self._model is None:
            return []
        objects = []
        try:
            result = self._model(frame, verbose=False)[0]
            for box in result.boxes:
                x1, y1, x2, y2 = (int(value) for value in box.xyxy[0].tolist())
                confidence = float(box.conf[0])
                label = result.names[int(box.cls[0])]
                width = max(1, x2 - x1)
                distance = round((0.5 * 700.0) / width, 2)
                item = {
                    "camera_type": stream,
                    "object": label,
                    "confidence": round(confidence * 100, 1),
                    "bbox": [x1, y1, x2, y2],
                    "distance": distance,
                    "width_m": round(width * distance / 700.0, 2),
                    "Blacklisted": str(label.lower() in {"person", "knife", "gun", "weapon"}).lower(),
                }
                objects.append(item)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(
                    frame,
                    f"{label} {confidence:.2f} D:{distance:.2f}m",
                    (x1, max(20, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (255, 255, 0),
                    2,
                )
        except Exception as exc:
            if not self._model_error_reported:
                self.get_logger().error(f"YOLO inference failed; disabling detections: {exc}")
                self._model_error_reported = True
            self._model = None
        return objects

    def _encode(self, frame):
        success, encoded = cv2.imencode(
            ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self._jpeg_quality]
        )
        return encoded.tobytes() if success else self._placeholder

    def _publish_frame(self, stream, raw_bytes, processed_bytes):
        stamp = self.get_clock().now().to_msg()
        for publisher, payload in (
            (self._raw_publishers[stream], raw_bytes),
            (self._processed_publishers[stream], processed_bytes),
        ):
            message = CompressedImage()
            message.header.stamp = stamp
            message.format = "jpeg"
            message.data = payload
            publisher.publish(message)

    def _retry_camera(self, stream):
        now = time.monotonic()
        if now - self._last_open_attempt[stream] < 5.0:
            return
        self._last_open_attempt[stream] = now
        previous = self._cameras[stream]
        if previous is not None:
            previous.release()
            self._cameras[stream] = None
            self._camera_indices[stream] = None
            self._last_frame_at[stream] = None
        candidates = (
            list(self.get_parameter("front_camera_indices").value)
            if stream == "fpv"
            else list(self.get_parameter("rear_camera_indices").value)
        )
        self._try_open_camera(stream, candidates)

    def _status_timer(self):
        message = String()
        connected = {
            stream: bool(
                self._cameras[stream]
                and self._cameras[stream].isOpened()
                and is_fresh(self._last_frame_at[stream], self._frame_timeout)
            )
            for stream in ("fpv", "rear")
        }
        message.data = json.dumps(
            {
                "fpv_connected": connected["fpv"],
                "rear_connected": connected["rear"],
                "fpv_index": self._camera_indices["fpv"],
                "rear_index": self._camera_indices["rear"],
                "object_detection_enabled": self._model is not None,
                "recording": {stream: writer is not None for stream, writer in self._writers.items()},
            }
        )
        self._status_publisher.publish(message)

    def _start_recording(self, message):
        stream = message.data.strip().lower()
        if stream not in self._cameras:
            self.get_logger().warning(f"Unknown camera stream requested for recording: {stream}")
            return
        capture = self._cameras[stream]
        if capture is None or not capture.isOpened():
            self._publish_recording_status(stream, False, "camera unavailable")
            return
        if self._writers[stream] is not None:
            self._publish_recording_status(stream, True, "already recording")
            return
        try:
            self._recordings_directory.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            path = self._recordings_directory / f"{stream}_recording_{timestamp}.mp4"
            codec = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(path), codec, self._fps, self._frame_sizes[stream])
            if not writer.isOpened():
                writer.release()
                raise OSError(f"Could not open video writer for {path}")
            self._writers[stream] = writer
            self._publish_recording_status(stream, True, str(path))
        except (OSError, cv2.error) as exc:
            self.get_logger().error(f"Could not start {stream} recording: {exc}")
            self._publish_recording_status(stream, False, str(exc))

    def _stop_recording(self, message):
        stream = message.data.strip().lower()
        if stream not in self._writers:
            self.get_logger().warning(f"Unknown camera stream requested to stop: {stream}")
            return
        writer = self._writers[stream]
        if writer is not None:
            writer.release()
            self._writers[stream] = None
        self._publish_recording_status(stream, False, "stopped")

    def _publish_recording_status(self, stream, recording, detail):
        message = String()
        message.data = json.dumps(
            {"stream": stream, "recording": recording, "detail": detail}
        )
        self._recording_status_publisher.publish(message)

    def destroy_node(self):
        for stream in self._writers:
            if self._writers[stream] is not None:
                self._writers[stream].release()
        for capture in self._cameras.values():
            if capture is not None:
                capture.release()
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = CameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
