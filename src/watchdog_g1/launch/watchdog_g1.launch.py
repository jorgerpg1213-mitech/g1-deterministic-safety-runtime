"""
watchdog_g1.launch.py
G1 ROS2 Pipeline — Launch file para watchdog_g1 skeleton
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    watchdog_node = Node(
        package='watchdog_g1',
        executable='watchdog_g1',
        name='watchdog_g1',
        output='screen',
        emulate_tty=True,
    )

    return LaunchDescription([watchdog_node])
