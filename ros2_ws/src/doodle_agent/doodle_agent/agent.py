"""DoodleMe AI agent — agentic loop with Claude tool use and streaming."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import anthropic

from .prompts.system_prompt import SYSTEM_PROMPT
from .session.session_manager import SessionManager
from .tools import TOOL_REGISTRY, TOOL_SCHEMAS

# ── Prompt-cache structures (built once, reused every call) ───────────────────
# Marking the system prompt and the last tool definition with cache_control
# means both blocks are cached server-side after the first call (5-min TTL).
# Cache reads cost $0.30/M vs $3.00/M for regular input — 10× cheaper.

_SYSTEM_CACHED: list[dict[str, Any]] = [
    {
        "type": "text",
        "text": SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"},
    }
]

_TOOLS_CACHED: list[dict[str, Any]] = [
    *TOOL_SCHEMAS[:-1],
    {**TOOL_SCHEMAS[-1], "cache_control": {"type": "ephemeral"}},
]


@dataclass
class UsageStats:
    """Cumulative token usage for the current agent session."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0

    @property
    def cost_usd(self) -> float:
        """Estimated cost in USD at Sonnet 4 list prices."""
        billable_input = self.input_tokens - self.cache_read_tokens
        return (
            billable_input        * 3.00 / 1_000_000
            + self.cache_write_tokens * 3.75 / 1_000_000
            + self.cache_read_tokens  * 0.30 / 1_000_000
            + self.output_tokens      * 15.00 / 1_000_000
        )

    @property
    def cache_hit_rate(self) -> float:
        total_in = self.input_tokens + self.cache_read_tokens
        return self.cache_read_tokens / total_in if total_in else 0.0

    def __str__(self) -> str:
        return (
            f"in={self.input_tokens:,} out={self.output_tokens:,} "
            f"cache_write={self.cache_write_tokens:,} cache_read={self.cache_read_tokens:,} "
            f"hit={self.cache_hit_rate:.0%} est=${self.cost_usd:.4f}"
        )


class DoodleAgent:
    """Manages a multi-turn Claude conversation for iterative robot design.

    Runs the API call in a background thread. Callers receive updates via
    callbacks — all callbacks are invoked from the background thread, so UI
    callers must use Qt's queued connection mechanism (already handled in the
    plugin's _AgentWorker bridge).
    """

    MODEL = "claude-sonnet-4-6"
    MAX_TOKENS = 8096

    def __init__(
        self,
        api_key: str,
        workspace: Path,
        session_manager: SessionManager,
        openscad_binary: str = "openscad",
    ) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._workspace = workspace
        self._session = session_manager
        self._openscad_binary = openscad_binary
        self._history: list[dict[str, Any]] = session_manager.load_history()
        self._lock = threading.Lock()
        self.usage = UsageStats()

    # ── Public API ──────────────────────────────────────────────────────────

    def send(
        self,
        user_message: str,
        on_token: Callable[[str], None],
        on_tool_call: Callable[[str, dict[str, Any]], None],
        on_tool_result: Callable[[str, Any], None],
        on_done: Callable[[], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Start processing a user message in a daemon thread."""
        threading.Thread(
            target=self._run,
            args=(user_message, on_token, on_tool_call, on_tool_result, on_done, on_error),
            daemon=True,
        ).start()

    def clear(self) -> None:
        with self._lock:
            self._history = []
            self._session.save_history([])
            self.usage = UsageStats()

    def message_count(self) -> int:
        return len(self._history)

    # ── Agentic loop ─────────────────────────────────────────────────────────

    def _run(
        self,
        user_message: str,
        on_token: Callable[[str], None],
        on_tool_call: Callable[[str, dict[str, Any]], None],
        on_tool_result: Callable[[str, Any], None],
        on_done: Callable[[], None],
        on_error: Callable[[str], None],
    ) -> None:
        with self._lock:
            try:
                self._history.append({"role": "user", "content": user_message})
                self._loop(on_token, on_tool_call, on_tool_result)
                self._session.save_history(self._history)
                on_done()
            except anthropic.AuthenticationError:
                on_error("Invalid API key. Check your key in Settings.")
            except anthropic.RateLimitError:
                on_error("Rate limit reached. Wait a moment and try again.")
            except anthropic.APIConnectionError as exc:
                on_error(f"Connection error: {exc}")
            except anthropic.APIError as exc:
                on_error(f"API error ({exc.status_code}): {exc.message}")
            except Exception as exc:  # noqa: BLE001
                on_error(f"Unexpected error: {exc}")

    def _loop(
        self,
        on_token: Callable[[str], None],
        on_tool_call: Callable[[str, dict[str, Any]], None],
        on_tool_result: Callable[[str, Any], None],
    ) -> None:
        """Keep calling Claude until it returns end_turn with no tool calls."""
        while True:
            tool_use_blocks: list[Any] = []

            with self._client.messages.stream(
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS,
                system=_SYSTEM_CACHED,
                tools=_TOOLS_CACHED,
                messages=self._history,
            ) as stream:
                for text in stream.text_stream:
                    on_token(text)
                message = stream.get_final_message()

            u = message.usage
            self.usage.input_tokens       += u.input_tokens
            self.usage.output_tokens      += u.output_tokens
            self.usage.cache_write_tokens += getattr(u, "cache_creation_input_tokens", 0)
            self.usage.cache_read_tokens  += getattr(u, "cache_read_input_tokens", 0)

            # Append assistant turn (convert SDK objects → dicts for serialisation)
            assistant_content: list[dict[str, Any]] = []
            for block in message.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    assistant_content.append(
                        {
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        }
                    )
                    tool_use_blocks.append(block)

            self._history.append({"role": "assistant", "content": assistant_content})

            if not tool_use_blocks:
                break

            # Execute tools and collect results
            tool_results: list[dict[str, Any]] = []
            for block in tool_use_blocks:
                on_tool_call(block.name, block.input)
                result = self._dispatch(block.name, block.input)
                on_tool_result(block.name, result)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": self._serialise_result(result),
                    }
                )

            self._history.append({"role": "user", "content": tool_results})

    # ── Tool dispatch ─────────────────────────────────────────────────────────

    def _dispatch(self, name: str, inputs: dict[str, Any]) -> Any:
        fn = TOOL_REGISTRY.get(name)
        if fn is None:
            return {"status": "error", "message": f"Unknown tool: {name!r}"}
        return fn(
            workspace=self._workspace,
            openscad_binary=self._openscad_binary
            if name == "render_stl"
            else inputs.get("openscad_binary", self._openscad_binary),
            **{k: v for k, v in inputs.items() if k != "openscad_binary"},
        )

    @staticmethod
    def _serialise_result(result: Any) -> str:
        import json

        if isinstance(result, str):
            return result
        try:
            return json.dumps(result)
        except (TypeError, ValueError):
            return str(result)
