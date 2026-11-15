import os
import sys
import time
import json
import signal
import threading
import serial
import cv2
import psutil
import socket
import math

import subprocess
import re
from datetime import datetime
from flask import Flask, render_template, Response, request, jsonify, send_from_directory
from flask_socketio import SocketIO
from ultralytics import YOLO
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
import numpy as np
import random
from collections import defaultdict, deque
import subprocess
from collections import defaultdict, deque
import argparse
from collections import defaultdict, deque

import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv
import json
import time
from collections import defaultdict, deque
import socket
import urllib.request

# Updated for webcam perspective (modify these coordinates based on your camera view)
SOURCE = np.array([[320, 240], [960, 240], [1280, 720], [0, 720]])  # Default 640x480 webcam coordinates
TARGET_WIDTH = 25
TARGET_HEIGHT = 250

TARGET = np.array([
    [0, 0],
    [TARGET_WIDTH - 1, 0],
    [TARGET_WIDTH - 1, TARGET_HEIGHT - 1],
    [0, TARGET_HEIGHT - 1]
])

class ViewTransformer:
    def __init__(self, source: np.ndarray, target: np.ndarray) -> None:
        self.m = cv2.getPerspectiveTransform(source.astype(np.float32), target.astype(np.float32))

    def transform_points(self, points: np.ndarray) -> np.ndarray:
        if points.size == 0:
            return points
        return cv2.perspectiveTransform(points.reshape(-1, 1, 2), self.m).reshape(-1, 2)


def get_wifi_strength():
    try:
        result = subprocess.check_output(["iwconfig"], stderr=subprocess.DEVNULL).decode()
        match = re.search(r"Signal level=(-?\d+) dBm", result)
        if match:
            signal_dbm = int(match.group(1))
            quality = 2 * (signal_dbm + 100)
            return max(0, min(100, quality))
    except Exception as e:
        print(f"Error getting WiFi strength: {e}")
    return None

def get_battery_level():
    try:
        output = subprocess.check_output(["upower", "-i", "/org/freedesktop/UPower/devices/battery_BAT0"]).decode()
        match = re.search(r"percentage:\s+(\d+)%", output)
        if match:
            return int(match.group(1))
    except Exception as e:
        print(f"Error getting battery level: {e}")
    return None





view_transformer = ViewTransformer(source=SOURCE, target=TARGET)
coordinates = defaultdict(lambda: deque(maxlen=30))

detected_objects = []
detected_objects2 = []

app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading')

# Load YOLO model
model = YOLO('yolov8n.pt')

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RECORDINGS_DIR = os.path.join(BASE_DIR, 'recordings')
SENSOR_DATA_DIR = os.path.join(BASE_DIR, 'sensor_data')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
PLACEHOLDER_PATH = os.path.join(STATIC_DIR, 'placeholder.jpg')

# Constants for object detection
KNOWN_WIDTH = 0.5  # meters
FOCAL_LENGTH = 700  # pixels

# Global variables
arduino = None
camera = None
rear_camera = None
camera_lock = threading.Lock()
rear_camera_lock = threading.Lock()
fpv_recording = False
rear_recording = False
fpv_video_writer = None
rear_video_writer = None
running = True
arduino_connected = False
current_control_mode = 'BUTTONS'
camera_fps = 30
camera_resolution = (640, 480)
camera_quality = 70

# ROS2 variables
ros_node = None
lidar_subscriber = None
obstacle_avoidance_node = None
ros_thread = None
obstacle_avoidance_thread = None

sensor_data = {
    'temperature': None,
    'humidity': None,
    'impact_count': 0,
    'impact_detected': False,
    'sound_count': 0,
    'sound_detected': False,
    'touch_count': 0,
    'touch_detected': False,
    'tilt_count': 0,
    'tilt_detected': False,
    'pir_count': 0,
    'pir_detected': False,
    'radar_count': 0,
    'radar_detected': False,
    'rain_count': 0,
    'rain_detected': False,
    'gas_count': 0,
    'gas_detected': False,
    'flame_count': 0,
    'flame_detected': False,
    'accel_x': 0.0,
    'accel_y': 0.0,
    'accel_z': 0.0,


    'arduino_connected': False,
    'camera_connected': False,
    'rear_camera_connected': False,
    'lidar_connected': False,
    'control_mode': 'BUTTONS',
    'wifi_strength': 80,
    'gps_connected': False,
    'battery_level': 85,
    'battery_plugged': False,
    


    'temperature_severity': None,
    'temperature_level': None,
    'temperature_description': None,

    'cpu_usage_severity': None,
    'cpu_usage_level': None,
    'cpu_usage_description': None,

    'memory_usage_severity': None,
    'memory_usage_level': None,
    'memory_usage_description': None,

    'disk_usage_severity': None,    
    'disk_usage_level': None,
    'disk_usage_description': None,
    'fan_speed_rpm': 1200,

    'fan_speed_severity': None,
    'fan_speed_level': None,
    'fan_speed_description': None,
    'battery_percent': 100,
    'battery_severity': None,
    'battery_level': None,
    'battery_description': None,

    'private_ip': None,
    'public_ip': None,
    'cpu_usage': None,
    'memory_usage': None,
    'disk_usage': None,
    'network_bytes_sent': None,
    'network_bytes_recv': None,
    'last_update': 'Never',
    'hostname': socket.gethostname(),
    'ip_address': socket.gethostbyname(socket.gethostname()),
    'arduino_connected': False,
    'control_mode': 'BUTTONS',
    'obstacle_avoidance_active': False,
    'location': {
        'lat': None,
        'lon': None,
        'city': None,
        'country': "India"
    }
}

detected_objects = []

# Predefined Indian cities with approximate lat-lon
INDIAN_CITIES = [
    {"city": "Delhi", "lat": 28.6139, "lon": 77.2090},
    {"city": "Mumbai", "lat": 19.0760, "lon": 72.8777},
    {"city": "Bangalore", "lat": 12.9716, "lon": 77.5946},
    {"city": "Chennai", "lat": 13.0827, "lon": 80.2707},
    {"city": "Hyderabad", "lat": 17.3850, "lon": 78.4867},
    {"city": "Kolkata", "lat": 22.5726, "lon": 88.3639},
    {"city": "Pune", "lat": 18.5204, "lon": 73.8567},
]


def start_gps_simulation(sensor_data):
    # Pick a random city to start
    city_data = random.choice(INDIAN_CITIES)
    sensor_data['location'].update({
        'lat': city_data['lat'],
        'lon': city_data['lon'],
        'city': city_data['city'],
        'country': 'India'
    })

    def simulate_movement():
        while True:
            # Simulate small movement
            delta_lat = random.uniform(-0.0005, 0.0005)
            delta_lon = random.uniform(-0.0005, 0.0005)

            sensor_data['location']['lat'] += delta_lat
            sensor_data['location']['lon'] += delta_lon
            sensor_data['last_update'] = time.strftime("%Y-%m-%d %H:%M:%S")
            sensor_data['gps_connected'] = True

            print(f"[GPS UPDATE] {sensor_data['location']}")
            time.sleep(1)

    # Run simulation in background
    threading.Thread(target=simulate_movement, daemon=True).start()

# Example usage
start_gps_simulation(sensor_data)


class LidarSubscriber(Node):
    def __init__(self):
        super().__init__('lidar_subscriber')
        self.subscription = self.create_subscription(
            LaserScan,
            '/scan',
            self.listener_callback,
            10)
        self.latest_scan = None
        self.get_logger().info('LidarSubscriber node initialized')

    def listener_callback(self, msg):
        try:
            scan_data = {
                'angle_min': msg.angle_min,
                'angle_max': msg.angle_max,
                'angle_increment': msg.angle_increment,
                'time_increment': msg.time_increment,
                'scan_time': msg.scan_time,
                'range_min': msg.range_min,
                'range_max': msg.range_max,
                'ranges': [float(x) if not math.isinf(x) else 0.0 for x in msg.ranges],
                'intensities': [float(x) if not math.isinf(x) else 0.0 for x in msg.intensities],
                'timestamp': time.time()
            }
            self.latest_scan = scan_data
            socketio.emit('lidar_update', scan_data)
        except Exception as e:
            self.get_logger().error(f'Error processing scan: {str(e)}')

class ObstacleAvoidance(Node):
    def __init__(self):
        super().__init__('obstacle_avoidance')
        self.subscription = self.create_subscription(
            LaserScan,
            '/scan',
            self.scan_callback,
            10)
        self.arduino = arduino
        self.get_logger().info("Obstacle Avoidance Node started")
        self.active = False

    def scan_callback(self, msg):
        if not self.active or arduino is None or not arduino_connected:
            return
            
        front_distances = msg.ranges[0:30] + msg.ranges[-30:]
        valid_distances = [d for d in front_distances if not math.isinf(d) and not math.isnan(d)]
        
        if not valid_distances:
            return
            
        min_distance = min(valid_distances)

        if min_distance < 0.5:
            try:
                arduino.write(b'L')
                self.get_logger().info(f"Obstacle at {min_distance:.2f}m → Turning Left")
            except Exception as e:
                print(f"Error sending command to Arduino: {e}")
                sensor_data['arduino_connected'] = False
        else:
            try:
                arduino.write(b'F')
                self.get_logger().info(f"Clear path → Moving Forward")
            except Exception as e:
                print(f"Error sending command to Arduino: {e}")
                sensor_data['arduino_connected'] = False

def init_ros():
    global ros_node, lidar_subscriber, ros_thread
    try:
        rclpy.init()
        ros_node = rclpy.create_node('web_interface_node')
        lidar_subscriber = LidarSubscriber()
        
        def ros_spin():
            while running:
                rclpy.spin_once(lidar_subscriber, timeout_sec=0.1)
        
        ros_thread = threading.Thread(target=ros_spin, daemon=True)
        ros_thread.start()
        print("ROS2 initialized successfully")
    except Exception as e:
        print(f"Error initializing ROS2: {e}")

def get_system_temperature():
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = float(f.read().strip()) / 1000.0
            return temp
    except:
        return None

def get_private_ip():
    try:
        # Use socket to get private/local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return None

def get_public_ip():
    try:
        # Query public IP from an external service
        return urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
    except:
        return None

def get_severity(value, metric_type):
    if value is None:
        return "Medium", "P3", f"{metric_type.capitalize()} data not available."

    if metric_type == "temperature":
        if value > 90:
            return "Critical", "P1", "CPU overheating may cause thermal shutdown or hardware damage."
        elif 70 <= value <= 90:
            return "High", "P2", "High CPU temperature may reduce performance due to throttling."
        else:
            return "Medium", "P3", "CPU temperature is within acceptable range."

    elif metric_type == "cpu":
        if value > 90:
            return "Critical", "P1", "CPU usage critically high; system may freeze or lag."
        elif 70 <= value <= 90:
            return "High", "P2", "High CPU usage may slow down other tasks."
        else:
            return "Medium", "P3", "CPU usage is normal."

    elif metric_type == "memory":
        if value > 90:
            return "Critical", "P1", "Insufficient memory can cause application crashes or slowdowns."
        elif 70 <= value <= 90:
            return "High", "P2", "Memory usage is high and could affect performance."
        else:
            return "Medium", "P3", "Memory usage is stable."

    elif metric_type == "disk":
        if value > 90:
            return "Critical", "P1", "Disk nearly full; system logging and apps may fail."
        elif 70 <= value <= 90:
            return "High", "P2", "Disk usage high; free up space soon."
        else:
            return "Medium", "P3", "Disk usage is within limits."

    elif metric_type == "fan":
        if value < 500:
            return "Critical", "P1", "Fan speed too low — cooling failure may occur."
        elif 500 <= value <= 1500:
            return "High", "P2", "Fan speed lower than optimal — check ventilation."
        else:
            return "Medium", "P3", "Fan speed is within optimal range."

    elif metric_type == "battery":
        if value < 20:
            return "Critical", "P1", "Battery critically low — system may shut down."
        elif 20 <= value < 50:
            return "High", "P2", "Battery level is low — consider charging."
        else:
            return "Medium", "P3", "Battery level is sufficient."

    return "Medium", "P3", "No abnormal behavior detected."


def collect_system_metrics():
    try:
        # Core metrics
        system_temp = get_system_temperature()
        cpu_usage = psutil.cpu_percent()
        memory_usage = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage('/').percent

        # Fan speed
        fan_speed = None
        try:
            fans = psutil.sensors_fans()
            if fans:
                for fan_group in fans.values():
                    if fan_group:
                        fan_speed = fan_group[0].current
                        break
        except:
            fan_speed = None

        # Battery level
        battery_percent = None
        try:
            battery = psutil.sensors_battery()
            if battery:
                battery_percent = battery.percent
        except:
            battery_percent = None

        # Severity evaluations
        temp_sev, temp_lvl, temp_desc = get_severity(system_temp, "temperature")
        cpu_sev, cpu_lvl, cpu_desc = get_severity(cpu_usage, "cpu")
        mem_sev, mem_lvl, mem_desc = get_severity(memory_usage, "memory")
        disk_sev, disk_lvl, disk_desc = get_severity(disk_usage, "disk")
        fan_sev, fan_lvl, fan_desc = get_severity(fan_speed, "fan")
        bat_sev, bat_lvl, bat_desc = get_severity(battery_percent, "battery")

        return {
            'system_temp': system_temp,
            'cpu_usage': cpu_usage,
            'memory_usage': memory_usage,
            'disk_usage': disk_usage,
            'fan_speed': 1200,
            'battery_percent': 15,
            'network_bytes_sent': psutil.net_io_counters().bytes_sent,
            'network_bytes_recv': psutil.net_io_counters().bytes_recv,
            'private_ip': get_private_ip(),
            'public_ip': get_public_ip(),

            # Severity info
            'temperature_severity': temp_sev,
            'temperature_level': temp_lvl,
            'temperature_description': temp_desc,

            'cpu_usage_severity': cpu_sev,
            'cpu_usage_level': cpu_lvl,
            'cpu_usage_description': cpu_desc,

            'memory_usage_severity': mem_sev,
            'memory_usage_level': mem_lvl,
            'memory_usage_description': mem_desc,

            'disk_usage_severity': disk_sev,
            'disk_usage_level': disk_lvl,
            'disk_usage_description': disk_desc,

            'fan_speed_severity': fan_sev,
            'fan_speed_level': fan_lvl,
            'fan_speed_description': fan_desc,

            'battery_severity': bat_sev,
            'battery_level': bat_lvl,
            'battery_description': bat_desc
        }
    except Exception as e:
        print(f"Error collecting system metrics: {e}")
        return {}
    


def log_sensor_data():
    global detected_objects

    timestamp = datetime.now().isoformat()

    # --- Environmental Severity ---
    sensor_severity_map = {
        'flame': ('Critical', 'P1', 'Flame is detected and may cause fire hazard.'),
        'gas': ('Critical', 'P1', 'Gas leak detected; may pose explosion or poisoning risk.'),
        'impact': ('Critical', 'P1', 'Impact detected; may indicate collision or physical damage.'),
        'tilt': ('High', 'P2', 'Tilt detected; device may be unstable.'),
        'sound': ('High', 'P2', 'Unusual sound detected; may require investigation.'),
        'rain': ('Medium', 'P3', 'Rain detected; may affect visibility or traction.'),
        'pir': ('Medium', 'P3', 'Motion detected by PIR sensor.'),
        'radar': ('Medium', 'P3', 'Radar sensor triggered.')
    }

    triggered_sensors = []
    highest_env_level = 'P3'
    highest_env_type = 'Medium'
    severity_priority = {'P1': 1, 'P2': 2, 'P3': 3}
    descriptions_by_level = {'P1': [], 'P2': [], 'P3': []}

    for sensor, (stype, level, desc) in sensor_severity_map.items():
        if sensor_data.get(f'{sensor}_detected', False):
            triggered_sensors.append(sensor)
            descriptions_by_level[level].append(desc)
            if severity_priority[level] < severity_priority[highest_env_level]:
                highest_env_level = level
                highest_env_type = stype

    highest_env_desc = ' '.join(descriptions_by_level[highest_env_level]) \
        if descriptions_by_level[highest_env_level] else 'No significant environmental anomalies detected.'

    # --- Operational Severity ---
    operational_level = sensor_data.get('cpu_usage_level', 'P3')
    operational_type = sensor_data.get('cpu_usage_severity', 'Medium')
    operational_desc_by_level = {'P1': [], 'P2': [], 'P3': []}

    system_keys = [
        ('cpu_usage_level', 'cpu_usage_description'),
        ('temperature_level', 'temperature_description'),
        ('memory_usage_level', 'memory_usage_description'),
        ('disk_usage_level', 'disk_usage_description'),
        ('fan_speed_level', 'fan_speed_description'),
        ('battery_level', 'battery_description')
    ]

    for level_key, desc_key in system_keys:
        level = sensor_data.get(level_key, 'P3')
        desc = sensor_data.get(desc_key)
        if desc:
            operational_desc_by_level[level].append(desc)
        if severity_priority[level] < severity_priority[operational_level]:
            operational_level = level
            operational_type = sensor_data.get(desc_key.replace('_description', '_severity'), 'Medium')

    operational_description = ' '.join(operational_desc_by_level[operational_level]) \
        if operational_desc_by_level[operational_level] else 'No major operational issues detected.'

    log_data = {
        '@timestamp': timestamp,

        'environmental_severity_level': highest_env_level,
        'environmental_severity_type': highest_env_type,
        'environmental_severity_description': highest_env_desc,
        'environmental_sensors_triggered': triggered_sensors,

        'operational_severity_level': operational_level,
        'operational_severity_type': operational_type,
        'operational_severity_description': operational_description,

        'host': sensor_data['hostname'],
        'location': sensor_data.get('location', {}),
        'sensors': {
            'temperature': sensor_data['temperature'],
            'humidity': sensor_data['humidity'],
            'impact': {
                'count': sensor_data['impact_count'],
                'detected': sensor_data['impact_detected']
            },
            'sound': {
                'count': sensor_data['sound_count'],
                'detected': sensor_data['sound_detected']
            },
            'touch': {
                'count': sensor_data['touch_count'],
                'detected': sensor_data['touch_detected']
            },
            'tilt': {
                'count': sensor_data['tilt_count'],
                'detected': sensor_data['tilt_detected']
            },
            'pir': {
                'count': sensor_data['pir_count'],
                'detected': sensor_data['pir_detected']
            },
            'radar': {
                'count': sensor_data['radar_count'],
                'detected': sensor_data['radar_detected']
            },
            'rain': {
                'count': sensor_data['rain_count'],
                'detected': sensor_data['rain_detected']
            },
            'gas': {
                'count': sensor_data['gas_count'],
                'detected': sensor_data['gas_detected']
            },
            'flame': {
                'count': sensor_data['flame_count'],
                'detected': sensor_data['flame_detected']
            },
            'accelerometer': {
                'x': sensor_data['accel_x'],
                'y': sensor_data['accel_y'],
                'z': sensor_data['accel_z']
            }
        },
        'system': {
            'system_temp': sensor_data['system_temp'],
            'temperature_severity': sensor_data['temperature_severity'],
            'temperature_level': sensor_data['temperature_level'],
            'temperature_description': sensor_data['temperature_description'],

            'cpu_usage': sensor_data['cpu_usage'],
            'cpu_usage_severity': sensor_data['cpu_usage_severity'],
            'cpu_usage_level': sensor_data['cpu_usage_level'],
            'cpu_usage_description': sensor_data['cpu_usage_description'],

            'memory_usage': sensor_data['memory_usage'],
            'memory_usage_severity': sensor_data['memory_usage_severity'],
            'memory_usage_level': sensor_data['memory_usage_level'],
            'memory_usage_description': sensor_data['memory_usage_description'],

            'disk_usage': sensor_data['disk_usage'],
            'disk_usage_severity': sensor_data['disk_usage_severity'],
            'disk_usage_level': sensor_data['disk_usage_level'],
            'disk_usage_description': sensor_data['disk_usage_description'],

            'fan_speed': sensor_data['fan_speed'],
            'fan_speed_severity': sensor_data['fan_speed_severity'],
            'fan_speed_level': sensor_data['fan_speed_level'],
            'fan_speed_description': sensor_data['fan_speed_description'],

            'battery_percent': sensor_data['battery_percent'],
            'battery_severity': sensor_data['battery_severity'],
            'battery_level': sensor_data['battery_level'],
            'battery_description': sensor_data['battery_description'],

            'network_bytes_sent': sensor_data['network_bytes_sent'],
            'network_bytes_recv': sensor_data['network_bytes_recv'],

            'private_ip': sensor_data.get('private_ip'),
            'public_ip': sensor_data.get('public_ip')
        },

        'arduino_connected': sensor_data['arduino_connected'],
        'control_mode': sensor_data['control_mode'],
        'obstacle_avoidance_active': sensor_data['obstacle_avoidance_active'],
        'yolo_detections_front': detected_objects,
        'yolo_detections_rear': detected_objects2
    }

    filename = datetime.now().strftime("%Y-%m-%d") + ".json"
    filepath = os.path.join(SENSOR_DATA_DIR, filename)

    try:
        with open(filepath, 'a') as f:
            json.dump(log_data, f)
            f.write('\n')
    except Exception as e:
        print(f"Error writing to sensor log: {e}")
def update_system_metrics():
    global sensor_data
    while running:
        try:
            metrics = collect_system_metrics()
            sensor_data.update(metrics)
            log_sensor_data()
            time.sleep(5)
        except Exception as e:
            print(f"Error updating system metrics: {e}")
            time.sleep(10)

def init_hardware():
    global arduino, camera, rear_camera, arduino_connected
    
    # Initialize Arduino
    for port in ['/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyUSB0', '/dev/ttyUSB1']:
        try:
            if arduino is not None:
                arduino.close()
            arduino = serial.Serial(port, 115200, timeout=1)
            time.sleep(2)
            arduino_connected = True
            sensor_data['arduino_connected'] = True
            print(f"Arduino connected on {port}")
            break
        except Exception as e:
            print(f"Failed to connect to Arduino on {port}: {e}")
            arduino_connected = False
            sensor_data['arduino_connected'] = False
    
    # Initialize Front Camera
    try:
        if camera is not None:
            camera.release()
        for i in [0, 1]:  # Try common front camera indices
            cap = cv2.VideoCapture(i, cv2.CAP_V4L2)
            if cap.isOpened():
                print(f"Front camera found at index {i}")
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_resolution[0])
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_resolution[1])
                cap.set(cv2.CAP_PROP_FPS, camera_fps)
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
                camera = cap
                break
    except Exception as e:
        print(f"Error initializing front camera: {e}")
    
    # Initialize Rear Camera
    try:
        if rear_camera is not None:
            rear_camera.release()
        for i in [2,1, 3]:  # Try common rear camera indices
            cap = cv2.VideoCapture(i, cv2.CAP_V4L2)
            if cap.isOpened():
                print(f"Rear camera found at index {i}")
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_resolution[0])
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_resolution[1])
                cap.set(cv2.CAP_PROP_FPS, camera_fps)
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
                rear_camera = cap
                break
    except Exception as e:
        print(f"Error initializing rear camera: {e}")
    
    socketio.emit('connection_update', {
        'arduino_connected': arduino_connected,
        'camera_connected': camera is not None,
        'rear_camera_connected': rear_camera is not None
    })

def check_connections():
    global arduino_connected
    while running:
        try:
            if arduino is not None:
                try:
                    arduino.write('D'.encode())
                    arduino_connected = True
                except:
                    arduino_connected = False
            else:
                arduino_connected = False
            
            camera_connected = camera is not None and camera.isOpened()
            rear_camera_connected = rear_camera is not None and rear_camera.isOpened()
            
            sensor_data['arduino_connected'] = arduino_connected
            socketio.emit('connection_update', {
                'arduino_connected': arduino_connected,
                'camera_connected': camera_connected,
                'rear_camera_connected': rear_camera_connected
            })
            
            time.sleep(5)
        except Exception as e:
            print(f"Error checking connections: {e}")
            time.sleep(10)

def read_sensor_data():
    global arduino, sensor_data, running, arduino_connected
    while running:
        if not arduino_connected:
            time.sleep(1)
            init_hardware()
            continue
            
        try:
            while arduino.in_waiting and running:
                line = arduino.readline().decode('utf-8').strip()
                if line.startswith('SENSORS:'):
                    parts = line[8:].split(',')
                    if len(parts) >= 23:
                        sensor_data.update({
                            'temperature': float(parts[0]) if parts[0] != 'NaN' else None,
                            'humidity': float(parts[1]) if parts[1] != 'NaN' else None,
                            'impact_count': int(parts[2]),
                            'impact_detected': bool(int(parts[3])),
                            'sound_count': int(parts[4]),
                            'sound_detected': bool(int(parts[5])),
                            'touch_count': int(parts[6]),
                            'touch_detected': bool(int(parts[7])),
                            'tilt_count': int(parts[8]),
                            'tilt_detected': bool(int(parts[9])),
                            'pir_count': int(parts[10]),
                            'pir_detected': bool(int(parts[11])),
                            'rain_count': int(parts[12]),
                            'rain_detected': bool(int(parts[13])),
                            'accel_x': float(parts[14]),
                            'accel_y': float(parts[15]),
                            'accel_z': float(parts[16]),
                            'gas_count': int(parts[17]),
                            'gas_detected': bool(int(parts[18])),
                            'flame_count': int(parts[19]),
                            'flame_detected': bool(int(parts[20])),
                            'radar_count': int(parts[21]),
                            'radar_detected': bool(int(parts[22])),
                            'last_update': datetime.now().strftime('%H:%M:%S'),
                            'arduino_connected': True
                        })
                        
                        if len(parts) >= 24:
                            sensor_data['obstacle_avoidance_active'] = bool(int(parts[23]))
                        
                        display_data = {
                            'temperature': f"{sensor_data['temperature']:.1f}°C" if sensor_data['temperature'] is not None else "--",
                            'humidity': f"{sensor_data['humidity']:.1f}%" if sensor_data['humidity'] is not None else "--",
                            'impact_count': sensor_data['impact_count'],
                            'impact_detected': sensor_data['impact_detected'],
                            'sound_count': sensor_data['sound_count'],
                            'sound_detected': sensor_data['sound_detected'],
                            'touch_count': sensor_data['touch_count'],
                            'touch_detected': sensor_data['touch_detected'],
                            'tilt_count': sensor_data['tilt_count'],
                            'tilt_detected': sensor_data['tilt_detected'],
                            'pir_count': sensor_data['pir_count'],
                            'pir_detected': sensor_data['pir_detected'],
                            'radar_count': sensor_data['radar_count'],
                            'radar_detected': sensor_data['radar_detected'],
                            'rain_count': sensor_data['rain_count'],
                            'rain_detected': sensor_data['rain_detected'],
                            'gas_count': sensor_data['gas_count'],
                            'gas_detected': sensor_data['gas_detected'],
                            'flame_count': sensor_data['flame_count'],
                            'flame_detected': sensor_data['flame_detected'],
                            'accel_x': f"{sensor_data['accel_x']:.2f}",
                            'accel_y': f"{sensor_data['accel_y']:.2f}",
                            'accel_z': f"{sensor_data['accel_z']:.2f}",
                            'system_temp': f"{sensor_data['system_temp'] or '--'}°C",
                            'cpu_usage': f"{sensor_data['cpu_usage'] or '--'}%",
                            'memory_usage': f"{sensor_data['memory_usage'] or '--'}%",
                            'last_update': sensor_data['last_update'],
                            'arduino_connected': sensor_data['arduino_connected'],
                            'control_mode': sensor_data['control_mode'],
                            'obstacle_avoidance_active': sensor_data.get('obstacle_avoidance_active', False),

                            'battery_level': sensor_data['battery_level'],
                            'wifi_strength': sensor_data['wifi_strength']
                        }



                     
                        socketio.emit('sensor_update', display_data)
                        socketio.emit('accel_update', {
                            'x': sensor_data['accel_x'],
                            'y': sensor_data['accel_y'],
                            'z': sensor_data['accel_z']
                        })
                elif line:
                    print(f"Arduino: {line}")
        except Exception as e:
            print(f"Error reading sensor data: {e}")
            arduino_connected = False
            sensor_data['arduino_connected'] = False
            time.sleep(1)

def estimate_distance(focal_length, real_width, width_in_frame):
    if width_in_frame == 0:
        return 0
    return (real_width * focal_length) / width_in_frame 



def generate_frames(camera_source, recording_flag, video_writer_ref):
    global detected_objects, detected_objects2

    try:
        placeholder = cv2.imread(PLACEHOLDER_PATH)
        _, buffer = cv2.imencode('.jpg', placeholder, [cv2.IMWRITE_JPEG_QUALITY, camera_quality])
        placeholder_bytes = buffer.tobytes()
    except Exception as e:
        print(f"Error loading placeholder image: {e}")
        placeholder_bytes = b''

    prev_time = time.time()
    start_minute = int(prev_time // 60)
    object_summary = {}
    current_camera = 'front' if camera_source == camera else 'rear'
    blacklisted_labels = {"person", "knife"}  # Define blacklisted classes

    while running:
        frame_bytes = placeholder_bytes

        if camera_source is not None:
            with (camera_lock if camera_source == camera else rear_camera_lock):
                ret, frame = camera_source.read()
                if not ret:
                    continue

                current_time = time.time()
                delta_time = current_time - prev_time
                prev_time = current_time
                current_minute = int(current_time // 60)
                initial_minute = int(time.time() // 60)

                if current_minute != start_minute:
                    # Generate the key like "minute_0_front" or "minute_0_rear"
                    # Add 'minute' field to each object before appending
                    minute_value = current_minute - initial_minute  # Relative minute count
                    flattened_summary = []
                    for obj in object_summary.values():
                        obj_with_minute = {"minute": minute_value}
                        obj_with_minute.update(obj)
                        flattened_summary.append(obj_with_minute)

                    # Append flattened list directly
                    if current_camera == 'front':
                        detected_objects.extend(flattened_summary)
                    else:
                        detected_objects2.extend(flattened_summary)

                    object_summary = {}
                    start_minute = current_minute

                results = model(frame, stream=True)

                for result in results:
                    for box in result.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        label = result.names[int(box.cls[0])]
                        conf = float(box.conf[0])
                        width = x2 - x1
                        height = y2 - y1
                        bottom_center = np.array([[[(x1 + x2) / 2, y2]]], dtype=np.float32)

                        transformed_point = view_transformer.transform_points(bottom_center).astype(int)[0]
                        tx, ty = transformed_point
                        tracker_id = f"{label}{x1}{y1}{x2}{y2}"
                        coordinates[tracker_id].append((tx, ty))

                        if len(coordinates[tracker_id]) < 15:
                            speed_kmh = 0.0
                            movement = "Stationary"
                            direction = None
                            distance_m = None
                        else:
                            track = list(coordinates[tracker_id])
                            dx = track[-1][0] - track[0][0]
                            dy = track[-1][1] - track[0][1]
                            dist_px = (dx ** 2 + dy ** 2) ** 0.5
                            time_sec = len(track) / 20
                            px_per_sec = dist_px / time_sec
                            speed_kmh = (px_per_sec / 30) * 1
                            movement = "Stationary" if px_per_sec <= 30 else ("towards" if dy < 0 else "away")
                            direction = "right" if dx > 0 else "left"
                            distance_m = round(dist_px / 30, 2)

                        key = label
                        if key not in object_summary:
                            object_summary[key] = {
                                "camera_type": current_camera,
                                "object": label,
                                "count": 1,
                                "confidence": round(conf * 100, 1),
                                "width_m": round(width / 200, 2),
                                "height_m": round(height / 200, 2),
                                "distance": distance_m,
                                "speed_kmh": round(speed_kmh, 1),
                                "movement": movement,
                                "direction": direction,
                                "Blacklisted": "true" if label.lower() in blacklisted_labels else "false"
                            }
                        else:
                            object_summary[key]["count"] += 1

                        info = f"{label} {conf:.2f}, D:{distance_m or 0.0:.2f}m, S:{speed_kmh:.2f}km/h"
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(frame, info, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

                # UI overlay
                if not recording_flag:
                    y_pos = 30
                    cam_label = "FRONT CAM" if current_camera == 'front' else "REAR CAM"
                    cv2.putText(frame, cam_label, (10, y_pos),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    y_pos += 30
                    cv2.putText(frame, f"Objects: {len(object_summary)}", (10, y_pos),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    y_pos += 30
                    cv2.putText(frame, datetime.now().strftime("%H:%M:%S"), (10, y_pos),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                if recording_flag and video_writer_ref is not None:
                    video_writer_ref.write(frame)

                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, camera_quality])
                frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')



def start_recording(stream_type):
    global fpv_recording, rear_recording, fpv_video_writer, rear_video_writer
    
    if stream_type == 'fpv' and camera is None:
        return False
        
    if stream_type == 'rear' and rear_camera is None:
        return False
    
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(RECORDINGS_DIR, f"{stream_type}_recording_{timestamp}.avi")
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        
        if stream_type == 'fpv':
            fpv_video_writer = cv2.VideoWriter(filename, fourcc, camera_fps, camera_resolution)
            if not fpv_video_writer.isOpened():
                return False
            fpv_recording = True
        else:
            rear_video_writer = cv2.VideoWriter(filename, fourcc, camera_fps, camera_resolution)
            if not rear_video_writer.isOpened():
                return False
            rear_recording = True
            
        return True
    except Exception as e:
        print(f"Error starting {stream_type} recording: {e}")
        return False

def stop_recording(stream_type):
    global fpv_recording, rear_recording, fpv_video_writer, rear_video_writer
    
    if stream_type == 'fpv' and fpv_recording and fpv_video_writer is not None:
        fpv_video_writer.release()
        fpv_video_writer = None
        fpv_recording = False
    elif stream_type == 'rear' and rear_recording and rear_video_writer is not None:
        rear_video_writer.release()
        rear_video_writer = None
        rear_recording = False

def cleanup():
    global running, arduino, camera, rear_camera, fpv_video_writer, rear_video_writer, ros_node, obstacle_avoidance_node
    
    running = False
    
    if fpv_recording:
        stop_recording('fpv')
    if rear_recording:
        stop_recording('rear')
    
    if camera is not None:
        camera.release()
    if rear_camera is not None:
        rear_camera.release()
    
    if arduino is not None:
        arduino.close()
    
    try:
        if ros_node is not None:
            ros_node.destroy_node()
        if obstacle_avoidance_node is not None:
            obstacle_avoidance_node.destroy_node()
        rclpy.shutdown()
    except:
        pass

def signal_handler(sig, frame):
    cleanup()
    sys.exit(0)

@app.route('/')
def index():
    recordings = []
    for f in sorted(os.listdir(RECORDINGS_DIR), reverse=True):
        if f.endswith('.avi'):
            filepath = os.path.join(RECORDINGS_DIR, f)
            recordings.append({
                'name': f,
                'size': f"{os.path.getsize(filepath)//1024} KB",
                'date': datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d %H:%M')
            })
    
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(camera, fpv_recording, fpv_video_writer),
                  mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/rear_video_feed')
def rear_video_feed():
    return Response(generate_frames(rear_camera, rear_recording, rear_video_writer),
                  mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/location', methods=['POST'])
def receive_location():
    data = request.get_json()
    try:
        sensor_data['location'] = {
            'lat': data.get('lat'),
            'lon': data.get('lon'),
            'city': data.get('city'),
            'country': data.get('country')
        }
        return jsonify({"status": "Location received", "location": sensor_data['location']})
    except Exception as e:
        return jsonify({"status": "Error", "error": str(e)}), 400

@app.route('/start_recording/<stream>', methods=['POST'])
def start_recording_route(stream):
    if stream not in ['fpv', 'rear']:
        return jsonify({"status": "Invalid stream type"}), 400
    
    success = start_recording(stream)
    return jsonify({"status": "recording started" if success else "failed to start recording"})

@app.route('/stop_recording/<stream>', methods=['POST'])
def stop_recording_route(stream):
    if stream not in ['fpv', 'rear']:
        return jsonify({"status": "Invalid stream type"}), 400
    
    stop_recording(stream)
    return jsonify({"status": "recording stopped"})

@app.route('/download/<filename>')
def download_recording(filename):
    return send_from_directory(RECORDINGS_DIR, filename, as_attachment=True)

@app.route('/download_sensor_logs')
def download_sensor_logs():
    from io import BytesIO
    import zipfile
    
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for fname in os.listdir(SENSOR_DATA_DIR):
            if fname.endswith('.json'):
                zf.write(os.path.join(SENSOR_DATA_DIR, fname), fname)
    
    memory_file.seek(0)
    return Response(
        memory_file,
        mimetype='application/zip',
        headers={'Content-Disposition': 'attachment;filename=sensor_logs.zip'}
    )

@app.route('/reset_sensors', methods=['POST'])
def reset_sensors():
    if arduino is not None and arduino_connected:
        try:
            arduino.write('X'.encode())
            return jsonify({"status": "All sensors reset"})
        except:
            return jsonify({"status": "Error sending reset command"}), 500
    return jsonify({"status": "Arduino not connected"}), 500

@app.route('/set_control_mode/<mode>', methods=['POST'])
def set_control_mode(mode):
    global current_control_mode, obstacle_avoidance_node
    if mode in ['JOYSTICK', 'BUTTONS']:
        current_control_mode = mode
        sensor_data['control_mode'] = mode
        
        if obstacle_avoidance_node is not None:
            obstacle_avoidance_node.active = False
            sensor_data['obstacle_avoidance_active'] = False
            if arduino is not None and arduino_connected:
                try:
                    arduino.write('O'.encode())
                except:
                    pass
        
        socketio.emit('control_mode_update', {'mode': mode})
        return jsonify({"status": f"Control mode set to {mode}"})
    return jsonify({"status": "Invalid mode"}), 400

@app.route('/set_obstacle_mode/<state>', methods=['POST'])
def set_obstacle_mode(state):
    global obstacle_avoidance_node, obstacle_avoidance_thread, current_control_mode
    
    if state == 'on':
        if obstacle_avoidance_node is None:
            try:
                obstacle_avoidance_node = ObstacleAvoidance()
                def ros_spin():
                    rclpy.spin(obstacle_avoidance_node)
                
                obstacle_avoidance_thread = threading.Thread(target=ros_spin, daemon=True)
                obstacle_avoidance_thread.start()
            except Exception as e:
                print(f"Error starting obstacle avoidance: {e}")
                return jsonify({"status": "Error starting obstacle avoidance"}), 500
        
        obstacle_avoidance_node.active = True
        current_control_mode = 'OBSTACLE'
        sensor_data['control_mode'] = 'OBSTACLE'
        sensor_data['obstacle_avoidance_active'] = True
        
        if arduino is not None and arduino_connected:
            try:
                arduino.write('O'.encode())
            except:
                pass
        
        socketio.emit('control_mode_update', {'mode': 'OBSTACLE'})
        return jsonify({"status": "Obstacle avoidance mode activated"})
    else:
        if obstacle_avoidance_node is not None:
            obstacle_avoidance_node.active = False
            sensor_data['obstacle_avoidance_active'] = False
        
        if arduino is not None and arduino_connected:
            try:
                arduino.write('S'.encode())
                arduino.write('O'.encode())
            except:
                pass
        
        current_control_mode = 'BUTTONS'
        sensor_data['control_mode'] = 'BUTTONS'
        socketio.emit('control_mode_update', {'mode': 'BUTTONS'})
        return jsonify({"status": "Obstacle avoidance mode deactivated"})

@socketio.on('control')
def handle_control(command):
    global arduino_connected
    
    if current_control_mode == 'BUTTONS' and arduino is not None and arduino_connected:
        try:
            print(f"Sending command to Arduino: {command}")
            arduino.write(command.encode())
            arduino.flush()
        except Exception as e:
            print(f"Error sending command to Arduino: {e}")
            socketio.emit('control_error', {'message': str(e)})
            arduino_connected = False
            sensor_data['arduino_connected'] = False

@socketio.on('joystick')
def handle_joystick(data):
    global current_control_mode, arduino, arduino_connected
    
    if current_control_mode != 'JOYSTICK' or not arduino_connected:
        return
        
    try:
        x, y = map(int, data.split(','))
        
        if abs(y) > abs(x):
            if y > 100:
                arduino.write('F'.encode())
            elif y < -100:
                arduino.write('B'.encode())
            else:
                arduino.write('S'.encode())
        else:
            if x > 100:
                arduino.write('R'.encode())
            elif x < -100:
                arduino.write('L'.encode())
            else:
                arduino.write('S'.encode())
    except Exception as e:
        print(f"Error processing joystick data: {e}")

@socketio.on('start_recording')
def handle_start_recording(data):
    stream = data.get('stream')
    if stream in ['fpv', 'rear']:
        success = start_recording(stream)
        socketio.emit('recording_status', {
            'stream': stream,
            'recording': success
        })

@socketio.on('stop_recording')
def handle_stop_recording(data):
    stream = data.get('stream')
    if stream in ['fpv', 'rear']:
        stop_recording(stream)
        socketio.emit('recording_status', {
            'stream': stream,
            'recording': False
        })

@socketio.on('pause_recording')
def handle_pause_recording(data):
    stream = data.get('stream')
    if stream == 'fpv':
        socketio.emit('recording_status', {
            'stream': stream,
            'recording': False,
            'paused': True
        })
    elif stream == 'rear':
        socketio.emit('recording_status', {
            'stream': stream,
            'recording': False,
            'paused': True
        })

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    os.makedirs(RECORDINGS_DIR, exist_ok=True)
    os.makedirs(SENSOR_DATA_DIR, exist_ok=True)
    os.makedirs(STATIC_DIR, exist_ok=True)
    
    init_hardware()
    init_ros()
    threading.Thread(target=update_system_metrics, daemon=True).start()
    threading.Thread(target=read_sensor_data, daemon=True).start()
    threading.Thread(target=check_connections, daemon=True).start()
    
    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)
    finally:
        cleanup()

