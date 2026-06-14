cmake_minimum_required(VERSION 3.8)
project(doodle_agent)

find_package(ament_cmake REQUIRED)

# Python package is installed via pip in the Dockerfile (Layer 4a).
# This CMakeLists.txt only registers the package in the ament_index.

ament_package()
