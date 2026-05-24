"""
src/ui/tabs/search_tab.py
SearchTab — Landing page with player/org mode toggle for starting searches.
Enhanced with rich animations, styling, and tooltips.
"""

import os
from PyQt6.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QEasingCurve, QRectF
from PyQt6.QtGui import QColor, QIcon, QPixmap, QPainter, QPen, QLinearGradient, QBrush
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect
)

from src.core.events import EventBus
from src.ui.theme import palette as P
from src.ui.theme.fonts import headline_xl, font_inter, label_caps
from src.ui.widgets.search_input import SearchInput

from src.core.paths import get_asset_path
from src.core.settings import SettingsManager

_RIGHT_ICON = get_asset_path("assets/icons/Icons/RIGHT.png")


class StyledToggleButton(QPushButton):
    """Enhanced toggle button with hover/active animations."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self._active = False
        self._hovered = False
        self.setFixedHeight(44)
        self.setMinimumWidth(170)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setMouseTracking(True)

    def set_active(self, active: bool) -> None:
        self._active = active
        self.update()

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)

        if self._active:
            # Active state: filled primary gradient
            grad = QLinearGradient(0, 0, rect.width(), 0)
            grad.setColorAt(0, QColor(0, 130, 200, 200))
            grad.setColorAt(1, QColor(0, 170, 255, 220))
            painter.setBrush(QBrush(grad))
            painter.setPen(QPen(QColor(0, 200, 255, 150), 1))
            painter.drawRoundedRect(rect, 6, 6)

            # Draw text
            painter.setPen(QColor("#FFFFFF"))
            painter.setFont(self.font())
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())
        elif self._hovered:
            # Hover state: subtle glow
            painter.setBrush(QColor(0, 170, 255, 30))
            painter.setPen(QPen(QColor(0, 170, 255, 120), 1))
            painter.drawRoundedRect(rect, 6, 6)

            painter.setPen(QColor(P.ON_SURFACE))
            painter.setFont(self.font())
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())
        else:
            # Default: ghost style
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(0, 170, 255, 60), 1))
            painter.drawRoundedRect(rect, 6, 6)

            painter.setPen(QColor(P.TEXT_DIM))
            painter.setFont(self.font())
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())

        painter.end()


class AnimatedSearchInput(SearchInput):
    """Search input with border paint animation on focus/hover."""

    def __init__(self, placeholder: str, parent=None):
        super().__init__(placeholder, parent)
        self._focused = False
        self._hovered = False
        self._anim_progress = 0.0
        self._anim_direction = 1

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate_border)
        self._anim_timer.setInterval(30)

        self.setFixedHeight(56)
        self.setFont(font_inter(16))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setToolTip("Enter an RSI handle, name, or profile URL to search")

    def focusInEvent(self, event) -> None:
        self._focused = True
        self._anim_progress = 0.0
        self._anim_direction = 1
        self._anim_timer.start()
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:
        self._focused = False
        self._anim_timer.stop()
        self._anim_progress = 0.0
        self.update()
        super().focusOutEvent(event)

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()

    def _animate_border(self):
        self._anim_progress += 0.05 * self._anim_direction
        if self._anim_progress >= 1.0:
            self._anim_direction = -1
        elif self._anim_progress <= 0.0:
            self._anim_direction = 1
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(2, 2, -2, -2)

        # Background
        if self._focused:
            bg = QColor(15, 30, 45, 230)
        elif self._hovered:
            bg = QColor(12, 25, 38, 210)
        else:
            bg = QColor(10, 20, 30, 200)

        painter.setBrush(bg)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 8, 8)

        # Border with animation when focused
        if self._focused:
            alpha = int(100 + 155 * self._anim_progress)
            border_color = QColor(0, 170, 255, alpha)
            painter.setPen(QPen(border_color, 2))
            painter.drawRoundedRect(rect, 8, 8)

            # Glow effect ring
            glow_color = QColor(0, 170, 255, int(30 * self._anim_progress))
            painter.setPen(QPen(glow_color, 4))
            painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 10, 10)
        elif self._hovered:
            painter.setPen(QPen(QColor(0, 170, 255, 180), 2))
            painter.drawRoundedRect(rect, 8, 8)
        else:
            painter.setPen(QPen(QColor(P.OUTLINE), 2))
            painter.drawRoundedRect(rect, 8, 8)

        # Draw placeholder text or content
        text_rect = rect.adjusted(16, 0, -16, 0)
        text_color = QColor(P.TEXT_DIM) if not self.text() else QColor(P.ON_SURFACE)
        painter.setPen(text_color)
        font = font_inter(15)
        painter.setFont(font)

        if not self.text():
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.placeholderText())
        else:
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())

        # Draw cursor if focused
        if self._focused and self.text():
            cursor_x = text_rect.x() + painter.fontMetrics().horizontalAdvance(self.text()[:self.cursorPosition()])
            painter.setPen(QPen(QColor(P.PRIMARY), 2))
            painter.drawLine(cursor_x, text_rect.center().y() - 10, cursor_x, text_rect.center().y() + 10)

        painter.end()

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        self.setFocus()


class StyledActionButton(QPushButton):
    """Icon-only action button with hover/click effects."""

    def __init__(self, icon_path: str, tooltip: str, size: int = 56, parent=None):
        super().__init__(parent)
        self._icon_path = icon_path
        self._hovered = False
        self._pressed = False
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setMouseTracking(True)
        self.setToolTip(tooltip)
        self.setStyleSheet("background: transparent; border: none; padding: 0;")

        # Load icon
        if os.path.exists(icon_path):
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(size - 16, size - 16))

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)

        if self._pressed:
            painter.setBrush(QColor(0, 170, 255, 80))
            painter.setPen(QPen(QColor(0, 200, 255, 150), 1))
            painter.drawRoundedRect(rect, 8, 8)
        elif self._hovered:
            grad = QLinearGradient(0, 0, rect.width(), 0)
            grad.setColorAt(0, QColor(0, 170, 255, 50))
            grad.setColorAt(1, QColor(0, 170, 255, 80))
            painter.setBrush(QBrush(grad))
            painter.setPen(QPen(QColor(0, 200, 255, 120), 1))
            painter.drawRoundedRect(rect, 8, 8)
        else:
            painter.setBrush(QColor(P.PRIMARY))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 8, 8)

        painter.end()

        # CRITICAL: Call super to render the QIcon properly
        super().paintEvent(event)


class SearchTab(QWidget):
    """
    Initial landing view with player/org mode toggle.
    """
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mode = "player"
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(32)

        # --- Mode Toggle ---
        mode_widget = QWidget()
        mode_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        mode_layout = QHBoxLayout(mode_widget)
        mode_layout.setSpacing(16)
        mode_layout.setContentsMargins(0, 0, 0, 0)

        self.player_btn = StyledToggleButton("SEARCH PLAYER")
        self.player_btn.set_active(True)
        self.player_btn.setToolTip("Switch to player profile search mode")
        self.player_btn.clicked.connect(lambda: self._set_mode("player"))

        self.org_btn = StyledToggleButton("SEARCH ORG")
        self.org_btn.setToolTip("Switch to organization search mode")
        self.org_btn.clicked.connect(lambda: self._set_mode("org"))

        mode_layout.addStretch()
        mode_layout.addWidget(self.player_btn)
        mode_layout.addWidget(self.org_btn)
        mode_layout.addStretch()

        # --- Search Bar ---
        search_container = QFrame()
        search_container.setFixedWidth(560)
        search_container.setStyleSheet("background: transparent;")
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(12)

        self.search_input = AnimatedSearchInput("IDENTIFY SUBJECT (RSI HANDLE)...")
        self.search_input.returnPressed.connect(self._on_search)

        # Glow effect behind search input
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(25)
        glow.setColor(QColor(0, 170, 255, 40))
        glow.setOffset(0, 0)
        self.search_input.setGraphicsEffect(glow)

        self.search_btn = StyledActionButton(
            _RIGHT_ICON,
            "Execute search for the entered player or organization",
            56
        )
        self.search_btn.clicked.connect(self._on_search)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)



        # Assembly
        layout.addStretch(1)
        layout.addWidget(mode_widget, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(search_container, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(2)

    def _set_mode(self, mode: str) -> None:
        self._mode = mode
        if mode == "player":
            self.player_btn.set_active(True)
            self.org_btn.set_active(False)
            self.search_input.setPlaceholderText("IDENTIFY SUBJECT (RSI HANDLE)...")
            self.search_input.setToolTip("Enter an RSI handle (e.g., PINKgeekPDX) to search for a player profile")
        else:
            self.org_btn.set_active(True)
            self.player_btn.set_active(False)
            self.search_input.setPlaceholderText("ENTER ORG NAME OR SID...")
            self.search_input.setToolTip("Enter an organization name or SID (e.g., REBELS) to search for org details")

    def _on_search(self) -> None:
        query = self.search_input.text().strip()
        if not query:
            return
        # Add to search history
        self._add_to_search_history(query)
        
        if self._mode == "player":
            EventBus.instance().search_player_requested.emit(query)
            EventBus.instance().navigate_to_tab.emit("dossier")
        else:
            EventBus.instance().search_org_requested.emit(query)
            EventBus.instance().navigate_to_tab.emit("organization")
        self.search_input.clear()

    def _add_to_search_history(self, query: str) -> None:
        """Add a search query to the history."""
        settings = SettingsManager.instance()
        history = settings.search_history
        
        # Remove if already exists to avoid duplicates
        if query in history:
            history.remove(query)
        
        # Add to the end (most recent)
        history.append(query)
        
        # Apply limit
        limit = settings.search_history_limit
        if limit >= 0 and len(history) > limit:
            history = history[-limit:]
        
        # Save back to settings
        settings.search_history = history