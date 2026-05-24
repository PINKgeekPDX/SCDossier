"""
src/ui/toolbar/overlay_toolbar.py
OverlayToolbar — always-on-top, frameless, screen-edge-snapping slip toolbar.

Features:
- Frameless + WindowStaysOnTopHint + Tool (no taskbar entry)
- Two icon buttons: Expand (open main window) and Capture (OCR mode)
- Drag to reposition; auto-snaps to nearest screen edge on release
- Saves position (x, y, edge) to SettingsManager on snap
- Restores saved position on startup
- Orientation auto-adjusts (horizontal for top/bottom, vertical for left/right)
- Configurable opacity
"""

import logging
import os
from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QIcon
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy,
    QApplication
)

from src.ui.theme import palette as P
from src.app.constants import ScreenEdge, TOOLBAR_BUTTON_SIZE

log = logging.getLogger(__name__)

TOOLBAR_THICKNESS = 56   # px — short dimension
TOOLBAR_LENGTH = 120     # px — long dimension (2 buttons)

# Resolve icon paths
_ICONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "icons")


class ToolbarButton(QPushButton):
    """A single icon button for the overlay toolbar."""

    def __init__(self, icon_path: str, tooltip: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._icon_path = icon_path
        self.setToolTip(tooltip)
        self.setFixedSize(TOOLBAR_BUTTON_SIZE, TOOLBAR_BUTTON_SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._hovered = False
        self._pressed = False
        self._load_icon()

    def _load_icon(self) -> None:
        """Load SVG icon with fallback to text character."""
        from PyQt6.QtCore import QSize
        icon = QIcon()
        if os.path.exists(self._icon_path):
            icon = QIcon(self._icon_path)
            if icon.isNull():
                icon = QIcon()
        if not icon.isNull():
            self.setIcon(icon)
            size = self.size()
            self.setIconSize(QSize(size.width() - 8, size.height() - 8))
            self.setText("")
        else:
            self.setText("▶")

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

        rect = self.rect()
        radius = 8

        if self._pressed:
            painter.fillRect(rect, QColor(0, 170, 255, 77))
        elif self._hovered:
            painter.fillRect(rect, QColor(0, 170, 255, 40))

        # Hover border
        if self._hovered:
            painter.setPen(QPen(QColor(0, 170, 255, 100), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(0, 0, -1, -1), radius, radius)

        painter.end()

        super().paintEvent(event)


class OverlayToolbar(QWidget):
    """
    Always-on-top edge-snapping overlay toolbar.

    Signals:
        expand_requested():   Emitted when expand button is clicked.
        capture_requested():  Emitted when capture button is clicked.
    """

    expand_requested = pyqtSignal()
    capture_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setMouseTracking(True)

        self._edge = ScreenEdge.LEFT
        self._drag_active = False
        self._drag_start_pos = QPoint()
        self._drag_start_window_pos = QPoint()

        self._build_ui()
        self._set_orientation(self._edge)

    def _build_ui(self) -> None:
        # Expand button
        expand_icon = os.path.join(os.path.dirname(_ICONS_DIR), "icons", "ships", "default", "MobiGlas.png")
        self._expand_btn = ToolbarButton(expand_icon, "Open SC Dossier", self)
        self._expand_btn.clicked.connect(self.expand_requested.emit)

        # Capture button
        capture_icon = os.path.join(os.path.dirname(_ICONS_DIR), "icons", "ships", "default", "Target_Lock.png")
        self._capture_btn = ToolbarButton(capture_icon, "OCR Screen Capture", self)
        self._capture_btn.clicked.connect(self.capture_requested.emit)

    def _set_orientation(self, edge: ScreenEdge) -> None:
        """Arrange buttons horizontally or vertically based on edge."""
        old = self.layout()
        if old is not None:
            while old.count():
                old.takeAt(0)
            old.deleteLater()

        padding = 6
        if edge in (ScreenEdge.TOP, ScreenEdge.BOTTOM):
            layout = QHBoxLayout(self)
            self.setFixedSize(TOOLBAR_LENGTH, TOOLBAR_THICKNESS)
        else:
            layout = QVBoxLayout(self)
            self.setFixedSize(TOOLBAR_THICKNESS, TOOLBAR_LENGTH)

        layout.setContentsMargins(padding, padding, padding, padding)
        layout.setSpacing(4)
        layout.addWidget(self._expand_btn)
        layout.addWidget(self._capture_btn)

    # ------------------------------------------------------------------
    # Position / Snapping
    # ------------------------------------------------------------------

    def restore_position(self, x: int, y: int, edge: str) -> None:
        """Restore toolbar position from saved settings.

        Ensures the toolbar is always positioned on a visible screen.
        If the saved coordinates are off-screen (e.g. after a monitor
        was disconnected), the toolbar defaults to the left edge of the
        primary screen.
        """
        try:
            self._edge = ScreenEdge(edge)
        except ValueError:
            self._edge = ScreenEdge.LEFT
        self._set_orientation(self._edge)

        # Validate that the saved position lands on a visible screen.
        # Use the known fixed size rather than self.width() / self.height()
        # because the widget may not have been shown yet.
        # LEFT/RIGHT -> vertical layout -> THICKNESS x LENGTH
        # TOP/BOTTOM -> horizontal layout -> LENGTH x THICKNESS
        w = TOOLBAR_THICKNESS if edge in ("left", "right") else TOOLBAR_LENGTH
        h = TOOLBAR_LENGTH if edge in ("left", "right") else TOOLBAR_THICKNESS
        target_rect = QRect(x, y, w, h)
        on_screen = False
        for screen in QApplication.screens():
            if screen.availableGeometry().intersects(target_rect):
                on_screen = True
                break

        if on_screen:
            self.move(x, y)
        else:
            # Saved coords are off-screen — snap to default position
            log.warning(
                "Saved toolbar position (%d, %d) is off-screen; resetting to default.",
                x, y,
            )
            self._edge = ScreenEdge.LEFT
            self._set_orientation(self._edge)
            primary = QApplication.primaryScreen()
            if primary:
                avail = primary.availableGeometry()
                self.move(
                    avail.left(),
                    avail.top() + (avail.height() - h) // 2,
                )
            else:
                self.move(0, 100)
            # Immediately save the corrected position
            self._save_position()

    def snap_to_nearest_edge(self) -> None:
        """Snap the toolbar flush to the nearest screen edge; save position."""
        screen = QApplication.primaryScreen()
        if not screen:
            return
        avail = screen.availableGeometry()
        pos = self.pos()
        cx = pos.x() + self.width() // 2
        cy = pos.y() + self.height() // 2

        # Distance from each edge
        dist_left = cx - avail.left()
        dist_right = avail.right() - cx
        dist_top = cy - avail.top()
        dist_bottom = avail.bottom() - cy

        nearest = min(
            (dist_left, ScreenEdge.LEFT),
            (dist_right, ScreenEdge.RIGHT),
            (dist_top, ScreenEdge.TOP),
            (dist_bottom, ScreenEdge.BOTTOM),
            key=lambda t: t[0],
        )
        edge = nearest[1]

        if edge != self._edge:
            self._edge = edge
            self._set_orientation(edge)

        # Snap flush to edge
        if edge == ScreenEdge.LEFT:
            new_x = avail.left()
            new_y = max(avail.top(), min(pos.y(), avail.bottom() - self.height()))
        elif edge == ScreenEdge.RIGHT:
            new_x = avail.right() - self.width()
            new_y = max(avail.top(), min(pos.y(), avail.bottom() - self.height()))
        elif edge == ScreenEdge.TOP:
            new_x = max(avail.left(), min(pos.x(), avail.right() - self.width()))
            new_y = avail.top()
        else:  # BOTTOM
            new_x = max(avail.left(), min(pos.x(), avail.right() - self.width()))
            new_y = avail.bottom() - self.height()

        self.move(new_x, new_y)
        self._save_position()

    def _save_position(self) -> None:
        """Persist current position to SettingsManager."""
        try:
            from src.core.settings import SettingsManager
            sm = SettingsManager.instance()
            sm.toolbar_x = self.x()
            sm.toolbar_y = self.y()
            sm.toolbar_edge = self._edge.value
        except Exception as e:
            log.debug("Could not save toolbar position: %s", e)

    # ------------------------------------------------------------------
    # Drag
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_active = True
            self._drag_start_pos = event.globalPosition().toPoint()
            self._drag_start_window_pos = self.pos()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_active:
            delta = event.globalPosition().toPoint() - self._drag_start_pos
            self.move(self._drag_start_window_pos + delta)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if self._drag_active:
            self._drag_active = False
            self.snap_to_nearest_edge()
            event.accept()

    # ------------------------------------------------------------------
    # Opacity
    # ------------------------------------------------------------------

    def set_opacity(self, opacity: float) -> None:
        self.setWindowOpacity(max(0.3, min(1.0, opacity)))

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        radius = 10

        # Glass background
        painter.setBrush(QBrush(QColor(5, 18, 28, 220)))
        painter.setPen(QPen(QColor(0, 170, 255, 80), 1))
        painter.drawRoundedRect(rect.adjusted(0, 0, -1, -1), radius, radius)

        # Subtle inner highlight on appropriate edge
        if self._edge == ScreenEdge.LEFT:
            grad = QLinearGradient(rect.width(), 0, 0, 0)
        elif self._edge == ScreenEdge.RIGHT:
            grad = QLinearGradient(0, 0, rect.width(), 0)
        elif self._edge == ScreenEdge.TOP:
            grad = QLinearGradient(0, rect.height(), 0, 0)
        else:
            grad = QLinearGradient(0, 0, 0, rect.height())

        grad.setColorAt(0, QColor(0, 170, 255, 25))
        grad.setColorAt(1, QColor(0, 170, 255, 0))
        painter.fillRect(rect, QBrush(grad))

        painter.end()


