from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from pathlib import Path


def generate_launch_description():
    parameters = str(Path(get_package_share_directory("drobotz_robot")) / "config" / "drobotz.yaml")
    return LaunchDescription(
        [
            DeclareLaunchArgument("enable_camera", default_value="true"),
            DeclareLaunchArgument("enable_ai", default_value="true"),
            DeclareLaunchArgument("enable_dashboard", default_value="true"),
            Node(
                package="drobotz_robot",
                executable="hardware_node",
                name="drobotz_hardware",
                parameters=[parameters],
                output="screen",
            ),
            Node(
                package="drobotz_robot",
                executable="camera_node",
                name="drobotz_camera",
                parameters=[parameters],
                condition=IfCondition(LaunchConfiguration("enable_camera")),
                output="screen",
            ),
            Node(
                package="drobotz_robot",
                executable="system_monitor_node",
                name="drobotz_system_monitor",
                parameters=[parameters],
                output="screen",
            ),
            Node(
                package="drobotz_robot",
                executable="obstacle_avoidance_node",
                name="drobotz_obstacle_avoidance",
                parameters=[parameters],
                output="screen",
            ),
            Node(
                package="drobotz_robot",
                executable="ai_controller_node",
                name="drobotz_ai_controller",
                parameters=[parameters],
                condition=IfCondition(LaunchConfiguration("enable_ai")),
                output="screen",
            ),
            Node(
                package="drobotz_robot",
                executable="web_dashboard_node",
                name="drobotz_web_dashboard",
                parameters=[parameters],
                condition=IfCondition(LaunchConfiguration("enable_dashboard")),
                output="screen",
            ),
        ]
    )
