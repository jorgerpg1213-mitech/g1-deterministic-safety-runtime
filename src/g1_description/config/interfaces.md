# G1 Pipeline — Interface Contracts
**Sistema:** G1 ROS2 Pipeline
**Fecha:** 2026-05-14
**Estado:** Phase 5 — EN DEFINICION

## Principios
- Todo topic tiene un propietario unico declarado
- Todo topic tiene QoS explicito justificado
- Todo frame pertenece al TF tree oficial
- Nada heredado del AGV sin justificacion explicita
- Todo provisional marcado, todo definitivo auditable

## 1. Topics del sistema

### 1.1 Navegacion y localizacion
- /odom | nav_msgs/Odometry | Reliable/10 | g1_adapter_node -> ekf_filter_node | PROVISIONAL: fuente real G1 SDK
- /odometry/filtered | nav_msgs/Odometry | Reliable/10 | ekf_filter_node -> Nav2 | ESTABLE
- /map | nav_msgs/OccupancyGrid | Reliable/latched | slam_toolbox -> Nav2 | ESTABLE
- /scan | sensor_msgs/LaserScan | BestEffort/10 | rplidar_node -> slam_toolbox | CONDICIONAL: solo si G1 lleva LiDAR externo
- /cmd_vel | geometry_msgs/Twist | Reliable/10 | Nav2 -> safety_policy_node | ESTABLE
- /cmd_vel_safe | geometry_msgs/Twist | Reliable/10 | safety_policy_node -> g1_adapter_node | ESTABLE

### 1.2 Sensores nativos G1
- /imu | sensor_msgs/Imu | BestEffort/10 | g1_adapter_node -> ekf_filter_node | PROVISIONAL: depende SDK G1
- /joint_states | sensor_msgs/JointState | Reliable/10 | g1_adapter_node -> robot_state_publisher | PROVISIONAL: joints Phase 4B

### 1.3 Resiliencia
- /g1/status | std_msgs/String JSON | Reliable/1 | g1_watchdog_node -> g1_recovery_manager | ESTABLE

### 1.4 Percepcion Phase 10
- /perception/detections | g1_msgs/DetectionArray3D | BestEffort/10 | gemini_perception_node -> Nav2 | PENDIENTE API Gemini

## 2. TF Tree
map -> odom (slam_toolbox)
  odom -> base_link (ekf_filter_node)
    base_link -> base_footprint (robot_state_publisher) TODO Phase 4B offset real
    base_link -> imu_link (robot_state_publisher) TODO Phase 4B posicion real
    base_link -> laser (robot_state_publisher) TODO Phase 4B si aplica

## 3. Mensajes custom

### 3.1 Descartados del AGV
- Detection.msg: percepcion 2D en pixeles, incompatible con G1/Gemini 3D
- DetectionArray.msg: wrapper del anterior, descartado junto

### 3.2 Nuevos mensajes G1
- Detection3D.msg: string class_name, float32 confidence, geometry_msgs/Pose pose, geometry_msgs/Vector3 dimensions, float64 timestamp | PENDIENTE API Gemini
- DetectionArray3D.msg: std_msgs/Header header, Detection3D[] detections | PENDIENTE API Gemini

## 4. QoS Policy
- Sensores alta frecuencia (IMU, scan): BestEffort / Volatile / Keep Last 10
- Navegacion (odom, cmd_vel): Reliable / Volatile / Keep Last 10
- Mapas (OccupancyGrid): Reliable / Transient Local / Keep Last 1
- Estado sistema (watchdog): Reliable / Volatile / Keep Last 1

## 5. Nodos del sistema
- g1_adapter_node | g1_adapter_node | PENDIENTE Phase 10 | SDK G1 a ROS2
- ekf_filter_node | robot_localization | ESTABLE migrado AGV | Fusion IMU odom
- async_slam_toolbox_node | slam_toolbox | ESTABLE migrado AGV | SLAM
- Nav2 stack | nav2_bringup | ESTABLE migrado AGV | Navegacion autonoma
- safety_policy_node | safety_policy_node | ESTABLE migrado AGV | Filtro cmd_vel
- g1_watchdog_node | agv_bringup | RENOMBRAR Phase 9 | Monitor topics
- g1_recovery_manager | agv_bringup | RENOMBRAR Phase 9 | Recovery automatico
- robot_state_publisher | g1_description | ESTABLE Phase 4A | TF desde URDF
- gemini_perception_node | TBD | PENDIENTE Phase 10 | Percepcion Gemini

*G1 Pipeline Interface Contracts — Phase 5 — 2026-05-14*
*Pendiente validacion Phase 4B USD y Phase 10 Gemini API*
