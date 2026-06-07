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
        self.setFixedHeight(36)   # was 44
        self.setMinimumWidth(130)  # was 170
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
            grad.setColorAt(0, QColor(P.SURFACE_CONTAINER_HIGH))
            grad.setColorAt(0.5, QColor(P.PRIMARY_CONTAINER))
            grad.setColorAt(1, QColor(P.PRIMARY_CONTAINER))
            painter.setBrush(QBrush(grad))
            painter.setPen(QPen(QColor(P.PRIMARY), 1))
            painter.drawRoundedRect(rect, 4, 4)

            # Draw text
            painter.setPen(QColor(P.ON_PRIMARY))
            painter.setFont(self.font())
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())
        elif self._hovered:
            # Hover state: subtle glow
            painter.setBrush(QColor(P.rgba(P.PRIMARY_CONTAINER, 0.15)))
            painter.setPen(QPen(QColor(P.PRIMARY_CONTAINER), 1))
            painter.drawRoundedRect(rect, 4, 4)

            painter.setPen(QColor(P.ON_SURFACE))
            painter.setFont(self.font())
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())
        else:
            # Default: ghost style
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(P.rgba(P.PRIMARY_CONTAINER, 0.4)), 1))
            painter.drawRoundedRect(rect, 4, 4)

            painter.setPen(QColor(P.TEXT_DIM))
            painter.setFont(self.font())
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())

        painter.end()


class AnimatedSearchInput(SearchInput):
    """Search input with border paint animation on focus/hover."""

    def __init__(self, placeholder: str, parent=None, history_type: str = "all"):
        super().__init__(placeholder, parent, history_type)
        self._focused = False
        self._hovered = False
        self._anim_progress = 0.0
        self._anim_direction = 1

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate_border)
        self._anim_timer.setInterval(30)

        self.setFixedHeight(46)   # was 56
        self.setFont(font_inter(13))  # was 16
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
            bg = P.qcolor(P.SURFACE_CONTAINER, 230)
        elif self._hovered:
            bg = P.qcolor(P.SURFACE_CONTAINER_LOW, 210)
        else:
            bg = P.qcolor(P.SURFACE_CONTAINER_LOW, 200)

        painter.setBrush(bg)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 5, 5)

        # Border with animation when focused
        if self._focused:
            alpha = int(100 + 155 * self._anim_progress)
            border_color = QColor(P.PRIMARY_CONTAINER)
            border_color.setAlpha(alpha)
            painter.setPen(QPen(border_color, 2))
            painter.drawRoundedRect(rect, 5, 5)

            # Glow effect ring
            glow_color = QColor(P.PRIMARY_CONTAINER)
            glow_color.setAlpha(int(30 * self._anim_progress))
            painter.setPen(QPen(glow_color, 4))
            painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 7, 7)
        elif self._hovered:
            painter.setPen(QPen(QColor(P.PRIMARY_CONTAINER), 2))
            painter.drawRoundedRect(rect, 5, 5)
        else:
            painter.setPen(QPen(QColor(P.OUTLINE), 2))
            painter.drawRoundedRect(rect, 5, 5)

        painter.end()

        # Let Qt render the actual text, cursor, and selection natively
        super().paintEvent(event)

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
            self.setIconSize(QSize(size - 12, size - 12))   # was size-16

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
            painter.setBrush(QColor(P.rgba(P.PRIMARY_CONTAINER, 0.5)))
            painter.setPen(QPen(QColor(P.PRIMARY), 1))
            painter.drawRoundedRect(rect, 5, 5)   # was 8
        elif self._hovered:
            grad = QLinearGradient(0, 0, rect.width(), 0)
            grad.setColorAt(0, QColor(P.rgba(P.PRIMARY_CONTAINER, 0.3)))
            grad.setColorAt(1, QColor(P.rgba(P.PRIMARY_CONTAINER, 0.5)))
            painter.setBrush(QBrush(grad))
            painter.setPen(QPen(QColor(P.PRIMARY), 1))
            painter.drawRoundedRect(rect, 5, 5)   # was 8
        else:
            # Default: transparent with subtle border
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(P.rgba(P.PRIMARY_CONTAINER, 0.3)), 1))
            painter.drawRoundedRect(rect, 5, 5)

        painter.end()

        # CRITICAL: Call super to render the QIcon properly
        super().paintEvent(event)


class RecentSearchChip(QPushButton):
    """A clean, premium SCPINK-style chip for a recent search query."""
    
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(22)   # was 26
        self.setFlat(True)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {P.rgba(P.PRIMARY_CONTAINER, 0.06)};
                color: {P.PRIMARY};
                border: 1px solid {P.rgba(P.PRIMARY_CONTAINER, 0.22)};
                border-radius: 11px;
                padding: 1px 10px;
                font-family: "Inter", sans-serif;
                font-size: 10px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {P.rgba(P.PRIMARY_CONTAINER, 0.15)};
                border-color: {P.PRIMARY};
                color: {P.ON_PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {P.rgba(P.PRIMARY_CONTAINER, 0.25)};
            }}
        """)


class SearchTab(QWidget):
    """
    Initial landing view with player/org mode toggle.
    """
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mode = "player"
        self._build_ui()
        self._update_recents()
        EventBus.instance().settings_changed.connect(self._on_settings_changed)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(18)   # was 32

        # --- App Logo ---
        self._logo_lbl = QLabel()
        self._logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _app_icon_path = get_asset_path("assets/appicon.png")
        if os.path.exists(_app_icon_path):
            logo_pix = QPixmap(_app_icon_path)
            target_width = 200
            scaled_pix = logo_pix.scaled(
                target_width, target_width,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self._logo_lbl.setPixmap(scaled_pix)
            self._logo_lbl.setFixedSize(scaled_pix.size())

            self._logo_glow = QGraphicsDropShadowEffect()
            self._logo_glow.setBlurRadius(40)
            self._logo_glow.setOffset(0, 0)
            self._logo_glow.setColor(P.qcolor(P.PRIMARY_CONTAINER, 80))
            self._logo_lbl.setGraphicsEffect(self._logo_glow)
        else:
            self._logo_glow = None
            self._logo_lbl.setText("SC DOSSIER")
            self._logo_lbl.setFont(font_inter(32))
            self._logo_lbl.setStyleSheet(f"color: {P.PRIMARY}; background: transparent;")

        # --- Mode Toggle ---
        mode_widget = QWidget()
        mode_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        mode_layout = QHBoxLayout(mode_widget)
        mode_layout.setSpacing(10)  # was 16
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
        search_container.setFixedWidth(480)  # was 560
        search_container.setStyleSheet("background: transparent;")
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(8)  # was 12

        self.search_input = AnimatedSearchInput("IDENTIFY SUBJECT (RSI HANDLE)...")
        self.search_input.returnPressed.connect(self._on_search)

        # Glow effect behind search input
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(25)
        glow.setColor(QColor(P.rgba(P.PRIMARY_CONTAINER, 0.15)))
        glow.setOffset(0, 0)
        self.search_input.setGraphicsEffect(glow)

        self.search_btn = StyledActionButton(
            _RIGHT_ICON,
            "Execute search for the entered player or organization",
            46   # was 56
        )
        self.search_btn.clicked.connect(self._on_search)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)



        # --- Recent Searches Row ---
        self.recent_widget = QWidget()
        self.recent_layout = QHBoxLayout(self.recent_widget)
        self.recent_layout.setContentsMargins(0, 0, 0, 0)
        self.recent_layout.setSpacing(6)  # was 8
        self.recent_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Assembly
        layout.addStretch(1)
        layout.addWidget(self._logo_lbl, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(mode_widget, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(search_container, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.recent_widget, 0, Qt.AlignmentFlag.AlignCenter)
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
        limit = settings.search_history_limit
        
        # 1. Update the master combined history
        master = settings.search_history
        if query in master:
            master.remove(query)
        master.append(query)
        if limit >= 0 and len(master) > limit:
            master = master[-limit:]
        settings.search_history = master

        # 2. Update the specific history based on active mode
        if self._mode == "player":
            player_hist = settings.search_history_player
            if query in player_hist:
                player_hist.remove(query)
            player_hist.append(query)
            if limit >= 0 and len(player_hist) > limit:
                player_hist = player_hist[-limit:]
            settings.search_history_player = player_hist
        else:
            org_hist = settings.search_history_org
            if query in org_hist:
                org_hist.remove(query)
            org_hist.append(query)
            if limit >= 0 and len(org_hist) > limit:
                org_hist = org_hist[-limit:]
            settings.search_history_org = org_hist

    def _on_settings_changed(self, key: str, value: object) -> None:
        if key == "search_history":
            self._update_recents()
        elif key == "theme_palette_overrides":
            self._refresh_logo_glow()

    def _refresh_logo_glow(self) -> None:
        if self._logo_glow is not None:
            self._logo_glow.setColor(P.qcolor(P.PRIMARY_CONTAINER, 80))

    def _on_recent_clicked(self, query: str) -> None:
        self.search_input.setText(query)
        self._on_search()

    def _update_recents(self) -> None:
        """Re-populate the horizontal recents row."""
        # Clear existing chips in layout
        while self.recent_layout.count():
            item = self.recent_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        settings = SettingsManager.instance()
        history = settings.search_history
        if not history:
            self.recent_widget.setVisible(False)
            return
            
        # Get unique recent searches up to 5 items
        seen = set()
        unique_history = []
        for x in reversed(history):
            if x not in seen:
                seen.add(x)
                unique_history.append(x)
        unique_history = unique_history[:5]
        
        if not unique_history:
            self.recent_widget.setVisible(False)
            return
            
        self.recent_widget.setVisible(True)
        
        # Add label
        lbl = QLabel("RECENTS:")
        lbl.setFont(font_inter(9))   # was 10
        lbl.setStyleSheet(f"color: {P.TEXT_DIM}; letter-spacing: 0.08em; background: transparent; border: none; margin-right: 3px;")
        self.recent_layout.addWidget(lbl)
        
        # Add chips
        for query in unique_history:
            chip = RecentSearchChip(query, self)
            chip.clicked.connect(lambda checked, q=query: self._on_recent_clicked(q))
            self.recent_layout.addWidget(chip)