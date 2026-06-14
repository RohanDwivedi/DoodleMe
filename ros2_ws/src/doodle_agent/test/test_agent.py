"""Unit tests for DoodleAgent and SessionManager (no API calls)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from doodle_agent.session.session_manager import SessionManager


# ── SessionManager ─────────────────────────────────────────────────────────────

class TestSessionManager:
    def test_empty_on_first_load(self, tmp_path: Path) -> None:
        sm = SessionManager(tmp_path / "sessions")
        assert sm.load_history() == []

    def test_save_and_reload(self, tmp_path: Path) -> None:
        sm = SessionManager(tmp_path / "sessions")
        history = [{"role": "user", "content": "Hello"}]
        sm.save_history(history)
        assert sm.load_history() == history

    def test_backup_created_on_second_save(self, tmp_path: Path) -> None:
        sm = SessionManager(tmp_path / "sessions")
        sm.save_history([{"role": "user", "content": "first"}])
        sm.save_history([{"role": "user", "content": "second"}])
        backup = tmp_path / "sessions" / "active.json.bak"
        assert backup.exists()

    def test_archive_clears_active(self, tmp_path: Path) -> None:
        sm = SessionManager(tmp_path / "sessions")
        sm.save_history([{"role": "user", "content": "x"}])
        archive = sm.archive_current()
        assert archive is not None
        assert archive.exists()
        assert sm.load_history() == []

    def test_list_archives_sorted(self, tmp_path: Path) -> None:
        sm = SessionManager(tmp_path / "sessions")
        for msg in ("a", "b", "c"):
            sm.save_history([{"role": "user", "content": msg}])
            sm.archive_current()
        archives = sm.list_archives()
        assert len(archives) == 3
        # Most recent first
        assert archives[0].stat().st_mtime >= archives[-1].stat().st_mtime

    def test_handles_corrupt_active(self, tmp_path: Path) -> None:
        session_dir = tmp_path / "sessions"
        session_dir.mkdir()
        (session_dir / "active.json").write_text("not json {{{{")
        sm = SessionManager(session_dir)
        assert sm.load_history() == []

    def test_prunes_old_archives(self, tmp_path: Path) -> None:
        sm = SessionManager(tmp_path / "sessions")
        sm._MAX_KEPT = 3
        for i in range(5):
            sm.save_history([{"role": "user", "content": str(i)}])
            sm.archive_current()
        sm._prune_old_archives()
        assert len(sm.list_archives()) <= 3


# ── DoodleAgent (mocked API) ──────────────────────────────────────────────────

class TestDoodleAgentDispatch:
    """Test tool dispatch without hitting the Anthropic API."""

    def _make_agent(self, tmp_path: Path) -> "DoodleAgent":  # type: ignore[name-defined]
        from doodle_agent.agent import DoodleAgent
        from doodle_agent.session.session_manager import SessionManager

        sm = SessionManager(tmp_path / "sessions")
        return DoodleAgent(
            api_key="sk-test-fake",
            workspace=tmp_path / "ws",
            session_manager=sm,
        )

    def test_unknown_tool_returns_error(self, tmp_path: Path) -> None:
        agent = self._make_agent(tmp_path)
        result = agent._dispatch("nonexistent_tool", {})
        assert result["status"] == "error"
        assert "Unknown tool" in result["message"]

    def test_dispatch_write_openscad(self, tmp_path: Path) -> None:
        agent = self._make_agent(tmp_path)
        (tmp_path / "ws").mkdir(parents=True, exist_ok=True)
        result = agent._dispatch("write_openscad", {"code": "cube([1,1,1]);"})
        assert result["status"] == "ok"

    def test_dispatch_update_bom(self, tmp_path: Path) -> None:
        agent = self._make_agent(tmp_path)
        (tmp_path / "ws").mkdir(parents=True, exist_ok=True)
        result = agent._dispatch(
            "update_bom", {"action": "add", "item": {"id": "x1", "name": "Test"}}
        )
        assert result["status"] == "ok"

    @pytest.mark.api
    def test_send_requires_valid_key(self, tmp_path: Path) -> None:
        """Skipped unless run with -m api (requires real key)."""
        pytest.skip("Requires valid Anthropic API key")
