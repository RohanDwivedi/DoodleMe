"""Settings dialog — first-run wizard and ongoing config editor."""

from __future__ import annotations

import threading

from python_qt_binding.QtCore import Qt, pyqtSignal as Signal
from python_qt_binding.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QFileDialog,
    QCheckBox,
    QHBoxLayout,
)

from ..config.settings import Settings


class SettingsDialog(QDialog):
    """Modal settings dialog with API, paths, and behaviour tabs."""

    api_key_changed = Signal(str)

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
        form.setContentsMargins(12, 12, 12, 12)
        form.setSpacing(10)

        source = self._settings.api_key_source()
        source_colours = {
            "secrets file": ("#4ec9b0", "Docker secret  ✓  (highest trust)"),
            "env var":      ("#dcdcaa", "Environment variable"),
            "settings":     ("#9cdcfe", "Saved in config file"),
            "not set":      ("#f48771", "Not configured"),
        }
        colour, label = source_colours.get(source, ("#9d9d9d", source))
        source_label = QLabel(f"Active source: <b>{label}</b>")
        source_label.setStyleSheet(f"color: {colour};")
        source_label.setWordWrap(True)
        form.addRow(source_label)

        note = QLabel(
            "Priority order: <code>ANTHROPIC_API_KEY</code> env var "
            "→ <code>/run/secrets/anthropic_api_key</code> (Docker secret) "
            "→ value saved below.<br>"
            "The field below is ignored when a secret file or env var is present."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #6a6a6a; font-size: 11px;")
        form.addRow(note)

        stored = self._settings.get("api_key", "")
        self._key_edit = QLineEdit(stored)
        self._key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_edit.setPlaceholderText("sk-ant-…  (only used if no secret file or env var)")
        if source in ("secrets file", "env var"):
            self._key_edit.setEnabled(False)
            self._key_edit.setPlaceholderText(f"Managed by {label} — field disabled")

        key_row = QHBoxLayout()
        key_row.addWidget(self._key_edit)
        self._show_key_btn = QPushButton("Show")
        self._show_key_btn.setProperty("flat", True)
        self._show_key_btn.setFixedWidth(52)
        self._show_key_btn.clicked.connect(self._toggle_key_visibility)
        key_row.addWidget(self._show_key_btn)

        self._test_btn = QPushButton("Test connection")
        self._test_btn.setProperty("secondary", True)
        self._test_btn.clicked.connect(self._test_api_key)
        self._test_label = QLabel("")
        self._test_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        form.addRow("Anthropic API Key:", key_row)
        form.addRow("", self._test_btn)
        form.addRow("", self._test_label)
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

    def _toggle_key_visibility(self) -> None:
        if self._key_edit.echoMode() == QLineEdit.EchoMode.Password:
            self._key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self._show_key_btn.setText("Hide")
        else:
            self._key_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self._show_key_btn.setText("Show")

    def _test_api_key(self) -> None:
        key = self._key_edit.text().strip()
        if not key:
            self._test_label.setText("⚠ Enter a key first")
            self._test_label.setProperty("status-warn", True)
            self._test_label.style().unpolish(self._test_label)
            self._test_label.style().polish(self._test_label)
            return

        self._test_btn.setEnabled(False)
        self._test_label.setText("Checking…")

        def _check() -> None:
            try:
                import anthropic

                client = anthropic.Anthropic(api_key=key)
                client.models.list()
                ok = True
                msg = "✓ Connected"
            except Exception as exc:  # noqa: BLE001
                ok = False
                msg = f"✗ {exc}"

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
        prop = "status-ok" if ok else "status-err"
        self._test_label.setProperty(prop, True)
        self._test_label.style().unpolish(self._test_label)
        self._test_label.style().polish(self._test_label)
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
        key = self._key_edit.text().strip()
        if key != self._settings.api_key():
            self._settings.set("api_key", key)
            self.api_key_changed.emit(key)

        self._settings.set("workspace", self._workspace_edit.text().strip())
        self._settings.set("openscad_path", self._openscad_edit.text().strip())
        self._settings.set("auto_render", self._auto_render_cb.isChecked())
        self._settings.set("auto_publish_urdf", self._auto_urdf_cb.isChecked())
        self.accept()
