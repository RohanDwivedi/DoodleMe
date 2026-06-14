cmake_minimum_required(VERSION 3.8)
project(doodle_agent)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

# Install the Python package into the ament install tree
ament_python_install_package(${PROJECT_NAME})

ament_package()
