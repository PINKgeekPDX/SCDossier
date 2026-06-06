"""
src/ui/widgets/status_bar.py
CustomStatusBar — thin bottom strip with minimal status display.
"""

import math
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel

from src.ui.theme import palette as P
from src.ui.theme.fonts import label_caps
from src.app.constants import STATUSBAR_HEIGHT
from src.core.events import EventBus

class CustomStatusBar(QWidget):
    """Ultra-thin status bar at the bottom of the main window."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(20)  # Ultra-slim
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            CustomStatusBar {{
                background-color: {P.SURFACE_CONTAINER};
                border-top: 1px solid {P.OUTLINE_VARIANT};
            }}
        """)
        
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._on_pulse)
        self._pulse_timer.setInterval(50)
        self._pulse_step = 0
        self._is_pulsing = False
        
        self._current_rep_color = P.TEXT_DIM

        self._hide_status_timer = QTimer(self)
        self._hide_status_timer.setSingleShot(True)
        self._hide_status_timer.timeout.connect(self._hide_status)

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)  # Tightly packed layout
        layout.setSpacing(8)

        font = label_caps()
        font.setLetterSpacing(font.SpacingType.AbsoluteSpacing, 1.0)
        font.setBold(True)

        # Left: Main Status Badge
        self._status_lbl = QLabel("IDLE")
        self._status_lbl.setFont(font)
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lbl.setFixedHeight(14) # Very compact pill height
        
        layout.addWidget(self._status_lbl)
        layout.addStretch(1)

        # Right: Reputation Indicator Badge
        self._rep_lbl = QLabel("REP: DISABLED")
        self._rep_lbl.setFont(font)
        self._rep_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._rep_lbl.setFixedHeight(14) # Very compact pill height
        
        layout.addWidget(self._rep_lbl)
        
        self._status_lbl.hide()
        self._update_rep_style()

    def _connect_signals(self) -> None:
        bus = EventBus.instance()
        bus.reputation_system_status.connect(self._on_rep_status)
        
        bus.scrape_completed.connect(lambda _: self._start_pulse())
        bus.reputation_report_requested.connect(lambda _, __: self._start_pulse())
        
        bus.reputation_loaded.connect(lambda _, __: self._stop_pulse())
        bus.reputation_load_failed.connect(lambda _, __: self._stop_pulse())
        bus.reputation_report_submitted.connect(lambda _: self._stop_pulse())
        bus.reputation_report_failed.connect(lambda _, __: self._stop_pulse())

    def _update_rep_style(self, alpha: float = 0.1, border_alpha: float = 0.3) -> None:
        c = QColor(self._current_rep_color)
        bg = f"rgba({c.red()}, {c.green()}, {c.blue()}, {alpha})"
        border = f"rgba({c.red()}, {c.green()}, {c.blue()}, {border_alpha})"
        text_color = self._current_rep_color
        
        self._rep_lbl.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 3px;
                padding: 0px 6px;
                font-size: 9px;
            }}
        """)

    def _on_rep_status(self, status: str) -> None:
        if status == "online":
            self._current_rep_color = "#00FF88"
            self._rep_lbl.setText("REP: ONLINE")
        elif status == "offline":
            self._current_rep_color = P.HAZARD_RED
            self._rep_lbl.setText("REP: OFFLINE")
        else:
            self._current_rep_color = P.TEXT_DIM
            self._rep_lbl.setText("REP: DISABLED")
            
        self._update_rep_style()

    def _start_pulse(self) -> None:
        if self._current_rep_color == P.TEXT_DIM:
            return 
        self._is_pulsing = True
        self._pulse_step = 0
        self._pulse_timer.start()

    def _stop_pulse(self) -> None:
        self._is_pulsing = False
        self._pulse_timer.stop()
        self._update_rep_style()

    def _on_pulse(self) -> None:
        self._pulse_step += 0.2
        intensity = 0.5 * (1 + math.sin(self._pulse_step))
        bg_alpha = 0.1 + 0.25 * intensity
        border_alpha = 0.3 + 0.6 * intensity
        self._update_rep_style(alpha=bg_alpha, border_alpha=border_alpha)

    def set_status(self, text: str, level: str = "info") -> None:
        colors = {
            "info": P.TEXT_DIM,
            "success": "#00FF88",
            "warning": "#FFAA00",
            "error": P.HAZARD_RED,
        }
        hex_color = colors.get(level, P.TEXT_DIM)
        c = QColor(hex_color)
        
        bg = f"rgba({c.red()}, {c.green()}, {c.blue()}, 0.1)"
        border = f"rgba({c.red()}, {c.green()}, {c.blue()}, 0.3)"
        
        self._status_lbl.setText(text.upper())
        self._status_lbl.setStyleSheet(f"""
            QLabel {{
                color: {hex_color};
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 3px;
                padding: 0px 6px;
                font-size: 9px;
            }}
        """)
        
        self._status_lbl.show()
        self._hide_status_timer.start(30000) # 30 seconds

    def _hide_status(self) -> None:
        self._status_lbl.hide()