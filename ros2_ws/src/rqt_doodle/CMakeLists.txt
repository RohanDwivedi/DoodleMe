cmake_minimum_required(VERSION 3.8)
project(rqt_doodle)

find_package(ament_cmake REQUIRED)

# Python package is installed via pip in the Dockerfile (Layer 4a).
# This CMakeLists.txt handles ament_index registration, plugin.xml, and assets.

# rqt plugin descriptor — rqt reads this via the export in package.xml
install(FILES plugin.xml
  DESTINATION share/${PROJECT_NAME})

# Stylesheet and SVG icons — loaded at runtime via get_package_share_directory()
install(DIRECTORY rqt_doodle/assets
  DESTINATION share/${PROJECT_NAME})

ament_package()
