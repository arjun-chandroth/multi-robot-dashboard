import os
import sys
import time
import json
import signal
import threading
from flask import Flask, render_template, Response, request, jsonify, send_from_directory
from flask_socketio import SocketIO
from datetime import datetime
from io import BytesIO
import zipfile
import psutil
import socket

# Import modularized components
from roverconf import RECORDINGS_DIR, SENSOR_DATA_DIR, STATIC_DIR, INITIAL_SENSOR_DATA, CAMERA_RESOLUTION, CAMERA_FPS
from hardware_controller import HardwareController
from camera_processor import CameraProcessor
from ros_handler import ROSHandler
from system_monitor import SystemMonitor
from ai_controller import AIController

app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading')

sensor_data = INITIAL_SENSOR_DATA.copy()
sensor_data['hostname'] = socket.gethostname()
sensor_data['ip_address'] = socket.gethostbyname(socket.gethostname())

current_control_mode = 'BUTTONS'
ai_voice_thread = None

hardware_controller = HardwareController(sensor_data, socketio, CAMERA_RESOLUTION, CAMERA_FPS)
camera_processor = CameraProcessor(sensor_data, socketio)
ros_handler = ROSHandler(socketio, hardware_controller, sensor_data)
system_monitor = SystemMonitor(sensor_data)
ai_controller = AIController(
    hardware_controller, socketio,
    lambda: current_control_mode,
    lambda mode: set_control_mode_internal(mode)
)

def set_control_mode_internal(mode):
    global current_control_mode
    if mode in ['JOYSTICK', 'BUTTONS', 'AI', 'OBSTACLE']:
        current_control_mode = mode
        sensor_data['control_mode'] = mode

        if mode != 'AI' and ai_controller.ai_active:
            ai_controller.stop_ai()

        if mode != 'OBSTACLE':
            ros_handler.set_obstacle_avoidance_active(False)
            hardware_controller.send_command('S')
            hardware_controller.send_command('O')
        else:
            if ai_controller.ai_active:
                ai_controller.stop_ai()
            hardware_controller.send_command('O')

        if mode == 'AI':
            ai_controller.start_ai_thread()

        socketio.emit('control_mode_update', {'mode': mode})
        return True
    return False

@app.route('/')
def index():
    recordings = []
    if os.path.exists(RECORDINGS_DIR):
        for f in sorted(os.listdir(RECORDINGS_DIR), reverse=True):
            if f.endswith('.avi'):
                filepath = os.path.join(RECORDINGS_DIR, f)
                try:
                    recordings.append({
                        'name': f,
                        'size': f"{os.path.getsize(filepath) // 1024} KB",
                        'date': datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d %H:%M')
                    })
                except Exception as e:
                    print(f"Error reading recording file {f}: {e}")
    return render_template('index.html', recordings=recordings)

@app.route('/video_feed_processed')
def video_feed_processed():
    return Response(camera_processor.generate_frames(
        hardware_controller.camera, 'fpv', hardware_controller.camera, hardware_controller.camera_lock, processing_enabled=True),
        mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/rear_video_feed_processed')
def rear_video_feed_processed():
    return Response(camera_processor.generate_frames(
        hardware_controller.rear_camera, 'rear', hardware_controller.rear_camera, hardware_controller.rear_camera_lock, processing_enabled=True),
        mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_feed_raw')
def video_feed_raw():
    return Response(camera_processor.generate_frames(
        hardware_controller.camera, 'fpv', hardware_controller.camera, hardware_controller.camera_lock, processing_enabled=False),
        mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/rear_video_feed_raw')
def rear_video_feed_raw():
    return Response(camera_processor.generate_frames(
        hardware_controller.rear_camera, 'rear', hardware_controller.rear_camera, hardware_controller.rear_camera_lock, processing_enabled=False),
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
    camera_instance = hardware_controller.camera if stream == 'fpv' else hardware_controller.rear_camera
    success = camera_processor.start_recording(stream, camera_instance)
    return jsonify({"status": "recording started" if success else "failed to start recording"})

@app.route('/stop_recording/<stream>', methods=['POST'])
def stop_recording_route(stream):
    if stream not in ['fpv', 'rear']:
        return jsonify({"status": "Invalid stream type"}), 400
    camera_processor.stop_recording(stream)
    return jsonify({"status": "recording stopped"})

@app.route('/download/<filename>')
def download_recording(filename):
    return send_from_directory(RECORDINGS_DIR, filename, as_attachment=True)

@app.route('/download_sensor_logs')
def download_sensor_logs():
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        if os.path.exists(SENSOR_DATA_DIR):
            for fname in os.listdir(SENSOR_DATA_DIR):
                if fname.endswith('.json'):
                    try:
                        zf.write(os.path.join(SENSOR_DATA_DIR, fname), fname)
                    except Exception as e:
                        print(f"Error zipping sensor log {fname}: {e}")
    memory_file.seek(0)
    return Response(
        memory_file,
        mimetype='application/zip',
        headers={'Content-Disposition': 'attachment;filename=sensor_logs.zip'}
    )

@app.route('/reset_sensors', methods=['POST'])
def reset_sensors():
    if hardware_controller.reset_sensors():
        return jsonify({"status": "All sensors reset"})
    return jsonify({"status": "Error sending reset command or Arduino not connected"}), 500

@app.route('/set_control_mode/<mode>', methods=['POST'])
def set_control_mode_route(mode):
    if set_control_mode_internal(mode):
        return jsonify({"status": f"Control mode set to {mode}"})
    return jsonify({"status": "Invalid mode"}), 400

@app.route('/set_obstacle_mode/<state>', methods=['POST'])
def set_obstacle_mode_route(state):
    global current_control_mode
    if state == 'on':
        if ros_handler.set_obstacle_avoidance_active(True):
            current_control_mode = 'OBSTACLE'
            sensor_data['control_mode'] = 'OBSTACLE'
            if hardware_controller.arduino_connected:
                hardware_controller.send_command('O')
            socketio.emit('control_mode_update', {'mode': 'OBSTACLE'})
            return jsonify({"status": "Obstacle avoidance mode activated"})
        else:
            return jsonify({"status": "Error activating obstacle avoidance"}), 500
    else:
        if ros_handler.set_obstacle_avoidance_active(False):
            if hardware_controller.arduino_connected:
                hardware_controller.send_command('S')
                hardware_controller.send_command('O')
            current_control_mode = 'BUTTONS'
            sensor_data['control_mode'] = 'BUTTONS'
            socketio.emit('control_mode_update', {'mode': 'BUTTONS'})
            return jsonify({"status": "Obstacle avoidance mode deactivated"})
        else:
            return jsonify({"status": "Error deactivating obstacle avoidance"}), 500

# --- SocketIO Control Handlers ---
@socketio.on('control')
def handle_control(command):
    global current_control_mode
    
    if current_control_mode == 'BUTTONS' and hardware_controller.arduino_connected:
        try:
            print(f"Sending command to Arduino: {command}")
            hardware_controller.send_command(command)
        except Exception as e:
            print(f"Error sending command to Arduino: {e}")
            socketio.emit('control_error', {'message': str(e)})

@socketio.on('joystick_input')
def handle_joystick_input(data):
    global current_control_mode
    
    if current_control_mode != 'JOYSTICK' or not hardware_controller.arduino_connected:
        return

    axes = data.get('axes', [])
    if len(axes) < 4:
        return

    x = round(axes[3], 1)
    y = round(axes[1], 1)

    if y == 1.0:
        command = 'F'
    elif y == -1.0:
        command = 'B'
    elif x == 1.0:
        command = 'L'
    elif x == -1.0:
        command = 'R'
    else:
        command = 'S'

    try:
        hardware_controller.send_command(command)
        print(f"[Joystick] Sent command: {command}")
    except Exception as e:
        print(f"[Joystick] Error sending command {command}: {e}")

@socketio.on('joystick')
def handle_joystick(data):
    global current_control_mode
    
    if current_control_mode != 'JOYSTICK' or not hardware_controller.arduino_connected:
        return
        
    try:
        x, y = map(int, data.split(','))
        
        if abs(y) > abs(x):
            if y > 100:
                hardware_controller.send_command('F')
            elif y < -100:
                hardware_controller.send_command('B')
            else:
                hardware_controller.send_command('S')
        else:
            if x > 100:
                hardware_controller.send_command('R')
            elif x < -100:
                hardware_controller.send_command('L')
            else:
                hardware_controller.send_command('S')
    except Exception as e:
        print(f"Error processing joystick data: {e}")

# --- SocketIO Recording Handlers ---
@socketio.on('start_recording')
def handle_start_recording(data):
    stream = data.get('stream')
    if stream in ['fpv', 'rear']:
        camera_instance = hardware_controller.camera if stream == 'fpv' else hardware_controller.rear_camera
        success = camera_processor.start_recording(stream, camera_instance)
        socketio.emit('recording_status', {
            'stream': stream,
            'recording': success
        })

@socketio.on('stop_recording')
def handle_stop_recording(data):
    stream = data.get('stream')
    if stream in ['fpv', 'rear']:
        camera_processor.stop_recording(stream)
        socketio.emit('recording_status', {
            'stream': stream,
            'recording': False
        })

@socketio.on('pause_recording')
def handle_pause_recording(data):
    stream = data.get('stream')
    # For now, treat pause as stop since VideoWriter doesn't support pausing
    if stream in ['fpv', 'rear']:
        camera_processor.stop_recording(stream)
        socketio.emit('recording_status', {
            'stream': stream,
            'recording': False,
            'paused': True
        })

# --- SocketIO Handler for AI ---
@socketio.on('ai_message')
def handle_ai_message(data):
    print(f"🧠 [DEBUG] Received AI message: {data}")

    if current_control_mode != 'AI':
        socketio.emit('ai_response', {
            'text': "AI mode is not active. Please enable AI mode first.",
            'error': True
        })
        return

    user_input = data.get('text', '').strip()
    if not user_input:
        socketio.emit('ai_response', {
            'text': "Empty message received. Please enter a valid question or command.",
            'error': True
        })
        return

    try:
        response = ai_controller.query_llama(user_input)
        if response:
            filtered_response = ai_controller.process_response(response)
            socketio.emit('ai_response', {
                'text': filtered_response if filtered_response else "Command executed",
                'user_input': user_input
            })
        else:
            socketio.emit('ai_response', {
                'text': "AI failed to respond. Please try again.",
                'error': True
            })
    except Exception as e:
        socketio.emit('ai_response', {
            'text': f"Error processing your request: {str(e)}",
            'error': True
        })

# --- Debug Route for Testing Arduino ---
@app.route('/test_arduino/<command>')
def test_arduino(command):
    if hardware_controller.send_command(command):
        return jsonify({"status": f"Command {command} sent successfully"})
    return jsonify({"status": "Failed to send command"}), 500

def cleanup():
    print("Initiating cleanup...")
    global running
    running = False
    try:
        if ros_handler:
            ros_handler.cleanup()
        if system_monitor:
            system_monitor.cleanup()
        if camera_processor:
            camera_processor.cleanup()
        if hardware_controller:
            hardware_controller.cleanup()
    except Exception as e:
        print(f"Cleanup error: {e}")
    print("Cleanup complete.")
    sys.exit(0)

def signal_handler(sig, frame):
    print(f"Received signal {sig}. Initiating graceful shutdown.")
    cleanup()

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    os.makedirs(RECORDINGS_DIR, exist_ok=True)
    os.makedirs(SENSOR_DATA_DIR, exist_ok=True)
    os.makedirs(STATIC_DIR, exist_ok=True)

    running = True

    # Initialize hardware with debug info
    print("Initializing Arduino...")
    hardware_controller.init_arduino()
    print("Initializing cameras...")
    hardware_controller.init_cameras()
    
    # Debug connection status
    print(f"Arduino connected: {hardware_controller.arduino_connected}")
    print(f"Front camera connected: {hardware_controller.camera is not None}")
    print(f"Rear camera connected: {hardware_controller.rear_camera is not None}")
    print(f"Control mode: {current_control_mode}")

    threading.Thread(target=system_monitor.update_system_metrics_loop, args=(camera_processor,), daemon=True).start()
    threading.Thread(target=hardware_controller.read_sensor_data_loop, daemon=True).start()
    threading.Thread(target=hardware_controller.check_connections_loop, daemon=True).start()

    ros_handler.init_ros()

    try:
        print("Starting Flask-SocketIO app on 0.0.0.0:5001")
        socketio.run(app, host='0.0.0.0', port=5001, debug=False)
    finally:
        cleanup()
