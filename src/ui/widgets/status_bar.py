"""
src/ui/widgets/status_bar.py
CustomStatusBar — thin bottom strip with system status, ping, and uptime display.

Layout:
  [● STATUS TEXT]          [PING: --ms] [UPTIME: --:--] [◉]
"""

import time
from PyQt6.QtCore import Qt, QTimer
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
        self._start_time = time.time()
        self._build_ui()
        self._start_timers()

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
        self._status_lbl = QLabel("SYSTEM STATUS: NOMINAL")
        self._status_lbl.setFont(font)
        self._status_lbl.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent;")
        self._status_lbl.setObjectName("StatusText")

        layout.addWidget(self._dot)
        layout.addSpacing(4)
        layout.addWidget(self._status_lbl)
        layout.addStretch(1)

        # Ping
        self._ping_lbl = QLabel("PING: --")
        self._ping_lbl.setFont(font)
        self._ping_lbl.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent;")

        # Uptime
        self._uptime_lbl = QLabel("UPTIME: 00:00")
        self._uptime_lbl.setFont(font)
        self._uptime_lbl.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent;")

        # Connection icon
        self._conn_lbl = QLabel("◉")
        self._conn_lbl.setFont(font)
        self._conn_lbl.setStyleSheet(f"color: {P.PRIMARY_CONTAINER}; background: transparent; font-size: 9px;")

        layout.addWidget(self._ping_lbl)
        layout.addSpacing(16)
        layout.addWidget(self._uptime_lbl)
        layout.addSpacing(8)
        layout.addWidget(self._conn_lbl)

    def _start_timers(self) -> None:
        self._uptime_timer = QTimer(self)
        self._uptime_timer.timeout.connect(self._update_uptime)
        self._uptime_timer.start(1000)

    def _update_uptime(self) -> None:
        elapsed = int(time.time() - self._start_time)
        minutes, seconds = divmod(elapsed, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            self._uptime_lbl.setText(f"UPTIME: {hours:02d}:{minutes:02d}:{seconds:02d}")
        else:
            self._uptime_lbl.setText(f"UPTIME: {minutes:02d}:{seconds:02d}")

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

    def set_ping(self, ms: int | None) -> None:
        """Update ping display."""
        if ms is None:
            self._ping_lbl.setText("PING: --")
        else:
            color = "#00FF88" if ms < 100 else ("#FFAA00" if ms < 300 else P.HAZARD_RED)
            self._ping_lbl.setText(f"PING: {ms}ms")
            self._ping_lbl.setStyleSheet(f"color: {color}; background: transparent;")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        # Dark status bar background
        painter.fillRect(self.rect(), QColor(2, 13, 20, 230))
        # Top border
        from PyQt6.QtGui import QPen
        painter.setPen(QPen(QColor(0, 170, 255, 25), 1))
        painter.drawLine(0, 0, self.width(), 0)
        painter.end()
