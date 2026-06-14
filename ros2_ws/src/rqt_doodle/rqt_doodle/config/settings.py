"""Persistent settings manager — config stored in ~/.config/rqt_doodle/config.yaml.

API KEY SECURITY
----------------
The Anthropic API key is NEVER stored here. The single authoritative copy lives at
/etc/doodleme/secrets/anthropic_api_key on the host, which Docker bind-mounts
read-only into the container at /run/secrets/anthropic_api_key.

  DO NOT log, print, cache, or copy the key anywhere else in this codebase.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


_CONFIG_PATH = Path.home() / ".config" / "rqt_doodle" / "config.yaml"

# Docker Compose bind-mounts /etc/doodleme/secrets here (read-only).
# The file contains only the raw key — no quotes, no whitespace.
_SECRET_PATH = Path("/run/secrets/anthropic_api_key")

_DEFAULTS: dict[str, Any] = {
    # api_key is intentionally absent — it must never be stored in this file.
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
    """Thread-safe settings backed by a YAML file.

    The API key is deliberately excluded from persistence — read api_key() for details.
    """

    def __init__(self, config_path: Path = _CONFIG_PATH) -> None:
        self._path = config_path
        self._data: dict[str, Any] = dict(_DEFAULTS)
        self._load()

    # ── Public API ──────────────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        if key == "api_key":
            raise ValueError(
                "API key must not be saved via Settings. "
                "Write it to /etc/doodleme/secrets/anthropic_api_key instead."
            )
        self._data[key] = value
        self._save()

    def api_key(self) -> str:
        """Read the API key — never logs or caches the value.

        Priority:
          1. /run/secrets/anthropic_api_key  — Docker bind-mount (authoritative)
          2. ANTHROPIC_API_KEY env var        — fallback for bare-metal installs only;
                                               note the key is visible in `ps`, docker
                                               inspect, and container logs — avoid in prod.
        """
        if _SECRET_PATH.exists():
            try:
                return _SECRET_PATH.read_text().strip()
            except OSError:
                pass
        # Env-var fallback: accepted but not recommended.
        return os.environ.get("ANTHROPIC_API_KEY", "")

    def api_key_source(self) -> str:
        """Human-readable label describing where the active key came from."""
        if _SECRET_PATH.exists():
            try:
                if _SECRET_PATH.read_text().strip():
                    return "secrets file"
            except OSError:
                pass
        if os.environ.get("ANTHROPIC_API_KEY"):
            return "env var"
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
                # Silently drop any api_key that leaked into an old config file.
                loaded.pop("api_key", None)
                self._data.update(loaded)
            except (yaml.YAMLError, OSError):
                pass

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # Defensive: strip api_key even if it somehow ended up in _data.
        safe = {k: v for k, v in self._data.items() if k != "api_key"}
        with self._path.open("w") as f:
            yaml.dump(safe, f, default_flow_style=False)
