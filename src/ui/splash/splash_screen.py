"""
src/ui/splash/splash_screen.py
Animated custom splash screen with a progress bar and glow effect.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QProgressBar,
    QApplication
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QRectF, pyqtSignal
from PyQt6.QtGui import QPixmap, QColor, QPainter, QPainterPath, QRadialGradient

from src.core.paths import get_asset_path
from src.ui.theme.palette import PRIMARY_CONTAINER, GLASS_BG_DARK, ON_SURFACE, PRIMARY


class SplashScreen(QWidget):
    fade_out_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.SplashScreen
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(460, 294)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(0)

        # 1. Main Container (no graphics effect — glow is painted manually)
        self.container = QWidget(self)
        self.container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 2. Image Label
        self.image_lbl = QLabel()
        self.image_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_lbl.setFixedSize(400, 200)

        img_path = get_asset_path("assets/social_preview.png")
        pixmap = QPixmap(img_path)
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(
                400, 200,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            rounded = QPixmap(400, 200)
            rounded.fill(Qt.GlobalColor.transparent)

            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

            path = QPainterPath()
            path.setFillRule(Qt.FillRule.WindingFill)
            path.addRoundedRect(0, 0, 400, 200, 12, 12)
            path.addRect(0, 100, 400, 100)

            painter.setClipPath(path)
            painter.drawPixmap(0, 0, scaled_pixmap)
            painter.end()

            self.image_lbl.setPixmap(rounded)

        container_layout.addWidget(self.image_lbl)

        # 3. Status Block
        self.status_block = QWidget()
        self.status_block.setFixedWidth(400)
        self.status_block.setFixedHeight(34)
        self.status_block.setObjectName("SplashStatusBlock")
        self.status_block.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.status_block.setStyleSheet(f"""
            QWidget#SplashStatusBlock {{
                background-color: {GLASS_BG_DARK};
                border: 1px solid rgba(0, 170, 255, 0.3);
                border-top: none;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
            }}
        """)

        block_layout = QVBoxLayout(self.status_block)
        block_layout.setContentsMargins(16, 5, 16, 6)
        block_layout.setSpacing(3)

        self.status_lbl = QLabel("Initializing...")
        self.status_lbl.setStyleSheet(
            f"color: {ON_SURFACE}; font-family: 'Inter'; font-size: 11px; font-weight: 600;"
        )
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        block_layout.addWidget(self.status_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(5)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: rgba(0, 0, 0, 0.4);
                border: 1px solid rgba(0, 170, 255, 0.2);
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {PRIMARY};
                border-radius: 1px;
            }}
        """)
        block_layout.addWidget(self.progress_bar)

        container_layout.addWidget(self.status_block)
        layout.addWidget(self.container, alignment=Qt.AlignmentFlag.AlignCenter)

        # 4. Animations
        self.setWindowOpacity(0.0)
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(400)
        self.anim.finished.connect(self._on_anim_finished)
        self._fading_out = False

    def paintEvent(self, event):
        """Paint a radial glow behind the container, synchronously with all content."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Compute the container bounds in splash-local coords
        cr = self.container.geometry()
        cx = cr.x() + cr.width() / 2.0
        cy = cr.y() + cr.height() / 2.0
        radius = max(cr.width(), cr.height()) * 0.55

        glow_color = QColor(PRIMARY_CONTAINER)

        # Outer soft glow
        grad = QRadialGradient(cx, cy, radius)
        grad.setColorAt(0.0, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 55))
        grad.setColorAt(0.5, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 18))
        grad.setColorAt(1.0, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 0))
        painter.fillRect(self.rect(), grad)

        painter.end()

        super().paintEvent(event)

    def update_progress(self, text: str, value: int):
        self.status_lbl.setText(text)
        self.progress_bar.setValue(value)
        QApplication.processEvents()

    def fade_in(self):
        self._fading_out = False
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self.activateWindow()
        self.repaint()
        QApplication.processEvents()
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()
        self.wait_for_animation()

    def fade_out(self):
        self._fading_out = True
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.start()
        self.wait_for_animation()

    def wait_for_animation(self):
        import time
        while self.anim.state() == QPropertyAnimation.State.Running:
            QApplication.processEvents()
            time.sleep(0.01)

    def _on_anim_finished(self):
        if self._fading_out:
            self.fade_out_finished.emit()
