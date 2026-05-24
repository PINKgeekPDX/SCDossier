import logging
from pathlib import Path
from datetime import datetime

from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QPixmap, QScreen
from PyQt6.QtWidgets import QWidget, QApplication, QRubberBand

from src.core.paths import PathManager

log = logging.getLogger(__name__)


class RegionSelector(QWidget):
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
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._start_pos = QPoint()
        self._current_rect = QRect()
        self._is_dragging = False

        self._full_screen_pixmap = QPixmap()
        self._grab_desktop()

    def _grab_desktop(self) -> None:
        # Get primary screen geometry
        screen = QApplication.primaryScreen()
        if not screen:
            return

        geo = screen.geometry()
        # Set the overlay to cover only the primary screen for reliable coordinate mapping
        self._virtual_rect = geo
        self.setGeometry(geo)

        # Grab the entire desktop (root window 0 captures all monitors)
        self._full_screen_pixmap = screen.grabWindow(0)

        # The root window pixmap may span multiple monitors. We need to use the portion
        # that corresponds to our overlay widget (the primary screen).
        # If the primary screen is at a non-zero position in the virtual desktop, offset
        # within the root window pixmap accordingly.
        if not self._full_screen_pixmap.isNull():
            px = self._full_screen_pixmap
            if geo.x() >= 0 and geo.y() >= 0 and geo.width() > 0 and geo.height() > 0:
                if (geo.x() + geo.width() <= px.width() and
                        geo.y() + geo.height() <= px.height()):
                    self._full_screen_pixmap = px.copy(
                        geo.x(), geo.y(), geo.width(), geo.height()
                    )
                else:
                    # Pixmap doesn't cover the required offset; crop from top-left
                    self._full_screen_pixmap = px.copy(0, 0, geo.width(), geo.height())
            else:
                # Primary screen has negative coordinates — just grab primary screen directly
                self._full_screen_pixmap = screen.grabWindow(0, 0, 0, geo.width(), geo.height())
            log.debug(
                "RegionSelector: geo=%s, pixmap after crop=%s",
                geo, self._full_screen_pixmap.size(),
            )

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.capture_cancelled.emit()
            self.close()
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_pos = self.mapFromGlobal(event.globalPosition().toPoint())
            self._current_rect = QRect(self._start_pos, self._start_pos)
            self._is_dragging = True
            self.update()

    def mouseMoveEvent(self, event) -> None:
        if self._is_dragging:
            cur = self.mapFromGlobal(event.globalPosition().toPoint())
            self._current_rect = QRect(self._start_pos, cur).normalized()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._is_dragging:
            self._is_dragging = False
            cur = self.mapFromGlobal(event.globalPosition().toPoint())
            self._current_rect = QRect(self._start_pos, cur).normalized()

            if self._current_rect.width() > 10 and self._current_rect.height() > 10:
                self._process_capture()
            else:
                self.capture_cancelled.emit()
            self.close()

    def _process_capture(self) -> None:
        if self._full_screen_pixmap.isNull():
            self.capture_cancelled.emit()
            return

        cropped = self._full_screen_pixmap.copy(self._current_rect)

        if cropped.isNull():
            log.error("Cropped pixmap is null (rect may be outside desktop bounds)")
            self.capture_cancelled.emit()
            return

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

        painter.fillRect(self.rect(), QColor(0, 0, 0, 150))

        if self._is_dragging and self._current_rect.isValid():
            if not self._full_screen_pixmap.isNull():
                painter.drawPixmap(
                    self._current_rect,
                    self._full_screen_pixmap,
                    self._current_rect
                )

            pen = QPen(QColor(0, 170, 255, 200), 1)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self._current_rect)

            s = 6
            painter.setPen(QPen(QColor(0, 170, 255), 2))
            x0, y0 = self._current_rect.left(), self._current_rect.top()
            x1, y1 = self._current_rect.right(), self._current_rect.bottom()
            painter.drawLine(x0, y0, x0+s, y0); painter.drawLine(x0, y0, x0, y0+s)
            painter.drawLine(x1-s, y0, x1, y0); painter.drawLine(x1, y0, x1, y0+s)
            painter.drawLine(x0, y1, x0+s, y1); painter.drawLine(x0, y1-s, x0, y1)
            painter.drawLine(x1-s, y1, x1, y1); painter.drawLine(x1, y1-s, x1, y1)

        painter.end()

    def showEvent(self, event) -> None:
        self._grab_desktop()
        super().showEvent(event)
