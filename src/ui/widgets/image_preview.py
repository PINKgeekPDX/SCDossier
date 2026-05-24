"""
src/ui/widgets/image_preview.py
ImagePreviewDialog — popup to view larger versions of images.
"""

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel

from src.ui.theme import palette as P

class ImagePreviewDialog(QDialog):
    """
    A frameless, modal dialog that displays a full-size image preview.
    Clicking anywhere on the dialog closes it.
    """
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)

        # Scale image if it's too large for the screen
        screen_geo = self.screen().availableGeometry()
        max_w = int(screen_geo.width() * 0.8)
        max_h = int(screen_geo.height() * 0.8)

        if pixmap.width() > max_w or pixmap.height() > max_h:
            pixmap = pixmap.scaled(
                max_w, max_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

        self._pixmap = pixmap
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        
        self.label = QLabel()
        self.label.setPixmap(self._pixmap)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        
        self.resize(self._pixmap.width() + 24, self._pixmap.height() + 24)

    def mousePressEvent(self, event):
        """Close on click."""
        self.accept()

    def paintEvent(self, event):
        """Draw a dark background with a tech border."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect().adjusted(0, 0, -1, -1)
        
        # Dark overlay background
        painter.setBrush(QColor(10, 15, 20, 240))
        pen = QPen(QColor(P.PRIMARY), 1)
        painter.setPen(pen)
        
        radius = 8
        painter.drawRoundedRect(rect, radius, radius)
        
        # Corner accents
        accent_size = 15
        painter.setPen(QPen(QColor(P.PRIMARY), 2))
        
        # Top-Left
        painter.drawLine(rect.left(), rect.top() + accent_size, rect.left(), rect.top() + radius)
        painter.drawLine(rect.left() + radius, rect.top(), rect.left() + accent_size, rect.top())
        
        # Top-Right
        painter.drawLine(rect.right(), rect.top() + accent_size, rect.right(), rect.top() + radius)
        painter.drawLine(rect.right() - radius, rect.top(), rect.right() - accent_size, rect.top())
        
        # Bottom-Left
        painter.drawLine(rect.left(), rect.bottom() - accent_size, rect.left(), rect.bottom() - radius)
        painter.drawLine(rect.left() + radius, rect.bottom(), rect.left() + accent_size, rect.bottom())
        
        # Bottom-Right
        painter.drawLine(rect.right(), rect.bottom() - accent_size, rect.right(), rect.bottom() - radius)
        painter.drawLine(rect.right() - radius, rect.bottom(), rect.right() - accent_size, rect.bottom())
        
        painter.end()
