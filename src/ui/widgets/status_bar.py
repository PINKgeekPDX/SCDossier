"""
src/ui/widgets/status_bar.py
CustomStatusBar — thin bottom strip with minimal status display.
No ping/uptime/connection indicators - just clean status text.

Layout:
  [● STATUS TEXT]
"""

import time
import math
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel

from src.ui.theme import palette as P
from src.ui.theme.fonts import label_caps
from src.app.constants import STATUSBAR_HEIGHT
from src.core.events import EventBus


class CustomStatusBar(QWidget):
    """Ultra-thin status bar at the bottom of the main window."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(STATUSBAR_HEIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._on_pulse)
        self._pulse_timer.setInterval(50)
        self._pulse_step = 0
        self._is_pulsing = False
        self._current_rep_color = "#444444"

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(3)

        font = label_caps()

        # Left: Main Status
        self._dot = QLabel("●")
        self._dot.setFont(font)
        self._dot.setStyleSheet("color: #00FF88; background: transparent; font-size: 7px;")
        self._dot.setToolTip("System status indicator")

        self._status_lbl = QLabel("IDLE")
        self._status_lbl.setFont(font)
        self._status_lbl.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent;")
        self._status_lbl.setObjectName("StatusText")
        self._status_lbl.setToolTip("Current system status message")

        layout.addWidget(self._dot)
        layout.addSpacing(3)
        layout.addWidget(self._status_lbl)
        
        layout.addStretch(1)

        # Right: Reputation Indicator
        self._rep_lbl = QLabel("REP: DISABLED")
        self._rep_lbl.setFont(font)
        self._rep_lbl.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent;")
        
        self._rep_dot = QLabel("●")
        self._rep_dot.setFont(font)
        self._rep_dot.setStyleSheet(f"color: {self._current_rep_color}; background: transparent; font-size: 7px;")
        
        layout.addWidget(self._rep_lbl)
        layout.addSpacing(4)
        layout.addWidget(self._rep_dot)

    def _connect_signals(self) -> None:
        bus = EventBus.instance()
        bus.reputation_system_status.connect(self._on_rep_status)
        
        # Start pulse on fetch (implied by scrape success) or submit
        bus.scrape_completed.connect(lambda _: self._start_pulse())
        bus.reputation_report_requested.connect(lambda _, __: self._start_pulse())
        
        # Stop pulse on success/fail
        bus.reputation_loaded.connect(lambda _, __: self._stop_pulse())
        bus.reputation_load_failed.connect(lambda _, __: self._stop_pulse())
        bus.reputation_report_submitted.connect(lambda _: self._stop_pulse())
        bus.reputation_report_failed.connect(lambda _, __: self._stop_pulse())

    def _on_rep_status(self, status: str) -> None:
        if status == "online":
            self._current_rep_color = "#00FF88"
            self._rep_lbl.setText("REP: ONLINE")
            self._rep_lbl.setStyleSheet(f"color: #00FF88; background: transparent;")
        elif status == "offline":
            self._current_rep_color = P.HAZARD_RED
            self._rep_lbl.setText("REP: OFFLINE")
            self._rep_lbl.setStyleSheet(f"color: {P.HAZARD_RED}; background: transparent;")
        else:
            self._current_rep_color = "#444444"
            self._rep_lbl.setText("REP: DISABLED")
            self._rep_lbl.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent;")
            
        self._rep_dot.setStyleSheet(f"color: {self._current_rep_color}; background: transparent; font-size: 7px;")

    def _start_pulse(self) -> None:
        if self._current_rep_color == "#444444":
            return # Don't pulse if disabled
        self._is_pulsing = True
        self._pulse_step = 0
        self._pulse_timer.start()

    def _stop_pulse(self) -> None:
        self._is_pulsing = False
        self._pulse_timer.stop()
        self._rep_dot.setStyleSheet(f"color: {self._current_rep_color}; background: transparent; font-size: 7px;")

    def _on_pulse(self) -> None:
        self._pulse_step += 0.2
        # Calculate alpha oscillation (e.g. between 0.3 and 1.0)
        alpha = 0.3 + 0.7 * (0.5 * (1 + math.sin(self._pulse_step)))
        
        # We need to construct an rgba string
        # Assuming current_rep_color is a hex code like #00FF88
        c = QColor(self._current_rep_color)
        c.setAlphaF(alpha)
        rgba = f"rgba({c.red()}, {c.green()}, {c.blue()}, {c.alpha()})"
        
        self._rep_dot.setStyleSheet(f"color: {rgba}; background: transparent; font-size: 7px;")

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
        self._dot.setStyleSheet(f"color: {dot_color}; background: transparent; font-size: 7px;")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(2, 10, 18, 240))
        from PyQt6.QtGui import QPen
        painter.setPen(QPen(QColor(0, 170, 255, 22), 1))
        painter.drawLine(0, 0, self.width(), 0)
        painter.end()