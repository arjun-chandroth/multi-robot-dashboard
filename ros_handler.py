import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from sensor_msgs.msg import LaserScan
import math
import threading
import time

class LidarSubscriber(Node):
    def __init__(self, socketio):
        
        super().__init__('lidar_subscriber')
        self.socketio = socketio
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
            self.socketio.emit('lidar_update', scan_data)
        except Exception as e:
            self.get_logger().error(f'Error processing scan: {str(e)}')

class ObstacleAvoidance(Node):
    def __init__(self, hardware_controller, sensor_data):
        super().__init__('obstacle_avoidance')
        self.hardware_controller = hardware_controller
        self.sensor_data = sensor_data
        self.subscription = self.create_subscription(
            LaserScan,
            '/scan',
            self.scan_callback,
            10)
        self.get_logger().info("Obstacle Avoidance Node started")
        self.active = False

    def scan_callback(self, msg):
        if not self.active or not self.hardware_controller.arduino_connected:
            return

        front_distances = msg.ranges[0:30] + msg.ranges[-30:] # Check front 60 degrees
        valid_distances = [d for d in front_distances if not math.isinf(d) and not math.isnan(d) and d > 0] # Filter out invalid ranges

        if not valid_distances:
            self.hardware_controller.send_command('F') # Keep moving if no obstacles detected
            self.get_logger().info("No valid distances, moving forward.")
            return

        min_distance = min(valid_distances)
        # print(f"Min distance: {min_distance}") # Debugging

        if min_distance < 0.5: # Obstacle too close
            if self.hardware_controller.send_command('L'): # Try to turn left
                self.get_logger().info(f"Obstacle at {min_distance:.2f}m → Turning Left")
            else:
                self.get_logger().error("Failed to send turn command to Arduino.")
        else: # Clear path
            if self.hardware_controller.send_command('F'): # Move forward
                self.get_logger().info(f"Clear path → Moving Forward")
            else:
                self.get_logger().error("Failed to send forward command to Arduino.")

class ROSHandler:
    def __init__(self, socketio, hardware_controller, sensor_data):
        self.ros_node = None
        self.lidar_subscriber = None
        self.obstacle_avoidance_node = None
        self.ros_spin_thread = None
        self.obstacle_avoidance_thread = None
        self.running = True
        self.socketio = socketio
        self.hardware_controller = hardware_controller
        self.sensor_data = sensor_data

    def init_ros(self):
        try:
            if not rclpy.ok():
                rclpy.init()
            self.ros_node = rclpy.create_node('web_interface_node')
            self.lidar_subscriber = LidarSubscriber(self.socketio)
            self.obstacle_avoidance_node = ObstacleAvoidance(self.hardware_controller, self.sensor_data)

            def ros_spin_once_loop():
                while self.running and rclpy.ok():
                    try:
                        rclpy.spin_once(self.lidar_subscriber, timeout_sec=0.1)
                        rclpy.spin_once(self.obstacle_avoidance_node, timeout_sec=0.1)
                        # time.sleep(0.01) # Small sleep to yield CPU
                    except ExternalShutdownException:
                        break

            self.ros_spin_thread = threading.Thread(target=ros_spin_once_loop, daemon=True)
            self.ros_spin_thread.start()
            print("ROS2 initialized successfully with Lidar and Obstacle Avoidance nodes.")
        except Exception as e:
            print(f"Error initializing ROS2: {e}")

    def set_obstacle_avoidance_active(self, state: bool):
        if self.obstacle_avoidance_node:
            self.obstacle_avoidance_node.active = state
            self.sensor_data['obstacle_avoidance_active'] = state
            print(f"Obstacle avoidance set to: {state}")
            return True
        print("Obstacle avoidance node not initialized.")
        return False

    def cleanup(self):
        self.running = False
        if self.ros_spin_thread and self.ros_spin_thread.is_alive():
            self.ros_spin_thread.join(timeout=1) # Give it a moment to finish

        if self.lidar_subscriber:
            self.lidar_subscriber.destroy_node()
        if self.obstacle_avoidance_node:
            self.obstacle_avoidance_node.destroy_node()
        if self.ros_node:
            self.ros_node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        print("ROS2 cleanup complete.")

