# camera_processor.py

import cv2
import numpy as np
from ultralytics import YOLO
import time
from collections import defaultdict, deque
from datetime import datetime
import os
import threading

from roverconf import RECORDINGS_DIR, PLACEHOLDER_PATH, CAMERA_RESOLUTION, CAMERA_FPS, CAMERA_QUALITY, SOURCE, TARGET
from utils import ViewTransformer

class CameraProcessor:
    def __init__(self, sensor_data, socketio):
        self.sensor_data = sensor_data
        self.socketio = socketio
        self.model = YOLO('yolov8n.pt')
        self.view_transformer = ViewTransformer(source=SOURCE, target=TARGET)
        self.detected_objects_front = []
        self.detected_objects_rear = []
        self.coordinates = defaultdict(lambda: deque(maxlen=30))
        self.running = True

        self.fpv_recording = False
        self.rear_recording = False
        self.fpv_video_writer = None
        self.rear_video_writer = None

        self.camera_lock = threading.Lock()
        self.rear_camera_lock = threading.Lock()

        try:
            self.placeholder_bytes = self._load_placeholder_image()
        except Exception as e:
            print(f"Error loading placeholder image: {e}")
            self.placeholder_bytes = b''

    def _load_placeholder_image(self):
        placeholder = cv2.imread(PLACEHOLDER_PATH)
        _, buffer = cv2.imencode('.jpg', placeholder, [cv2.IMWRITE_JPEG_QUALITY, CAMERA_QUALITY])
        return buffer.tobytes()

    def generate_frames(self, camera_source, stream_type, camera_instance, camera_lock_instance, processing_enabled=True):
        prev_time = time.time()
        start_minute = int(prev_time // 60)
        object_summary = {} # Store summary per minute for current stream
        blacklisted_labels = {"person", "knife"} # Define blacklisted classes

        while self.running:
            frame_bytes = self.placeholder_bytes
            current_camera = stream_type

            if camera_instance is not None:
                with camera_lock_instance:
                    ret, frame = camera_instance.read()
                    if not ret:
                        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + self.placeholder_bytes + b'\r\n')
                        time.sleep(0.1) # Prevent busy-waiting
                        continue

                # --- MODIFIED SECTION ---
                if processing_enabled:
                    current_time = time.time()
                    prev_time = current_time
                    current_minute = int(current_time // 60)
                    initial_minute = int(time.time() // 60)

                    if current_minute != start_minute:
                        flattened_summary = []
                        for obj_key, obj_value in object_summary.items():
                            obj_with_minute = {"minute": current_minute - initial_minute}
                            obj_with_minute.update(obj_value)
                            flattened_summary.append(obj_with_minute)
                        
                        if current_camera == 'fpv':
                            self.detected_objects_front.extend(flattened_summary)
                        else:
                            self.detected_objects_rear.extend(flattened_summary)

                        object_summary = {}
                        start_minute = current_minute

                    results = self.model(frame, stream=True, verbose=False)

                    for result in results:
                        for box in result.boxes:
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            label = result.names[int(box.cls[0])]
                            conf = float(box.conf[0])
                            width, height = x2 - x1, y2 - y1

                            bottom_center = np.array([[[(x1 + x2) / 2, y2]]], dtype=np.float32)
                            transformed_point = self.view_transformer.transform_points(bottom_center).astype(int)[0]
                            tx, ty = transformed_point.flatten()

                            tracker_id = f"{label}_{x1}_{y1}_{x2}_{y2}"
                            self.coordinates[tracker_id].append((tx, ty))

                            speed_kmh, movement, direction, distance_m = 0.0, "Stationary", None, None

                            if len(self.coordinates[tracker_id]) >= 15:
                                track = list(self.coordinates[tracker_id])
                                dx, dy = track[-1][0] - track[0][0], track[-1][1] - track[0][1]
                                dist_px = (dx ** 2 + dy ** 2) ** 0.5
                                time_sec = len(track) / CAMERA_FPS
                                if time_sec > 0:
                                    px_per_sec = dist_px / time_sec
                                    speed_kmh = (px_per_sec / 30) * 1
                                    movement = "Stationary" if px_per_sec <= 30 else ("towards" if dy < 0 else "away")
                                    direction = "right" if dx > 0 else "left"
                                    distance_m = round(dist_px / 30, 2)

                            key = label
                            if key not in object_summary:
                                object_summary[key] = {
                                    "camera_type": current_camera, "object": label, "count": 1,
                                    "confidence": round(conf * 100, 1), "width_m": round(width / 200, 2),
                                    "height_m": round(height / 200, 2), "distance": distance_m,
                                    "speed_kmh": round(speed_kmh, 1), "movement": movement, "direction": direction,
                                    "Blacklisted": "true" if label.lower() in blacklisted_labels else "false"
                                }
                            else:
                                object_summary[key]["count"] += 1

                            info = f"{label} {conf:.2f}, D:{distance_m or 0.0:.2f}m, S:{speed_kmh:.2f}km/h"
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                            cv2.putText(frame, info, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

                    y_pos = 30
                    cam_label = "FRONT CAM (PROCESSED)" if current_camera == 'fpv' else "REAR CAM (PROCESSED)"
                    cv2.putText(frame, cam_label, (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    y_pos += 30
                    cv2.putText(frame, f"Objects: {len(object_summary)}", (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    y_pos += 30
                    cv2.putText(frame, datetime.now().strftime("%H:%M:%S"), (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                # --- END OF MODIFIED SECTION ---

                if (stream_type == 'fpv' and self.fpv_recording and self.fpv_video_writer is not None) or \
                   (stream_type == 'rear' and self.rear_recording and self.rear_video_writer is not None):
                    writer = self.fpv_video_writer if stream_type == 'fpv' else self.rear_video_writer
                    if writer:
                        writer.write(frame)

                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, CAMERA_QUALITY])
                frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    def start_recording(self, stream_type, camera_instance):
        if stream_type == 'fpv' and camera_instance is None:
            return False
        if stream_type == 'rear' and camera_instance is None:
            return False

        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = os.path.join(RECORDINGS_DIR, f"{stream_type}_recording_{timestamp}.mp4")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')

            if stream_type == 'fpv':
                self.fpv_video_writer = cv2.VideoWriter(filename, fourcc, CAMERA_FPS, CAMERA_RESOLUTION)
                if not self.fpv_video_writer.isOpened():
                    print(f"Error: FPV video writer not opened at {filename}")
                    return False
                self.fpv_recording = True
                print(f"Started FPV recording to {filename}")
            else: # rear
                self.rear_video_writer = cv2.VideoWriter(filename, fourcc, CAMERA_FPS, CAMERA_RESOLUTION)
                if not self.rear_video_writer.isOpened():
                    print(f"Error: Rear video writer not opened at {filename}")
                    return False
                self.rear_recording = True
                print(f"Started Rear recording to {filename}")
            return True
        except Exception as e:
            print(f"Error starting {stream_type} recording: {e}")
            return False

    def stop_recording(self, stream_type):
        if stream_type == 'fpv' and self.fpv_recording and self.fpv_video_writer is not None:
            self.fpv_video_writer.release()
            self.fpv_video_writer = None
            self.fpv_recording = False
            print("Stopped FPV recording")
        elif stream_type == 'rear' and self.rear_recording and self.rear_video_writer is not None:
            self.rear_video_writer.release()
            self.rear_video_writer = None
            self.rear_recording = False
            print("Stopped Rear recording")

    def get_detected_objects_data(self):
        front_data = list(self.detected_objects_front)
        rear_data = list(self.detected_objects_rear)
        self.detected_objects_front.clear()
        self.detected_objects_rear.clear()
        return front_data, rear_data

    def cleanup(self):
        self.running = False
        self.stop_recording('fpv')
        self.stop_recording('rear')
