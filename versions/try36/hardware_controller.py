import serial
import time
import cv2
from threading import Lock

class HardwareController:
    def __init__(self, sensor_data, socketio, camera_resolution, camera_fps):
        self.arduino = None
        self.arduino_connected = False
        self.sensor_data = sensor_data
        self.socketio = socketio
        self.camera_resolution = camera_resolution
        self.camera_fps = camera_fps
        self.running = True

        self.camera = None
        self.rear_camera = None
        self.camera_lock = Lock()
        self.rear_camera_lock = Lock()

    def init_arduino(self):
        for port in ['/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyUSB0', '/dev/ttyUSB1']:
            try:
                if self.arduino is not None:
                    self.arduino.close()
                self.arduino = serial.Serial(port, 115200, timeout=1)
                time.sleep(2)
                self.arduino_connected = True
                self.sensor_data['arduino_connected'] = True
                print(f"Arduino connected on {port}")
                return True
            except Exception as e:
                print(f"Failed to connect to Arduino on {port}: {e}")
        self.arduino_connected = False
        self.sensor_data['arduino_connected'] = False
        return False

    def init_cameras(self):
        # Initialize Front Camera
        try:
            if self.camera is not None:
                self.camera.release()
            for i in [0, 1]:  # Try common front camera indices
                cap = cv2.VideoCapture(i, cv2.CAP_V4L2)
                if cap.isOpened():
                    print(f"Front camera found at index {i}")
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_resolution[0])
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_resolution[1])
                    cap.set(cv2.CAP_PROP_FPS, self.camera_fps)
                    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
                    self.camera = cap
                    self.sensor_data['camera_connected'] = True
                    break
        except Exception as e:
            print(f"Error initializing front camera: {e}")

        # Initialize Rear Camera
        try:
            if self.rear_camera is not None:
                self.rear_camera.release()
            for i in [2, 1, 3]:  # Try common rear camera indices
                cap = cv2.VideoCapture(i, cv2.CAP_V4L2)
                if cap.isOpened():
                    print(f"Rear camera found at index {i}")
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_resolution[0])
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_resolution[1])
                    cap.set(cv2.CAP_PROP_FPS, self.camera_fps)
                    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
                    self.rear_camera = cap
                    self.sensor_data['rear_camera_connected'] = True
                    break
        except Exception as e:
            print(f"Error initializing rear camera: {e}")

        self.socketio.emit('connection_update', {
            'arduino_connected': self.arduino_connected,
            'camera_connected': self.camera is not None,
            'rear_camera_connected': self.rear_camera is not None
        })

    def check_connections_loop(self):
        while self.running:
            try:
                if self.arduino is not None:
                    try:
                        self.arduino.write('D'.encode()) # Ping Arduino to check connection
                        self.arduino_connected = True
                    except:
                        self.arduino_connected = False
                else:
                    self.arduino_connected = False

                camera_connected = self.camera is not None and self.camera.isOpened()
                rear_camera_connected = self.rear_camera is not None and self.rear_camera.isOpened()
                self.sensor_data['arduino_connected'] = self.arduino_connected
                self.sensor_data['camera_connected'] = camera_connected
                self.sensor_data['rear_camera_connected'] = rear_camera_connected

                self.socketio.emit('connection_update', {
                    'arduino_connected': self.arduino_connected,
                    'camera_connected': camera_connected,
                    'rear_camera_connected': rear_camera_connected
                })
                time.sleep(5)
            except Exception as e:
                print(f"Error checking connections: {e}")
                time.sleep(10) # Longer sleep on error

    def read_sensor_data_loop(self):
        from datetime import datetime # Import here to avoid circular dependency if placed at top

        while self.running:
            if not self.arduino_connected:
                time.sleep(1)
                self.init_arduino() # Try to re-initialize Arduino
                continue
            try:
                while self.arduino.in_waiting and self.running:
                    line = self.arduino.readline().decode('utf-8').strip()
                    print(f"Arduino: {line}") # Debugging: Print all lines from Arduino

                    if line.startswith('SENSORS:'):
                        parts = line[8:].split(',')
                        if len(parts) >= 23:
                            self.sensor_data.update({
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
                                self.sensor_data['obstacle_avoidance_active'] = bool(int(parts[23]))

                            display_data = {
                                'temperature': f"{self.sensor_data['temperature']:.1f}°C" if self.sensor_data['temperature'] is not None else "--",
                                'humidity': f"{self.sensor_data['humidity']:.1f}%" if self.sensor_data['humidity'] is not None else "--",
                                'impact_count': self.sensor_data['impact_count'],
                                'impact_detected': self.sensor_data['impact_detected'],
                                'sound_count': self.sensor_data['sound_count'],
                                'sound_detected': self.sensor_data['sound_detected'],
                                'touch_count': self.sensor_data['touch_count'],
                                'touch_detected': self.sensor_data['touch_detected'],
                                'tilt_count': self.sensor_data['tilt_count'],
                                'tilt_detected': self.sensor_data['tilt_detected'],
                                'pir_count': self.sensor_data['pir_count'],
                                'pir_detected': self.sensor_data['pir_detected'],
                                'radar_count': self.sensor_data['radar_count'],
                                'radar_detected': self.sensor_data['radar_detected'],
                                'rain_count': self.sensor_data['rain_count'],
                                'rain_detected': self.sensor_data['rain_detected'],
                                'gas_count': self.sensor_data['gas_count'],
                                'gas_detected': self.sensor_data['gas_detected'],
                                'flame_count': self.sensor_data['flame_count'],
                                'flame_detected': self.sensor_data['flame_detected'],
                                'accel_x': f"{self.sensor_data['accel_x']:.2f}",
                                'accel_y': f"{self.sensor_data['accel_y']:.2f}",
                                'accel_z': f"{self.sensor_data['accel_z']:.2f}",
                                'system_temp': f"{self.sensor_data['system_temp'] or '--'}°C",
                                'cpu_usage': f"{self.sensor_data['cpu_usage'] or '--'}%",
                                'memory_usage': f"{self.sensor_data['memory_usage'] or '--'}%",
                                'last_update': self.sensor_data['last_update'],
                                'arduino_connected': self.sensor_data['arduino_connected'],
                                'control_mode': self.sensor_data['control_mode'],
                                'obstacle_avoidance_active': self.sensor_data.get('obstacle_avoidance_active', False),
                                'battery_level': self.sensor_data['battery_level'],
                                'wifi_strength': self.sensor_data['wifi_strength']
                            }
                            self.socketio.emit('sensor_update', display_data)
                            self.socketio.emit('accel_update', {
                                'x': self.sensor_data['accel_x'],
                                'y': self.sensor_data['accel_y'],
                                'z': self.sensor_data['accel_z']
                            })
                    elif line.startswith('GPS:'):
                        try:
                            _, payload = line.split(':', 1)
                            lat_str, lon_str = payload.split(',', 1)
                            lat, lon = float(lat_str), float(lon_str)
                            self.sensor_data['location'] = {'lat': lat, 'lon': lon}
                            self.sensor_data['gps_connected'] = True
                            self.socketio.emit('gps_update', {'lat': lat, 'lon': lon})
                        except Exception as e:
                            print(f"Error parsing GPS: {e}")
                    elif line:
                        print(f"Arduino: {line}")
            except Exception as e:
                print(f"Error reading sensor data from Arduino: {e}")
                self.arduino_connected = False
                self.sensor_data['arduino_connected'] = False
                time.sleep(1) # Short delay before attempting re-connection

    def send_command(self, command: str):
        if self.arduino_connected and self.arduino is not None:
            try:
                print(f"Sending command to Arduino: {command}")
                self.arduino.write(command.encode())
                self.arduino.flush()
                return True
            except Exception as e:
                print(f"Error sending command to Arduino: {e}")
                self.arduino_connected = False
                self.sensor_data['arduino_connected'] = False
                return False
        return False

    def reset_sensors(self):
        return self.send_command('X')

    def stop_motors(self):
        return self.send_command('S')

    def cleanup(self):
        self.running = False
        if self.arduino is not None:
            self.arduino.close()
        if self.camera is not None:
            self.camera.release()
        if self.rear_camera is not None:
            self.rear_camera.release()

