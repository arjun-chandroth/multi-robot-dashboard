import os
import numpy as np
from datetime import datetime
import socket

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

# Joystick Configuration
JOYSTICK_DEADZONE = 0.2  # Ignore small joystick movements
JOYSTICK_CHECK_INTERVAL = 15  # Check joystick connection every 15 seconds
JOYSTICK_AXIS_MAPPING = {
    'left_x': 0,    # Left stick horizontal
    'left_y': 1,    # Left stick vertical  
    'right_x': 2,   # Right stick horizontal
    'right_y': 3,   # Right stick vertical
    'lt': 4,        # Left trigger
    'rt': 5         # Right trigger
}
JOYSTICK_BUTTON_MAPPING = {
    'a': 0,
    'b': 1,
    'x': 2,
    'y': 3,
    'lb': 4,
    'rb': 5,
    'back': 6,
    'start': 7,
    'guide': 8,
    'l3': 9,
    'r3': 10
}

# Control Modes
CONTROL_MODES = {
    'BUTTONS': 'Button Control',
    'JOYSTICK': 'Joystick/Gamepad Control', 
    'JOYMODE': 'Joystick Mode (Legacy)',
    'AI': 'AI Voice Control',
    'OBSTACLE': 'Autonomous Obstacle Avoidance'
}

# Motor Commands
MOTOR_COMMANDS = {
    'FORWARD': 'F',
    'BACKWARD': 'B', 
    'LEFT': 'L',
    'RIGHT': 'R',
    'STOP': 'S',
    'OBSTACLE_MODE': 'O',
    'RESET_SENSORS': 'X',
    'DIAGNOSTIC': 'D'
}

# Arduino Communication
ARDUINO_BAUDRATE = 115200
ARDUINO_TIMEOUT = 1
ARDUINO_PORTS = ['/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyUSB0', '/dev/ttyUSB1']
ARDUINO_RECONNECT_DELAY = 5  # seconds

# Sensor Thresholds
SENSOR_THRESHOLDS = {
    'OBSTACLE_DISTANCE': 0.5,  # meters
    'TEMPERATURE_ALERT': 70.0, # °C
    'TEMPERATURE_CRITICAL': 90.0, # °C
    'IMPACT_SENSITIVITY': 100, # arbitrary units
    'SOUND_THRESHOLD': 500,    # dB
    'GAS_THRESHOLD': 300,      # ppm
    'FLAME_THRESHOLD': 100     # arbitrary units
}

# System Monitoring
SYSTEM_UPDATE_INTERVAL = 5  # seconds
SENSOR_LOG_INTERVAL = 5     # seconds
CONNECTION_CHECK_INTERVAL = 5  # seconds

# AI Configuration
AI_MODEL_NAME = "phi"
OLLAMA_BASE_URL = "http://localhost:11434/api/generate"
AI_RESPONSE_TIMEOUT = 30  # seconds
AI_VOICE_RATE = 150
AI_VOICE_VOLUME = 0.9

# ROS2 Configuration
ROS_NODE_NAME = "rover_controller"
LIDAR_TOPIC = "/scan"
OBSTACLE_AVOIDANCE_TOPIC = "/scan"

# Video Recording
VIDEO_FORMAT = "mp4"
VIDEO_CODEC = "mp4v"
RECORDING_SEGMENT_DURATION = 300  # 5 minutes per segment

# Object Detection
YOLO_MODEL_PATH = "yolov8n.pt"
BLACKLISTED_OBJECTS = {"person", "knife", "gun", "weapon"}
TRACKING_HISTORY_LENGTH = 30  # frames
CONFIDENCE_THRESHOLD = 0.5
SPEED_CALIBRATION_FACTOR = 1.0  # Adjust based on real-world testing

# Network Configuration
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5001
SOCKETIO_ASYNC_MODE = "threading"
CORS_ORIGINS = "*"

# Security Settings
API_KEY_REQUIRED = False
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_MAX_SIZE = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 5

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

SENSOR_ENABLED = {
    'touch': False,
    'tilt': False,
    'rain': False,
    'gas': False,
    'flame': False,
    'impact': False,
    'sound': False,
    'pir': False,
    'radar': False,
}

# Initial sensor data structure
INITIAL_SENSOR_DATA = {
    # Environmental Sensors
    'temperature': None, 
    'humidity': None, 
    
    # Event Counters
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
    
    # Accelerometer Data
    'accel_x': 0.0, 
    'accel_y': 0.0, 
    'accel_z': 0.0,
    
    # Hardware Connection Status
    'arduino_connected': False, 
    'camera_connected': False, 
    'rear_camera_connected': False,
    'lidar_connected': False, 
    'joystick_connected': False,
    'gps_connected': False,
    
    # Control and Status
    'control_mode': 'BUTTONS', 
    'wifi_strength': 80,
    'battery_level': 85, 
    'battery_plugged': False,
    'obstacle_avoidance_active': False,
    'sensor_enabled': SENSOR_ENABLED.copy(),
    
    # System Health Metrics
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
    
    # Hardware Metrics
    'fan_speed_rpm': 1200, 
    'fan_speed_severity': None, 
    'fan_speed_level': None, 
    'fan_speed_description': None,
    'battery_percent': 100, 
    'battery_severity': None, 
    'battery_level': None, 
    'battery_description': None,
    
    # Network and System Info
    'private_ip': None, 
    'public_ip': None, 
    'cpu_usage': None, 
    'memory_usage': None, 
    'disk_usage': None,
    'network_bytes_sent': None, 
    'network_bytes_recv': None,
    'last_update': 'Never',
    'hostname': socket.gethostname() if 'socket' in locals() else 'unknown',
    'ip_address': socket.gethostbyname(socket.gethostname()) if 'socket' in locals() else 'unknown',
    
    # Location Data
    'location': { 
        'lat': None, 
        'lon': None, 
        'city': None, 
        'country': "India" 
    }
}

# Severity Levels for System Monitoring
SEVERITY_LEVELS = {
    'CRITICAL': {
        'color': '#ff4444',
        'priority': 'P1',
        'description': 'Immediate attention required'
    },
    'HIGH': {
        'color': '#ffaa00', 
        'priority': 'P2',
        'description': 'Attention required soon'
    },
    'MEDIUM': {
        'color': '#ffff00',
        'priority': 'P3', 
        'description': 'Monitor situation'
    },
    'LOW': {
        'color': '#00ff00',
        'priority': 'P4',
        'description': 'Normal operation'
    }
}

# File Extensions and Formats
SUPPORTED_VIDEO_FORMATS = ['.mp4', '.avi', '.mov']
SUPPORTED_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.bmp']
LOG_FILE_EXTENSIONS = ['.json', '.log', '.txt']

# Default Values for Missing Data
DEFAULT_VALUES = {
    'TEMPERATURE': 25.0,
    'HUMIDITY': 50.0,
    'GPS_LAT': 28.6139,  # Delhi
    'GPS_LON': 77.2090,
    'BATTERY_LEVEL': 100,
    'WIFI_STRENGTH': 80
}

# Error Messages
ERROR_MESSAGES = {
    'ARDUINO_DISCONNECTED': 'Arduino controller disconnected',
    'CAMERA_DISCONNECTED': 'Camera feed unavailable',
    'JOYSTICK_DISCONNECTED': 'Joystick/gamepad not detected',
    'LIDAR_DISCONNECTED': 'LIDAR sensor not available',
    'AI_SERVICE_UNAVAILABLE': 'AI service not responding',
    'ROS_UNAVAILABLE': 'ROS2 bridge not available',
    'LOW_BATTERY': 'Battery level critically low',
    'OVERHEATING': 'System temperature too high'
}

# Success Messages
SUCCESS_MESSAGES = {
    'ARDUINO_CONNECTED': 'Arduino controller connected successfully',
    'CAMERA_CONNECTED': 'Camera initialized successfully', 
    'JOYSTICK_CONNECTED': 'Joystick/gamepad detected',
    'LIDAR_CONNECTED': 'LIDAR sensor connected',
    'AI_SERVICE_READY': 'AI service ready',
    'ROS_CONNECTED': 'ROS2 bridge connected',
    'RECORDING_STARTED': 'Video recording started',
    'RECORDING_STOPPED': 'Video recording stopped',
    'SENSORS_RESET': 'All sensors reset successfully'
}

# Web Interface Configuration
UI_CONFIG = {
    'THEME': 'dark',
    'REFRESH_RATE': 1000,  # ms
    'CHARTS_HISTORY': 60,  # data points
    'MAP_ZOOM_LEVEL': 15,
    'VIDEO_QUALITY': 'medium',  # low, medium, high
    'ENABLE_NOTIFICATIONS': True,
    'AUTO_RECONNECT': True
}

# Performance Optimization
PERFORMANCE_SETTINGS = {
    'MAX_THREADS': 10,
    'CAMERA_BUFFER_SIZE': 1,
    'SENSOR_QUEUE_SIZE': 100,
    'LOG_BUFFER_SIZE': 1000,
    'VIDEO_BUFFER_SIZE': 10  # frames
}

# Feature Toggles
FEATURE_FLAGS = {
    'ENABLE_AI': True,
    'ENABLE_ROS': True, 
    'ENABLE_OBJECT_DETECTION': True,
    'ENABLE_VIDEO_RECORDING': True,
    'ENABLE_SENSOR_LOGGING': True,
    'ENABLE_JOYSTICK': True,
    'ENABLE_GPS': True,
    'ENABLE_OBSTACLE_AVOIDANCE': True
}
