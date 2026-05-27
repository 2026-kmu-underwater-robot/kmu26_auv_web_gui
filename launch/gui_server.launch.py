#!/usr/bin/env python3

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    host = LaunchConfiguration("host")
    port = LaunchConfiguration("port")
    robot_package = LaunchConfiguration("robot_package")
    robot_launch = LaunchConfiguration("robot_launch")

    return LaunchDescription(
        [
            DeclareLaunchArgument("host", default_value="0.0.0.0"),
            DeclareLaunchArgument("port", default_value="8080"),
            DeclareLaunchArgument("robot_package", default_value="hit25_auv_ros2"),
            DeclareLaunchArgument("robot_launch", default_value="localization_test.launch.py"),
            Node(
                package="kmu26_auv_web_gui",
                executable="server",
                name="kmu26_auv_web_gui_server",
                output="screen",
                arguments=[
                    "--host",
                    host,
                    "--port",
                    port,
                    "--robot-package",
                    robot_package,
                    "--robot-launch",
                    robot_launch,
                ],
            ),
        ]
    )
