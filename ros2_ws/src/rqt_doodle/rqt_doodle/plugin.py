"""Main rqt plugin class — wires all panels, agent, and ROS2 together."""

from __future__ import annotations

import importlib.resources
import subprocess
from pathlib import Path
from typing import Any

from python_qt_binding.QtCore import Qt, pyqtSignal as Signal, QObject, QThread
from python_qt_binding.QtGui import QIcon
from python_qt_binding.QtWidgets import (
    QAction,
    QHBoxLayout,
    QLabel,
    QMenuBar,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from rqt_gui_py.plugin import Plugin

from .config.settings import Settings
from .panels.chat_panel import ChatPanel
from .panels.viewer_panel import ViewerPanel
from .panels.bom_panel import BOMPanel
from .panels.wiring_panel import WiringPanel
from .widgets.settings_dialog import SettingsDialog
from .widgets.status_bar import DoodleStatusBar, ServiceStatus
from .ros2.urdf_publisher import URDFPublisher
from .ros2.gazebo_bridge import GazeboBridge


# ── Agent worker (runs API calls off the Qt main thread) ─────────────────────

class _AgentWorker(QObject):
    """Thin QObject wrapper so signals can cross the thread boundary."""

    token = Signal(str)
    tool_called = Signal(str, dict)
    tool_done = Signal(str, object)
    finished = Signal(str)   # carries usage summary string
    error = Signal(str)
    stl_ready = Signal(str)   # path to newly rendered STL
    urdf_ready = Signal(str)  # path to updated URDF
    bom_ready = Signal(list)  # updated BOM items
    wiring_ready = Signal(str)  # updated Mermaid source

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self._settings = settings
        self._agent: Any = None

    def init_agent(self) -> None:
        from doodle_agent.agent import DoodleAgent
        from doodle_agent.session.session_manager import SessionManager

        workspace = self._settings.workspace_path()
        session_mgr = SessionManager(self._settings.session_dir())
        self._agent = DoodleAgent(
            api_key=self._settings.api_key(),
            workspace=workspace,
            session_manager=session_mgr,
        )

    def send(self, message: str) -> None:
        if self._agent is None:
            self.error.emit("Agent not initialised. Set your API key in Settings.")
            self.finished.emit("")
            return

        def _on_done() -> None:
            summary = str(self._agent.usage) if self._agent else ""
            self.finished.emit(summary)

        self._agent.send(
            user_message=message,
            on_token=self.token.emit,
            on_tool_call=lambda name, inputs: self.tool_called.emit(name, inputs),
            on_tool_result=self._on_tool_result,
            on_done=_on_done,
            on_error=self.error.emit,
        )

    def _on_tool_result(self, name: str, result: Any) -> None:
        self.tool_done.emit(name, result)
        if isinstance(result, dict):
            if "stl_path" in result:
                self.stl_ready.emit(result["stl_path"])
            if "urdf_path" in result:
                self.urdf_ready.emit(result["urdf_path"])
            if "bom" in result:
                self.bom_ready.emit(result["bom"])
            if "mermaid" in result:
                self.wiring_ready.emit(result["mermaid"])


# ── Plugin ────────────────────────────────────────────────────────────────────

class DoodlePlugin(Plugin):
    """DoodleMe rqt plugin — AI-assisted robot design."""

    def __init__(self, context: Any) -> None:
        super().__init__(context)
        self.setObjectName("DoodlePlugin")

        self._settings = Settings()
        self._urdf_pub = URDFPublisher()
        self._gazebo = GazeboBridge()
        self._worker_thread: QThread | None = None
        self._worker: _AgentWorker | None = None

        self._widget = QWidget()
        self._widget.setObjectName("DoodleWidget")

        self._apply_theme()
        self._build_ui()
        self._init_agent_thread()
        self._check_services()

        context.addWidget(self._widget)

        if not self._settings.has_api_key():
            self._open_settings(first_run=True)

    # ── Theme ─────────────────────────────────────────────────────────────────

    def _apply_theme(self) -> None:
        qss_path = Path(__file__).parent / "assets" / "themes" / "dark.qss"
        if qss_path.exists():
            self._widget.setStyleSheet(qss_path.read_text())

    def _icon(self, name: str) -> QIcon:
        path = Path(__file__).parent / "assets" / "icons" / f"{name}.svg"
        return QIcon(str(path)) if path.exists() else QIcon()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self._widget)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: chat panel
        self._chat = ChatPanel(send_icon=self._icon("send"))
        self._chat.user_message_sent.connect(self._on_user_message)
        self._chat.setMinimumWidth(300)
        splitter.addWidget(self._chat)

        # Right: tabbed panels
        self._tabs = QTabWidget()
        self._tabs.setTabPosition(QTabWidget.TabPosition.North)

        self._viewer = ViewerPanel()
        self._bom = BOMPanel()
        self._wiring = WiringPanel()

        self._tabs.addTab(self._viewer, self._icon("viewer"), "3D View")
        self._tabs.addTab(self._bom,    self._icon("bom"),    "BOM")
        self._tabs.addTab(self._wiring, self._icon("wiring"), "Wiring")
        self._tabs.setMinimumWidth(400)
        splitter.addWidget(self._tabs)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        root.addWidget(splitter)

        self._status_bar = DoodleStatusBar(self._widget)
        root.addWidget(self._status_bar)

    def _build_header(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("HeaderBar")
        row = QHBoxLayout(bar)
        row.setContentsMargins(12, 0, 12, 0)
        row.setSpacing(8)

        logo = QLabel()
        logo.setPixmap(self._icon("logo").pixmap(24, 24))
        row.addWidget(logo)

        title = QLabel("DoodleMe")
        title.setProperty("heading", True)
        row.addWidget(title)

        version = QLabel("v0.1.0")
        version.setProperty("subheading", True)
        version.setContentsMargins(0, 4, 0, 0)
        row.addWidget(version)

        row.addStretch()

        simulate_btn = self._header_btn("simulate", "Simulate in Gazebo", self._spawn_gazebo)
        export_btn   = self._header_btn("export",   "Export files",        self._export_files)
        settings_btn = self._header_btn("settings", "Settings",            lambda: self._open_settings())

        for btn in (simulate_btn, export_btn, settings_btn):
            row.addWidget(btn)

        return bar

    def _header_btn(self, icon: str, tooltip: str, slot: Any) -> "QPushButton":  # type: ignore[name-defined]
        from python_qt_binding.QtWidgets import QPushButton
        btn = QPushButton()
        btn.setIcon(self._icon(icon))
        btn.setToolTip(tooltip)
        btn.setProperty("flat", True)
        btn.setFixedSize(32, 32)
        btn.clicked.connect(slot)
        return btn

    # ── Agent thread ──────────────────────────────────────────────────────────

    def _init_agent_thread(self) -> None:
        self._worker_thread = QThread(self._widget)
        self._worker = _AgentWorker(self._settings)
        self._worker.moveToThread(self._worker_thread)

        self._worker.token.connect(self._chat.stream_token)
        self._worker.tool_called.connect(self._on_tool_called)
        self._worker.finished.connect(self._on_agent_done)  # type: ignore[arg-type]
        self._worker.error.connect(self._on_agent_error)
        self._worker.stl_ready.connect(self._viewer.load_stl)
        self._worker.bom_ready.connect(self._bom.set_bom)
        self._worker.wiring_ready.connect(self._wiring.set_diagram)
        self._worker.urdf_ready.connect(self._on_urdf_ready)

        self._worker_thread.started.connect(self._worker.init_agent)
        self._worker_thread.start()

    # ── Signal handlers ───────────────────────────────────────────────────────

    def _on_user_message(self, text: str) -> None:
        self._chat.begin_assistant_message()
        self._status_bar.show_message("Claude is thinking…")
        if self._worker:
            self._worker.send(text)

    def _on_tool_called(self, name: str, inputs: dict[str, Any]) -> None:
        self._chat.add_tool_call(name, inputs)

    def _on_agent_done(self, usage_summary: str) -> None:
        self._chat.end_assistant_message()
        self._chat.set_input_enabled(True)
        if usage_summary:
            # Show cost estimate briefly, then revert to "Ready"
            parts = usage_summary.split()
            cost = next((p for p in parts if p.startswith("est=$")), "")
            hit  = next((p for p in parts if p.startswith("hit=")), "")
            label = f"Ready  |  {hit}  {cost}" if hit else "Ready"
            self._status_bar.show_message(label, 5000)
        else:
            self._status_bar.show_message("Ready", 2000)

    def _on_agent_error(self, msg: str) -> None:
        self._chat.end_assistant_message()
        self._chat.add_system_message(f"Error: {msg}")
        self._chat.set_input_enabled(True)
        self._status_bar.show_error(msg)
        self._status_bar.set_service_status("Claude API", ServiceStatus.ERROR, msg)

    def _on_urdf_ready(self, path: str) -> None:
        if self._settings.get("auto_publish_urdf", True):
            self._urdf_pub.publish(Path(path))
            ros2_ok = self._urdf_pub.is_running()
            self._status_bar.set_service_status(
                "ROS2", ServiceStatus.OK if ros2_ok else ServiceStatus.ERROR
            )

    # ── Actions ───────────────────────────────────────────────────────────────

    def _spawn_gazebo(self) -> None:
        workspace = self._settings.workspace_path()
        urdf_candidates = list(workspace.glob("*.urdf"))
        if not urdf_candidates:
            self._status_bar.show_error("No URDF found in workspace.")
            return
        self._gazebo.launch_and_spawn(urdf_candidates[0])
        self._status_bar.show_message("Spawning in Gazebo…")

    def _export_files(self) -> None:
        from python_qt_binding.QtWidgets import QFileDialog

        dest = QFileDialog.getExistingDirectory(self._widget, "Export to…")
        if not dest:
            return
        workspace = self._settings.workspace_path()
        dest_path = Path(dest)
        for pattern in ("*.urdf", "*.scad", "*.stl", "*.kicad_sch"):
            for f in workspace.glob(pattern):
                import shutil

                shutil.copy2(f, dest_path / f.name)
        self._status_bar.show_message(f"Exported to {dest}")

    def _open_settings(self, first_run: bool = False) -> None:
        dlg = SettingsDialog(self._settings, self._widget)
        dlg.api_key_changed.connect(self._on_api_key_changed)
        if first_run:
            dlg.setWindowTitle("DoodleMe — First-run Setup")
        dlg.exec()

    def _on_api_key_changed(self, _key: str) -> None:
        if self._worker:
            self._worker.init_agent()
        self._check_services()

    # ── Service health checks ─────────────────────────────────────────────────

    def _check_services(self) -> None:
        self._status_bar.set_service_status("Claude API", ServiceStatus.CHECKING)
        self._status_bar.set_service_status("OpenSCAD", ServiceStatus.CHECKING)
        self._status_bar.set_service_status("ROS2", ServiceStatus.CHECKING)
        self._status_bar.set_service_status("Gazebo", ServiceStatus.CHECKING)

        import threading

        threading.Thread(target=self._do_health_checks, daemon=True).start()

    def _do_health_checks(self) -> None:
        from python_qt_binding.QtCore import QMetaObject, Qt

        def _set(svc: str, st: ServiceStatus, detail: str = "") -> None:
            QMetaObject.invokeMethod(
                self._status_bar,
                "set_service_status",
                Qt.ConnectionType.QueuedConnection,
                svc,
                st,
                detail,
            )

        # Claude API
        if self._settings.has_api_key():
            try:
                import anthropic

                anthropic.Anthropic(api_key=self._settings.api_key()).models.list()
                _set("Claude API", ServiceStatus.OK)
            except Exception as e:  # noqa: BLE001
                _set("Claude API", ServiceStatus.ERROR, str(e))
        else:
            _set("Claude API", ServiceStatus.ERROR, "No API key configured")

        # OpenSCAD
        osc = self._settings.get("openscad_path", "openscad")
        try:
            r = subprocess.run([osc, "--version"], capture_output=True, timeout=5)
            ver = (r.stdout or r.stderr).decode().split("\n")[0]
            _set("OpenSCAD", ServiceStatus.OK, ver)
        except Exception:  # noqa: BLE001
            _set("OpenSCAD", ServiceStatus.ERROR, "not found")

        # ROS2
        try:
            r = subprocess.run(["ros2", "--help"], capture_output=True, timeout=5)
            _set("ROS2", ServiceStatus.OK if r.returncode == 0 else ServiceStatus.ERROR)
        except Exception:  # noqa: BLE001
            _set("ROS2", ServiceStatus.ERROR, "not sourced")

        # Gazebo
        try:
            r = subprocess.run(["gz", "sim", "--version"], capture_output=True, timeout=5)
            _set("Gazebo", ServiceStatus.OK if r.returncode == 0 else ServiceStatus.ERROR)
        except Exception:  # noqa: BLE001
            _set("Gazebo", ServiceStatus.ERROR, "not installed")

    # ── rqt lifecycle ─────────────────────────────────────────────────────────

    def shutdown_plugin(self) -> None:
        self._urdf_pub.stop()
        self._gazebo.stop()
        if self._worker_thread:
            self._worker_thread.quit()
            self._worker_thread.wait(3000)

    def save_settings(self, plugin_settings: Any, instance_settings: Any) -> None:
        pass

    def restore_settings(self, plugin_settings: Any, instance_settings: Any) -> None:
        pass
