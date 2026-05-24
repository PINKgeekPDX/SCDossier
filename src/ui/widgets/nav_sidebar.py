"""
src/ui/widgets/nav_sidebar.py
NavSidebar — left-side icon rail navigation for the main window.

Features:
- 64px collapsed icon rail, expandable to 240px on hover/toggle
- Nav items with SVG icons + label
- Active item: bg-primary/10 + left border glow (3px, higher alpha)
- Hover: horizontal gradient highlight
- Animated width transition via QPropertyAnimation
- Emits tab_selected(tab_id: str) signal on click
"""

import os
import logging
from PyQt6.QtCore import (
    Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize, QRect
)
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QPen, QFont, QBrush, QIcon
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QSizePolicy, QFrame
)
import webbrowser

from src.ui.theme import palette as P
from src.ui.theme.fonts import label_caps, font_inter
from src.app.constants import (
    SIDEBAR_WIDTH_COLLAPSED, SIDEBAR_WIDTH_EXPANDED, TabId
)

log = logging.getLogger(__name__)

# Resolve icon paths
_ICONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "assets", "icons"
)
_ICONS_MISC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "assets", "icons", "misc"
)


class NavItem(QWidget):
    """A single navigation item in the sidebar."""

    clicked = pyqtSignal(str)  # emits tab_id

    def __init__(self, tab_id: str, icon_path: str, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.tab_id = tab_id
        self._icon_path = icon_path
        self._label = label
        self._active = False
        self._hovered = False
        self.setFixedHeight(52)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, value: bool) -> None:
        self._active = value
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.tab_id)

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        parent_width = self.parent().width() if self.parent() else SIDEBAR_WIDTH_COLLAPSED
        expanded = parent_width > SIDEBAR_WIDTH_COLLAPSED + 10

        # --- Active background (higher alpha = stronger glow) ---
        if self._active:
            painter.fillRect(rect, QColor(0, 170, 255, 40))  # alpha 26 → 40
            # Left accent bar (2px → 3px)
            accent_pen = QPen(QColor(P.PRIMARY_CONTAINER), 3)
            painter.setPen(accent_pen)
            painter.drawLine(0, 4, 0, rect.height() - 4)

        # --- Hover gradient ---
        elif self._hovered:
            grad = QLinearGradient(0, 0, rect.width(), 0)
            grad.setColorAt(0, QColor(79, 142, 255, 51))   # 0.20 alpha
            grad.setColorAt(1, QColor(79, 142, 255, 0))
            painter.fillRect(rect, QBrush(grad))

        # --- SVG Icon ---
        icon_rect = QRect(0, 0, SIDEBAR_WIDTH_COLLAPSED, rect.height())
        if os.path.exists(self._icon_path):
            icon = QIcon(self._icon_path)
            pixmap = icon.pixmap(22, 22)
            if not pixmap.isNull():
                # Tint the pixmap based on active state
                if self._active:
                    # Draw with primary color
                    tmp_icon = QIcon()
                    tmp_icon.addPixmap(pixmap)
                    painter.drawPixmap(
                        icon_rect.x() + (icon_rect.width() - 22) // 2,
                        icon_rect.y() + (icon_rect.height() - 22) // 2,
                        22, 22, pixmap
                    )
                else:
                    painter.drawPixmap(
                        icon_rect.x() + (icon_rect.width() - 22) // 2,
                        icon_rect.y() + (icon_rect.height() - 22) // 2,
                        22, 22, pixmap
                    )
            else:
                self._draw_fallback_icon(painter, icon_rect)
        else:
            self._draw_fallback_icon(painter, icon_rect)

        # --- Label (only when expanded) ---
        if expanded:
            label_color = QColor(P.PRIMARY) if self._active else QColor(P.ON_SURFACE_VARIANT)
            if self._hovered and not self._active:
                label_color = QColor(P.ON_SURFACE)
            painter.setPen(label_color)
            painter.setFont(label_caps())
            label_rect = QRect(SIDEBAR_WIDTH_COLLAPSED, 0, rect.width() - SIDEBAR_WIDTH_COLLAPSED - 12, rect.height())
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._label)

        painter.end()

    def _draw_fallback_icon(self, painter, icon_rect):
        """Draw Unicode fallback if SVG is missing."""
        icon_color = QColor(P.PRIMARY_CONTAINER) if self._active else QColor(P.TEXT_DIM)
        if self._hovered and not self._active:
            icon_color = QColor(P.ON_SURFACE)
        painter.setPen(icon_color)
        icon_font = QFont("Segoe UI Symbol", 18)
        painter.setFont(icon_font)
        # Use first char of label as fallback
        fallback_char = self._label[0] if self._label else "?"
        painter.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, fallback_char)


class NavSidebar(QWidget):
    """
    Left-side navigation sidebar with icon rail.

    Signals:
        tab_selected(str): Emits the TabId.value when a nav item is clicked.
    """

    tab_selected = pyqtSignal(str)

    NAV_ITEMS = [
        (TabId.SEARCH.value,       os.path.join(_ICONS_MISC_DIR, "icon_search.svg"),  "SEARCH"),
        (TabId.DOSSIER.value,      os.path.join(_ICONS_DIR, "Icons", "FOIP.png"),     "DOSSIER"),
        (TabId.ORGANIZATION.value, os.path.join(_ICONS_DIR, "Icons", "SHLD.png"),     "ORGANIZATION"),
        (TabId.ARCHIVE.value,      os.path.join(_ICONS_DIR, "Icons", "JOURNAL.png"),  "ARCHIVE"),
        (TabId.SETTINGS.value,     os.path.join(_ICONS_MISC_DIR, "icon_settings.svg"), "SETTINGS"),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(SIDEBAR_WIDTH_COLLAPSED)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setMouseTracking(True)

        self._expanded = False
        self._active_id = TabId.SEARCH.value
        self._items: dict[str, NavItem] = {}

        self._build_ui()
        self._setup_animation()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(0)

        for tab_id, icon_path, label in self.NAV_ITEMS:
            item = NavItem(tab_id, icon_path, label, self)
            item.clicked.connect(self._on_item_clicked)
            self._items[tab_id] = item
            layout.addWidget(item)

        layout.addStretch(1)

        # Github profile button at bottom (replaced toggle)
        self._toggle_btn = QPushButton()
        icon_path = os.path.join(_ICONS_DIR, "Icons", "!.png")
        if os.path.exists(icon_path):
            self._toggle_btn.setIcon(QIcon(icon_path))
        self._toggle_btn.setFixedHeight(40)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setToolTip("Open GitHub Profile")
        self._toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {P.TEXT_DIM};
                border: none;
                border-top: 1px solid {P.OUTLINE_VARIANT};
                font-size: 14px;
            }}
            QPushButton:hover {{
                color: {P.PRIMARY};
                background: rgba(0, 170, 255, 0.10);
            }}
        """)
        self._toggle_btn.clicked.connect(self._open_github)
        layout.addWidget(self._toggle_btn)

        # Set initial active
        self._items[self._active_id].active = True

    def _setup_animation(self) -> None:
        self._anim = QPropertyAnimation(self, b"maximumWidth")
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_active_tab(self, tab_id: str) -> None:
        """Set the active navigation item programmatically."""
        if tab_id not in self._items:
            return
        for tid, item in self._items.items():
            item.active = (tid == tab_id)
        self._active_id = tab_id

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_item_clicked(self, tab_id: str) -> None:
        if tab_id == "_toggle":
            return
        self.set_active_tab(tab_id)
        self.tab_selected.emit(tab_id)

    def _open_github(self) -> None:
        webbrowser.open("https://github.com/pinkgeekpdx")

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        # Dark sidebar background
        painter.fillRect(self.rect(), QColor(10, 21, 29, 180))
        # Right border
        pen = QPen(QColor(0, 170, 255, 25), 1)
        painter.setPen(pen)
        painter.drawLine(self.width() - 1, 0, self.width() - 1, self.height())
        painter.end()