"""KiCad export tool — generates a .kicad_sch schematic file."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any


def export_kicad(
    components: list[dict[str, Any]],
    nets: list[dict[str, Any]] | None = None,
    title: str = "DoodleMe Robot",
    filename: str = "robot.kicad_sch",
    workspace: Path | None = None,
) -> dict[str, Any]:
    """Generate a KiCad 6+ schematic file from component and net lists."""
    workspace = _ws(workspace)
    path = workspace / filename
    nets = nets or []

    content = _render_kicad_sch(title, components, nets)
    path.write_text(content)

    return {
        "status": "ok",
        "kicad_path": str(path),
        "component_count": len(components),
        "net_count": len(nets),
        "message": f"KiCad schematic written to {path.name}",
    }


# ── KiCad 6 S-expression renderer ────────────────────────────────────────────

def _render_kicad_sch(
    title: str,
    components: list[dict[str, Any]],
    nets: list[dict[str, Any]],
) -> str:
    stamp = int(time.time())
    lines = [
        '(kicad_sch (version 20230121) (generator doodle_me)',
        '',
        f'  (title_block',
        f'    (title "{title}")',
        f'    (date "{time.strftime("%Y-%m-%d")}")',
        f'    (rev "0.1")',
        f'  )',
        '',
    ]

    for i, comp in enumerate(components):
        ref = comp.get("ref", f"U{i+1}")
        value = comp.get("value", "")
        footprint = comp.get("footprint", "")
        x = float(comp.get("x", 50 + i * 40))
        y = float(comp.get("y", 50))
        uid = f"{stamp:08x}{i:04x}"
        lines += [
            f'  (symbol (lib_id "Device:Generic") (at {x} {y} 0) (unit 1)',
            f'    (reference "{ref}")',
            f'    (value "{value}")',
            f'    (footprint "{footprint}")',
            f'    (uuid "{uid}")',
            f'  )',
            '',
        ]

    for net in nets:
        net_name = net.get("name", "")
        lines.append(f'  (net_tie (net_name "{net_name}"))')

    lines.append(')')
    return "\n".join(lines)


def _ws(workspace: Path | None) -> Path:
    if workspace is not None:
        return workspace
    default = Path.home() / "doodle_workspace"
    default.mkdir(parents=True, exist_ok=True)
    return default
