import serial
import time
import cv2
from threading import Lock
import glob
import subprocess
import re

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

        # Joystick related attributes
        self.joystick_connected = False
        self.joystick_devices = []

        # Track recent commands to avoid flooding Arduino with duplicates.
        self.last_command_sent = None
        self.last_command_time = 0.0

    def init_arduino(self):
        """Initialize Arduino connection"""
        for port in ['/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyUSB0', '/dev/ttyUSB1']:
            try:
                if self.arduino is not None:
                    self.arduino.close()
                self.arduino = serial.Serial(port, 115200, timeout=1)
                time.sleep(2)  # Wait for Arduino to reset
                self.arduino_connected = True
                self.sensor_data['arduino_connected'] = True
                print(f"Arduino connected on {port}")
                
                # Send initial handshake
                self.send_command('D')
                return True
            except Exception as e:
                print(f"Failed to connect to Arduino on {port}: {e}")
        
        self.arduino_connected = False
        self.sensor_data['arduino_connected'] = False
        return False

    def init_cameras(self):
        """Initialize front and rear cameras"""
        # Initialize Front Camera
        try:
            if self.camera is not None:
                self.camera.release()
            for i in [0, 1, 2]:  # Try common camera indices
                cap = cv2.VideoCapture(i, cv2.CAP_V4L2)
                if cap.isOpened():
                    print(f"Front camera found at index {i}")
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_resolution[0])
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_resolution[1])
                    cap.set(cv2.CAP_PROP_FPS, self.camera_fps)
                    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer for lower latency
                    self.camera = cap
                    self.sensor_data['camera_connected'] = True
                    break
                else:
                    cap.release()
        except Exception as e:
            print(f"Error initializing front camera: {e}")
            self.sensor_data['camera_connected'] = False

        # Initialize Rear Camera
        try:
            if self.rear_camera is not None:
                self.rear_camera.release()
            for i in [2, 1, 3, 4]:  # Try common rear camera indices
                if i == self._get_camera_index(self.camera):
                    continue  # Skip if it's the same as front camera
                    
                cap = cv2.VideoCapture(i, cv2.CAP_V4L2)
                if cap.isOpened():
                    print(f"Rear camera found at index {i}")
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_resolution[0])
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_resolution[1])
                    cap.set(cv2.CAP_PROP_FPS, self.camera_fps)
                    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    self.rear_camera = cap
                    self.sensor_data['rear_camera_connected'] = True
                    break
                else:
                    cap.release()
        except Exception as e:
            print(f"Error initializing rear camera: {e}")
            self.sensor_data['rear_camera_connected'] = False

        self._emit_connection_update()

    def _get_camera_index(self, camera_obj):
        """Get the index of a camera object"""
        if camera_obj is None:
            return -1
        try:
            return int(camera_obj.getBackendName()) if hasattr(camera_obj, 'getBackendName') else -1
        except:
            return -1

    def detect_joystick(self):
        """Detect connected joystick devices"""
        try:
            # Method 1: Check /dev/input/js* devices
            js_devices = glob.glob('/dev/input/js*')
            
            # Method 2: Check using evdev devices
            evdev_devices = glob.glob('/dev/input/event*')
            joystick_events = []
            
            for device in evdev_devices:
                try:
                    # Try to read device info
                    result = subprocess.run(['evtest', '--info', device], 
                                          capture_output=True, text=True, timeout=2)
                    if 'joystick' in result.stdout.lower() or 'gamepad' in result.stdout.lower():
                        joystick_events.append(device)
                except:
                    continue
            
            # Method 3: Check using lsusb for gamepad devices
            try:
                lsusb_result = subprocess.run(['lsusb'], capture_output=True, text=True)
                gamepad_count = len([line for line in lsusb_result.stdout.split('\n') 
                                   if any(keyword in line.lower() for keyword in 
                                         ['gamepad', 'joystick', 'xbox', 'playstation', 'logitech'])])
            except:
                gamepad_count = 0
            
            self.joystick_devices = js_devices + joystick_events
            was_connected = self.joystick_connected
            self.joystick_connected = len(self.joystick_devices) > 0 or gamepad_count > 0
            
            # Only emit update if status changed
            if was_connected != self.joystick_connected:
                self.sensor_data['joystick_connected'] = self.joystick_connected
                self.socketio.emit('joystick_connection_update', {
                    'connected': self.joystick_connected,
                    'devices': self.joystick_devices,
                    'count': len(self.joystick_devices)
                })
                print(f"Joystick status: {self.joystick_connected} (devices: {len(self.joystick_devices)})")
            
            return self.joystick_connected
            
        except Exception as e:
            print(f"Error detecting joystick: {e}")
            self.joystick_connected = False
            self.sensor_data['joystick_connected'] = False
            return False

    def get_joystick_info(self):
        """Get detailed information about connected joysticks"""
        if not self.joystick_connected:
            return {"connected": False, "devices": []}
        
        joystick_info = []
        for device in self.joystick_devices:
            try:
                if device.startswith('/dev/input/js'):
                    # Get joystick info using jstest or similar
                    result = subprocess.run(['jstest', '--normal', device], 
                                          capture_output=True, text=True, timeout=3)
                    info = {
                        'device': device,
                        'type': 'joystick',
                        'raw_info': result.stdout[:200] if result.stdout else 'No info'
                    }
                    joystick_info.append(info)
            except Exception as e:
                joystick_info.append({
                    'device': device,
                    'type': 'unknown',
                    'error': str(e)
                })
        
        return {
            "connected": True,
            "devices": joystick_info,
            "count": len(joystick_info)
        }

    def check_connections_loop(self):
        """Continuous loop to check hardware connections"""
        connection_check_count = 0
        while self.running:
            try:
                # Check Arduino connection
                if self.arduino is not None:
                    try:
                        # Avoid sending periodic raw ping bytes that can
                        # interleave with movement commands on the firmware side.
                        self.arduino_connected = bool(getattr(self.arduino, 'is_open', False))
                    except:
                        self.arduino_connected = False
                        # Try to reinitialize Arduino if disconnected
                        if connection_check_count % 12 == 0:  # Try every minute
                            print("Arduino disconnected, attempting reconnection...")
                            self.init_arduino()
                else:
                    self.arduino_connected = False
                    if connection_check_count % 12 == 0:
                        self.init_arduino()

                # Check camera connections
                camera_connected = self.camera is not None and self.camera.isOpened()
                rear_camera_connected = self.rear_camera is not None and self.rear_camera.isOpened()
                
                # Check joystick connection (less frequently to reduce load)
                if connection_check_count % 3 == 0:  # Check every 15 seconds
                    self.detect_joystick()

                # Update sensor data
                self.sensor_data['arduino_connected'] = self.arduino_connected
                self.sensor_data['camera_connected'] = camera_connected
                self.sensor_data['rear_camera_connected'] = rear_camera_connected
                self.sensor_data['joystick_connected'] = self.joystick_connected

                # Emit connection update every 5 seconds or on status change
                if connection_check_count % 1 == 0:  # Every 5 seconds
                    self._emit_connection_update()

                connection_check_count += 1
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                print(f"Error checking connections: {e}")
                time.sleep(10)  # Longer sleep on error

    def _emit_connection_update(self):
        """Emit connection status update to frontend"""
        self.socketio.emit('connection_update', {
            'arduino_connected': self.arduino_connected,
            'camera_connected': self.camera is not None and self.camera.isOpened(),
            'rear_camera_connected': self.rear_camera is not None and self.rear_camera.isOpened(),
            'joystick_connected': self.joystick_connected,
            'joystick_devices': self.joystick_devices,
            'timestamp': time.time()
        })

    def read_sensor_data_loop(self):
        """Continuous loop to read sensor data from Arduino"""
        from datetime import datetime
        
        buffer = ""
        while self.running:
            if not self.arduino_connected:
                time.sleep(1)
                self.init_arduino()  # Try to re-initialize Arduino
                continue
            
            try:
                while self.arduino.in_waiting and self.running:
                    try:
                        # Read raw bytes and decode
                        raw_data = self.arduino.readline()
                        if not raw_data:
                            continue
                            
                        line = raw_data.decode('utf-8', errors='ignore').strip()
                        if not line:
                            continue

                        # Debug: Print all lines from Arduino (optional)
                        # print(f"Arduino: {line}")

                        if line.startswith('SENSORS:'):
                            self._process_sensor_data(line[8:])
                        elif line.count(',') >= 22:
                            # Some firmware/serial sessions can lose the "SENSORS:" prefix;
                            # still parse full comma-separated sensor frames.
                            self._process_sensor_data(line)
                        elif line.startswith('GPS:'):
                            self._process_gps_data(line[4:])
                        elif line.startswith('DEBUG:'):
                            print(f"Arduino Debug: {line[6:]}")
                        elif line.startswith('ERROR:'):
                            print(f"Arduino Error: {line[6:]}")
                            self.socketio.emit('arduino_error', {'message': line[6:]})
                        else:
                            # Handle other message types or print for debugging
                            if len(line) > 1:  # Ignore single character responses
                                print(f"Arduino: {line}")

                    except UnicodeDecodeError as e:
                        print(f"Unicode decode error: {e}")
                        continue
                    except Exception as e:
                        print(f"Error processing Arduino line: {e}")
                        continue
                        
            except Exception as e:
                print(f"Error reading sensor data from Arduino: {e}")
                self.arduino_connected = False
                self.sensor_data['arduino_connected'] = False
                time.sleep(1)  # Short delay before attempting re-connection

    def _process_sensor_data(self, sensor_string):
        """Process SENSORS: data from Arduino"""
        from datetime import datetime
        
        try:
            parts = [part.strip() for part in sensor_string.split(',')]
            # Some firmware builds prefix payload with an extra comma.
            while parts and parts[0] == '':
                parts.pop(0)

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

                # Optional firmware extension:
                # Append 9 presence flags after obstacle mode in this order:
                # touch, tilt, rain, gas, flame, impact, sound, pir, radar
                if len(parts) >= 33:
                    self.sensor_data['sensor_enabled'] = {
                        'touch': bool(int(parts[24])),
                        'tilt': bool(int(parts[25])),
                        'rain': bool(int(parts[26])),
                        'gas': bool(int(parts[27])),
                        'flame': bool(int(parts[28])),
                        'impact': bool(int(parts[29])),
                        'sound': bool(int(parts[30])),
                        'pir': bool(int(parts[31])),
                        'radar': bool(int(parts[32])),
                    }

                # Prepare display data for frontend
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
                    'system_temp': f"{self.sensor_data.get('system_temp', '--')}°C",
                    'cpu_usage': f"{self.sensor_data.get('cpu_usage', '--')}%",
                    'memory_usage': f"{self.sensor_data.get('memory_usage', '--')}%",
                    'last_update': self.sensor_data['last_update'],
                    'arduino_connected': self.sensor_data['arduino_connected'],
                    'sensor_enabled': self.sensor_data.get('sensor_enabled', {}),
                    'control_mode': self.sensor_data['control_mode'],
                    'obstacle_avoidance_active': self.sensor_data.get('obstacle_avoidance_active', False),
                    'battery_level': self.sensor_data.get('battery_level', '--'),
                    'wifi_strength': self.sensor_data.get('wifi_strength', '--')
                }

                self.socketio.emit('sensor_update', display_data)
                self.socketio.emit('accel_update', {
                    'x': self.sensor_data['accel_x'],
                    'y': self.sensor_data['accel_y'],
                    'z': self.sensor_data['accel_z']
                })
                
        except Exception as e:
            print(f"Error parsing sensor data: {e}")

    def _process_gps_data(self, gps_string):
        """Process GPS: data from Arduino"""
        try:
            parts = gps_string.split(',')
            if len(parts) >= 2:
                lat, lon = float(parts[0]), float(parts[1])
                self.sensor_data['location'] = {'lat': lat, 'lon': lon}
                self.sensor_data['gps_connected'] = True
                self.socketio.emit('gps_update', {'lat': lat, 'lon': lon})
        except Exception as e:
            print(f"Error parsing GPS data: {e}")

    def send_command(self, command: str):
        """Send command to Arduino"""
        if self.arduino_connected and self.arduino is not None:
            try:
                command = command.strip()

                # Drop rapid duplicate keepalive/stop commands to reduce serial spam.
                now = time.time()
                if command in ('S', 'D') and command == self.last_command_sent:
                    if now - self.last_command_time < 0.2:
                        return True

                # Ensure command ends with newline
                if not command.endswith('\n'):
                    command += '\n'
                    
                self.arduino.write(command.encode())
                self.arduino.flush()
                print(f"Sent command to Arduino: {command.strip()}")
                self.last_command_sent = command.strip()
                self.last_command_time = now
                return True
            except Exception as e:
                print(f"Error sending command to Arduino: {e}")
                self.arduino_connected = False
                self.sensor_data['arduino_connected'] = False
                return False
        return False

    def reset_sensors(self):
        """Reset all sensors on Arduino"""
        return self.send_command('X')

    def stop_motors(self):
        """Stop all motors"""
        return self.send_command('S')

    def emergency_stop(self):
        """Emergency stop - stop motors and disable systems"""
        self.send_command('S')  # Stop motors
        self.send_command('O')  # Disable obstacle avoidance
        print("EMERGENCY STOP ACTIVATED")

    def get_camera_frame(self, camera_type='front'):
        """Get a single frame from specified camera"""
        camera_obj = self.camera if camera_type == 'front' else self.rear_camera
        camera_lock = self.camera_lock if camera_type == 'front' else self.rear_camera_lock
        
        if camera_obj is None:
            return None
            
        with camera_lock:
            ret, frame = camera_obj.read()
            if ret:
                return frame
            return None

    def get_status_report(self):
        """Get comprehensive hardware status report"""
        return {
            'arduino': {
                'connected': self.arduino_connected,
                'port': self.arduino.port if self.arduino else None
            },
            'cameras': {
                'front_connected': self.camera is not None and self.camera.isOpened(),
                'rear_connected': self.rear_camera is not None and self.rear_camera.isOpened(),
                'resolution': self.camera_resolution,
                'fps': self.camera_fps
            },
            'joystick': {
                'connected': self.joystick_connected,
                'devices': self.joystick_devices,
                'count': len(self.joystick_devices)
            },
            'sensors': {
                'last_update': self.sensor_data.get('last_update', 'Never'),
                'temperature': self.sensor_data.get('temperature'),
                'humidity': self.sensor_data.get('humidity')
            }
        }

    def cleanup(self):
        """Cleanup resources"""
        self.running = False
        
        # Stop motors before cleanup
        if self.arduino_connected:
            self.stop_motors()
        
        # Close Arduino connection
        if self.arduino is not None:
            try:
                self.arduino.close()
            except:
                pass
        
        # Release cameras
        if self.camera is not None:
            try:
                self.camera.release()
            except:
                pass
                
        if self.rear_camera is not None:
            try:
                self.rear_camera.release()
            except:
                pass
        
        print("Hardware controller cleanup complete")
