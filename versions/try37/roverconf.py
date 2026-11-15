import os
import numpy as np
from datetime import datetime

# Updated for webcam perspective (modify these coordinates based on your camera view)
SOURCE = np.array([[320, 240], [960, 240], [1280, 720], [0, 720]]) # Default 640x480 webcam coordinates
TARGET_WIDTH = 25
TARGET_HEIGHT = 250
TARGET = np.array([
    [0, 0],
    [TARGET_WIDTH - 1, 0],
    [TARGET_WIDTH - 1, TARGET_HEIGHT - 1],
    [0, TARGET_HEIGHT - 1]
])

# Base Directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RECORDINGS_DIR = os.path.join(BASE_DIR, 'recordings')
SENSOR_DATA_DIR = os.path.join(BASE_DIR, 'sensor_data')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
PLACEHOLDER_PATH = os.path.join(STATIC_DIR, 'placeholder.jpg')

# Constants for object detection
KNOWN_WIDTH = 0.5  # meters
FOCAL_LENGTH = 700 # pixels

# Camera settings
CAMERA_FPS = 30
CAMERA_RESOLUTION = (1280, 720)
CAMERA_QUALITY = 30 # JPEG quality for streaming

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

# Initial sensor data structure
INITIAL_SENSOR_DATA = {
    'temperature': None, 'humidity': None, 'impact_count': 0, 'impact_detected': False,
    'sound_count': 0, 'sound_detected': False, 'touch_count': 0, 'touch_detected': False,
    'tilt_count': 0, 'tilt_detected': False, 'pir_count': 0, 'pir_detected': False,
    'radar_count': 0, 'radar_detected': False, 'rain_count': 0, 'rain_detected': False,
    'gas_count': 0, 'gas_detected': False, 'flame_count': 0, 'flame_detected': False,
    'accel_x': 0.0, 'accel_y': 0.0, 'accel_z': 0.0,
    'arduino_connected': False, 'camera_connected': False, 'rear_camera_connected': False,
    'lidar_connected': False, 'control_mode': 'BUTTONS', 'wifi_strength': 80,
    'gps_connected': False, 'battery_level': 85, 'battery_plugged': False,
    'temperature_severity': None, 'temperature_level': None, 'temperature_description': None,
    'cpu_usage_severity': None, 'cpu_usage_level': None, 'cpu_usage_description': None,
    'memory_usage_severity': None, 'memory_usage_level': None, 'memory_usage_description': None,
    'disk_usage_severity': None, 'disk_usage_level': None, 'disk_usage_description': None,
    'fan_speed_rpm': 1200, 'fan_speed_severity': None, 'fan_speed_level': None, 'fan_speed_description': None,
    'battery_percent': 100, 'battery_severity': None, 'battery_level': None, 'battery_description': None,
    'private_ip': None, 'public_ip': None, 'cpu_usage': None, 'memory_usage': None, 'disk_usage': None,
    'network_bytes_sent': None, 'network_bytes_recv': None,
    'last_update': 'Never',
    'hostname': socket.gethostname() if 'socket' in locals() else 'unknown',
    'ip_address': socket.gethostbyname(socket.gethostname()) if 'socket' in locals() else 'unknown',
    'obstacle_avoidance_active': False,
    'location': { 'lat': None, 'lon': None, 'city': None, 'country': "India" }
}
