cmake_minimum_required(VERSION 3.8)
project(agv_bringup)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY
    launch
    config
    maps
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)

  ament_add_pytest_test(smoke_test_watchdog test/smoke_test_watchdog.py
    TIMEOUT 30
    ENV ROS_DOMAIN_ID=99
  )

  ament_add_pytest_test(smoke_test_recovery_manager test/smoke_test_recovery_manager.py
    TIMEOUT 30
    ENV ROS_DOMAIN_ID=99
  )
endif()

ament_package()
