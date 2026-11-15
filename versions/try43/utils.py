import subprocess
import re
import psutil
import socket
import urllib.request
import math

import numpy as np
import cv2

class ViewTransformer:
    def __init__(self, source: np.ndarray, target: np.ndarray) -> None:
        self.m = cv2.getPerspectiveTransform(source.astype(np.float32), target.astype(np.float32))

    def transform_points(self, points: np.ndarray) -> np.ndarray:
        if points.size == 0:
            return points
        return cv2.perspectiveTransform(points.reshape(-1, 1, 2), self.m).reshape(-1, 2)

def get_wifi_strength():
    """Get WiFi signal strength as percentage"""
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
    """Get battery level using upower"""
    try:
        output = subprocess.check_output(["upower", "-i", "/org/freedesktop/UPower/devices/battery_BAT0"]).decode()
        match = re.search(r"percentage:\s+(\d+)%", output)
        if match:
            return int(match.group(1))
    except Exception as e:
        print(f"Error getting battery level: {e}")
    return None

def get_system_temperature():
    """Get system temperature from thermal zone"""
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = float(f.read().strip()) / 1000.0
        return temp
    except:
        return None

def get_private_ip():
    """Get private/local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return None

def get_public_ip():
    """Get public IP address from external service"""
    try:
        return urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
    except:
        return None

def get_severity(value, metric_type):
    """Get severity level, priority, and description for system metrics"""
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

def estimate_distance(focal_length, real_width, width_in_frame):
    """Estimate distance to object using camera perspective"""
    if width_in_frame == 0:
        return 0
    return (real_width * focal_length) / width_in_frame

def check_camera_connection(camera_index=0):
    """Check if camera is connected and accessible"""
    try:
        cap = cv2.VideoCapture(camera_index)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            return ret
        return False
    except Exception as e:
        print(f"Error checking camera connection: {e}")
        return False

def get_system_uptime():
    """Get system uptime in seconds"""
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
        return uptime_seconds
    except:
        return None

def format_uptime(seconds):
    """Format uptime seconds to human readable format"""
    if seconds is None:
        return "Unknown"
    
    days = seconds // (24 * 3600)
    seconds = seconds % (24 * 3600)
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    
    if days > 0:
        return f"{int(days)}d {int(hours)}h {int(minutes)}m"
    elif hours > 0:
        return f"{int(hours)}h {int(minutes)}m"
    else:
        return f"{int(minutes)}m {int(seconds)}s"

def get_network_interfaces():
    """Get list of active network interfaces"""
    try:
        interfaces = psutil.net_if_addrs()
        return list(interfaces.keys())
    except Exception as e:
        print(f"Error getting network interfaces: {e}")
        return []

def get_disk_usage_all():
    """Get disk usage for all mounted partitions"""
    try:
        disk_partitions = psutil.disk_partitions()
        disk_usage = {}
        
        for partition in disk_partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_usage[partition.mountpoint] = {
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': usage.percent
                }
            except PermissionError:
                # Skip partitions that require root permissions
                continue
                
        return disk_usage
    except Exception as e:
        print(f"Error getting disk usage: {e}")
        return {}

def get_process_count():
    """Get number of running processes"""
    try:
        return len(psutil.pids())
    except:
        return None

def get_load_average():
    """Get system load average"""
    try:
        return os.getloadavg()
    except:
        return None

def bytes_to_human(bytes_size):
    """Convert bytes to human readable format"""
    if bytes_size is None:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"

def validate_ip_address(ip):
    """Validate IP address format"""
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False

def get_mac_address(interface='eth0'):
    """Get MAC address for specified interface"""
    try:
        with open(f'/sys/class/net/{interface}/address', 'r') as f:
            return f.read().strip()
    except:
        return None

def calculate_fps(start_time, frame_count):
    """Calculate frames per second"""
    if start_time == 0:
        return 0
    elapsed_time = time.time() - start_time
    if elapsed_time > 0:
        return frame_count / elapsed_time
    return 0

def create_directory_if_not_exists(path):
    """Create directory if it doesn't exist"""
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creating directory {path}: {e}")
        return False

def is_raspberry_pi():
    """Check if running on Raspberry Pi"""
    try:
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read()
            return 'Raspberry Pi' in model
    except:
        return False

def get_gpu_usage():
    """Get GPU usage (if available)"""
    try:
        # Try to get GPU info using nvidia-smi for NVIDIA GPUs
        result = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except:
        pass
    return None

def safe_division(numerator, denominator, default=0):
    """Safe division to avoid division by zero"""
    if denominator == 0:
        return default
    return numerator / denominator

# Import time and os for new functions
import time
import os

# Add these constants for consistency
KNOWN_WIDTH = 0.5  # meters
FOCAL_LENGTH = 700  # pixels

print("Utils module loaded successfully with all functions from car_latest.py")
