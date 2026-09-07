cmake_minimum_required(VERSION 3.8)
project(coordination_px4_bridge)

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  add_compile_options(-Wall -Wextra -Wpedantic -Werror)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(px4_msgs REQUIRED)
find_package(coordination_msgs REQUIRED)

add_executable(coordination_px4_bridge src/coordination_px4_bridge.cpp)
target_compile_features(coordination_px4_bridge PUBLIC cxx_std_17)
ament_target_dependencies(coordination_px4_bridge rclcpp px4_msgs coordination_msgs)

install(TARGETS coordination_px4_bridge DESTINATION lib/${PROJECT_NAME})
ament_package()
