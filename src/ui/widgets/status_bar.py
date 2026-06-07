"""
src/ui/widgets/status_bar.py
CustomStatusBar — thin bottom strip with queued status pill notifications.

Messages are pushed via EventBus.status_message (legacy) or EventBus.status_push (full control).
They queue up and display one at a time, each visible for a configurable duration.
"""

import math
from collections import deque
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel

from src.ui.theme import palette as P
from src.ui.theme.fonts import label_caps
from src.app.constants import STATUSBAR_HEIGHT
from src.core.events import EventBus

# ---------------------------------------------------------------------------
# Preset pill colors (matched to the 4 pill styles: INFO / ONLINE / COOLDOWN / ERROR)
# ---------------------------------------------------------------------------
_COLOR_PRESETS = {
    "info":    "#93CCFF",
    "success": "#00FF88",
    "warning": "#FFAA00",
    "error":   "#FF4444",
}

_DEFAULT_PILL_COLOR = _COLOR_PRESETS["info"]
_DEFAULT_PILL_DURATION_MS = 30000


class CustomStatusBar(QWidget):
    """Ultra-thin status bar at the bottom of the main window.

    Message queue behavior:
        1. A message is enqueued with (text, tooltip, color, duration).
        2. If the pill is idle the message is shown immediately.
        3. Otherwise it waits in the deque until the current message's
           disposal timer fires.
        4. After disposal the next queued message is shown automatically.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(26)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Queue of pending messages: deque of (text, tooltip, color_hex, duration_ms)
        self._msg_queue: deque[tuple[str, str, str, int]] = deque()

        self._current_rep_color = P.TEXT_DIM
        self._pulse_step = 0
        self._is_pulsing = False

        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._on_pulse)
        self._pulse_timer.setInterval(50)

        self._hide_status_timer = QTimer(self)
        self._hide_status_timer.setSingleShot(True)
        self._hide_status_timer.timeout.connect(self._on_disposal_timer)

        self._fade_anim: QPropertyAnimation | None = None

        self._queue_paused = False

        self._build_ui()
        self._connect_signals()
        self._refresh_bar_style()

        EventBus.instance().theme_changed.connect(self._refresh_bar_style)

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 8, 3)
        layout.setSpacing(8)

        font = label_caps()
        font.setLetterSpacing(font.SpacingType.AbsoluteSpacing, 1.0)
        font.setBold(True)

        # Left: Main Status Badge
        self._status_lbl = QLabel("IDLE")
        self._status_lbl.setFont(font)
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lbl.setFixedHeight(14)

        layout.addWidget(self._status_lbl)
        layout.addStretch(1)

        # Right: Reputation Indicator Badge
        self._rep_lbl = QLabel("REP: DISABLED")
        self._rep_lbl.setFont(font)
        self._rep_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._rep_lbl.setFixedHeight(14)

        layout.addWidget(self._rep_lbl)

        self._status_lbl.hide()
        self._update_rep_style()

    def _connect_signals(self) -> None:
        bus = EventBus.instance()
        # Legacy signal — maps level to preset color
        bus.status_message.connect(self._on_status_message)
        # New queue-based push with full control
        bus.status_push.connect(self._on_status_push)

        bus.reputation_system_status.connect(self._on_rep_status)

        bus.scrape_completed.connect(lambda _: self._start_pulse())
        bus.reputation_report_requested.connect(lambda _, __: self._start_pulse())

        bus.reputation_loaded.connect(lambda _, __: self._stop_pulse())
        bus.reputation_load_failed.connect(lambda _, __: self._stop_pulse())
        bus.reputation_report_submitted.connect(lambda _: self._stop_pulse())
        bus.reputation_report_failed.connect(lambda _, __: self._stop_pulse())

    # ------------------------------------------------------------------
    # Style helpers
    # ------------------------------------------------------------------

    def _refresh_bar_style(self) -> None:
        self.setStyleSheet(f"""
            CustomStatusBar {{
                background-color: {P.SURFACE_CONTAINER};
                border-top: 1px solid {P.OUTLINE_VARIANT};
            }}
        """)
        self._update_rep_style()

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

    @staticmethod
    def _pill_style(color_hex: str) -> str:
        """Return the full stylesheet for the status pill at a given color."""
        c = QColor(color_hex)
        bg = f"rgba({c.red()}, {c.green()}, {c.blue()}, 0.1)"
        border = f"rgba({c.red()}, {c.green()}, {c.blue()}, 0.3)"
        return f"""
            QLabel {{
                color: {color_hex};
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 3px;
                padding: 0px 6px;
                font-size: 9px;
            }}
        """

    # ------------------------------------------------------------------
    # Reputation pill
    # ------------------------------------------------------------------

    def _on_rep_status(self, status: str) -> None:
        if status == "online":
            self._current_rep_color = _COLOR_PRESETS["success"]
            self._rep_lbl.setText("REP: ONLINE")
            self._rep_lbl.setToolTip("Reputation database is connected and operational.")
        elif status == "offline":
            self._current_rep_color = P.HAZARD_RED
            self._rep_lbl.setText("REP: OFFLINE")
            self._rep_lbl.setToolTip("Reputation database is unreachable. Check your network connection.")
        elif status == "error":
            self._current_rep_color = P.HAZARD_RED
            self._rep_lbl.setText("REP: ERROR")
            self._rep_lbl.setToolTip("Reputation system connected but failed to load data. Possible authentication or database error.")
        else:
            self._current_rep_color = P.TEXT_DIM
            self._rep_lbl.setText("REP: DISABLED")
            self._rep_lbl.setToolTip("Reputation system is disabled in settings.")

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

    # ------------------------------------------------------------------
    # Queue-based message system
    # ------------------------------------------------------------------

    def _on_status_message(self, text: str, level: str = "info") -> None:
        """Slot for legacy EventBus.status_message — maps level to preset color."""
        color = _COLOR_PRESETS.get(level, _DEFAULT_PILL_COLOR)
        self.push_message(text, "", color, _DEFAULT_PILL_DURATION_MS)

    def _on_status_push(self, text: str, tooltip: str, color_hex: str, duration_ms: int) -> None:
        """Slot for EventBus.status_push — full control over pill appearance."""
        if not color_hex:
            color_hex = _DEFAULT_PILL_COLOR
        if duration_ms <= 0:
            duration_ms = _DEFAULT_PILL_DURATION_MS
        self.push_message(text, tooltip, color_hex, duration_ms)

    def push_message(
        self,
        text: str,
        tooltip: str = "",
        color_hex: str = "",
        duration_ms: int = _DEFAULT_PILL_DURATION_MS,
    ) -> None:
        """Public API — enqueue a status pill message for display.

        Args:
            text:        Message body shown in the pill (uppercased automatically).
            tooltip:     Optional tooltip text shown on hover.
            color_hex:   Hex color string for the pill (e.g. "#00FF88").
                         Falls back to the default info blue if empty.
            duration_ms: How long the pill stays visible before disposal.
        """
        if not color_hex:
            color_hex = _DEFAULT_PILL_COLOR
        if duration_ms <= 0:
            duration_ms = _DEFAULT_PILL_DURATION_MS

        self._msg_queue.append((text, tooltip, color_hex, duration_ms))

        # If the pill is currently idle, show immediately
        if not self._queue_paused and not self._hide_status_timer.isActive() and not self._status_lbl.isVisible():
            self._show_next()

    def _show_next(self) -> None:
        """Pop the next message from the queue and display it."""
        if self._queue_paused:
            return
        if not self._msg_queue:
            self._status_lbl.hide()
            return

        # Cancel any running fade-out (should not happen)
        if self._fade_anim and self._fade_anim.state() == QPropertyAnimation.State.Running:
            self._fade_anim.stop()
        self._fade_anim = None

        text, tooltip, color_hex, duration_ms = self._msg_queue.popleft()

        self._status_lbl.setText(text.upper())
        self._status_lbl.setStyleSheet(self._pill_style(color_hex))
        if tooltip:
            self._status_lbl.setToolTip(tooltip)
        else:
            self._status_lbl.setToolTip("")
        self._status_lbl.show()
        # Ensure label is invisible before fade-in
        self._status_lbl.setWindowOpacity(0.0)

        # Create fade-in animation
        self._fade_anim = QPropertyAnimation(self._status_lbl, b"windowOpacity")
        self._fade_anim.setDuration(300)  # 300ms fade-in
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.finished.connect(self._on_fade_in_complete)
        self._current_duration_ms = duration_ms
        self._fade_anim.start()

    def _on_fade_in_complete(self) -> None:
        """Fade-in complete → start disposal timer."""
        if self._fade_anim:
            self._fade_anim.finished.disconnect(self._on_fade_in_complete)
            self._fade_anim = None
        # Start disposal timer now that pill is fully visible
        self._hide_status_timer.start(self._current_duration_ms)

    def _on_disposal_timer(self) -> None:
        """Current message's duration expired — start fade-out animation."""
        # Start fade-out
        self._fade_anim = QPropertyAnimation(self._status_lbl, b"windowOpacity")
        self._fade_anim.setDuration(300)  # 300ms fade-out
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self._on_fade_out_complete)
        self._fade_anim.start()

    def _on_fade_out_complete(self) -> None:
        """Fade-out complete — hide and process next."""
        if self._fade_anim:
            self._fade_anim.finished.disconnect(self._on_fade_out_complete)
            self._fade_anim = None
        self._status_lbl.hide()
        # After brief pause, show next message
        if self._msg_queue:
            QTimer.singleShot(300, self._show_next)

    def clear_queue(self) -> None:
        """Discard all pending messages and hide the pill immediately."""
        self._msg_queue.clear()
        self._hide_status_timer.stop()
        self._status_lbl.hide()

    def set_status(self, text: str, level: str = "info") -> None:
        """Legacy API — maps (text, level) to queue with preset color."""
        color = _COLOR_PRESETS.get(level, _DEFAULT_PILL_COLOR)
        self.push_message(text, "", color, _DEFAULT_PILL_DURATION_MS)

    def pause_queue(self) -> None:
        """Pause queue processing — messages still enqueue but won't display."""
        self._queue_paused = True
        # Stop any running animations and timers
        if self._fade_anim and self._fade_anim.state() == QPropertyAnimation.State.Running:
            self._fade_anim.stop()
            self._fade_anim = None
        if self._hide_status_timer.isActive():
            self._hide_status_timer.stop()
            self._status_lbl.hide()

    def resume_queue(self) -> None:
        """Resume queue processing and show next message if any."""
        self._queue_paused = False
        if self._msg_queue and not self._status_lbl.isVisible():
            self._show_next()
