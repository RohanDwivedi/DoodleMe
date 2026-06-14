"""Session manager — auto-saves conversation history and recovers after crashes."""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any


class SessionManager:
    """Persists conversation history to disk with atomic writes and crash recovery."""

    _ACTIVE = "active.json"
    _BACKUP = "active.json.bak"
    _MAX_KEPT = 20

    def __init__(self, session_dir: Path) -> None:
        self._dir = session_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._active = self._dir / self._ACTIVE
        self._backup = self._dir / self._BACKUP

    # ── Public API ──────────────────────────────────────────────────────────

    def load_history(self) -> list[dict[str, Any]]:
        """Load the most recent conversation history, recovering from backup if needed."""
        for candidate in (self._active, self._backup):
            if candidate.exists():
                try:
                    data = json.loads(candidate.read_text())
                    if isinstance(data, list):
                        return data
                except (json.JSONDecodeError, OSError):
                    continue
        return []

    def save_history(self, history: list[dict[str, Any]]) -> None:
        """Atomically save history: write → backup → swap."""
        tmp = self._dir / f".tmp_{int(time.time() * 1000)}.json"
        try:
            tmp.write_text(json.dumps(history, indent=2))
            if self._active.exists():
                shutil.copy2(self._active, self._backup)
            shutil.move(str(tmp), self._active)
        except OSError:
            tmp.unlink(missing_ok=True)

    def has_crash_recovery(self) -> bool:
        """Return True if a session was interrupted (backup exists but differs from active)."""
        if not self._backup.exists():
            return False
        if not self._active.exists():
            return True
        return self._backup.stat().st_mtime > self._active.stat().st_mtime

    def archive_current(self) -> Path | None:
        """Save the current session to a timestamped archive and start fresh."""
        if not self._active.exists():
            return None
        stamp = time.strftime("%Y%m%d_%H%M%S")
        archive = self._dir / f"session_{stamp}.json"
        shutil.copy2(self._active, archive)
        self._active.unlink()
        self._backup.unlink(missing_ok=True)
        self._prune_old_archives()
        return archive

    def list_archives(self) -> list[Path]:
        return sorted(self._dir.glob("session_*.json"), reverse=True)

    def load_archive(self, path: Path) -> list[dict[str, Any]]:
        try:
            data = json.loads(path.read_text())
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    # ── Internal ────────────────────────────────────────────────────────────

    def _prune_old_archives(self) -> None:
        archives = self.list_archives()
        for old in archives[self._MAX_KEPT:]:
            old.unlink(missing_ok=True)
