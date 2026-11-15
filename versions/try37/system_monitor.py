import psutil
import time
from datetime import datetime
import json
import os

from utils import get_system_temperature, get_private_ip, get_public_ip, get_severity
from roverconf import SENSOR_DATA_DIR

class SystemMonitor:
    def __init__(self, sensor_data):
        self.sensor_data = sensor_data
        self.running = True

    def collect_system_metrics(self):
        try:
            system_temp = get_system_temperature()
            cpu_usage = psutil.cpu_percent(interval=None) # Non-blocking
            memory_usage = psutil.virtual_memory().percent
            disk_usage = psutil.disk_usage('/').percent

            fan_speed = None
            try:
                fans = psutil.sensors_fans()
                if fans:
                    for fan_group in fans.values():
                        if fan_group:
                            fan_speed = fan_group[0].current
                            break
            except Exception as e:
                # print(f"Could not get fan speed: {e}") # Usually 'AttributeError' if no sensors
                pass

            battery_percent = None
            battery_plugged = None
            try:
                battery = psutil.sensors_battery()
                if battery:
                    battery_percent = battery.percent
                    battery_plugged = battery.power_plugged
            except Exception as e:
                # print(f"Could not get battery info: {e}")
                pass

            net_io_counters = psutil.net_io_counters()

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
                'fan_speed_rpm': fan_speed,
                'battery_percent': battery_percent,
                'battery_plugged': battery_plugged,
                'network_bytes_sent': net_io_counters.bytes_sent,
                'network_bytes_recv': net_io_counters.bytes_recv,
                'private_ip': get_private_ip(),
                'public_ip': get_public_ip(),
                'temperature_severity': temp_sev, 'temperature_level': temp_lvl, 'temperature_description': temp_desc,
                'cpu_usage_severity': cpu_sev, 'cpu_usage_level': cpu_lvl, 'cpu_usage_description': cpu_desc,
                'memory_usage_severity': mem_sev, 'memory_usage_level': mem_lvl, 'memory_usage_description': mem_desc,
                'disk_usage_severity': disk_sev, 'disk_usage_level': disk_lvl, 'disk_usage_description': disk_desc,
                'fan_speed_severity': fan_sev, 'fan_speed_level': fan_lvl, 'fan_speed_description': fan_desc,
                'battery_severity': bat_sev, 'battery_level': bat_lvl, 'battery_description': bat_desc
            }
        except Exception as e:
            print(f"Error collecting system metrics: {e}")
            return {}

    def log_sensor_data(self, detected_objects_front, detected_objects_rear):
        timestamp = datetime.now().isoformat()
        log_data = {
            '@timestamp': timestamp,
            'host': self.sensor_data['hostname'],
            'location': self.sensor_data.get('location', {}),
            'sensors': {
                'temperature': self.sensor_data['temperature'],
                'humidity': self.sensor_data['humidity'],
                'impact': {'count': self.sensor_data['impact_count'], 'detected': self.sensor_data['impact_detected']},
                'sound': {'count': self.sensor_data['sound_count'], 'detected': self.sensor_data['sound_detected']},
                'touch': {'count': self.sensor_data['touch_count'], 'detected': self.sensor_data['touch_detected']},
                'tilt': {'count': self.sensor_data['tilt_count'], 'detected': self.sensor_data['tilt_detected']},
                'pir': {'count': self.sensor_data['pir_count'], 'detected': self.sensor_data['pir_detected']},
                'radar': {'count': self.sensor_data['radar_count'], 'detected': self.sensor_data['radar_detected']},
                'rain': {'count': self.sensor_data['rain_count'], 'detected': self.sensor_data['rain_detected']},
                'gas': {'count': self.sensor_data['gas_count'], 'detected': self.sensor_data['gas_detected']},
                'flame': {'count': self.sensor_data['flame_count'], 'detected': self.sensor_data['flame_detected']},
                'accelerometer': {
                    'x': self.sensor_data['accel_x'], 'y': self.sensor_data['accel_y'], 'z': self.sensor_data['accel_z']
                },
            },
            'system': {
                'system_temp': self.sensor_data['system_temp'],
                'temperature_severity': self.sensor_data['temperature_severity'],
                'temperature_level': self.sensor_data['temperature_level'],
                'temperature_description': self.sensor_data['temperature_description'],
                'cpu_usage': self.sensor_data['cpu_usage'],
                'cpu_usage_severity': self.sensor_data['cpu_usage_severity'],
                'cpu_usage_level': self.sensor_data['cpu_usage_level'],
                'cpu_usage_description': self.sensor_data['cpu_usage_description'],
                'memory_usage': self.sensor_data['memory_usage'],
                'memory_usage_severity': self.sensor_data['memory_usage_severity'],
                'memory_usage_level': self.sensor_data['memory_usage_level'],
                'memory_usage_description': self.sensor_data['memory_usage_description'],
                'disk_usage': self.sensor_data['disk_usage'],
                'disk_usage_severity': self.sensor_data['disk_usage_severity'],
                'disk_usage_level': self.sensor_data['disk_usage_level'],
                'disk_usage_description': self.sensor_data['disk_usage_description'],
                'fan_speed': self.sensor_data['fan_speed_rpm'],
                'fan_speed_severity': self.sensor_data['fan_speed_severity'],
                'fan_speed_level': self.sensor_data['fan_speed_level'],
                'fan_speed_description': self.sensor_data['fan_speed_description'],
                'battery_percent': self.sensor_data['battery_percent'],
                'battery_severity': self.sensor_data['battery_severity'],
                'battery_level': self.sensor_data['battery_level'],
                'battery_description': self.sensor_data['battery_description'],
                'network_bytes_sent': self.sensor_data['network_bytes_sent'],
                'network_bytes_recv': self.sensor_data['network_bytes_recv'],
                'private_ip': self.sensor_data.get('private_ip'),
                'public_ip': self.sensor_data.get('public_ip')
            },
            'arduino_connected': self.sensor_data['arduino_connected'],
            'control_mode': self.sensor_data['control_mode'],
            'obstacle_avoidance_active': self.sensor_data['obstacle_avoidance_active'],
            'yolo_detections_front': detected_objects_front,
            'yolo_detections_rear': detected_objects_rear
        }

        filename = datetime.now().strftime("%Y-%m-%d") + ".json"
        filepath = os.path.join(SENSOR_DATA_DIR, filename)
        try:
            with open(filepath, 'a') as f:
                json.dump(log_data, f)
                f.write('\n')
        except Exception as e:
            print(f"Error writing to sensor log: {e}")

    def update_system_metrics_loop(self, camera_processor):
        while self.running:
            try:
                metrics = self.collect_system_metrics()
                self.sensor_data.update(metrics)
                front_objects, rear_objects = camera_processor.get_detected_objects_data()
                self.log_sensor_data(front_objects, rear_objects)
                time.sleep(5)
            except Exception as e:
                print(f"Error in system metrics update loop: {e}")
                time.sleep(10) # Longer sleep on error

    def cleanup(self):
        self.running = False

