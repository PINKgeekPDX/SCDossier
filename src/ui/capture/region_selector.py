"""
src/ui/capture/region_selector.py
RegionSelector — fullscreen transparent overlay for OCR screen capture.

Dims the screen and allows the user to drag a rectangle (QRubberBand).
Upon release, captures that specific screen region, saves it to the temp cache,
and emits the file path for the OCR service to process.
"""

import logging
from pathlib import Path
from datetime import datetime

from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QPixmap, QScreen
from PyQt6.QtWidgets import QWidget, QApplication, QRubberBand

from src.core.paths import PathManager

log = logging.getLogger(__name__)


class RegionSelector(QWidget):
    """
    Fullscreen overlay that captures a user-selected screen region.

    Signals:
        capture_completed(Path): Emitted when a region is selected and saved.
        capture_cancelled():     Emitted if the user presses Escape or clicks without dragging.
    """

    capture_completed = pyqtSignal(Path)
    capture_cancelled = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._start_pos = QPoint()
        self._current_rect = QRect()
        self._is_dragging = False

        # Grab the full screen geometry
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())
            self._full_screen_pixmap = screen.grabWindow(0)
        else:
            self._full_screen_pixmap = QPixmap()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.capture_cancelled.emit()
            self.close()
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_pos = event.globalPosition().toPoint()
            self._current_rect = QRect(self._start_pos, self._start_pos)
            self._is_dragging = True
            self.update()

    def mouseMoveEvent(self, event) -> None:
        if self._is_dragging:
            self._current_rect = QRect(self._start_pos, event.globalPosition().toPoint()).normalized()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._is_dragging:
            self._is_dragging = False
            self._current_rect = QRect(self._start_pos, event.globalPosition().toPoint()).normalized()

            if self._current_rect.width() > 10 and self._current_rect.height() > 10:
                self._process_capture()
            else:
                self.capture_cancelled.emit()
            self.close()

    def _process_capture(self) -> None:
        """Crop the screen pixmap to the selected region and save it."""
        if self._full_screen_pixmap.isNull():
            self.capture_cancelled.emit()
            return

        cropped = self._full_screen_pixmap.copy(self._current_rect)

        paths = PathManager.instance()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = paths.ocr_captures_dir() / f"capture_{timestamp}.png"

        if cropped.save(str(out_path), "PNG"):
            log.info("Region captured and saved to: %s", out_path)
            self.capture_completed.emit(out_path)
        else:
            log.error("Failed to save capture to: %s", out_path)
            self.capture_cancelled.emit()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # Draw the darkened background
        painter.fillRect(self.rect(), QColor(0, 0, 0, 150))

        if self._is_dragging and self._current_rect.isValid():
            # "Punch a hole" in the dark overlay by drawing the original bright pixmap over the rect
            if not self._full_screen_pixmap.isNull():
                painter.drawPixmap(self._current_rect, self._full_screen_pixmap, self._current_rect)

            # Draw the Aegis blue border around the selection
            pen = QPen(QColor(0, 170, 255, 200), 1)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self._current_rect)

            # Draw small corner markers for the "HUD" feel
            s = 6
            painter.setPen(QPen(QColor(0, 170, 255), 2))
            x0, y0 = self._current_rect.left(), self._current_rect.top()
            x1, y1 = self._current_rect.right(), self._current_rect.bottom()
            # Top-left
            painter.drawLine(x0, y0, x0+s, y0); painter.drawLine(x0, y0, x0, y0+s)
            # Top-right
            painter.drawLine(x1-s, y0, x1, y0); painter.drawLine(x1, y0, x1, y0+s)
            # Bottom-left
            painter.drawLine(x0, y1, x0+s, y1); painter.drawLine(x0, y1-s, x0, y1)
            # Bottom-right
            painter.drawLine(x1-s, y1, x1, y1); painter.drawLine(x1, y1-s, x1, y1)

        painter.end()

    def showEvent(self, event) -> None:
        # Re-grab the screen just in case something changed before showing
        screen = QApplication.primaryScreen()
        if screen:
            self._full_screen_pixmap = screen.grabWindow(0)
        super().showEvent(event)
