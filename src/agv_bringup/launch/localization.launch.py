# [LEGACY AGV BASELINE] — DO NOT USE IN G1 CONTEXT
# This file is preserved as AGV terrestrial reference (v1.0-audit-x86).
# G1 canonical runtime: system_g1.launch.py

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():

    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[{
            'yaml_filename': '/root/agv_ws/src/agv_bringup/maps/map.yaml'
        }]
    )

    amcl = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=['/root/agv_ws/src/agv_bringup/config/amcl.yaml']
    )

    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_localization',
        output='screen',
        parameters=[{
            'use_sim_time': False,
            'autostart': True,
            'node_names': ['map_server', 'amcl']
        }]
    )

    return LaunchDescription([
        map_server,
        amcl,
        lifecycle_manager
    ])
