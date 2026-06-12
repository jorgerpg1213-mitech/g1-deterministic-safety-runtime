cmake_minimum_required(VERSION 3.8)
project(g1_msgs)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(builtin_interfaces REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/Detection3D.msg"
  "msg/DetectionArray3D.msg"
  "msg/SafetyEvent.msg"
  "msg/SystemState.msg"
  "msg/SafetyAction.msg"
  "msg/RecoveryEvent.msg"
  "msg/FootContact.msg"
  DEPENDENCIES std_msgs geometry_msgs builtin_interfaces
)

ament_package()
