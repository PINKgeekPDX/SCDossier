import logging
from pathlib import Path
from datetime import datetime

from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QPixmap, QScreen, QFont, QFontMetrics, QBrush
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
        self.setMouseTracking(True)

        self._start_pos = QPoint()
        self._mouse_pos = QPoint(-1, -1)
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
        self.setGeometry(geo)

        # Grab the primary screen directly using its device-independent coordinates.
        # This returns a physical pixel pixmap.
        self._full_screen_pixmap = screen.grabWindow(0, geo.x(), geo.y(), geo.width(), geo.height())
        log.debug(
            "RegionSelector: geo=%s, dpr=%s, pixmap size=%s",
            geo, self.devicePixelRatio(), self._full_screen_pixmap.size(),
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
        self._mouse_pos = self.mapFromGlobal(event.globalPosition().toPoint())
        if self._is_dragging:
            self._current_rect = QRect(self._start_pos, self._mouse_pos).normalized()
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

        # self._current_rect is in device-independent pixels; scale to physical pixels for cropping
        dpr = self.devicePixelRatio()
        physical_rect = QRect(
            int(self._current_rect.x() * dpr),
            int(self._current_rect.y() * dpr),
            int(self._current_rect.width() * dpr),
            int(self._current_rect.height() * dpr)
        )
        cropped = self._full_screen_pixmap.copy(physical_rect)

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
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Draw darkened background
        painter.fillRect(self.rect(), QColor(0, 0, 0, 160))

        dpr = self.devicePixelRatio()

        # If dragging, draw the selected area and its glowing border
        if self._is_dragging and self._current_rect.isValid():
            if not self._full_screen_pixmap.isNull():
                physical_rect = QRect(
                    int(self._current_rect.x() * dpr),
                    int(self._current_rect.y() * dpr),
                    int(self._current_rect.width() * dpr),
                    int(self._current_rect.height() * dpr)
                )
                painter.drawPixmap(self._current_rect, self._full_screen_pixmap, physical_rect)

            # Draw sleek glowing border
            pen = QPen(QColor(0, 170, 255, 230), 1)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self._current_rect)

            # Draw thicker corner handles
            s = 8
            painter.setPen(QPen(QColor(0, 255, 200), 2))
            x0, y0 = self._current_rect.left(), self._current_rect.top()
            x1, y1 = self._current_rect.right(), self._current_rect.bottom()
            painter.drawLine(x0, y0, x0+s, y0); painter.drawLine(x0, y0, x0, y0+s)
            painter.drawLine(x1-s, y0, x1, y0); painter.drawLine(x1, y0, x1, y0+s)
            painter.drawLine(x0, y1, x0+s, y1); painter.drawLine(x0, y1-s, x0, y1)
            painter.drawLine(x1-s, y1, x1, y1); painter.drawLine(x1, y1-s, x1, y1)

            # Draw dimensions HUD
            font = QFont("Inter", 9, QFont.Weight.Bold)
            painter.setFont(font)
            hud_text = f" W: {self._current_rect.width()}  H: {self._current_rect.height()} "
            fm = QFontMetrics(font)
            hud_rect = QRect(x0, y1 + 5, fm.horizontalAdvance(hud_text) + 10, fm.height() + 6)
            if hud_rect.bottom() > self.height():
                hud_rect.moveBottom(y0 - 5)
            
            painter.fillRect(hud_rect, QColor(20, 25, 30, 220))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(hud_rect, Qt.AlignmentFlag.AlignCenter, hud_text)
            painter.setPen(QPen(QColor(0, 170, 255), 1))
            painter.drawRect(hud_rect)

        # Draw full-screen crosshairs if mouse is on screen
        if self._mouse_pos.x() >= 0 and self._mouse_pos.y() >= 0:
            mx, my = self._mouse_pos.x(), self._mouse_pos.y()
            painter.setPen(QPen(QColor(0, 170, 255, 120), 1, Qt.PenStyle.DashLine))
            painter.drawLine(0, my, self.width(), my)
            painter.drawLine(mx, 0, mx, self.height())

            # Magnifier Logic
            if not self._full_screen_pixmap.isNull():
                mag_size = 120
                zoom = 2.5
                
                # Source rect around cursor
                src_w = int(mag_size / zoom)
                src_x = int(mx * dpr) - src_w // 2
                src_y = int(my * dpr) - src_w // 2
                src_rect = QRect(src_x, src_y, src_w, src_w)
                
                mag_img = self._full_screen_pixmap.copy(src_rect)
                
                # Destination for magnifier (bottom right offset)
                offset = 20
                dst_x = mx + offset
                dst_y = my + offset
                
                # Keep magnifier on screen
                if dst_x + mag_size > self.width():
                    dst_x = mx - mag_size - offset
                if dst_y + mag_size > self.height():
                    dst_y = my - mag_size - offset
                    
                dst_rect = QRect(dst_x, dst_y, mag_size, mag_size)
                
                # Draw the magnified image
                painter.drawPixmap(dst_rect, mag_img, mag_img.rect())
                
                # Draw magnifier border and center cross
                painter.setPen(QPen(QColor(0, 170, 255), 2))
                painter.drawRect(dst_rect)
                
                cx, cy = dst_rect.center().x(), dst_rect.center().y()
                painter.setPen(QPen(QColor(255, 0, 50, 200), 1))
                painter.drawLine(cx - 5, cy, cx + 5, cy)
                painter.drawLine(cx, cy - 5, cx, cy + 5)

        painter.end()

    def showEvent(self, event) -> None:
        self._grab_desktop()
        super().showEvent(event)
