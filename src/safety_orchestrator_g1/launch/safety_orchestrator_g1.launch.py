"""
safety_orchestrator_g1.launch.py
G1 ROS2 Pipeline — Launch file para safety_orchestrator_g1 skeleton
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    orchestrator_node = Node(
        package='safety_orchestrator_g1',
        executable='safety_orchestrator_g1',
        name='safety_orchestrator_g1',
        output='screen',
        emulate_tty=True,
    )

    return LaunchDescription([orchestrator_node])
