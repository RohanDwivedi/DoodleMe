cmake_minimum_required(VERSION 3.8)
project(rqt_doodle)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

# Install the Python package into the ament install tree
ament_python_install_package(${PROJECT_NAME})

# rqt plugin descriptor
install(FILES plugin.xml
  DESTINATION share/${PROJECT_NAME})

# Stylesheet and SVG icons — loaded at runtime via get_package_share_directory()
install(DIRECTORY rqt_doodle/assets
  DESTINATION share/${PROJECT_NAME})

ament_package()
