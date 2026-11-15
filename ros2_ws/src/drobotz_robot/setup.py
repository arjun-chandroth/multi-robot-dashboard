import os
from glob import glob

from setuptools import find_packages, setup


package_name = "drobotz_robot"
share_files = []
for directory, _, filenames in os.walk("web"):
    for filename in filenames:
        source = os.path.join(directory, filename)
        share_files.append((os.path.join("share", package_name, directory), [source]))

setup(
    name=package_name,
    version="1.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
        ("share/" + package_name + "/firmware", glob("firmware/*")),
        ("share/" + package_name + "/models", glob("models/*")),
        *share_files,
    ],
    install_requires=["setuptools"],
    zip_safe=False,
    maintainer="DROBOTZ",
    maintainer_email="maintainer@example.com",
    description="DROBOTZ robot control nodes for ROS 2 Jazzy",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "hardware_node = drobotz_robot.nodes.hardware_node:main",
            "camera_node = drobotz_robot.nodes.camera_node:main",
            "system_monitor_node = drobotz_robot.nodes.system_monitor_node:main",
            "obstacle_avoidance_node = drobotz_robot.nodes.obstacle_avoidance_node:main",
            "ai_controller_node = drobotz_robot.nodes.ai_controller_node:main",
            "web_dashboard_node = drobotz_robot.nodes.web_dashboard_node:main",
        ],
    },
)
