"""Settings dialog — config editor.

API KEY SECURITY
----------------
The key is NEVER entered, displayed, or saved through this dialog.
The single authoritative copy lives at /etc/doodleme/secrets/anthropic_api_key
(host), bind-mounted read-only at /run/secrets/anthropic_api_key in the container.

To update the key:  docker compose run --rm setup
"""

from __future__ import annotations

import threading

from python_qt_binding.QtCore import Qt
from python_qt_binding.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..config.settings import Settings


class SettingsDialog(QDialog):
    """Modal settings dialog with API status, paths, and behaviour tabs."""

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle("DoodleMe Settings")
        self.setMinimumWidth(520)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        tabs = QTabWidget()
        tabs.addTab(self._build_api_tab(), "API")
        tabs.addTab(self._build_paths_tab(), "Paths")
        tabs.addTab(self._build_behaviour_tab(), "Behaviour")
        layout.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ── Tabs ────────────────────────────────────────────────────────────────

    def _build_api_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(12, 16, 12, 12)
        form.setSpacing(14)

        source = self._settings.api_key_source()

        # Status badge
        if source == "secrets file":
            colour, badge = "#4ec9b0", "✓  API key loaded from secrets file"
        elif source == "env var":
            colour, badge = "#dcdcaa", "⚠  API key loaded from environment variable"
        else:
            colour, badge = "#f48771", "✗  No API key found"

        status = QLabel(f"<b>{badge}</b>")
        status.setStyleSheet(f"color: {colour}; font-size: 13px;")
        status.setWordWrap(True)
        form.addRow(status)

        # Where the key lives
        path_note = QLabel(
            "The key is stored <b>only</b> at:<br>"
            "<code>/etc/doodleme/secrets/anthropic_api_key</code><br>"
            "bind-mounted read-only at <code>/run/secrets/anthropic_api_key</code> "
            "inside the container.<br><br>"
            "The key is <b>never</b> saved in this config file, env vars, "
            "or Docker images."
        )
        path_note.setWordWrap(True)
        path_note.setTextFormat(Qt.TextFormat.RichText)
        path_note.setStyleSheet("color: #cccccc; font-size: 12px; line-height: 1.5;")
        form.addRow(path_note)

        # How to update
        update_note = QLabel(
            "To set or update the key, run the setup wizard:<br>"
            "<code>docker compose run --rm setup</code><br><br>"
            "Or write directly (requires root):<br>"
            "<code>sudo sh -c 'echo \"sk-ant-…\" "
            "&gt; /etc/doodleme/secrets/anthropic_api_key'</code><br>"
            "<code>sudo chmod 600 /etc/doodleme/secrets/anthropic_api_key</code>"
        )
        update_note.setWordWrap(True)
        update_note.setTextFormat(Qt.TextFormat.RichText)
        update_note.setStyleSheet("color: #9d9d9d; font-size: 11px; line-height: 1.5;")
        form.addRow(update_note)

        # Test connection (reads from secrets file — never from a dialog field)
        test_row = QHBoxLayout()
        self._test_btn = QPushButton("Test connection")
        self._test_btn.setEnabled(source != "not set")
        self._test_btn.clicked.connect(self._test_api_key)
        test_row.addWidget(self._test_btn)
        test_row.addStretch()
        self._test_label = QLabel("")
        self._test_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        test_row.addWidget(self._test_label)
        form.addRow(test_row)

        return w

    def _build_paths_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(12, 12, 12, 12)
        form.setSpacing(10)

        self._workspace_edit = QLineEdit(str(self._settings.workspace_path()))
        ws_row = QHBoxLayout()
        ws_row.addWidget(self._workspace_edit)
        ws_browse = QPushButton("…")
        ws_browse.setFixedWidth(32)
        ws_browse.clicked.connect(
            lambda: self._browse_dir(self._workspace_edit, "Select workspace folder")
        )
        ws_row.addWidget(ws_browse)

        self._openscad_edit = QLineEdit(self._settings.get("openscad_path", "openscad"))
        osc_row = QHBoxLayout()
        osc_row.addWidget(self._openscad_edit)
        osc_browse = QPushButton("…")
        osc_browse.setFixedWidth(32)
        osc_browse.clicked.connect(
            lambda: self._browse_file(self._openscad_edit, "Locate OpenSCAD binary")
        )
        osc_row.addWidget(osc_browse)

        form.addRow("Workspace:", ws_row)
        form.addRow("OpenSCAD binary:", osc_row)
        return w

    def _build_behaviour_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(12, 12, 12, 12)
        form.setSpacing(10)

        self._auto_render_cb = QCheckBox("Auto-render STL after OpenSCAD changes")
        self._auto_render_cb.setChecked(self._settings.get("auto_render", True))

        self._auto_urdf_cb = QCheckBox("Auto-publish URDF to robot_description topic")
        self._auto_urdf_cb.setChecked(self._settings.get("auto_publish_urdf", True))

        form.addRow(self._auto_render_cb)
        form.addRow(self._auto_urdf_cb)
        return w

    # ── Actions ──────────────────────────────────────────────────────────────

    def _test_api_key(self) -> None:
        """Test the key loaded from the secrets file — never from user input."""
        key = self._settings.api_key()
        if not key:
            self._test_label.setText("⚠ No key available")
            return

        self._test_btn.setEnabled(False)
        self._test_label.setText("Checking…")

        def _check() -> None:
            try:
                import anthropic

                client = anthropic.Anthropic(api_key=key)
                client.models.list()
                ok, msg = True, "✓ Connected"
            except Exception as exc:  # noqa: BLE001
                ok, msg = False, f"✗ {exc}"
            finally:
                # Do not hold a reference to `key` beyond this scope.
                del key  # type: ignore[name-defined]

            from python_qt_binding.QtCore import QMetaObject, Qt

            QMetaObject.invokeMethod(
                self,
                "_on_test_done",
                Qt.ConnectionType.QueuedConnection,
                *[ok, msg],  # type: ignore[arg-type]
            )

        threading.Thread(target=_check, daemon=True).start()

    def _on_test_done(self, ok: bool, msg: str) -> None:  # noqa: FBT001
        self._test_label.setText(msg)
        colour = "#4ec9b0" if ok else "#f48771"
        self._test_label.setStyleSheet(f"color: {colour};")
        self._test_btn.setEnabled(True)

    def _browse_dir(self, target: QLineEdit, title: str) -> None:
        path = QFileDialog.getExistingDirectory(self, title, target.text())
        if path:
            target.setText(path)

    def _browse_file(self, target: QLineEdit, title: str) -> None:
        path, _ = QFileDialog.getOpenFileName(self, title, target.text())
        if path:
            target.setText(path)

    def _on_accept(self) -> None:
        # api_key is intentionally excluded — it must not pass through here.
        self._settings.set("workspace", self._workspace_edit.text().strip())
        self._settings.set("openscad_path", self._openscad_edit.text().strip())
        self._settings.set("auto_render", self._auto_render_cb.isChecked())
        self._settings.set("auto_publish_urdf", self._auto_urdf_cb.isChecked())
        self.accept()
