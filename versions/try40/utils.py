import subprocess
import re
import psutil
import socket
import urllib.request
import math

import numpy as np  # <-- ADD THIS LINE
import cv2          # <-- ADD THIS LINE



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

def get_system_temperature():
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = float(f.read().strip()) / 1000.0
        return temp
    except:
        return None

def get_private_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return None

def get_public_ip():
    try:
        return urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
    except:
        return None

def get_severity(value, metric_type):
    if value is None:
        return "Medium", "P3", f"{metric_type.capitalize()} data not available."
    if metric_type == "temperature":
        if value > 90: return "Critical", "P1", "CPU overheating may cause thermal shutdown or hardware damage."
        elif 70 <= value <= 90: return "High", "P2", "High CPU temperature may reduce performance due to throttling."
        else: return "Medium", "P3", "CPU temperature is within acceptable range."
    elif metric_type == "cpu":
        if value > 90: return "Critical", "P1", "CPU usage critically high; system may freeze or lag."
        elif 70 <= value <= 90: return "High", "P2", "High CPU usage may slow down other tasks."
        else: return "Medium", "P3", "CPU usage is normal."
    elif metric_type == "memory":
        if value > 90: return "Critical", "P1", "Insufficient memory can cause application crashes or slowdowns."
        elif 70 <= value <= 90: return "High", "P2", "Memory usage is high and could affect performance."
        else: return "Medium", "P3", "Memory usage is stable."
    elif metric_type == "disk":
        if value > 90: return "Critical", "P1", "Disk nearly full; system logging and apps may fail."
        elif 70 <= value <= 90: return "High", "P2", "Disk usage high; free up space soon."
        else: return "Medium", "P3", "Disk usage is within limits."
    elif metric_type == "fan":
        if value < 500: return "Critical", "P1", "Fan speed too low — cooling failure may occur."
        elif 500 <= value <= 1500: return "High", "P2", "Fan speed lower than optimal — check ventilation."
        else: return "Medium", "P3", "Fan speed is within optimal range."
    elif metric_type == "battery":
        if value < 20: return "Critical", "P1", "Battery critically low — system may shut down."
        elif 20 <= value < 50: return "High", "P2", "Battery level is low — consider charging."
        else: return "Medium", "P3", "Battery level is sufficient."
    return "Medium", "P3", "No abnormal behavior detected."

def estimate_distance(focal_length, real_width, width_in_frame):
    if width_in_frame == 0:
        return 0
    return (real_width * focal_length) / width_in_frame
