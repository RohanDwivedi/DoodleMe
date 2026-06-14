"""3D viewer panel — displays STL meshes and URDF previews via pyvistaqt."""

from __future__ import annotations

from pathlib import Path

from python_qt_binding.QtCore import Qt, pyqtSignal as Signal
from python_qt_binding.QtWidgets import (
    QLabel,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class ViewerPanel(QWidget):
    """Embeds a PyVista 3D plotter for STL and URDF visualisation."""

    load_requested = Signal(str)  # file path

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._plotter: object | None = None
        self._current_path: Path | None = None
        self._setup_ui()
        self._try_init_plotter()

    # ── UI ──────────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._toolbar = self._build_toolbar()
        layout.addWidget(self._toolbar)

        self._plotter_container = QWidget()
        self._plotter_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._plotter_layout = QVBoxLayout(self._plotter_container)
        self._plotter_layout.setContentsMargins(0, 0, 0, 0)

        self._placeholder = QLabel(
            "3D viewer\n\nA preview will appear here\nafter Claude renders a model."
        )
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: #555555; font-size: 13px;")
        self._plotter_layout.addWidget(self._placeholder)

        layout.addWidget(self._plotter_container)

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("ViewerToolbar")
        row = QHBoxLayout(bar)
        row.setContentsMargins(6, 4, 6, 4)
        row.setSpacing(4)

        for label, slot in (
            ("Fit", self._fit_view),
            ("Top", lambda: self._set_view("top")),
            ("Front", lambda: self._set_view("front")),
            ("Isometric", lambda: self._set_view("iso")),
            ("Wireframe", self._toggle_wireframe),
        ):
            btn = QPushButton(label)
            btn.setProperty("flat", True)
            btn.setFixedHeight(24)
            btn.clicked.connect(slot)
            row.addWidget(btn)

        row.addStretch()

        self._status_label = QLabel("No model loaded")
        self._status_label.setStyleSheet("color: #555555; font-size: 11px;")
        row.addWidget(self._status_label)

        return bar

    # ── Plotter init ─────────────────────────────────────────────────────────

    def _try_init_plotter(self) -> None:
        try:
            from pyvistaqt import QtInteractor  # type: ignore[import]

            self._plotter = QtInteractor(parent=self._plotter_container)
            self._plotter.set_background("#1e1e1e")
            self._plotter_layout.removeWidget(self._placeholder)
            self._placeholder.hide()
            self._plotter_layout.addWidget(self._plotter)
        except ImportError:
            self._plotter = None
            self._placeholder.setText(
                "3D viewer unavailable\n\npyvistaqt not installed.\n"
                "Run: pip install pyvistaqt"
            )

    # ── Public API ──────────────────────────────────────────────────────────

    def load_stl(self, path: str | Path) -> None:
        path = Path(path)
        if not path.exists():
            return
        if self._plotter is None:
            self._status_label.setText(f"Loaded: {path.name} (no renderer)")
            return

        try:
            import pyvista as pv  # type: ignore[import]

            self._plotter.clear()
            mesh = pv.read(str(path))
            self._plotter.add_mesh(
                mesh,
                color="#7ec8e3",
                show_edges=False,
                smooth_shading=True,
                ambient=0.3,
                diffuse=0.7,
                specular=0.2,
            )
            self._plotter.add_axes(interactive=False)
            self._fit_view()
            self._current_path = path
            self._status_label.setText(
                f"{path.name}  —  {mesh.n_points:,} pts / {mesh.n_faces:,} faces"
            )
        except Exception as exc:  # noqa: BLE001
            self._status_label.setText(f"Error: {exc}")

    def clear(self) -> None:
        if self._plotter is not None:
            self._plotter.clear()
        self._current_path = None
        self._status_label.setText("No model loaded")

    # ── View controls ────────────────────────────────────────────────────────

    def _fit_view(self) -> None:
        if self._plotter is not None:
            self._plotter.reset_camera()

    def _set_view(self, view: str) -> None:
        if self._plotter is None:
            return
        {"top": self._plotter.view_xy, "front": self._plotter.view_xz, "iso": self._plotter.view_isometric}.get(view, lambda: None)()  # type: ignore[operator]

    def _toggle_wireframe(self) -> None:
        if self._plotter is None:
            return
        for actor in self._plotter.actors.values():
            try:
                prop = actor.GetProperty()
                if prop.GetRepresentation() == 2:  # wireframe
                    prop.SetRepresentationToSurface()
                else:
                    prop.SetRepresentationToWireframe()
            except AttributeError:
                pass
        self._plotter.render()

    def closeEvent(self, event: object) -> None:  # type: ignore[override]
        if self._plotter is not None:
            try:
                self._plotter.close()
            except Exception:  # noqa: BLE001
                pass
        super().closeEvent(event)  # type: ignore[arg-type]
