cmake_minimum_required(VERSION 3.8)
project(g1_description)

find_package(ament_cmake REQUIRED)

install(DIRECTORY urdf xacro launch config meshes
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
