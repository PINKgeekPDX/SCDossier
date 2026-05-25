"""
src/ui/widgets/avatar_widget.py
AvatarWidget — image display with tech-bracket corner overlay.

Displays a player avatar or org logo with the Aegis bracket ornaments
painted over the image. Shows a placeholder icon when no image is set.
"""

from pathlib import Path
from PyQt6.QtCore import Qt, QSize, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QPixmap, QBrush, QPainterPath, QFont
from PyQt6.QtWidgets import QWidget

from src.ui.theme import palette as P


class AvatarWidget(QWidget):
    """
    Displays a square image with tech-bracket corner ornaments.

    Args:
        size:       Widget size in pixels (square). Default 90 (was 120).
        parent:     Parent widget.
    """

    def __init__(self, size: int = 90, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._size = size
        self._pixmap: QPixmap | None = None
        self._image_path: str | Path | None = None
        self._original_pixmap: QPixmap | None = None
        self.setFixedSize(QSize(size, size))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_image(self, path: str | Path | None) -> None:
        """
        Load and display an image from a file path.
        Pass None to clear and show placeholder.
        """
        self._image_path = path
        self._original_pixmap = None
        if path is None:
            self._pixmap = None
            self.update()
            return

        pix = QPixmap(str(path))
        if pix.isNull():
            self._pixmap = None
        else:
            self._pixmap = pix.scaled(
                self._size, self._size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        self.update()

    def set_pixmap(self, pixmap: QPixmap | None) -> None:
        """Set a pixmap directly."""
        self._original_pixmap = pixmap
        self._image_path = None
        if pixmap and not pixmap.isNull():
            self._pixmap = pixmap.scaled(
                self._size, self._size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            self._pixmap = None
        self.update()

    def clear(self) -> None:
        """Reset to placeholder."""
        self._image_path = None
        self._original_pixmap = None
        self._pixmap = None
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            pix = None
            if self._original_pixmap and not self._original_pixmap.isNull():
                pix = self._original_pixmap
            elif self._image_path:
                pix = QPixmap(str(self._image_path))
                
            if pix and not pix.isNull():
                from src.ui.widgets.image_preview import show_image_preview
                origin = self.mapToGlobal(self.rect().center())
                show_image_preview(pix, self, origin)
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        radius = 3   # was 4

        if self._pixmap:
            # Clip to rounded rect
            path = QPainterPath()
            path.addRoundedRect(
                float(rect.x()), float(rect.y()),
                float(rect.width()), float(rect.height()),
                radius, radius
            )
            painter.setClipPath(path)
            # Center-crop the pixmap
            src_w = self._pixmap.width()
            src_h = self._pixmap.height()
            x_off = max(0, (src_w - self._size) // 2)
            y_off = max(0, (src_h - self._size) // 2)
            painter.drawPixmap(rect, self._pixmap, QRect(x_off, y_off, self._size, self._size))
            painter.setClipping(False)
        else:
            # Placeholder background
            painter.fillRect(rect, QColor(15, 33, 46))
            # Placeholder icon — user silhouette symbol
            painter.setPen(QColor(P.TEXT_DIM))
            f = QFont("Segoe UI Symbol", self._size // 3)
            painter.setFont(f)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "◎")

        # Tech bracket corners
        self._draw_brackets(painter, rect)

        # Border
        pen = QPen(QColor(0, 170, 255, 45), 1)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(0, 0, -1, -1), radius, radius)

        painter.end()

    def _draw_brackets(self, painter: QPainter, rect: QRect) -> None:
        bracket_size = max(4, min(6, self._size // 10))   # slightly smaller brackets
        pen = QPen(QColor(P.BRACKET_COLOR), P.BRACKET_WIDTH)
        pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        x0, y0 = rect.left(), rect.top()
        x1, y1 = rect.right(), rect.bottom()

        painter.drawLine(x0, y0, x0 + bracket_size, y0)
        painter.drawLine(x0, y0, x0, y0 + bracket_size)

        painter.drawLine(x1 - bracket_size, y0, x1, y0)
        painter.drawLine(x1, y0, x1, y0 + bracket_size)

        painter.drawLine(x0, y1, x0 + bracket_size, y1)
        painter.drawLine(x0, y1 - bracket_size, x0, y1)

        painter.drawLine(x1 - bracket_size, y1, x1, y1)
        painter.drawLine(x1, y1 - bracket_size, x1, y1)
