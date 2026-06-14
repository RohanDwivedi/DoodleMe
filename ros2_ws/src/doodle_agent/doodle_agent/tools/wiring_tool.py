"""Wiring tool — persist a Mermaid diagram to the workspace."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def generate_wiring(
    diagram: str,
    filename: str = "wiring.mmd",
    workspace: Path | None = None,
) -> dict[str, Any]:
    """Save a Mermaid wiring diagram source file."""
    workspace = _ws(workspace)
    path = workspace / filename
    path.write_text(diagram)
    return {
        "status": "ok",
        "mermaid": diagram,
        "wiring_path": str(path),
        "message": f"Wiring diagram saved to {path.name}",
    }


def _ws(workspace: Path | None) -> Path:
    if workspace is not None:
        return workspace
    default = Path.home() / "doodle_workspace"
    default.mkdir(parents=True, exist_ok=True)
    return default
