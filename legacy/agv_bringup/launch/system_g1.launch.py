"""
system_g1.launch.py — Runtime Canónico G1
==========================================
Launch file principal del pipeline G1 ROS2.

SCOPE EXPLÍCITO:
  - Arranca TF tree desde g1_description (XACRO ultraconservador Phase 4A)
  - Arranca slam_toolbox (agnóstico al hardware)
  - Arranca safety_policy_node (agnóstico al hardware)
  - Arranca ekf_node como placeholder G1-ready (config separada de AGV)
  - Arranca watchdog y recovery con paths parametrizables (sin hardcodes)

CONTRATOS PENDIENTES (deuda transicional explícita):
  - /odom       → pendiente g1_adapter_node (Deferred D-004, requiere SDK Unitree G1)
  - /imu        → pendiente g1_adapter_node (Deferred D-004, requiere SDK Unitree G1)
  - /scan       → condicional (LiDAR externo opcional o Isaac Sim Phase 8)
  - Nav2        → no incluido hasta tener odometría G1 real validada

EXCLUIDO EXPLÍCITAMENTE (hardware AGV — no aplica al G1):
  - esp32_bridge_node
  - odom_node (AGV wheel encoder)
  - rplidar hardcodeado
  - static_transform_publisher (reemplazado por robot_state_publisher + XACRO)

REFERENCIA LEGACY:
  Los launch files AGV originales permanecen en launch/ marcados como legacy.
  Ver: system_nav2_slam.launch.py (AGV baseline — NO usar en contexto G1)

Phase 4B: cuando USD oficiales Unitree estén disponibles en MIT VM,
  actualizar g1.xacro y ekf_g1.yaml con valores físicos reales.
Phase 8: agregar use_sim_time=true y topics Isaac cuando VM esté disponible.
Phase 10: agregar g1_adapter_node cuando SDK Unitree esté disponible.
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, ExecuteProcess, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, EnvironmentVariable
from launch_ros.actions import Node


def generate_launch_description():

    # ── Launch Arguments ──────────────────────────────────────────────────────
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation time — set true for Isaac Sim (Phase 8)'
    )

    workspace_arg = DeclareLaunchArgument(
        'workspace_path',
        default_value=EnvironmentVariable('PIPELINE_WS', default_value='/opt/pipeline_ws'),
        description='Pipeline workspace path — overrides hardcoded /root/agv_ws'
    )

    share_path_arg = DeclareLaunchArgument(
        'share_path',
        default_value=EnvironmentVariable('PIPELINE_SHARE', default_value='/mnt/g1_share'),
        description='Shared volume path for status/logs — replaces /mnt/agv_share'
    )

    use_sim_time = LaunchConfiguration('use_sim_time')
    workspace_path = LaunchConfiguration('workspace_path')
    share_path = LaunchConfiguration('share_path')

    # ── Package Directories ───────────────────────────────────────────────────
    g1_description_dir = get_package_share_directory('g1_description')
    slam_toolbox_dir = get_package_share_directory('slam_toolbox')

    # ── Config Paths ──────────────────────────────────────────────────────────
    # NOTE: ekf_g1.yaml es config separada del AGV — pendiente valores Phase 4B
    # TODO Phase 4B: reemplazar con parámetros derivados de USD oficial Unitree
    g1_bringup_dir = get_package_share_directory('agv_bringup')  # TODO Phase 9: renombrar a g1_bringup
    ekf_params = os.path.join(g1_bringup_dir, 'config', 'ekf.yaml')
    slam_params = os.path.join(g1_bringup_dir, 'config', 'slam_toolbox_online.yaml')

    # ── TF Tree — desde XACRO G1 (Phase 4A ultraconservador) ─────────────────
    # Publica: base_link → base_footprint, base_link → imu_link, base_link → laser
    # Reemplaza los 3 static_transform_publisher hardcodeados del stack AGV
    description_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(g1_description_dir, 'launch', 'description.launch.py')
        )
    )

    # ── EKF — placeholder G1-ready ────────────────────────────────────────────
    # CONTRATO PENDIENTE:
    #   /imu  → pendiente g1_adapter_node (Phase 10 / SDK Unitree)
    #   /odom → pendiente g1_adapter_node (Phase 10 / SDK Unitree)
    # El nodo arranca pero no tendrá datos reales hasta Phase 10
    ekf_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[
            ekf_params,
            {'use_sim_time': use_sim_time}
        ]
    )

    # ── SLAM Toolbox — agnóstico al hardware ──────────────────────────────────
    # Requiere /scan — condicional hasta LiDAR externo o Isaac Sim (Phase 8)
    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(slam_toolbox_dir, 'launch', 'online_async_launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'slam_params_file': slam_params
        }.items()
    )

    # ── Safety Policy — agnóstico al hardware ─────────────────────────────────
    safety_policy_node = Node(
        package='safety_policy_node',
        executable='safety_policy_node',
        name='safety_policy_node',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'cmd_in_topic': '/cmd_vel',
            'cmd_out_topic': '/cmd_vel_safe',
            'detections_topic': '/detections',
        }]
    )

    # ── Watchdog — paths parametrizables (sin hardcodes) ─────────────────────
    # Entrypoint Docker ya hace source de ROS2 + workspace — no requiere bash -c
    # PIPELINE_SHARE inyectado como env var — leído por el script en runtime
    # TODO Phase 9: renombrar script a g1_watchdog_node.py
    watchdog_process = ExecuteProcess(
        cmd=[
            'python3',
            [workspace_path, '/src/agv_bringup/scripts/agv_watchdog_node.py']
        ],
        additional_env={'PIPELINE_SHARE': share_path},
        output='screen'
    )

    # ── Recovery Manager — paths parametrizables (sin hardcodes) ─────────────
    # Entrypoint Docker ya hace source de ROS2 + workspace — no requiere bash -c
    # PIPELINE_SHARE inyectado como env var — leído por el script en runtime
    # TODO Phase 6 Upgrade: refactor a RecoveryAction abstraction
    # TODO Phase 9: renombrar script a g1_recovery_manager.py
    recovery_process = ExecuteProcess(
        cmd=[
            'python3',
            [workspace_path, '/src/agv_bringup/scripts/agv_recovery_manager.py']
        ],
        additional_env={'PIPELINE_SHARE': share_path},
        output='screen'
    )

    return LaunchDescription([
        # Arguments
        use_sim_time_arg,
        workspace_arg,
        share_path_arg,

        # TF Tree desde XACRO G1
        description_launch,

        # Localización — placeholder hasta SDK G1
        ekf_node,

        # SLAM — agnóstico al hardware
        slam,

        # Seguridad — agnóstico al hardware
        safety_policy_node,

        # Monitoreo y recovery — paths parametrizables
        watchdog_process,
        recovery_process,
    ])
