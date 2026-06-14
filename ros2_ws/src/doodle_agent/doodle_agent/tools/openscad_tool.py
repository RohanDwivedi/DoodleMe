"""OpenSCAD tools — write .scad source and render to STL."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any


def write_openscad(
    code: str,
    filename: str = "model.scad",
    workspace: Path | None = None,
) -> dict[str, Any]:
    """Write OpenSCAD source to the workspace."""
    workspace = _ws(workspace)
    path = workspace / filename
    path.write_text(code)
    return {
        "status": "ok",
        "scad_path": str(path),
        "lines": code.count("\n") + 1,
        "message": f"Wrote {path.name} ({code.count(chr(10)) + 1} lines)",
    }


def render_stl(
    scad_filename: str = "model.scad",
    stl_filename: str = "model.stl",
    openscad_binary: str = "openscad",
    workspace: Path | None = None,
) -> dict[str, Any]:
    """Render a .scad file to STL using OpenSCAD subprocess."""
    workspace = _ws(workspace)
    scad_path = workspace / scad_filename
    stl_path = workspace / stl_filename

    if not scad_path.exists():
        return {"status": "error", "message": f"{scad_filename} not found in workspace"}

    t0 = time.monotonic()
    try:
        result = subprocess.run(
            [openscad_binary, "-o", str(stl_path), str(scad_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        return {
            "status": "error",
            "message": f"OpenSCAD binary '{openscad_binary}' not found. Install openscad.",
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "OpenSCAD render timed out after 120 s"}

    elapsed = time.monotonic() - t0

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        return {
            "status": "error",
            "message": f"OpenSCAD render failed:\n{stderr}",
        }

    size_kb = stl_path.stat().st_size // 1024
    return {
        "status": "ok",
        "stl_path": str(stl_path),
        "elapsed_s": round(elapsed, 2),
        "size_kb": size_kb,
        "message": f"Rendered {stl_path.name} ({size_kb} kB) in {elapsed:.1f} s",
    }


def _ws(workspace: Path | None) -> Path:
    if workspace is not None:
        return workspace
    default = Path.home() / "doodle_workspace"
    default.mkdir(parents=True, exist_ok=True)
    return default
