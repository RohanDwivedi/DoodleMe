"""URDF tool — write and validate robot description files."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def write_urdf(
    content: str,
    filename: str = "robot.urdf",
    workspace: Path | None = None,
) -> dict[str, Any]:
    """Write a URDF file and return validation results."""
    workspace = _ws(workspace)
    path = workspace / filename
    path.write_text(content)

    validation = _validate_urdf(content)
    return {
        "status": "ok" if validation["valid"] else "warning",
        "urdf_path": str(path),
        "validation": validation,
        "message": (
            f"Wrote {path.name}"
            + (f" — {validation['warning']}" if validation.get("warning") else "")
        ),
    }


def _validate_urdf(content: str) -> dict[str, Any]:
    try:
        from lxml import etree  # type: ignore[import]

        root = etree.fromstring(content.encode())
        links = root.findall(".//link")
        joints = root.findall(".//joint")
        issues: list[str] = []

        if not any(l.get("name") == "base_link" for l in links):
            issues.append("No 'base_link' found — URDF should have a base_link")

        for joint in joints:
            jtype = joint.get("type")
            if jtype in ("revolute", "prismatic"):
                if joint.find("limit") is None:
                    name = joint.get("name", "?")
                    issues.append(f"Joint '{name}' is {jtype} but has no <limit>")

        return {
            "valid": True,
            "link_count": len(links),
            "joint_count": len(joints),
            "warning": "; ".join(issues) if issues else None,
        }
    except ImportError:
        return {"valid": True, "warning": "lxml not installed, skipping validation"}
    except Exception as exc:  # noqa: BLE001
        return {"valid": False, "warning": f"Parse error: {exc}"}


def _ws(workspace: Path | None) -> Path:
    if workspace is not None:
        return workspace
    default = Path.home() / "doodle_workspace"
    default.mkdir(parents=True, exist_ok=True)
    return default
