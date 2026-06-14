"""BOM tool — maintain a JSON bill of materials in the workspace."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_BOM_FILE = "bom.json"


def update_bom(
    action: str,
    item: dict[str, Any] | None = None,
    workspace: Path | None = None,
) -> dict[str, Any]:
    """Add, update, remove, or clear BOM items."""
    workspace = _ws(workspace)
    bom = _load(workspace)

    match action:
        case "add":
            if item is None:
                return {"status": "error", "message": "item required for 'add'"}
            existing_ids = {e["id"] for e in bom}
            if item.get("id") in existing_ids:
                return update_bom("update", item, workspace)
            bom.append(_normalise(item))

        case "update":
            if item is None:
                return {"status": "error", "message": "item required for 'update'"}
            for i, entry in enumerate(bom):
                if entry["id"] == item.get("id"):
                    bom[i] = {**entry, **_normalise(item)}
                    break
            else:
                bom.append(_normalise(item))

        case "remove":
            if item is None:
                return {"status": "error", "message": "item with id required for 'remove'"}
            bom = [e for e in bom if e["id"] != item.get("id")]

        case "clear":
            bom = []

        case _:
            return {"status": "error", "message": f"Unknown action: {action!r}"}

    _save(workspace, bom)
    return {
        "status": "ok",
        "bom": bom,
        "count": len(bom),
        "total_price": sum(
            e.get("unit_price", 0) * e.get("qty", 1) for e in bom
        ),
        "message": f"BOM updated — {len(bom)} item(s)",
    }


# ── Internal ─────────────────────────────────────────────────────────────────

def _normalise(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id", ""),
        "name": item.get("name", ""),
        "category": item.get("category", "other"),
        "qty": int(item.get("qty", 1)),
        "supplier": item.get("supplier", ""),
        "part_number": item.get("part_number", ""),
        "unit_price": float(item.get("unit_price", 0.0)),
        "notes": item.get("notes", ""),
    }


def _load(workspace: Path) -> list[dict[str, Any]]:
    path = workspace / _BOM_FILE
    if path.exists():
        try:
            data = json.loads(path.read_text())
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _save(workspace: Path, bom: list[dict[str, Any]]) -> None:
    (workspace / _BOM_FILE).write_text(json.dumps(bom, indent=2))


def _ws(workspace: Path | None) -> Path:
    if workspace is not None:
        return workspace
    default = Path.home() / "doodle_workspace"
    default.mkdir(parents=True, exist_ok=True)
    return default
