"""Persistent settings manager — config stored in ~/.config/rqt_doodle/config.yaml."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


_CONFIG_PATH = Path.home() / ".config" / "rqt_doodle" / "config.yaml"

# Docker Compose mounts secrets here as read-only files owned by root.
# The file contains only the raw key, no quotes or extra whitespace.
_SECRET_PATH = Path("/run/secrets/anthropic_api_key")

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
        """Return API key using this priority order:

        1. ANTHROPIC_API_KEY env var   — explicit override, highest priority
        2. Docker secret file          — /run/secrets/anthropic_api_key (never in env/image)
        3. Stored config               — entered via Settings dialog, saved to YAML
        """
        if env := os.environ.get("ANTHROPIC_API_KEY", ""):
            return env
        if _SECRET_PATH.exists():
            try:
                return _SECRET_PATH.read_text().strip()
            except OSError:
                pass
        return self._data.get("api_key", "")

    def api_key_source(self) -> str:
        """Human-readable label describing where the active key came from."""
        if os.environ.get("ANTHROPIC_API_KEY"):
            return "env var"
        if _SECRET_PATH.exists():
            try:
                if _SECRET_PATH.read_text().strip():
                    return "secrets file"
            except OSError:
                pass
        if self._data.get("api_key"):
            return "settings"
        return "not set"

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
