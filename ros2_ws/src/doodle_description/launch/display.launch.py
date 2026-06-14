"""Launch robot_state_publisher + joint_state_publisher_gui + RViz2 for the current design."""

from __future__ import annotations

from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description() -> LaunchDescription:
    urdf_default = str(Path.home() / "doodle_workspace" / "robot.urdf")

    urdf_arg = DeclareLaunchArgument(
        "urdf",
        default_value=urdf_default,
        description="Absolute path to the URDF file to display",
    )

    robot_description = ParameterValue(
        Command(["cat ", LaunchConfiguration("urdf")]),
        value_type=str,
    )

    rsp = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        parameters=[{"robot_description": robot_description}],
        output="screen",
    )

    jsp_gui = Node(
        package="joint_state_publisher_gui",
        executable="joint_state_publisher_gui",
        name="joint_state_publisher_gui",
        output="screen",
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
    )

    return LaunchDescription([urdf_arg, rsp, jsp_gui, rviz])
