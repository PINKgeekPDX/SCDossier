"""
src/ui/splash/splash_screen.py
Animated custom splash screen with a progress bar and glow effect.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QProgressBar, 
    QGraphicsDropShadowEffect, QApplication
)
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtSignal
from PyQt6.QtGui import QPixmap, QColor, QPainter, QPainterPath

from src.core.paths import get_asset_path
from src.ui.theme.palette import PRIMARY_CONTAINER, GLASS_BG_DARK, ON_SURFACE, PRIMARY

class SplashScreen(QWidget):
    # Emitted when the fade-out animation is fully complete
    fade_out_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        # Set flags: Splash screen and frameless
        self.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.setFixedSize(440, 265)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(0)

        # 1. Image Label
        self.image_lbl = QLabel()
        self.image_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_lbl.setFixedSize(400, 225)
        
        img_path = get_asset_path("assets/social_preview.png")
        pixmap = QPixmap(img_path)
        if not pixmap.isNull():
            # Scale down
            scaled_pixmap = pixmap.scaled(
                400, 225, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_lbl.setPixmap(scaled_pixmap)

        # Glow Effect on Image
        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(25)
        glow.setColor(QColor(PRIMARY_CONTAINER))
        glow.setOffset(0, 0)
        self.image_lbl.setGraphicsEffect(glow)
        
        layout.addWidget(self.image_lbl, alignment=Qt.AlignmentFlag.AlignHCenter)

        # 2. Status Block - overlayed on the bottom of the image label
        self.status_block = QWidget(self.image_lbl)
        self.status_block.setFixedWidth(360)
        self.status_block.setFixedHeight(40)
        self.status_block.move(20, 168)
        self.status_block.setObjectName("SplashStatusBlock")
        # Paint the status block with glass background using StyleSheet
        self.status_block.setStyleSheet(f"""
            QWidget#SplashStatusBlock {{
                background-color: {GLASS_BG_DARK};
                border: 1px solid rgba(0, 170, 255, 0.3);
                border-radius: 6px;
            }}
        """)
        
        block_layout = QVBoxLayout(self.status_block)
        block_layout.setContentsMargins(12, 6, 12, 8)
        block_layout.setSpacing(4)

        # Status Label
        self.status_lbl = QLabel("Initializing...")
        self.status_lbl.setStyleSheet(f"color: {ON_SURFACE}; font-family: 'Inter'; font-size: 11px; font-weight: 600;")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        block_layout.addWidget(self.status_lbl)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: rgba(0, 0, 0, 0.4);
                border: 1px solid rgba(0, 170, 255, 0.2);
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {PRIMARY};
                border-radius: 2px;
            }}
        """)
        block_layout.addWidget(self.progress_bar)

        # 3. Setup Animations
        self.setWindowOpacity(0.0)
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(400) # 400ms fade
        self.anim.finished.connect(self._on_anim_finished)
        self._fading_out = False

    def update_progress(self, text: str, value: int):
        self.status_lbl.setText(text)
        self.progress_bar.setValue(value)
        QApplication.processEvents()

    def fade_in(self):
        self._fading_out = False
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.show()
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
