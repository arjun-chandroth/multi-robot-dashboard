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
from datetime import datetime
from flask import Flask, render_template, Response, request, send_from_directory
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading')

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RECORDINGS_DIR = os.path.join(BASE_DIR, 'recordings')
SENSOR_DATA_DIR = '/opt/rover/sensors'
STATIC_DIR = os.path.join(BASE_DIR, 'static')
PLACEHOLDER_PATH = os.path.join(STATIC_DIR, 'placeholder.jpg')

# Global variables
arduino = None
camera = None
camera_lock = threading.Lock()
recording = False
video_writer = None
running = True
arduino_connected = False
current_control_mode = 'BUTTONS'
camera_fps = 30
camera_resolution = (640, 480)
camera_quality = 70

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
    'system_temp': None,
    'cpu_usage': None,
    'memory_usage': None,
    'disk_usage': None,
    'network_io': None,
    'last_update': 'Never',
    'hostname': socket.gethostname(),
    'ip_address': socket.gethostbyname(socket.gethostname()),
    'arduino_connected': False,
    'control_mode': 'BUTTONS'
}

def get_system_temperature():
    try:
        temp = os.popen('vcgencmd measure_temp').readline()
        return float(temp.replace("temp=", "").replace("'C\n", ""))
    except:
        return None

def collect_system_metrics():
    try:
        return {
            'system_temp': get_system_temperature(),
            'cpu_usage': psutil.cpu_percent(),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'network_io': {
                'bytes_sent': psutil.net_io_counters().bytes_sent,
                'bytes_recv': psutil.net_io_counters().bytes_recv
            }
        }
    except Exception as e:
        print(f"Error collecting system metrics: {e}")
        return {}

def log_sensor_data():
    timestamp = datetime.now().isoformat()
    log_data = {
        '@timestamp': timestamp,
        'host': sensor_data['hostname'],
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
            'temperature': sensor_data['system_temp'],
            'cpu_usage': sensor_data['cpu_usage'],
            'memory_usage': sensor_data['memory_usage'],
            'disk_usage': sensor_data['disk_usage'],
            'network_io': sensor_data['network_io']
        },
        'arduino_connected': sensor_data['arduino_connected'],
        'control_mode': sensor_data['control_mode']
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
    global arduino, camera, arduino_connected
    # Try to connect to Arduino
    for port in ['/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyUSB0']:
        try:
            if arduino is not None:
                arduino.close()
            arduino = serial.Serial(port, 115200, timeout=1)
            time.sleep(2)
            arduino_connected = True
            sensor_data['arduino_connected'] = True
            print(f"Arduino connected on {port}")
            socketio.emit('connection_update', {
                'arduino_connected': True,
                'camera_connected': camera is not None
            })
            break
        except Exception as e:
            print(f"Failed to connect to Arduino on {port}: {e}")
            arduino_connected = False
            sensor_data['arduino_connected'] = False
    
    # Try to connect to camera
    try:
        if camera is not None:
            camera.release()
        for i in range(0, 4):
            cap = cv2.VideoCapture(i, cv2.CAP_V4L2)
            if cap.isOpened():
                print(f"Camera found at index {i}")
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_resolution[0])
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_resolution[1])
                cap.set(cv2.CAP_PROP_FPS, camera_fps)
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
                camera = cap
                socketio.emit('connection_update', {
                    'arduino_connected': arduino_connected,
                    'camera_connected': True
                })
                break
    except Exception as e:
        print(f"Error initializing camera: {e}")

def check_connections():
    global arduino_connected
    while running:
        try:
            # Check Arduino connection
            if arduino is not None:
                try:
                    arduino.write('D'.encode())
                    arduino_connected = True
                except:
                    arduino_connected = False
            else:
                arduino_connected = False
            
            # Check camera connection
            camera_connected = camera is not None and camera.isOpened()
            
            sensor_data['arduino_connected'] = arduino_connected
            socketio.emit('connection_update', {
                'arduino_connected': arduino_connected,
                'camera_connected': camera_connected
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
                    if len(parts) == 23:
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
                            'control_mode': sensor_data['control_mode']
                        }
                        socketio.emit('sensor_update', display_data)
                        socketio.emit('accel_update', {
                            'x': sensor_data['accel_x'],
                            'y': sensor_data['accel_y'],
                            'z': sensor_data['accel_z']
                        })
                elif line:  # Print any other messages from Arduino
                    print(f"Arduino: {line}")
        except Exception as e:
            print(f"Error reading sensor data: {e}")
            arduino_connected = False
            sensor_data['arduino_connected'] = False
            time.sleep(1)

def generate_frames():
    try:
        placeholder = cv2.imread(PLACEHOLDER_PATH)
        _, buffer = cv2.imencode('.jpg', placeholder, [cv2.IMWRITE_JPEG_QUALITY, camera_quality])
        placeholder_bytes = buffer.tobytes()
    except Exception as e:
        print(f"Error loading placeholder image: {e}")
        placeholder_bytes = b''
    
    while running:
        frame_bytes = placeholder_bytes
        
        if camera is not None:
            with camera_lock:
                ret, frame = camera.read()
                if ret:
                    if not recording:
                        y_position = 30
                        cv2.putText(frame, f"Temp: {sensor_data['temperature'] or '--'}°C", (10, y_position),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        y_position += 30
                        cv2.putText(frame, f"Mode: {current_control_mode}", (10, y_position),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                        y_position += 30
                        cv2.putText(frame, f"Tilt: {'YES' if sensor_data['tilt_detected'] else 'NO'}", (10, y_position),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                        y_position += 30
                        cv2.putText(frame, f"Motion: {'YES' if sensor_data['pir_detected'] else 'NO'}", (10, y_position),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                        y_position += 30
                        cv2.putText(frame, f"Radar: {'YES' if sensor_data['radar_detected'] else 'NO'}", (10, y_position),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (128, 0, 128), 2)
                        y_position += 30
                        cv2.putText(frame, f"Rain: {'YES' if sensor_data['rain_detected'] else 'NO'}", (10, y_position),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                        y_position += 30
                        cv2.putText(frame, f"Gas: {'YES' if sensor_data['gas_detected'] else 'NO'}", (10, y_position),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (128, 0, 128), 2)
                        y_position += 30
                        cv2.putText(frame, f"Flame: {'YES' if sensor_data['flame_detected'] else 'NO'}", (10, y_position),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 69, 0), 2)
                        y_position += 30
                        cv2.putText(frame, f"Accel: X={sensor_data['accel_x']:.1f} Y={sensor_data['accel_y']:.1f} Z={sensor_data['accel_z']:.1f}", 
                                   (10, y_position), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                    
                    if recording and video_writer is not None:
                        video_writer.write(frame)
                    
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, camera_quality])
                    frame_bytes = buffer.tobytes()
        
        yield (b'--frame\r\n'
              b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

def start_recording():
    global recording, video_writer
    if camera is None or recording:
        return False
    
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(RECORDINGS_DIR, f"recording_{timestamp}.avi")
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        video_writer = cv2.VideoWriter(filename, fourcc, camera_fps, camera_resolution)
        if not video_writer.isOpened():
            return False
            
        recording = True
        return True
    except Exception as e:
        print(f"Error starting recording: {e}")
        return False

def stop_recording():
    global recording, video_writer
    if recording and video_writer is not None:
        video_writer.release()
        video_writer = None
        recording = False

def cleanup():
    global running, arduino, camera, video_writer
    running = False
    
    if recording:
        stop_recording()
    
    if camera is not None:
        camera.release()
    
    if arduino is not None:
        arduino.close()

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
    
    display_data = {
        'temperature': f"{sensor_data['temperature'] or '--'}°C",
        'humidity': f"{sensor_data['humidity'] or '--'}%",
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
        'control_mode': sensor_data['control_mode']
    }
    
    return render_template('index.html', recordings=recordings, sensor_data=display_data)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                  mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/record', methods=['POST'])
def toggle_recording():
    if not recording:
        success = start_recording()
        return {"status": "recording started" if success else "failed to start recording"}
    else:
        stop_recording()
        return {"status": "recording stopped"}

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

@app.route('/reset_shock_count', methods=['POST'])
def reset_shock_count():
    if arduino is not None and arduino_connected:
        try:
            arduino.write('X'.encode())
            return {"status": "All sensors reset"}
        except:
            return {"status": "Error sending reset command"}, 500
    return {"status": "Arduino not connected"}, 500

@app.route('/set_control_mode/<mode>', methods=['POST'])
def set_control_mode(mode):
    global current_control_mode
    if mode in ['JOYSTICK', 'BUTTONS']:
        current_control_mode = mode
        sensor_data['control_mode'] = mode
        socketio.emit('control_mode_update', {'mode': mode})
        return {"status": f"Control mode set to {mode}"}
    return {"status": "Invalid mode"}, 400

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
        
        if abs(y) > abs(x):  # Forward/backward dominant
            if y > 100:
                arduino.write('F'.encode())
            elif y < -100:
                arduino.write('B'.encode())
            else:
                arduino.write('S'.encode())
        else:  # Left/right dominant
            if x > 100:
                arduino.write('R'.encode())
            elif x < -100:
                arduino.write('L'.encode())
            else:
                arduino.write('S'.encode())
    except Exception as e:
        print(f"Error processing joystick data: {e}")

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create required directories if they don't exist
    os.makedirs(RECORDINGS_DIR, exist_ok=True)
    os.makedirs(SENSOR_DATA_DIR, exist_ok=True)
    os.makedirs(STATIC_DIR, exist_ok=True)
    
    init_hardware()
    threading.Thread(target=update_system_metrics, daemon=True).start()
    threading.Thread(target=read_sensor_data, daemon=True).start()
    threading.Thread(target=check_connections, daemon=True).start()
    
    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)
    finally:
        cleanup()