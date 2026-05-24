"""
src/ui/widgets/status_bar.py
CustomStatusBar — thin bottom strip with system status display.

Layout:
  [● STATUS TEXT]          [◉]
"""

import time
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel

from src.ui.theme import palette as P
from src.ui.theme.fonts import label_caps
from src.app.constants import STATUSBAR_HEIGHT


class CustomStatusBar(QWidget):
    """Thin status bar at the bottom of the main window."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(STATUSBAR_HEIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(4)

        font = label_caps()

        # Status dot
        self._dot = QLabel("●")
        self._dot.setFont(font)
        self._dot.setStyleSheet("color: #00FF88; background: transparent; font-size: 9px;")

        # Status text
        self._status_lbl = QLabel("IDLE")
        self._status_lbl.setFont(font)
        self._status_lbl.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent;")
        self._status_lbl.setObjectName("StatusText")

        layout.addWidget(self._dot)
        layout.addSpacing(4)
        layout.addWidget(self._status_lbl)
        layout.addStretch(1)

        # Connection icon
        self._conn_lbl = QLabel("◉")
        self._conn_lbl.setFont(font)
        self._conn_lbl.setStyleSheet(f"color: {P.PRIMARY_CONTAINER}; background: transparent; font-size: 9px;")

        layout.addWidget(self._conn_lbl)

    def set_status(self, text: str, level: str = "info") -> None:
        """Update the status message. level: 'info'|'success'|'warning'|'error'"""
        colors = {
            "info": P.TEXT_DIM,
            "success": "#00FF88",
            "warning": "#FFAA00",
            "error": P.HAZARD_RED,
        }
        dot_colors = {
            "info": "#00FF88",
            "success": "#00FF88",
            "warning": "#FFAA00",
            "error": P.HAZARD_RED,
        }
        color = colors.get(level, P.TEXT_DIM)
        dot_color = dot_colors.get(level, "#00FF88")

        self._status_lbl.setText(text.upper())
        self._status_lbl.setStyleSheet(f"color: {color}; background: transparent;")
        self._dot.setStyleSheet(f"color: {dot_color}; background: transparent; font-size: 9px;")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        # Dark status bar background
        painter.fillRect(self.rect(), QColor(2, 13, 20, 230))
        # Top border
        from PyQt6.QtGui import QPen
        painter.setPen(QPen(QColor(0, 170, 255, 25), 1))
        painter.drawLine(0, 0, self.width(), 0)
        painter.end()
