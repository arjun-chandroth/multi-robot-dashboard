import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String

from drobotz_robot.protocol import front_sector_minimum


class ObstacleAvoidanceNode(Node):
    """Converts fresh forward LaserScan data into short, mode-gated motor commands."""

    def __init__(self):
        super().__init__("drobotz_obstacle_avoidance")
        self.declare_parameter("scan_topic", "/scan")
        self.declare_parameter("obstacle_distance_m", 0.5)
        self.declare_parameter("front_angle_degrees", 60.0)
        self._mode = "BUTTONS"
        self._obstacle_distance = float(self.get_parameter("obstacle_distance_m").value)
        self._front_angle = float(self.get_parameter("front_angle_degrees").value)
        self._publisher = self.create_publisher(String, "/drobotz/cmd/autonomy", 10)
        self.create_subscription(
            LaserScan,
            str(self.get_parameter("scan_topic").value),
            self._scan_callback,
            qos_profile_sensor_data,
        )
        self.create_subscription(String, "/drobotz/control_mode", self._mode_callback, 10)
        self.get_logger().info("Obstacle avoidance ready; activate it with OBSTACLE control mode.")

    def _mode_callback(self, message):
        self._mode = message.data.strip().upper()
        if self._mode == "JOYMODE":
            self._mode = "JOYSTICK"

    def _scan_callback(self, scan):
        if self._mode != "OBSTACLE":
            return
        distance = front_sector_minimum(
            list(scan.ranges),
            scan.angle_min,
            scan.angle_increment,
            scan.range_min,
            scan.range_max,
            self._front_angle,
        )
        if distance is None:
            command = "S"
            self.get_logger().warning("No valid forward LiDAR samples; stopping the robot.")
        elif distance < self._obstacle_distance:
            command = "L"
            self.get_logger().info(f"Obstacle at {distance:.2f} m; turning left.")
        else:
            command = "F"
        message = String()
        message.data = command
        self._publisher.publish(message)


def main(args=None):
    rclpy.init(args=args)
    node = ObstacleAvoidanceNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
