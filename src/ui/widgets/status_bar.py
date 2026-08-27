"""
src/ui/widgets/status_bar.py
CustomStatusBar — bottom strip displaying stacked status pill notifications.

Messages are pushed via EventBus.status_message or EventBus.status_push.
They stack left-to-right up to the available width. Clicking a pill expands
it into a popup and pauses the display timers.
"""

import math
import time
from collections import deque
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QColor, QGuiApplication
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QApplication

from src.ui.theme import palette as P
from src.ui.theme.fonts import label_caps
from src.app.constants import (
    STATUSBAR_HEIGHT,
    STATUS_COLOR_PRESETS as _COLOR_PRESETS,
    STATUS_DEFAULT_PILL_COLOR as _DEFAULT_PILL_COLOR,
    STATUS_DEFAULT_PILL_DURATION_MS as _DEFAULT_PILL_DURATION_MS,
    STATUS_STAGGER_CREATE_DELAY_MS as _STAGGER_CREATE_DELAY_MS,
    STATUS_STAGGER_DISPOSE_DELAY_MS as _STAGGER_DISPOSE_DELAY_MS,
    STATUS_PULSE_TIMER_INTERVAL_MS
)
from src.core.events import EventBus


class PopupMessageBox(QWidget):
    """
    Frameless popup that displays the full verbose details when a status badge is clicked.
    Shows full message + tooltip with word wrap. Pauses all disposal timers while open.
    Clicking anywhere outside the popup collapses it and resumes timers.
    """

    def __init__(self, text: str, color_hex: str, parent_badge: QWidget, status_bar: "CustomStatusBar") -> None:
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._text = text
        self._color_hex = color_hex
        self._parent_badge = parent_badge
        self._status_bar = status_bar
        # Retrieve verbose tooltip from badge if available
        badge_tooltip = getattr(parent_badge, '_tooltip', '')
        verbose_text = text
        if badge_tooltip and badge_tooltip != text:
            verbose_text = f"{text}\n\n{badge_tooltip}"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Re-use status bar font
        font = label_caps()
        font.setLetterSpacing(font.SpacingType.AbsoluteSpacing, 1.0)
        font.setBold(True)

        # Preserve original casing for readability in expanded view
        self.lbl = QLabel(verbose_text)
        self.lbl.setFont(font)
        self.lbl.setWordWrap(True)
        self.lbl.setMinimumWidth(200)
        self.lbl.setMaximumWidth(480)

        c = QColor(color_hex)
        bg = f"rgba({c.red()}, {c.green()}, {c.blue()}, 0.92)"
        border = f"rgba({c.red()}, {c.green()}, {c.blue()}, 1.0)"
        self.lbl.setStyleSheet(f"""
            QLabel {{
                color: #FFFFFF;
                background-color: {bg};
                border: 2px solid {border};
                border-radius: 6px;
                padding: 12px 16px;
                font-size: 12px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(self.lbl)
        self.adjustSize()

        # Position popup slightly above the badge, centered horizontally
        global_pos = parent_badge.mapToGlobal(QPoint(0, 0))
        x = global_pos.x() + (parent_badge.width() - self.width()) // 2
        y = global_pos.y() - self.height() - 8

        # Bound check within screen
        screen = QGuiApplication.primaryScreen().geometry()
        x = max(screen.left() + 10, min(x, screen.right() - self.width() - 10))
        y = max(screen.top() + 10, y)
        self.move(x, y)

        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:
        if event.type() == event.Type.MouseButtonPress:
            # Close if the click occurs outside this popup and not on the originating badge
            click_pos = event.globalPosition().toPoint()
            if not self.geometry().contains(click_pos):
                # Also check if click is on the parent badge itself — allow badge clicks to pass through but still close popup
                try:
                    if not self._parent_badge or not getattr(self._parent_badge, 'isVisible', lambda: False)():
                        self.close_popup()
                        return True
                    badge_geo = self._parent_badge.mapToGlobal(QPoint(0, 0))
                    badge_rect = self._parent_badge.rect()
                    badge_rect.moveTopLeft(badge_geo)
                except Exception:
                    self.close_popup()
                    return True
                # Close popup regardless, but don't consume badge clicks
                self.close_popup()
                # If click was on badge, let it propagate so badge can handle it
                if badge_rect.contains(click_pos):
                    return False
                return True
        return super().eventFilter(obj, event)

    def close_popup(self) -> None:
        try:
            QApplication.instance().removeEventFilter(self)
        except Exception:
            pass
        self.close()
        self._status_bar.resume_from_popup()


FLASH_THRESHOLD_MS = 3000
FLASH_INTERVAL_MS = 350
FLASH_COLOR = "#FFFF00"


class StatusBadgeWidget(QLabel):
    """
    A single status notification badge shown in the status bar.
    Handles its own click expansion, hover tooltip, expiration timer, and expiry flashing.
    """

    def __init__(self, text: str, tooltip: str, color_hex: str, duration_ms: int, parent_bar: "CustomStatusBar") -> None:
        super().__init__()
        self._parent_bar = parent_bar
        self._full_text = text
        self._tooltip = tooltip
        self._color_hex = color_hex
        self._original_color = color_hex
        self._duration_ms = duration_ms
        self._remaining_ms = duration_ms
        self._is_flashing = False
        self._flash_on = False

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._on_timeout)

        # Flash timer — checks every FLASH_INTERVAL_MS once in the final threshold
        self._flash_timer = QTimer(self)
        self._flash_timer.setInterval(FLASH_INTERVAL_MS)
        self._flash_timer.timeout.connect(self._on_flash_tick)

        # Truncate text if exceeds length limit
        display_text = text
        if len(text) > 35:
            display_text = text[:32] + "..."

        self.setText(display_text.upper())
        self.setFixedHeight(14)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Styling
        self.setStyleSheet(parent_bar._pill_style(color_hex))

        # Tooltip — verbose on hover
        tip = tooltip if tooltip else text
        # Show full text plus tooltip if different
        if tooltip and tooltip != text:
            tip = f"{text}\n\n{tooltip}"
        self.setToolTip(tip)

        self._start_time = time.time()
        self.timer.start(duration_ms)
        # Schedule flash check if duration allows flashing
        if duration_ms > FLASH_THRESHOLD_MS:
            QTimer.singleShot(duration_ms - FLASH_THRESHOLD_MS, self._start_flashing)
        else:
            # Short-lived pill: start flashing immediately after a brief delay
            QTimer.singleShot(200, self._start_flashing)

    def _start_flashing(self) -> None:
        if self._is_flashing or not self.timer.isActive():
            return
        self._is_flashing = True
        self._flash_timer.start()

    def _stop_flashing(self) -> None:
        self._is_flashing = False
        self._flash_timer.stop()
        self._flash_on = False
        # Restore original color
        self.setStyleSheet(self._parent_bar._pill_style(self._original_color))

    def _on_flash_tick(self) -> None:
        # Stop flashing if timer already expired or paused
        if not self.timer.isActive():
            self._stop_flashing()
            return
        self._flash_on = not self._flash_on
        flash_color = FLASH_COLOR if self._flash_on else self._original_color
        self.setStyleSheet(self._parent_bar._pill_style(flash_color))

    def _on_timeout(self) -> None:
        self._stop_flashing()
        self._parent_bar.request_dispose(self)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._parent_bar.show_expanded_badge(self)
            event.accept()
        else:
            super().mousePressEvent(event)

    def pause(self) -> None:
        # Only pause if timer is active
        if self.timer.isActive():
            elapsed = int((time.time() - self._start_time) * 1000)
            self._remaining_ms = max(0, self._remaining_ms - elapsed)
            self.timer.stop()
        if self._flash_timer.isActive():
            self._flash_timer.stop()

    def resume(self) -> None:
        if self._remaining_ms > 0:
            self._start_time = time.time()
            self.timer.start(self._remaining_ms)
            # Resume flashing if in threshold window
            if self._remaining_ms <= FLASH_THRESHOLD_MS and not self._is_flashing:
                self._start_flashing()
            elif self._is_flashing:
                self._flash_timer.start()
        else:
            self._stop_flashing()
            self._parent_bar.request_dispose(self)


class CustomStatusBar(QWidget):
    """Ultra-thin status bar at the bottom of the main window."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(26)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._msg_queue: deque[tuple[str, str, str, int]] = deque()
        self._pending_disposals: deque[StatusBadgeWidget] = deque()
        self._active_badges: list[StatusBadgeWidget] = []
        self._popup_active = False
        self._last_create_time = 0.0
        self._last_dispose_time = 0.0

        self._current_rep_color = P.TEXT_DIM
        self._pulse_step = 0
        self._is_pulsing = False

        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._on_pulse)
        self._pulse_timer.setInterval(STATUS_PULSE_TIMER_INTERVAL_MS)

        # Staggered timers
        self._stagger_create_timer = QTimer(self)
        self._stagger_create_timer.setInterval(_STAGGER_CREATE_DELAY_MS)
        self._stagger_create_timer.setSingleShot(True)
        self._stagger_create_timer.timeout.connect(self._deploy_one_badge)

        self._stagger_dispose_timer = QTimer(self)
        self._stagger_dispose_timer.setInterval(_STAGGER_DISPOSE_DELAY_MS)
        self._stagger_dispose_timer.setSingleShot(True)
        self._stagger_dispose_timer.timeout.connect(self._dispose_one_badge)

        self._queue_paused = False

        self._build_ui()
        self._connect_signals()
        self._refresh_bar_style()

        EventBus.instance().theme_changed.connect(self._refresh_bar_style)

        # Sync initial rep status with settings (avoid showing DISABLED when enabled)
        try:
            from src.core.settings import SettingsManager
            sm = SettingsManager.instance()
            if not sm.reputation_enabled:
                self._on_rep_status("disabled")
            else:
                # Show offline until startup ping confirms online
                self._on_rep_status("offline")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self._main_layout = QHBoxLayout(self)
        self._main_layout.setContentsMargins(8, 3, 8, 3)
        self._main_layout.setSpacing(8)

        font = label_caps()
        font.setLetterSpacing(font.SpacingType.AbsoluteSpacing, 1.0)
        font.setBold(True)
        self.setFont(font)

        # Left: Container/Layout for multiple stacked badges
        self._status_layout = QHBoxLayout()
        self._status_layout.setContentsMargins(0, 0, 0, 0)
        self._status_layout.setSpacing(6)
        self._main_layout.addLayout(self._status_layout)

        # Middle: Stretch to push badges left and reputation right
        self._main_layout.addStretch(1)

        # Right: Reputation Indicator Badge
        self._rep_lbl = QLabel("REP: DISABLED")
        self._rep_lbl.setFont(font)
        self._rep_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._rep_lbl.setFixedHeight(14)
        self._main_layout.addWidget(self._rep_lbl)

        self._update_rep_style()

    def _connect_signals(self) -> None:
        bus = EventBus.instance()
        bus.status_message.connect(self._on_status_message)
        bus.status_push.connect(self._on_status_push)
        bus.reputation_system_status.connect(self._on_rep_status)

        bus.scrape_completed.connect(lambda _: self._start_pulse())
        bus.reputation_report_requested.connect(lambda _, __, ___: self._start_pulse())
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
                font-weight: bold;
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
        color = _COLOR_PRESETS.get(level, _DEFAULT_PILL_COLOR)
        self.push_message(text, "", color, _DEFAULT_PILL_DURATION_MS)

    def _on_status_push(self, text: str, tooltip: str, color_hex: str, duration_ms: int) -> None:
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
        if not color_hex:
            color_hex = _DEFAULT_PILL_COLOR
        if duration_ms <= 0:
            duration_ms = _DEFAULT_PILL_DURATION_MS

        # Deduplicate: suppress identical text already visible or queued
        # (prevents double WELCOME and other rapid duplicate pushes)
        for badge in self._active_badges:
            if getattr(badge, "_full_text", None) == text:
                return
        for queued_text, _, _, _ in self._msg_queue:
            if queued_text == text:
                return

        self._msg_queue.append((text, tooltip, color_hex, duration_ms))
        self._trigger_creation()

    def _trigger_creation(self) -> None:
        if self._stagger_create_timer.isActive():
            return
        
        elapsed = (time.time() - self._last_create_time) * 1000.0
        if elapsed < _STAGGER_CREATE_DELAY_MS:
            remaining = max(1, int(_STAGGER_CREATE_DELAY_MS - elapsed))
            self._stagger_create_timer.start(remaining)
        else:
            self._deploy_one_badge()

    def _deploy_one_badge(self) -> None:
        """Process queue and display badges left-to-right up to available width.
        
        When popup is active (timers paused), we still allow new badges to appear
        up to the width cap — they queue and display, but their timers are immediately
        paused. Any beyond the cap remain in _msg_queue until popup closes.
        """
        if self._queue_paused:
            return

        if not self._msg_queue:
            return

        # Calculate max width available for badges
        rep_width = self._rep_lbl.width() if self._rep_lbl.isVisible() else 0
        max_width = self.width() - rep_width - 32

        # Compute current total width of visible badges
        from PyQt6.QtGui import QFontMetrics
        fm = QFontMetrics(self.font())
        
        current_width = 0
        for badge in self._active_badges:
            display_text = badge.text()
            current_width += fm.horizontalAdvance(display_text) + 20

        # Deploy exactly one badge if it fits
        text, tooltip, color_hex, duration_ms = self._msg_queue[0]
        display_text = text
        if len(text) > 35:
            display_text = text[:32] + "..."
        
        badge_width = fm.horizontalAdvance(display_text) + 20
        
        if current_width + badge_width <= max_width:
            self._msg_queue.popleft()
            badge = StatusBadgeWidget(text, tooltip, color_hex, duration_ms, self)
            self._active_badges.append(badge)
            self._status_layout.addWidget(badge)
            self._last_create_time = time.time()
            # If popup is active, immediately pause the new badge's timers
            if self._popup_active:
                badge.pause()
            
            # Start timer for the next enqueued badge
            if self._msg_queue:
                self._stagger_create_timer.start()
        else:
            # Badge does not fit, stop deploying for now
            pass

    def request_dispose(self, badge: StatusBadgeWidget) -> None:
        """Enqueue a badge for staggered disposal."""
        if badge not in self._pending_disposals:
            self._pending_disposals.append(badge)
            self._trigger_disposal()

    def _trigger_disposal(self) -> None:
        if self._stagger_dispose_timer.isActive():
            return
        
        elapsed = (time.time() - self._last_dispose_time) * 1000.0
        if elapsed < _STAGGER_DISPOSE_DELAY_MS:
            remaining = max(1, int(_STAGGER_DISPOSE_DELAY_MS - elapsed))
            self._stagger_dispose_timer.start(remaining)
        else:
            self._dispose_one_badge()

    def _dispose_one_badge(self) -> None:
        """Dispose exactly one expired badge and queue next one."""
        if self._queue_paused or self._popup_active:
            return

        if not self._pending_disposals:
            return

        badge = self._pending_disposals.popleft()
        if badge in self._active_badges:
            self._active_badges.remove(badge)
            self._status_layout.removeWidget(badge)
            # Ensure flashing stopped before deletion
            try:
                badge._stop_flashing()
            except Exception:
                pass
            badge.setToolTip("")
            badge.deleteLater()
            self._last_dispose_time = time.time()

        # Trigger disposal timer for the next expired badge
        if self._pending_disposals:
            self._stagger_dispose_timer.start()
        
        # Check if more enqueued items can fit now
        self._trigger_creation()

    def show_expanded_badge(self, badge: StatusBadgeWidget) -> None:
        """Pause all timers and show the expanded popup message."""
        self._popup_active = True
        
        # Pause all active badges
        for b in self._active_badges:
            b.pause()
            
        # Stop staggered timers
        self._stagger_create_timer.stop()
        self._stagger_dispose_timer.stop()
            
        # Create popup
        self._popup = PopupMessageBox(badge._full_text, badge._color_hex, badge, self)
        self._popup.show()

    def resume_from_popup(self) -> None:
        """Resume active timers when the expanded popup is closed."""
        self._popup_active = False
        self._popup = None
        
        # Resume active badges
        for b in self._active_badges:
            b.resume()
            
        self._trigger_creation()
        self._trigger_disposal()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._trigger_creation()

    def clear_queue(self) -> None:
        """Discard all pending messages and hide all active badges immediately."""
        self._msg_queue.clear()
        self._pending_disposals.clear()
        self._stagger_create_timer.stop()
        self._stagger_dispose_timer.stop()
        
        for b in self._active_badges:
            self._status_layout.removeWidget(b)
            b.deleteLater()
        self._active_badges.clear()

    def set_status(self, text: str, level: str = "info") -> None:
        color = _COLOR_PRESETS.get(level, _DEFAULT_PILL_COLOR)
        self.push_message(text, "", color, _DEFAULT_PILL_DURATION_MS)

    def pause_queue(self) -> None:
        """Pause queue processing — active badges are paused and hidden."""
        self._queue_paused = True
        self._stagger_create_timer.stop()
        self._stagger_dispose_timer.stop()
        for b in self._active_badges:
            b.pause()
            b.hide()

    def resume_queue(self) -> None:
        """Resume queue processing and restore badge states."""
        self._queue_paused = False
        for b in self._active_badges:
            b.show()
            b.resume()
        self._trigger_creation()
        self._trigger_disposal()
