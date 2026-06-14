"""Shared pytest fixtures for doodle_agent tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """Return a temporary workspace directory."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


@pytest.fixture
def sample_scad(tmp_workspace: Path) -> Path:
    code = """
// DoodleMe sample — parametric servo bracket
servo_width = 23.0;
servo_height = 30.0;
wall = 2.0;
hole_d = 3.2;

module servo_bracket() {
    difference() {
        cube([servo_width + wall*2, servo_height + wall*2, 20]);
        translate([wall, wall, wall])
            cube([servo_width, servo_height, 25]);
        // Mounting holes
        for (x = [wall/2, servo_width + wall + wall/2])
            translate([x, (servo_height + wall*2)/2, -1])
                cylinder(d=hole_d, h=22, $fn=32);
    }
}

servo_bracket();
"""
    p = tmp_workspace / "model.scad"
    p.write_text(code)
    return p


@pytest.fixture
def sample_urdf(tmp_workspace: Path) -> Path:
    xml = """<?xml version="1.0"?>
<robot name="test_robot">
  <link name="base_link">
    <visual>
      <geometry><box size="0.1 0.1 0.05"/></geometry>
    </visual>
    <inertial>
      <mass value="0.5"/>
      <inertia ixx="0.001" iyy="0.001" izz="0.001" ixy="0" ixz="0" iyz="0"/>
    </inertial>
  </link>
  <link name="arm_link">
    <visual>
      <geometry><cylinder radius="0.01" length="0.1"/></geometry>
    </visual>
  </link>
  <joint name="arm_joint" type="revolute">
    <parent link="base_link"/>
    <child link="arm_link"/>
    <axis xyz="0 0 1"/>
    <limit lower="-1.57" upper="1.57" velocity="1.0" effort="10.0"/>
  </joint>
</robot>"""
    p = tmp_workspace / "robot.urdf"
    p.write_text(xml)
    return p
