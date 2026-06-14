cmake_minimum_required(VERSION 3.8)
project(doodle_msgs)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/AgentRequest.msg"
  "msg/AgentResponse.msg"
  "msg/DesignState.msg"
  DEPENDENCIES std_msgs
)

ament_export_dependencies(rosidl_default_runtime std_msgs)
ament_package()
