"""
cross_consistency_observer.launch.py
G1 ROS2 Pipeline — Launch file para cross_consistency_observer skeleton
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    observer_node = Node(
        package='cross_consistency_observer',
        executable='cross_consistency_observer',
        name='cross_consistency_observer',
        output='screen',
        emulate_tty=True,
    )

    return LaunchDescription([observer_node])
