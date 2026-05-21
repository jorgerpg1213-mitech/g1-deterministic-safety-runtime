"""
recovery_g1.launch.py
G1 ROS2 Pipeline — Launch file para recovery_g1 skeleton
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    recovery_node = Node(
        package='recovery_g1',
        executable='recovery_g1',
        name='recovery_g1',
        output='screen',
        emulate_tty=True,
    )

    return LaunchDescription([recovery_node])
