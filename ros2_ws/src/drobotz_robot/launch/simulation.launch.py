from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    package_share = Path(get_package_share_directory("drobotz_robot"))
    world = package_share / "worlds" / "drobotz_sim.sdf"
    parameters = package_share / "config" / "drobotz.yaml"
    gazebo_launch = (
        Path(get_package_share_directory("ros_gz_sim"))
        / "launch"
        / "gz_sim.launch.py"
    )

    gazebo_launch_source = PythonLaunchDescriptionSource(str(gazebo_launch))
    gazebo_gui = IncludeLaunchDescription(
        gazebo_launch_source,
        launch_arguments={"gz_args": f"-r '{world}'"}.items(),
        condition=IfCondition(LaunchConfiguration("gui")),
    )
    gazebo_headless = IncludeLaunchDescription(
        gazebo_launch_source,
        launch_arguments={"gz_args": f"-s -r '{world}'"}.items(),
        condition=UnlessCondition(LaunchConfiguration("gui")),
    )
    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=[
            "/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist",
            "/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan",
        ],
        output="screen",
    )
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "gui",
                default_value="true",
                description="Show the Gazebo graphical interface",
            ),
            DeclareLaunchArgument("enable_ai", default_value="true"),
            DeclareLaunchArgument("enable_dashboard", default_value="true"),
            DeclareLaunchArgument("enable_system_monitor", default_value="true"),
            gazebo_gui,
            gazebo_headless,
            bridge,
            Node(
                package="drobotz_robot",
                executable="simulation_hardware_node",
                name="drobotz_simulation_hardware",
                output="screen",
            ),
            Node(
                package="drobotz_robot",
                executable="obstacle_avoidance_node",
                name="drobotz_obstacle_avoidance",
                parameters=[str(parameters)],
                output="screen",
            ),
            Node(
                package="drobotz_robot",
                executable="system_monitor_node",
                name="drobotz_system_monitor",
                parameters=[str(parameters)],
                condition=IfCondition(LaunchConfiguration("enable_system_monitor")),
                output="screen",
            ),
            Node(
                package="drobotz_robot",
                executable="ai_controller_node",
                name="drobotz_ai_controller",
                parameters=[str(parameters)],
                condition=IfCondition(LaunchConfiguration("enable_ai")),
                output="screen",
            ),
            Node(
                package="drobotz_robot",
                executable="web_dashboard_node",
                name="drobotz_web_dashboard",
                parameters=[str(parameters)],
                condition=IfCondition(LaunchConfiguration("enable_dashboard")),
                output="screen",
            ),
        ]
    )
