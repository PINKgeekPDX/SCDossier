"""
src/ui/widgets/title_bar.py
CustomTitleBar — draggable window chrome for the main window.
"""

import logging
import os
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QLinearGradient, QIcon, QPixmap
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton

from src.ui.theme import palette as P
from src.ui.theme.fonts import label_caps, font_inter
from src.app.constants import APP_NAME, TITLEBAR_HEIGHT

log = logging.getLogger(__name__)

# Shared button base style
_BTN_BASE = (
    "QPushButton {{ color: {color}; font-size: 16px; border: none; "
    "background: {bg}; border-radius: 6px; }}"
    "QPushButton:hover {{ background: {hover_bg}; color: {hover_color}; }}"
    "QPushButton:pressed {{ background: {pressed_bg}; }}"
    "QPushButton:disabled {{ opacity: 0.4; }}"
)

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
_APP_ICON = os.path.join(_PROJECT_ROOT, "assets", "appicon.png")
_PIN_UNLOCKED_ICON = os.path.join(_PROJECT_ROOT, "assets", "icons", "ships", "default", "Unlock.png")
_PIN_LOCKED_ICON = os.path.join(_PROJECT_ROOT, "assets", "icons", "ships", "default", "Lock.png")
_HIDE_ICON = os.path.join(_PROJECT_ROOT, "assets", "icons", "ships", "default", "Return.png")

class CustomTitleBar(QWidget):
    pin_toggled = pyqtSignal(bool)
    hide_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(TITLEBAR_HEIGHT)
        self.setObjectName("CustomTitleBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

        self._pinned = False
        self._drag_active = False
        self._drag_start_pos = QPoint()
        self._drag_start_window_pos = QPoint()

        # Animation states
        self._anim_step = 0
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._update_animation)
        self._anim_timer.start(100) # every 100ms

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 12, 0)
        layout.setSpacing(0)

        # App Icon
        icon_lbl = QLabel()
        if os.path.exists(_APP_ICON):
            pix = QPixmap(_APP_ICON).scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon_lbl.setPixmap(pix)
        else:
            icon_lbl.setText("🚀")
        
        layout.addWidget(icon_lbl)
        layout.addSpacing(12)

        # Animated Title Label
        self._title_lbl = QLabel("SCD: Star Citizen Dossier")
        font = label_caps()
        font.setPointSize(10)
        font.setBold(True)
        self._title_lbl.setFont(font)
        self._title_lbl.setStyleSheet(f"color: {P.PRIMARY}; background: transparent; letter-spacing: 0.15em;")
        layout.addWidget(self._title_lbl)

        layout.addStretch(1)

        # Right: Pin + Hide buttons
        self._pin_btn = QPushButton()
        self._pin_btn.setProperty("class", "icon")
        self._pin_btn.setFixedSize(32, 32)
        self._pin_btn.setToolTip("Pin window (stay on top)")
        self._pin_btn.setCheckable(True)
        self._pin_btn.clicked.connect(self._on_pin_clicked)
        self._update_pin_style()

        self._hide_btn = QPushButton()
        self._hide_btn.setProperty("class", "icon")
        self._hide_btn.setFixedSize(32, 32)
        self._hide_btn.setToolTip("Hide (return to toolbar)")
        self._hide_btn.clicked.connect(self.hide_requested.emit)
        self._update_hide_style()

        layout.addSpacing(8)
        layout.addWidget(self._pin_btn)
        layout.addSpacing(4)
        layout.addWidget(self._hide_btn)

    def _update_animation(self):
        self._anim_step = (self._anim_step + 5) % 360
        # Slowly pulse brightness of primary color
        val = 0.5 + 0.5 * __import__("math").sin(self._anim_step * 3.14159 / 180.0)
        c = QColor(0, int(170 + 85*val), 255)
        self._title_lbl.setStyleSheet(f"color: {c.name()}; background: transparent; letter-spacing: 0.15em;")

    def _load_button_icon(self, btn: QPushButton, icon_path: str, fallback_text: str) -> None:
        from PyQt6.QtCore import QSize
        icon = QIcon()
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
        if not icon.isNull():
            btn.setIcon(icon)
            btn.setIconSize(QSize(20, 20))
            btn.setText("")
        else:
            btn.setText(fallback_text)
            btn.setIcon(QIcon())

    def _update_pin_style(self) -> None:
        icon_path = _PIN_LOCKED_ICON if self._pinned else _PIN_UNLOCKED_ICON
        self._load_button_icon(self._pin_btn, icon_path, "◈" if self._pinned else "◇")
        if self._pinned:
            self._pin_btn.setStyleSheet(_BTN_BASE.format(
                color=P.PRIMARY_CONTAINER, bg="rgba(0,170,255,0.20)",
                hover_bg="rgba(0,170,255,0.30)", hover_color=P.PRIMARY,
                pressed_bg="rgba(0,170,255,0.40)",
            ))
        else:
            self._pin_btn.setStyleSheet(_BTN_BASE.format(
                color=P.TEXT_DIM, bg="transparent",
                hover_bg="rgba(0,170,255,0.15)", hover_color=P.PRIMARY,
                pressed_bg="rgba(0,170,255,0.25)",
            ))

    def _update_hide_style(self) -> None:
        self._load_button_icon(self._hide_btn, _HIDE_ICON, "⊟")
        self._hide_btn.setStyleSheet(_BTN_BASE.format(
            color=P.TEXT_DIM, bg="transparent",
            hover_bg="rgba(255,59,59,0.15)", hover_color=P.HAZARD_RED,
            pressed_bg="rgba(255,59,59,0.25)",
        ))

    @property
    def is_pinned(self) -> bool:
        return self._pinned

    def _on_pin_clicked(self) -> None:
        self._pinned = not self._pinned
        self._update_pin_style()
        self._hide_btn.setEnabled(not self._pinned)
        if self._pinned:
            self._hide_btn.setToolTip("Unpin first to hide")
        else:
            self._hide_btn.setToolTip("Hide (return to toolbar)")
        self.pin_toggled.emit(self._pinned)

    def set_pinned(self, pinned: bool) -> None:
        if self._pinned != pinned:
            self._pinned = pinned
            self._update_pin_style()
            self._hide_btn.setEnabled(not pinned)

    def set_status(self, text: str, ok: bool = True) -> None:
        pass # Removed per request

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_active = True
            self._drag_start_pos = event.globalPosition().toPoint()
            if self.window():
                self._drag_start_window_pos = self.window().pos()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_active and self.window():
            delta = event.globalPosition().toPoint() - self._drag_start_pos
            self.window().move(self._drag_start_window_pos + delta)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._drag_active = False
        event.accept()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Darker background with gradient between darker blue and grey
        grad = QLinearGradient(0, 0, self.width(), 0)
        grad.setColorAt(0, QColor(4, 18, 30, 240)) # darker blue
        grad.setColorAt(1, QColor(35, 40, 45, 240)) # grey
        painter.fillRect(self.rect(), grad)

        # Bottom border
        pen = QPen(QColor(0, 170, 255, 38), 1)
        painter.setPen(pen)
        painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)

        painter.end()
