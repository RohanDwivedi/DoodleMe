"""Persistent settings manager — config stored in ~/.config/rqt_doodle/config.yaml."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


_CONFIG_PATH = Path.home() / ".config" / "rqt_doodle" / "config.yaml"

_DEFAULTS: dict[str, Any] = {
    "api_key": "",
    "model": "claude-sonnet-4-6",
    "workspace": str(Path.home() / "doodle_workspace"),
    "theme": "dark",
    "auto_render": True,
    "auto_publish_urdf": True,
    "openscad_path": "openscad",
    "session_dir": str(Path.home() / ".local" / "share" / "rqt_doodle" / "sessions"),
    "max_history_messages": 100,
}


class Settings:
    """Thread-safe settings backed by a YAML file."""

    def __init__(self, config_path: Path = _CONFIG_PATH) -> None:
        self._path = config_path
        self._data: dict[str, Any] = dict(_DEFAULTS)
        self._load()

    # ── Public API ──────────────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._save()

    def api_key(self) -> str:
        """Return API key from config or ANTHROPIC_API_KEY env var."""
        env = os.environ.get("ANTHROPIC_API_KEY", "")
        return env or self._data.get("api_key", "")

    def has_api_key(self) -> bool:
        return bool(self.api_key())

    def workspace_path(self) -> Path:
        p = Path(self._data.get("workspace", _DEFAULTS["workspace"]))
        p.mkdir(parents=True, exist_ok=True)
        return p

    def session_dir(self) -> Path:
        p = Path(self._data.get("session_dir", _DEFAULTS["session_dir"]))
        p.mkdir(parents=True, exist_ok=True)
        return p

    # ── Internal ────────────────────────────────────────────────────────────

    def _load(self) -> None:
        if self._path.exists():
            try:
                with self._path.open() as f:
                    loaded = yaml.safe_load(f) or {}
                self._data.update(loaded)
            except (yaml.YAMLError, OSError):
                pass

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w") as f:
            yaml.dump(self._data, f, default_flow_style=False)
