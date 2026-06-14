#!/usr/bin/env python3
"""DoodleMe first-run setup wizard.

Checks whether the Anthropic API key secret exists. If not, shows a modal
dialog to collect it, writes it to /secrets/anthropic_api_key, then exits 0.
The main app service depends_on this completing successfully.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SECRET_FILE = Path("/secrets/anthropic_api_key")
_KEY_RE = re.compile(r"^sk-ant-[A-Za-z0-9_\-]{20,}$")

_DARK = """
QWidget {
    background-color: #1e1e1e;
    color: #d4d4d4;
    font-family: "Segoe UI", system-ui, Ubuntu, sans-serif;
    font-size: 13px;
}
QDialog { background-color: #1e1e1e; }
QLabel  { background: transparent; }
QLabel#title {
    font-size: 18px; font-weight: 700; color: #ffffff;
}
QLabel#subtitle {
    font-size: 12px; color: #9d9d9d;
}
QLabel#body {
    font-size: 13px; color: #cccccc; line-height: 1.5;
}
QLabel#error  { color: #f48771; font-size: 12px; }
QLabel#ok     { color: #4ec9b0; font-size: 12px; }
QLabel#hint {
    font-size: 11px; color: #6a6a6a;
}
QLineEdit {
    background-color: #3c3c3c;
    color: #cccccc;
    border: 1px solid #3c3c3c;
    border-radius: 3px;
    padding: 8px 10px;
    font-size: 13px;
}
QLineEdit:focus { border-color: #007acc; }
QPushButton {
    background-color: #0e639c;
    color: #ffffff;
    border: none;
    border-radius: 3px;
    padding: 8px 20px;
    font-weight: 600;
    font-size: 13px;
    min-height: 32px;
}
QPushButton:hover   { background-color: #1177bb; }
QPushButton:pressed { background-color: #0d5a8e; }
QPushButton#skip {
    background-color: #3a3d41;
    color: #cccccc;
    border: 1px solid #5a5d61;
}
QPushButton#skip:hover { background-color: #45484d; }
QPushButton#show {
    background-color: transparent;
    color: #9d9d9d;
    border: none;
    padding: 4px 8px;
    font-size: 11px;
    min-height: 0;
}
QPushButton#show:hover { color: #cccccc; }
QFrame#separator { color: #2d2d2d; }
"""


def key_is_set() -> bool:
    try:
        return bool(SECRET_FILE.exists() and SECRET_FILE.read_text().strip())
    except OSError:
        return False


def write_key(key: str) -> None:
    # SECURITY: the key is written to disk exactly once, then the local variable
    # goes out of scope. It is never logged, returned, or held in any other field.
    SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    SECRET_FILE.parent.chmod(0o700)   # directory: only owner can list contents
    SECRET_FILE.write_text(key.strip())
    SECRET_FILE.chmod(0o600)          # file: only owner can read/write


def run_wizard() -> bool:
    """Show the setup dialog. Returns True if a key was saved."""
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QFont
    from PyQt5.QtWidgets import (
        QApplication,
        QDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QVBoxLayout,
    )

    app = QApplication(sys.argv)
    app.setApplicationName("DoodleMe Setup")
    app.setStyleSheet(_DARK)

    dlg = QDialog()
    dlg.setWindowTitle("DoodleMe — First-run Setup")
    dlg.setFixedWidth(480)
    dlg.setWindowFlags(
        Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint
    )

    root = QVBoxLayout(dlg)
    root.setContentsMargins(32, 28, 32, 24)
    root.setSpacing(0)

    # ── Header ────────────────────────────────────────────────────────────────
    title = QLabel("◈  DoodleMe")
    title.setObjectName("title")
    root.addWidget(title)
    root.addSpacing(4)

    sub = QLabel("AI-assisted robot design  ·  First-run setup")
    sub.setObjectName("subtitle")
    root.addWidget(sub)
    root.addSpacing(20)

    sep = QFrame()
    sep.setObjectName("separator")
    sep.setFrameShape(QFrame.Shape.HLine)
    root.addWidget(sep)
    root.addSpacing(20)

    # ── Body ──────────────────────────────────────────────────────────────────
    body = QLabel(
        "An <b>Anthropic API key</b> is needed to power the design assistant.\n\n"
        "Get yours at <b>console.anthropic.com</b> → API Keys.\n"
        "This is separate from your Claude.ai subscription."
    )
    body.setObjectName("body")
    body.setWordWrap(True)
    body.setTextFormat(Qt.TextFormat.RichText)
    root.addWidget(body)
    root.addSpacing(20)

    # ── Key input ─────────────────────────────────────────────────────────────
    key_row = QHBoxLayout()
    key_row.setSpacing(6)

    key_edit = QLineEdit()
    key_edit.setEchoMode(QLineEdit.EchoMode.Password)
    key_edit.setPlaceholderText("sk-ant-…")
    key_row.addWidget(key_edit)

    show_btn = QPushButton("Show")
    show_btn.setObjectName("show")
    show_btn.setFixedWidth(44)
    show_btn.setCursor(Qt.CursorShape.PointingHandCursor)

    def _toggle_visibility() -> None:
        if key_edit.echoMode() == QLineEdit.EchoMode.Password:
            key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            show_btn.setText("Hide")
        else:
            key_edit.setEchoMode(QLineEdit.EchoMode.Password)
            show_btn.setText("Show")

    show_btn.clicked.connect(_toggle_visibility)
    key_row.addWidget(show_btn)
    root.addLayout(key_row)
    root.addSpacing(8)

    # ── Validation feedback ───────────────────────────────────────────────────
    feedback = QLabel("")
    feedback.setObjectName("error")
    root.addWidget(feedback)
    root.addSpacing(4)

    hint = QLabel("Key is stored in secrets/anthropic_api_key on your host (chmod 600).")
    hint.setObjectName("hint")
    root.addWidget(hint)
    root.addSpacing(24)

    # ── Buttons ───────────────────────────────────────────────────────────────
    btn_row = QHBoxLayout()
    btn_row.setSpacing(10)

    skip_btn = QPushButton("Skip — configure later in the app")
    skip_btn.setObjectName("skip")
    btn_row.addWidget(skip_btn)

    btn_row.addStretch()

    save_btn = QPushButton("Save & Launch  →")
    btn_row.addWidget(save_btn)

    root.addLayout(btn_row)

    saved = [False]

    def _validate(key: str) -> str | None:
        """Return error string or None if valid."""
        key = key.strip()
        if not key:
            return "Key is required."
        if not _KEY_RE.match(key):
            return "Key must start with sk-ant- followed by at least 20 characters."
        return None

    def _on_save() -> None:
        key = key_edit.text().strip()
        err = _validate(key)
        if err:
            feedback.setText(err)
            feedback.setObjectName("error")
            feedback.style().unpolish(feedback)
            feedback.style().polish(feedback)
            return
        write_key(key)
        feedback.setText(f"✓  Saved to {SECRET_FILE}")
        feedback.setObjectName("ok")
        feedback.style().unpolish(feedback)
        feedback.style().polish(feedback)
        saved[0] = True
        dlg.accept()

    def _on_skip() -> None:
        saved[0] = False
        dlg.reject()

    save_btn.clicked.connect(_on_save)
    skip_btn.clicked.connect(_on_skip)
    key_edit.returnPressed.connect(_on_save)

    dlg.exec()
    return saved[0]


def main() -> None:
    if key_is_set():
        print("[setup] API key already present — skipping wizard.")
        sys.exit(0)

    print("[setup] No API key found — launching setup wizard.")
    saved = run_wizard()

    if saved:
        print(f"[setup] Key written to {SECRET_FILE}. Starting main app.")
    else:
        print("[setup] Wizard skipped. Key can be entered in Settings → API.")

    sys.exit(0)


if __name__ == "__main__":
    main()
