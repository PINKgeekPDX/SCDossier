"""
src/ui/widgets/base_window.py
BaseWindow — frameless, draggable, resizable QWidget base for all SC Dossier windows.

Features:
- FramelessWindowHint + WA_TranslucentBackground for glass effect
- Click-drag repositioning via custom title bar drag region
- 8-direction resize handles on all edges/corners
- Min/max size constraints (no maximize)
- Radial gradient background from Aegis Liquid Interface
- Conditional WindowStaysOnTopHint (for toolbar and when pinned)
"""

import logging
from PyQt6.QtCore import Qt, QPoint, QRect, QSize
from PyQt6.QtGui import QColor, QPainter, QRadialGradient, QLinearGradient, QCursor
from PyQt6.QtWidgets import QWidget, QApplication

from src.ui.theme import palette as P

log = logging.getLogger(__name__)

# Resize handle thickness in pixels
RESIZE_MARGIN = 8


class BaseWindow(QWidget):
    """
    Base class for all SC Dossier frameless windows.

    Subclasses should:
    - Call super().__init__() with appropriate flags
    - Implement their content layout in __init__
    - Call set_drag_widget(widget) to designate the drag region

    Args:
        always_on_top: If True, adds WindowStaysOnTopHint.
        tool_window:   If True, adds Tool flag (no taskbar entry).
        parent:        Optional parent widget.
    """

    def __init__(
        self,
        always_on_top: bool = False,
        tool_window: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        flags = Qt.WindowType.FramelessWindowHint
        if always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        if tool_window:
            flags |= Qt.WindowType.Tool

        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

        self._drag_widget: QWidget | None = None
        self._drag_active = False
        self._drag_start_pos = QPoint()
        self._drag_start_window_pos = QPoint()

        # Resize state
        self._resize_active = False
        self._resize_edge: str = ""
        self._resize_start_pos = QPoint()
        self._resize_start_geom = QRect()

        self.setMouseTracking(True)

    # ------------------------------------------------------------------
    # Drag Region
    # ------------------------------------------------------------------

    def set_drag_widget(self, widget: QWidget) -> None:
        """Designate a widget as the drag handle for repositioning the window."""
        self._drag_widget = widget
        widget.installEventFilter(self)
        widget.setMouseTracking(True)

    # ------------------------------------------------------------------
    # Always On Top Toggle
    # ------------------------------------------------------------------

    def set_always_on_top(self, enabled: bool) -> None:
        """Toggle WindowStaysOnTopHint at runtime."""
        flags = self.windowFlags()
        if enabled:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    # ------------------------------------------------------------------
    # Mouse Events — Dragging
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event):
        """Handle drag and double-click events on the designated drag widget."""
        from PyQt6.QtCore import QEvent
        if obj is self._drag_widget:
            if event.type() == QEvent.Type.MouseButtonDblClick:
                if event.button() == Qt.MouseButton.LeftButton:
                    self._drag_active = False
                    self._toggle_size_limits()
                    return True
            elif event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self._drag_active = True
                    self._drag_start_pos = event.globalPosition().toPoint()
                    self._drag_start_window_pos = self.pos()
                    return True
            elif event.type() == QEvent.Type.MouseMove and self._drag_active:
                delta = event.globalPosition().toPoint() - self._drag_start_pos
                self.move(self._drag_start_window_pos + delta)
                return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                self._drag_active = False
                self._on_drag_released()
                return True
        return super().eventFilter(obj, event)

    def _on_drag_released(self) -> None:
        """Override in subclasses to handle post-drag behavior (e.g., snap to edge)."""
        pass

    def _toggle_size_limits(self) -> None:
        """Alternate the window size between its minimum and maximum limits, centering it on the screen."""
        screen = self.screen()
        if not screen:
            screen = QApplication.primaryScreen()
        if not screen:
            return

        screen_geo = screen.availableGeometry()

        min_size = self.minimumSize()
        if min_size.width() <= 0 or min_size.height() <= 0:
            min_size = QSize(800, 600)

        max_w = self.maximumWidth()
        max_h = self.maximumHeight()
        # QWidget default maximum width/height is QWIDGETSIZE_MAX (16777215)
        if max_w > screen_geo.width():
            max_w = screen_geo.width()
        if max_h > screen_geo.height():
            max_h = screen_geo.height()
        max_size = QSize(max_w, max_h)

        current_size = self.size()

        # If we are close to minimum size, toggle to maximum size
        if abs(current_size.width() - min_size.width()) < 10 and abs(current_size.height() - min_size.height()) < 10:
            new_x = screen_geo.left() + (screen_geo.width() - max_size.width()) // 2
            new_y = screen_geo.top() + (screen_geo.height() - max_size.height()) // 2
            self.setGeometry(new_x, new_y, max_size.width(), max_size.height())
        else:
            new_x = screen_geo.left() + (screen_geo.width() - min_size.width()) // 2
            new_y = screen_geo.top() + (screen_geo.height() - min_size.height()) // 2
            self.setGeometry(new_x, new_y, min_size.width(), min_size.height())

    # ------------------------------------------------------------------
    # Mouse Events — Resizing
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._get_resize_edge(event.position().toPoint())
            if edge:
                self._resize_active = True
                self._resize_edge = edge
                self._resize_start_pos = event.globalPosition().toPoint()
                self._resize_start_geom = self.geometry()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._resize_active:
            self._do_resize(event.globalPosition().toPoint())
            event.accept()
            return

        # Update cursor based on hover position
        edge = self._get_resize_edge(event.position().toPoint())
        self._set_resize_cursor(edge)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._resize_active:
            self._resize_active = False
            self._resize_edge = ""
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _get_resize_edge(self, pos: QPoint) -> str:
        """Return resize edge identifier string for a given local mouse position."""
        r = self.rect()
        m = RESIZE_MARGIN
        left = pos.x() < m
        right = pos.x() > r.width() - m
        top = pos.y() < m
        bottom = pos.y() > r.height() - m

        if top and left:
            return "top-left"
        if top and right:
            return "top-right"
        if bottom and left:
            return "bottom-left"
        if bottom and right:
            return "bottom-right"
        if top:
            return "top"
        if bottom:
            return "bottom"
        if left:
            return "left"
        if right:
            return "right"
        return ""

    def _set_resize_cursor(self, edge: str) -> None:
        cursors = {
            "top": Qt.CursorShape.SizeVerCursor,
            "bottom": Qt.CursorShape.SizeVerCursor,
            "left": Qt.CursorShape.SizeHorCursor,
            "right": Qt.CursorShape.SizeHorCursor,
            "top-left": Qt.CursorShape.SizeFDiagCursor,
            "bottom-right": Qt.CursorShape.SizeFDiagCursor,
            "top-right": Qt.CursorShape.SizeBDiagCursor,
            "bottom-left": Qt.CursorShape.SizeBDiagCursor,
        }
        if edge in cursors:
            self.setCursor(QCursor(cursors[edge]))
        else:
            self.unsetCursor()

    def _do_resize(self, global_pos: QPoint) -> None:
        """Perform window resize based on mouse delta and active edge."""
        delta = global_pos - self._resize_start_pos
        geom = QRect(self._resize_start_geom)
        min_w = self.minimumWidth() or 200
        min_h = self.minimumHeight() or 150
        max_w = self.maximumWidth() or 4096
        max_h = self.maximumHeight() or 2160

        edge = self._resize_edge

        if "right" in edge:
            new_w = max(min_w, geom.width() + delta.x())
            new_w = min(new_w, max_w)
            geom.setWidth(new_w)

        if "bottom" in edge:
            new_h = max(min_h, geom.height() + delta.y())
            new_h = min(new_h, max_h)
            geom.setHeight(new_h)

        if "left" in edge:
            new_w = max(min_w, geom.width() - delta.x())
            new_w = min(new_w, max_w)
            new_x = geom.right() - new_w
            geom.setLeft(new_x)
            geom.setWidth(new_w)

        if "top" in edge:
            new_h = max(min_h, geom.height() - delta.y())
            new_h = min(new_h, max_h)
            new_y = geom.bottom() - new_h
            geom.setTop(new_y)
            geom.setHeight(new_h)

        self.setGeometry(geom)

    # ------------------------------------------------------------------
    # Paint — Background
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        """Paint the Aegis deep-space radial gradient background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        center_x = rect.width() * 0.35
        center_y = rect.height() * 0.2
        radius = max(rect.width(), rect.height()) * 0.8

        gradient = QRadialGradient(center_x, center_y, radius)
        gradient.setColorAt(0.0, QColor("#0A1E2E"))
        gradient.setColorAt(0.5, QColor("#041219"))
        gradient.setColorAt(1.0, QColor(P.SPACE_VOID))

        painter.fillRect(rect, gradient)
        painter.end()
