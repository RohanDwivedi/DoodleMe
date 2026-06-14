"""Wiring diagram panel — renders Mermaid diagrams via QWebEngineView."""

from __future__ import annotations

from python_qt_binding.QtCore import Qt, pyqtSignal as Signal, QUrl
from python_qt_binding.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)


_MERMAID_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ background: #1e1e1e; margin: 0; padding: 16px; }}
  .mermaid {{ background: #1e1e1e; color: #d4d4d4; }}
  svg {{ max-width: 100%; height: auto; }}
</style>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>
  mermaid.initialize({{
    startOnLoad: true,
    theme: 'dark',
    themeVariables: {{
      background: '#1e1e1e',
      primaryColor: '#007acc',
      primaryTextColor: '#d4d4d4',
      lineColor: '#6a6a6a',
      edgeLabelBackground: '#252526',
    }}
  }});
</script>
</head>
<body>
<div class="mermaid">
{diagram}
</div>
</body>
</html>"""


class WiringPanel(QWidget):
    """Split-pane: Mermaid source editor on left, rendered diagram on right."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._web_available = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = self._build_toolbar()
        layout.addWidget(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: source editor
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        source_label = QLabel("  Mermaid source")
        source_label.setProperty("subheading", True)
        source_label.setContentsMargins(8, 6, 0, 4)
        left_layout.addWidget(source_label)
        self._editor = QPlainTextEdit()
        self._editor.setPlaceholderText(
            "graph LR\n    MCU-->|PWM| Servo\n    Battery-->|5V| MCU"
        )
        self._editor.setFont(_monospace_font())
        left_layout.addWidget(self._editor)
        splitter.addWidget(left)

        # Right: rendered view
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        render_label = QLabel("  Preview")
        render_label.setProperty("subheading", True)
        render_label.setContentsMargins(8, 6, 0, 4)
        right_layout.addWidget(render_label)

        self._render_widget = self._create_render_widget()
        right_layout.addWidget(self._render_widget)
        splitter.addWidget(right)

        splitter.setSizes([300, 500])
        layout.addWidget(splitter)

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("ViewerToolbar")
        row = QHBoxLayout(bar)
        row.setContentsMargins(8, 4, 8, 4)
        row.setSpacing(6)
        row.addStretch()
        render_btn = QPushButton("Render")
        render_btn.clicked.connect(self._render)
        row.addWidget(render_btn)
        return bar

    def _create_render_widget(self) -> QWidget:
        try:
            from python_qt_binding.QtWebEngineWidgets import QWebEngineView  # type: ignore[import]

            self._web_view = QWebEngineView()
            self._web_view.setHtml(
                _MERMAID_HTML.format(diagram="graph LR\n    Start-->End"),
                QUrl("about:blank"),
            )
            self._web_available = True
            return self._web_view
        except ImportError:
            self._web_available = False
            fallback = QLabel(
                "Install python3-pyqt5.qtwebengine\nfor live Mermaid rendering.\n\n"
                "Edit the source on the left."
            )
            fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fallback.setStyleSheet("color: #555555;")
            return fallback

    # ── Public API ──────────────────────────────────────────────────────────

    def set_diagram(self, mermaid_source: str) -> None:
        self._editor.setPlainText(mermaid_source)
        self._render()

    def get_source(self) -> str:
        return self._editor.toPlainText()

    # ── Internal ────────────────────────────────────────────────────────────

    def _render(self) -> None:
        if not self._web_available:
            return
        source = self._editor.toPlainText().strip()
        if not source:
            return
        html = _MERMAID_HTML.format(diagram=source)
        self._web_view.setHtml(html, QUrl("about:blank"))


def _monospace_font():  # type: ignore[return]
    from python_qt_binding.QtGui import QFont

    f = QFont("Fira Code", 12)
    if not f.exactMatch():
        f = QFont("Monospace", 12)
    return f
