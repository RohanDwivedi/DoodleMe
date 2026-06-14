"""Status bar widget showing live health of each integrated service."""

from __future__ import annotations

from enum import Enum, auto

from python_qt_binding.QtCore import QTimer
from python_qt_binding.QtWidgets import QLabel, QStatusBar, QWidget, QHBoxLayout


class ServiceStatus(Enum):
    UNKNOWN = auto()
    OK = auto()
    ERROR = auto()
    CHECKING = auto()


_ICONS = {
    ServiceStatus.OK:       "✓",
    ServiceStatus.ERROR:    "✗",
    ServiceStatus.CHECKING: "…",
    ServiceStatus.UNKNOWN:  "?",
}

_STYLE = {
    ServiceStatus.OK:       "color:#4ec9b0;",
    ServiceStatus.ERROR:    "color:#f48771;",
    ServiceStatus.CHECKING: "color:#dcdcaa;",
    ServiceStatus.UNKNOWN:  "color:#9d9d9d;",
}


class ServiceIndicator(QLabel):
    """A single service pill in the status bar."""

    def __init__(self, name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._name = name
        self.set_status(ServiceStatus.UNKNOWN)

    def set_status(self, status: ServiceStatus, detail: str = "") -> None:
        icon = _ICONS[status]
        tip = f"{self._name}: {detail}" if detail else self._name
        self.setText(f"{icon} {self._name}")
        self.setStyleSheet(_STYLE[status])
        self.setToolTip(tip)


class DoodleStatusBar(QStatusBar):
    """Application status bar with per-service health indicators."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizeGripEnabled(False)

        self._indicators: dict[str, ServiceIndicator] = {}
        for service in ("Claude API", "OpenSCAD", "ROS2", "Gazebo"):
            ind = ServiceIndicator(service, self)
            self._indicators[service] = ind
            self.addPermanentWidget(ind)

        self._message_timer = QTimer(self)
        self._message_timer.setSingleShot(True)
        self._message_timer.timeout.connect(self.clearMessage)

    def set_service_status(
        self, service: str, status: ServiceStatus, detail: str = ""
    ) -> None:
        if service in self._indicators:
            self._indicators[service].set_status(status, detail)

    def show_message(self, text: str, timeout_ms: int = 4000) -> None:
        self.showMessage(f"  {text}", timeout_ms)

    def show_error(self, text: str) -> None:
        self.showMessage(f"  ✗  {text}", 6000)
        self.setStyleSheet("QStatusBar { background-color: #5a1d1d; }")
        QTimer.singleShot(6000, self._reset_style)

    def _reset_style(self) -> None:
        self.setStyleSheet("")
