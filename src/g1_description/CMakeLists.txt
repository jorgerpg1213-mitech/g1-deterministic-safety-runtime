cmake_minimum_required(VERSION 3.8)
project(g1_description)

find_package(ament_cmake REQUIRED)

install(DIRECTORY urdf xacro launch config meshes
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  find_package(launch_testing_ament_cmake REQUIRED)
  add_launch_test(test/test_description_launch.py
    TIMEOUT 30
    ENV ROS_DOMAIN_ID=99
  )
endif()
ament_package()
