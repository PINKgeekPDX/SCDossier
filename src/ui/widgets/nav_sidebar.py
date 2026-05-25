"""
src/ui/widgets/nav_sidebar.py
NavSidebar — left-side icon rail navigation for the main window.

Features:
- 52px collapsed icon rail, expandable to 220px on hover/toggle
- Nav items with SVG icons + label
- Active item: bg-primary/10 + left border glow (3px, higher alpha)
- Hover: horizontal gradient highlight
- Animated width transition via QPropertyAnimation
- Emits tab_selected(tab_id: str) signal on click
"""

import os
import logging
from PyQt6.QtCore import (
    Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize, QRect, QByteArray
)
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QPen, QFont, QBrush, QIcon, QPixmap
from PyQt6.QtSvg import QSvgRenderer
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

from src.core.paths import get_asset_path


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
        self.setFixedHeight(44)   # was 52
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

    def _load_icon_pixmap(self) -> QPixmap | None:
        """Load and return a 18x18 pixmap from the icon path, handling SVGs properly."""
        if not os.path.exists(self._icon_path):
            return None

        # Try QSvgRenderer first for SVGs
        if self._icon_path.lower().endswith('.svg'):
            renderer = QSvgRenderer(self._icon_path)
            if renderer.isValid():
                pixmap = QPixmap(18, 18)
                pixmap.fill(Qt.GlobalColor.transparent)
                p = QPainter(pixmap)
                renderer.render(p)
                p.end()
                return pixmap

        # Fallback to QIcon for PNGs
        icon = QIcon(self._icon_path)
        pixmap = icon.pixmap(18, 18)
        if not pixmap.isNull():
            return pixmap
        return None

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        parent_width = self.parent().width() if self.parent() else SIDEBAR_WIDTH_COLLAPSED
        expanded = parent_width > SIDEBAR_WIDTH_COLLAPSED + 10

        # --- Active background ---
        if self._active:
            painter.fillRect(rect, QColor(0, 170, 255, 36))
            # Left accent bar (2px — slimmer)
            accent_pen = QPen(QColor(P.PRIMARY_CONTAINER), 2)
            painter.setPen(accent_pen)
            painter.drawLine(0, 3, 0, rect.height() - 3)

        # --- Hover gradient ---
        elif self._hovered:
            grad = QLinearGradient(0, 0, rect.width(), 0)
            grad.setColorAt(0, QColor(79, 142, 255, 45))
            grad.setColorAt(1, QColor(79, 142, 255, 0))
            painter.fillRect(rect, QBrush(grad))

        # --- Icon (18×18, centred in the collapsed rail) ---
        icon_x = (SIDEBAR_WIDTH_COLLAPSED - 18) // 2
        icon_y = (rect.height() - 18) // 2
        pixmap = self._load_icon_pixmap()
        if pixmap is not None:
            if self._active:
                tinted = QPixmap(18, 18)
                tinted.fill(Qt.GlobalColor.transparent)
                tp = QPainter(tinted)
                tp.drawPixmap(0, 0, pixmap)
                tp.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
                tp.fillRect(tinted.rect(), QColor(0, 200, 255, 200))
                tp.end()
                painter.drawPixmap(icon_x, icon_y, tinted)
            else:
                painter.drawPixmap(icon_x, icon_y, pixmap)
        else:
            self._draw_fallback_icon(painter, QRect(0, 0, SIDEBAR_WIDTH_COLLAPSED, rect.height()))

        # --- Label (only when expanded) ---
        if expanded:
            label_color = QColor(P.PRIMARY) if self._active else QColor(P.ON_SURFACE_VARIANT)
            if self._hovered and not self._active:
                label_color = QColor(P.ON_SURFACE)
            painter.setPen(label_color)
            painter.setFont(label_caps())
            label_rect = QRect(SIDEBAR_WIDTH_COLLAPSED + 6, 0,
                               rect.width() - SIDEBAR_WIDTH_COLLAPSED - 16, rect.height())
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._label)

        painter.end()

    def _draw_fallback_icon(self, painter, icon_rect):
        """Draw Unicode fallback if SVG is missing."""
        icon_color = QColor(P.PRIMARY_CONTAINER) if self._active else QColor(P.TEXT_DIM)
        if self._hovered and not self._active:
            icon_color = QColor(P.ON_SURFACE)
        painter.setPen(icon_color)
        icon_font = QFont("Segoe UI Symbol", 14)   # was 18
        painter.setFont(icon_font)
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
        (TabId.SEARCH.value,       "assets/icons/misc/icon_search.svg",  "SEARCH"),
        (TabId.DOSSIER.value,      "assets/icons/Icons/FOIP.png",     "DOSSIER"),
        (TabId.ORGANIZATION.value, "assets/icons/Icons/SHLD.png",     "ORGANIZATION"),
        (TabId.ARCHIVE.value,      "assets/icons/Icons/JOURNAL.png",  "ARCHIVE"),
        (TabId.SETTINGS.value,     "assets/icons/misc/icon_settings.svg", "SETTINGS"),
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
        layout.setContentsMargins(0, 6, 0, 6)   # was 0,8,0,8
        layout.setSpacing(0)

        tooltips = {
            TabId.SEARCH.value: "Search — Find player profiles and orgs",
            TabId.DOSSIER.value: "Dossier — View active player profile",
            TabId.ORGANIZATION.value: "Organization — View active org details",
            TabId.ARCHIVE.value: "Archive — Saved offline profiles",
            TabId.SETTINGS.value: "Settings — App preferences and updates"
        }

        for tab_id, icon_rel, label in self.NAV_ITEMS:
            icon_path = get_asset_path(icon_rel)
            item = NavItem(tab_id, icon_path, label, self)
            item.setToolTip(tooltips.get(tab_id, ""))
            item.clicked.connect(self._on_item_clicked)
            self._items[tab_id] = item
            layout.addWidget(item)

        layout.addStretch(1)

        # Github profile button at bottom
        self._toggle_btn = QPushButton()
        icon_path = get_asset_path("assets/icons/Icons/!.png")
        if os.path.exists(icon_path):
            self._toggle_btn.setIcon(QIcon(icon_path))
            self._toggle_btn.setIconSize(QSize(16, 16))
        self._toggle_btn.setFixedHeight(32)   # was 40
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setToolTip("Open PINKgeekPDX GitHub profile in your browser")
        self._toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {P.TEXT_DIM};
                border: none;
                border-top: 1px solid {P.OUTLINE_VARIANT};
                font-size: 11px;
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
        self._anim.setDuration(180)   # was 200 — slightly snappier
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
        # Dark sidebar background — slightly more opaque for clear delineation
        painter.fillRect(self.rect(), QColor(8, 18, 26, 200))
        # Right border — subtle glow line
        pen = QPen(QColor(0, 170, 255, 22), 1)
        painter.setPen(pen)
        painter.drawLine(self.width() - 1, 0, self.width() - 1, self.height())
        painter.end()