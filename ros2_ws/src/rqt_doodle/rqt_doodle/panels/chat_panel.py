"""Chat panel — conversational interface to the DoodleMe agent."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from python_qt_binding.QtCore import Qt, pyqtSignal as Signal, QSize
from python_qt_binding.QtGui import QColor, QFont, QIcon, QKeyEvent, QPixmap, QPainter
from python_qt_binding.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


# ── Message bubble widgets ────────────────────────────────────────────────────

class _Bubble(QFrame):
    """A single chat message bubble."""

    def __init__(self, role: str, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._role = role
        self._text_label = QLabel()
        self._text_label.setWordWrap(True)
        self._text_label.setTextFormat(Qt.TextFormat.RichText)
        self._text_label.setOpenExternalLinks(True)
        self._text_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self._text_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        object_name = {
            "user": "MessageBubbleUser",
            "assistant": "MessageBubbleAssistant",
            "tool": "MessageBubbleToolCall",
        }.get(role, "MessageBubbleAssistant")
        self.setObjectName(object_name)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        if role == "user":
            row.addStretch()
            bubble_wrap = QVBoxLayout()
            bubble_wrap.setContentsMargins(8, 6, 8, 6)
            bubble_wrap.addWidget(self._text_label)
            self.setLayout(None)
            outer = QVBoxLayout(self)
            outer.setContentsMargins(0, 0, 0, 0)
            inner = QFrame()
            inner.setObjectName("MessageBubbleUser")
            inner_layout = QVBoxLayout(inner)
            inner_layout.setContentsMargins(10, 8, 10, 8)
            inner_layout.addWidget(self._text_label)
            row2 = QHBoxLayout()
            row2.addStretch()
            row2.addWidget(inner)
            outer.addLayout(row2)
        else:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(10, 8, 10, 8)
            if role == "tool":
                role_label = QLabel("⚙  Tool call")
                role_label.setStyleSheet("color: #dcdcaa; font-size: 11px; font-weight: 600;")
                layout.addWidget(role_label)
            layout.addWidget(self._text_label)

        if text:
            self.append(text)

    def append(self, text: str) -> None:
        current = self._text_label.text()
        self._text_label.setText(current + text)

    def set_text(self, text: str) -> None:
        self._text_label.setText(text)


class _TimestampLabel(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setText(datetime.now().strftime("%H:%M"))
        self.setStyleSheet("color: #555555; font-size: 10px;")
        self.setAlignment(Qt.AlignmentFlag.AlignRight)


# ── Input area ────────────────────────────────────────────────────────────────

class _InputArea(QWidget):
    """Multi-line text input with send button."""

    submitted = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("InputArea")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self._edit = QPlainTextEdit()
        self._edit.setPlaceholderText(
            "Describe your robot or ask for a design change… (Enter to send, Shift+Enter for new line)"
        )
        self._edit.setMaximumHeight(120)
        self._edit.setMinimumHeight(44)
        self._edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._edit.installEventFilter(self)
        layout.addWidget(self._edit)

        self._send_btn = QPushButton()
        self._send_btn.setFixedSize(QSize(36, 36))
        self._send_btn.setToolTip("Send (Enter)")
        self._send_btn.clicked.connect(self._submit)
        layout.addWidget(self._send_btn, 0, Qt.AlignmentFlag.AlignBottom)

    def set_send_icon(self, icon: QIcon) -> None:
        self._send_btn.setIcon(icon)
        self._send_btn.setIconSize(QSize(18, 18))

    def set_enabled(self, enabled: bool) -> None:  # noqa: FBT001
        self._edit.setEnabled(enabled)
        self._send_btn.setEnabled(enabled)

    def eventFilter(self, obj: object, event: object) -> bool:
        if obj is self._edit and isinstance(event, QKeyEvent):
            if (
                event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
                and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            ):
                self._submit()
                return True
        return super().eventFilter(obj, event)  # type: ignore[arg-type]

    def _submit(self) -> None:
        text = self._edit.toPlainText().strip()
        if text:
            self._edit.clear()
            self.submitted.emit(text)


# ── Chat panel ────────────────────────────────────────────────────────────────

class ChatPanel(QWidget):
    """Full chat panel: message history + input area."""

    user_message_sent = Signal(str)

    def __init__(self, send_icon: QIcon | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_bubble: _Bubble | None = None
        self._bubbles_layout: QVBoxLayout | None = None
        self._setup_ui(send_icon)

    def _setup_ui(self, send_icon: QIcon | None) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Scroll area with messages ──────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        messages_widget = QWidget()
        messages_widget.setObjectName("ChatWidget")
        self._bubbles_layout = QVBoxLayout(messages_widget)
        self._bubbles_layout.setContentsMargins(12, 12, 12, 12)
        self._bubbles_layout.setSpacing(8)
        self._bubbles_layout.addStretch()

        scroll.setWidget(messages_widget)
        self._scroll = scroll
        layout.addWidget(scroll)

        # ── Input area ─────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        self._input = _InputArea()
        if send_icon:
            self._input.set_send_icon(send_icon)
        self._input.submitted.connect(self._on_user_submit)
        layout.addWidget(self._input)

    # ── Public API ──────────────────────────────────────────────────────────

    def add_user_message(self, text: str) -> None:
        self._insert_bubble("user", text)

    def begin_assistant_message(self) -> None:
        self._current_bubble = self._insert_bubble("assistant", "")

    def stream_token(self, token: str) -> None:
        if self._current_bubble:
            self._current_bubble.append(token)
            self._scroll_to_bottom()

    def end_assistant_message(self) -> None:
        self._current_bubble = None

    def add_tool_call(self, name: str, inputs: dict[str, Any]) -> None:
        summary = f"<b>{name}</b>"
        if inputs:
            args = ", ".join(f"{k}={repr(v)[:40]}" for k, v in list(inputs.items())[:3])
            summary += f"({args})"
        self._insert_bubble("tool", summary)

    def add_system_message(self, text: str) -> None:
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #555555; font-size: 11px; padding: 4px 0;")
        self._bubbles_layout.insertWidget(self._bubbles_layout.count() - 1, label)

    def set_input_enabled(self, enabled: bool) -> None:  # noqa: FBT001
        self._input.set_enabled(enabled)

    def clear(self) -> None:
        while self._bubbles_layout.count() > 1:
            item = self._bubbles_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._current_bubble = None

    # ── Internal ────────────────────────────────────────────────────────────

    def _insert_bubble(self, role: str, text: str) -> _Bubble:
        bubble = _Bubble(role, text)
        self._bubbles_layout.insertWidget(self._bubbles_layout.count() - 1, bubble)
        self._scroll_to_bottom()
        return bubble

    def _scroll_to_bottom(self) -> None:
        vsb = self._scroll.verticalScrollBar()
        vsb.setValue(vsb.maximum())

    def _on_user_submit(self, text: str) -> None:
        self.add_user_message(text)
        self.set_input_enabled(False)
        self.user_message_sent.emit(text)
