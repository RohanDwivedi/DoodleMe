"""Unit tests for doodle_agent tool functions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from doodle_agent.tools.bom_tool import update_bom
from doodle_agent.tools.openscad_tool import write_openscad
from doodle_agent.tools.urdf_tool import write_urdf, _validate_urdf
from doodle_agent.tools.wiring_tool import generate_wiring
from doodle_agent.tools.kicad_tool import export_kicad


# ── OpenSCAD tool ─────────────────────────────────────────────────────────────

class TestWriteOpenSCAD:
    def test_writes_file(self, tmp_workspace: Path) -> None:
        code = "cube([10, 10, 10]);"
        result = write_openscad(code, workspace=tmp_workspace)
        assert result["status"] == "ok"
        assert Path(result["scad_path"]).exists()
        assert Path(result["scad_path"]).read_text() == code

    def test_custom_filename(self, tmp_workspace: Path) -> None:
        result = write_openscad("sphere(5);", filename="part.scad", workspace=tmp_workspace)
        assert Path(tmp_workspace / "part.scad").exists()

    def test_overwrite(self, tmp_workspace: Path) -> None:
        write_openscad("cube([1,1,1]);", workspace=tmp_workspace)
        result = write_openscad("sphere(10);", workspace=tmp_workspace)
        assert result["status"] == "ok"
        assert "sphere" in Path(result["scad_path"]).read_text()


# ── URDF tool ─────────────────────────────────────────────────────────────────

class TestWriteURDF:
    _VALID = """<?xml version="1.0"?>
<robot name="test">
  <link name="base_link"/>
  <link name="arm"/>
  <joint name="j1" type="revolute">
    <parent link="base_link"/>
    <child link="arm"/>
    <axis xyz="0 0 1"/>
    <limit lower="-1.57" upper="1.57" velocity="1.0" effort="5.0"/>
  </joint>
</robot>"""

    def test_writes_file(self, tmp_workspace: Path) -> None:
        result = write_urdf(self._VALID, workspace=tmp_workspace)
        assert result["status"] == "ok"
        assert Path(result["urdf_path"]).exists()

    def test_validate_no_base_link(self) -> None:
        xml = '<robot name="r"><link name="foo"/></robot>'
        v = _validate_urdf(xml)
        assert v["warning"] is not None
        assert "base_link" in v["warning"]

    def test_validate_missing_limit(self) -> None:
        xml = """<robot name="r">
          <link name="base_link"/>
          <link name="arm"/>
          <joint name="j1" type="revolute">
            <parent link="base_link"/><child link="arm"/>
          </joint>
        </robot>"""
        v = _validate_urdf(xml)
        assert "limit" in (v["warning"] or "")

    def test_validate_valid_urdf(self) -> None:
        v = _validate_urdf(self._VALID)
        assert v["valid"]
        assert v["link_count"] == 2
        assert v["joint_count"] == 1


# ── BOM tool ──────────────────────────────────────────────────────────────────

class TestBOMTool:
    def test_add_item(self, tmp_workspace: Path) -> None:
        result = update_bom(
            "add",
            {"id": "u1", "name": "Arduino Nano", "qty": 1, "unit_price": 5.99},
            workspace=tmp_workspace,
        )
        assert result["status"] == "ok"
        assert result["count"] == 1
        assert result["bom"][0]["name"] == "Arduino Nano"

    def test_add_duplicate_updates(self, tmp_workspace: Path) -> None:
        update_bom("add", {"id": "u1", "name": "Servo", "qty": 1}, workspace=tmp_workspace)
        result = update_bom(
            "add", {"id": "u1", "name": "Servo", "qty": 3}, workspace=tmp_workspace
        )
        assert result["count"] == 1
        assert result["bom"][0]["qty"] == 3

    def test_remove_item(self, tmp_workspace: Path) -> None:
        update_bom("add", {"id": "u1", "name": "A"}, workspace=tmp_workspace)
        update_bom("add", {"id": "u2", "name": "B"}, workspace=tmp_workspace)
        result = update_bom("remove", {"id": "u1"}, workspace=tmp_workspace)
        assert result["count"] == 1
        assert result["bom"][0]["id"] == "u2"

    def test_clear(self, tmp_workspace: Path) -> None:
        update_bom("add", {"id": "x1", "name": "X"}, workspace=tmp_workspace)
        result = update_bom("clear", workspace=tmp_workspace)
        assert result["count"] == 0

    def test_total_price(self, tmp_workspace: Path) -> None:
        update_bom(
            "add", {"id": "a", "name": "A", "qty": 2, "unit_price": 3.0}, workspace=tmp_workspace
        )
        result = update_bom(
            "add", {"id": "b", "name": "B", "qty": 1, "unit_price": 4.0}, workspace=tmp_workspace
        )
        assert result["total_price"] == pytest.approx(10.0)

    def test_persists_to_disk(self, tmp_workspace: Path) -> None:
        update_bom("add", {"id": "p1", "name": "Persisted"}, workspace=tmp_workspace)
        bom_file = tmp_workspace / "bom.json"
        assert bom_file.exists()
        data = json.loads(bom_file.read_text())
        assert any(item["id"] == "p1" for item in data)


# ── Wiring tool ───────────────────────────────────────────────────────────────

class TestWiringTool:
    def test_saves_diagram(self, tmp_workspace: Path) -> None:
        diagram = "graph LR\n    MCU-->|PWM| Servo"
        result = generate_wiring(diagram, workspace=tmp_workspace)
        assert result["status"] == "ok"
        assert result["mermaid"] == diagram
        assert Path(result["wiring_path"]).read_text() == diagram


# ── KiCad tool ────────────────────────────────────────────────────────────────

class TestKiCadTool:
    def test_generates_file(self, tmp_workspace: Path) -> None:
        result = export_kicad(
            components=[
                {"ref": "U1", "value": "Arduino Nano"},
                {"ref": "M1", "value": "MG996R Servo"},
            ],
            workspace=tmp_workspace,
        )
        assert result["status"] == "ok"
        assert result["component_count"] == 2
        assert Path(result["kicad_path"]).exists()

    def test_kicad_file_contains_refs(self, tmp_workspace: Path) -> None:
        export_kicad(
            components=[{"ref": "U1", "value": "ESP32"}],
            workspace=tmp_workspace,
        )
        content = (tmp_workspace / "robot.kicad_sch").read_text()
        assert "U1" in content
        assert "ESP32" in content
