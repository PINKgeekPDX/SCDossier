"""
src/ui/widgets/image_preview.py
ImagePreviewDialog — frameless overlay-style image popout.

Pops out near the origin widget position, dismisses on any click
anywhere on screen via a Qt.WindowType.Popup flag.
"""

from PyQt6.QtCore import Qt, QPoint, QRect, QSize
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QScreen
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication

from src.ui.theme import palette as P


class ImagePreviewDialog(QWidget):
    """
    A frameless overlay-style popout that displays a full-size image preview.

    Uses Qt.WindowType.Popup so it automatically closes when the user
    clicks anywhere outside it. Also closes on click inside.

    Args:
        pixmap:     The image to display.
        parent:     The widget that triggered the preview (used for origin_pos).
        origin_pos: Global screen position near which to show the popout.
                    If None, uses parent.mapToGlobal(center) or screen center.
    """

    def __init__(
        self,
        pixmap: QPixmap,
        parent: QWidget | None = None,
        origin_pos: QPoint | None = None,
    ) -> None:
        # Use Popup flag — Qt auto-dismisses on outside click; no parent ownership
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        # --- Determine target screen from origin ---
        screen: QScreen | None = None
        if origin_pos is not None:
            screen = QApplication.screenAt(origin_pos)
        if screen is None and parent is not None:
            screen = parent.screen()
        if screen is None:
            screen = QApplication.primaryScreen()

        screen_geo: QRect = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)

        # --- Scale image dynamically for a clear, larger preview ---
        max_w = int(screen_geo.width() * 0.92)
        max_h = int(screen_geo.height() * 0.92)

        # Scale up small images (like standard 150x150 avatars) to at least 512px
        target_size = 512
        w, h = pixmap.width(), pixmap.height()
        if w > 0 and h > 0:
            if w < target_size and h < target_size:
                factor = target_size / min(w, h)
                w = int(w * factor)
                h = int(h * factor)

        # Clamp/scale down if it exceeds the maximum screen boundaries
        if w > max_w or h > max_h:
            factor = min(max_w / w, max_h / h)
            w = int(w * factor)
            h = int(h * factor)

        if w > 0 and h > 0 and (w != pixmap.width() or h != pixmap.height()):
            pixmap = pixmap.scaled(
                w, h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

        self._pixmap = pixmap

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.label = QLabel()
        self.label.setPixmap(self._pixmap)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        dialog_w = self._pixmap.width() + 20
        dialog_h = self._pixmap.height() + 20
        self.resize(dialog_w, dialog_h)

        # --- Position near origin, clamped to screen ---
        self._position_near(origin_pos, parent, screen_geo, dialog_w, dialog_h)

    def _position_near(
        self,
        origin_pos: QPoint | None,
        parent: QWidget | None,
        screen_geo: QRect,
        dw: int,
        dh: int,
    ) -> None:
        """Position the dialog near the origin point, keeping it on screen."""
        if origin_pos is not None:
            ox, oy = origin_pos.x(), origin_pos.y()
        elif parent is not None:
            center = parent.rect().center()
            global_center = parent.mapToGlobal(center)
            ox, oy = global_center.x(), global_center.y()
        else:
            ox = screen_geo.center().x()
            oy = screen_geo.center().y()

        # Try to center the dialog on the origin point, then clamp to screen
        x = ox - dw // 2
        y = oy - dh // 2

        # Clamp to screen bounds
        x = max(screen_geo.left(), min(x, screen_geo.right() - dw))
        y = max(screen_geo.top(), min(y, screen_geo.bottom() - dh))

        self.move(x, y)

    # ── Events ────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        """Close on any click inside the dialog."""
        self.close()

    def keyPressEvent(self, event) -> None:
        """Close on Escape."""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        """Clear active global preview reference on close."""
        global _active_preview
        _active_preview = None
        super().closeEvent(event)

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:
        """Draw dark background with 2px accent border and corner accents."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(0, 0, -1, -1)
        radius = 6

        # Dark overlay background
        painter.setBrush(QColor(8, 14, 20, 245))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, radius, radius)

        # 2px accent border
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(P.PRIMARY), 2))
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), radius, radius)

        # Corner bracket accents
        accent_size = 18
        painter.setPen(QPen(QColor(P.PRIMARY_CONTAINER), 2))

        # Top-left
        painter.drawLine(rect.left() + 1, rect.top() + radius, rect.left() + 1, rect.top() + accent_size)
        painter.drawLine(rect.left() + radius, rect.top() + 1, rect.left() + accent_size, rect.top() + 1)
        # Top-right
        painter.drawLine(rect.right() - 1, rect.top() + radius, rect.right() - 1, rect.top() + accent_size)
        painter.drawLine(rect.right() - radius, rect.top() + 1, rect.right() - accent_size, rect.top() + 1)
        # Bottom-left
        painter.drawLine(rect.left() + 1, rect.bottom() - radius, rect.left() + 1, rect.bottom() - accent_size)
        painter.drawLine(rect.left() + radius, rect.bottom() - 1, rect.left() + accent_size, rect.bottom() - 1)
        # Bottom-right
        painter.drawLine(rect.right() - 1, rect.bottom() - radius, rect.right() - 1, rect.bottom() - accent_size)
        painter.drawLine(rect.right() - radius, rect.bottom() - 1, rect.right() - accent_size, rect.bottom() - 1)

        painter.end()


# Keep a global reference to prevent garbage collection of the modeless Popup window
_active_preview = None


def show_image_preview(
    pixmap: QPixmap,
    parent: QWidget | None = None,
    origin_pos: QPoint | None = None,
) -> None:
    """
    Convenience function — show the overlay preview and return immediately.
    The dialog owns itself (WA_DeleteOnClose) and dismisses on any click.
    """
    global _active_preview
    if pixmap.isNull():
        return
    # Close any existing active preview first
    if _active_preview:
        try:
            _active_preview.close()
        except Exception:
            pass
            
    _active_preview = ImagePreviewDialog(pixmap, parent, origin_pos)
    _active_preview.show()
    _active_preview.raise_()
    _active_preview.activateWindow()
