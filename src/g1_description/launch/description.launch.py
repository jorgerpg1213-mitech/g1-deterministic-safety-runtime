import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import Command

def generate_launch_description():
    pkg = get_package_share_directory('g1_description')
    xacro_file = os.path.join(pkg, 'xacro', 'g1.xacro')

    return LaunchDescription([
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{
                'robot_description': Command(['xacro', ' ', xacro_file]),
                # Phase 4B: set use_sim_time=true when connecting Isaac
                'use_sim_time': False,
            }]
        )
    ])
