"""
src/ui/widgets/progress_overlay.py
ProgressOverlay — semi-transparent scanning animation shown during scrape operations.

Covers the parent widget area with a dim overlay and an animated scanline.
"""

from PyQt6.QtCore import Qt, QTimer, QRect, QRectF
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QBrush, QPen, QPainterPath
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

from src.ui.theme import palette as P
from src.ui.theme.fonts import label_caps, font_inter


class ProgressOverlay(QWidget):
    """
    Full-area semi-transparent overlay with:
    - Dark glassmorphism backdrop
    - Animated horizontal scanline
    - Status text label

    Usage:
        overlay = ProgressOverlay(parent=tab_widget)
        overlay.set_message("RETRIEVING CITIZEN PROFILE...")
        overlay.show_overlay()
        # ... when done:
        overlay.hide_overlay()
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ProgressOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.hide()

        self._scan_y = 0.0
        self._scan_direction = 1

        self._build_ui()
        self._setup_animation()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)   # was 16

        self._status_label = QLabel("RETRIEVING DATA...")
        self._status_label.setFont(label_caps())
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet(
            f"color: {P.PRIMARY}; background: transparent; letter-spacing: 0.20em;"
        )

        self._sub_label = QLabel("ACCESSING RSI NETWORK")
        self._sub_label.setFont(font_inter(10))   # was 12
        self._sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sub_label.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent;")

        layout.addWidget(self._status_label)
        layout.addWidget(self._sub_label)

    def _setup_animation(self) -> None:
        """Scanline animation using QTimer."""
        self._scan_timer = QTimer(self)
        self._scan_timer.timeout.connect(self._advance_scanline)
        self._scan_timer.setInterval(16)  # ~60fps

    def _advance_scanline(self) -> None:
        self._scan_y += self._scan_direction * 3.0
        h = float(self.height())
        if self._scan_y >= h:
            self._scan_y = h
            self._scan_direction = -1
        elif self._scan_y <= 0:
            self._scan_y = 0
            self._scan_direction = 1
        self.update()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_message(self, message: str, sub: str = "") -> None:
        """Update the status text."""
        self._status_label.setText(message.upper())
        self._sub_label.setText(sub.upper() if sub else "ACCESSING RSI NETWORK")

    def show_overlay(self) -> None:
        """Show the overlay and start the scanline animation."""
        if self.parent():
            self.setGeometry(self.parent().rect())
        self.raise_()
        self.show()
        self._scan_y = 0.0
        self._scan_timer.start()

    def hide_overlay(self) -> None:
        """Hide the overlay and stop animation."""
        self._scan_timer.stop()
        self.hide()

    def resizeEvent(self, event) -> None:
        if self.parent():
            self.setGeometry(self.parent().rect())
        super().resizeEvent(event)

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        w, h = rect.width(), rect.height()

        # --- Dark overlay backdrop ---
        painter.fillRect(rect, QColor(3, 21, 33, 210))

        # --- Scanline beam ---
        if self._scan_y > 0 and self._scan_y < h:
            beam_h = 60   # was 80
            grad = QLinearGradient(0, self._scan_y - beam_h, 0, self._scan_y + beam_h)
            grad.setColorAt(0.0, QColor(0, 170, 255, 0))
            grad.setColorAt(0.4, QColor(0, 170, 255, 30))
            grad.setColorAt(0.5, QColor(0, 170, 255, 60))
            grad.setColorAt(0.6, QColor(0, 170, 255, 30))
            grad.setColorAt(1.0, QColor(0, 170, 255, 0))
            painter.fillRect(
                QRect(0, max(0, int(self._scan_y) - beam_h), w, beam_h * 2),
                QBrush(grad),
            )

            # Scanline core line
            pen = QPen(QColor(0, 170, 255, 120), 1)
            painter.setPen(pen)
            painter.drawLine(0, int(self._scan_y), w, int(self._scan_y))

        # --- Center glass panel ---
        panel_w = min(320, w - 60)   # was 380, w-80
        panel_h = 90                  # was 120
        panel_x = (w - panel_w) // 2
        panel_y = (h - panel_h) // 2
        panel_rect = QRect(panel_x, panel_y, panel_w, panel_h)

        # Clip to rounded rect
        clip_path = QPainterPath()
        clip_path.addRoundedRect(QRectF(panel_rect), 4, 4)
        painter.setClipPath(clip_path)

        painter.setBrush(QColor(10, 29, 41, 180))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(panel_rect)

        painter.setClipping(False)

        # Panel border
        painter.setPen(QPen(QColor(0, 170, 255, 60), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(panel_rect), 4, 4)

        # Bracket corners on panel
        s = 6   # was 8
        pen = QPen(QColor(P.BRACKET_COLOR), 1.5)   # was 2
        pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        painter.setPen(pen)
        x0, y0 = panel_rect.left(), panel_rect.top()
        x1, y1 = panel_rect.right(), panel_rect.bottom()
        for px, py, dx, dy in [(x0,y0,1,1),(x1,y0,-1,1),(x0,y1,1,-1),(x1,y1,-1,-1)]:
            painter.drawLine(px, py, px + dx*s, py)
            painter.drawLine(px, py, px, py + dy*s)

        painter.end()
