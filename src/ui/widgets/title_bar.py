"""
src/ui/widgets/title_bar.py
CustomTitleBar — draggable window chrome for the main window.
"""

import logging
import os
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QPainter, QColor, QPen, QLinearGradient, QIcon, QPixmap
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton

from src.ui.theme import palette as P
from src.ui.theme.fonts import label_caps, font_inter
from src.app.constants import APP_NAME, TITLEBAR_HEIGHT

log = logging.getLogger(__name__)

# Shared button base style
_BTN_BASE = (
    "QPushButton {{ color: {color}; font-size: 14px; border: none; "
    "background: {bg}; border-radius: 4px; }}"
    "QPushButton:hover {{ background: {hover_bg}; color: {hover_color}; }}"
    "QPushButton:pressed {{ background: {pressed_bg}; }}"
    "QPushButton:disabled {{ opacity: 0.4; }}"
)

# Clear results button style (yellow hover)
_CLEAR_BTN_BASE = (
    "QPushButton {{ color: {color}; font-size: 14px; border: none; "
    "background: {bg}; border-radius: 4px; }}"
    "QPushButton:hover {{ background: {hover_bg}; color: {hover_color}; }}"
    "QPushButton:pressed {{ background: {pressed_bg}; }}"
    "QPushButton:disabled {{ opacity: 0.4; }}"
)

from src.core.paths import get_asset_path

_APP_ICON = get_asset_path("assets/appicon.png")
_PIN_UNLOCKED_ICON = get_asset_path("assets/icons/ships/default/Unlock.png")
_PIN_LOCKED_ICON = get_asset_path("assets/icons/ships/default/Lock.png")
_HIDE_ICON = get_asset_path("assets/icons/ships/default/Return.png")
_CLEAR_ICON = get_asset_path("assets/icons/Icons/default/RESET_Text.png")

class CustomTitleBar(QWidget):
    pin_toggled = pyqtSignal(bool)
    hide_requested = pyqtSignal()
    clear_results_requested = pyqtSignal()

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
        self._anim_timer.start(120)  # slightly slower pulse

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 8, 0)   # was 16,0,12,0
        layout.setSpacing(0)

        # App Icon — compact 22×22
        icon_lbl = QLabel()
        if os.path.exists(_APP_ICON):
            pix = QPixmap(_APP_ICON).scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio,
                                             Qt.TransformationMode.SmoothTransformation)
            icon_lbl.setPixmap(pix)
        else:
            icon_lbl.setText("🚀")
        layout.addWidget(icon_lbl)
        layout.addSpacing(8)   # was 12

        # Animated Title Label
        self._title_lbl = QLabel("Star Citizen Dossier")
        font = label_caps()
        font.setPointSize(9)
        font.setBold(True)
        self._title_lbl.setFont(font)
        self._title_lbl.setStyleSheet(
            f"color: {P.PRIMARY}; background: transparent; letter-spacing: 0.14em;"
        )
        self._title_lbl.setMouseTracking(True)
        layout.addWidget(self._title_lbl)

        layout.addStretch(1)

        # --- Control buttons: compact 32×32 ---
        btn_size = 32   # was 28

        # Pin button
        self._pin_btn = QPushButton()
        self._pin_btn.setProperty("class", "icon")
        self._pin_btn.setFixedSize(btn_size, btn_size)
        self._pin_btn.setToolTip("Pin window (stay on top)")
        self._pin_btn.setCheckable(True)
        self._pin_btn.clicked.connect(self._on_pin_clicked)
        self._update_pin_style()

        # Hide button
        self._hide_btn = QPushButton()
        self._hide_btn.setProperty("class", "icon")
        self._hide_btn.setFixedSize(btn_size, btn_size)
        self._hide_btn.setToolTip("Minimize to toolbar — hides main window and shows the overlay toolbar")
        self._hide_btn.clicked.connect(self.hide_requested.emit)
        self._update_hide_style()

        # Clear results button
        self._clear_btn = QPushButton()
        self._clear_btn.setProperty("class", "icon")
        self._clear_btn.setFixedSize(btn_size, btn_size)
        self._clear_btn.setToolTip("Clear all search results")
        self._clear_btn.clicked.connect(self.clear_results_requested.emit)
        self._update_clear_style()

        # Layout order: Clear, Pin, Hide — with tighter spacing
        layout.addWidget(self._clear_btn)
        layout.addSpacing(2)   # was 4
        layout.addWidget(self._pin_btn)
        layout.addSpacing(2)
        layout.addWidget(self._hide_btn)

    def _update_animation(self):
        self._anim_step = (self._anim_step + 4) % 360
        val = 0.5 + 0.5 * __import__("math").sin(self._anim_step * 3.14159 / 180.0)
        c = QColor(0, int(160 + 95 * val), 255)
        self._title_lbl.setStyleSheet(
            f"color: {c.name()}; background: transparent; letter-spacing: 0.14em;"
        )

    def _load_button_icon(self, btn: QPushButton, icon_path: str, fallback_text: str) -> None:
        icon = QIcon()
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
        if not icon.isNull():
            btn.setIcon(icon)
            btn.setIconSize(QSize(20, 20))   # was 16,16
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

    def _update_clear_style(self) -> None:
        self._load_button_icon(self._clear_btn, _CLEAR_ICON, "✕")
        self._clear_btn.setStyleSheet(_CLEAR_BTN_BASE.format(
            color=P.TEXT_DIM, bg="transparent",
            hover_bg="rgba(255,255,0,0.18)", hover_color="#FFFF00",
            pressed_bg="rgba(255,255,0,0.28)",
        ))

    @property
    def is_pinned(self) -> bool:
        return self._pinned

    def _on_pin_clicked(self) -> None:
        self._pinned = not self._pinned
        self._update_pin_style()
        self._hide_btn.setEnabled(not self._pinned)
        if self._pinned:
            self._pin_btn.setToolTip("Unpin window — allow other windows to overlap")
            self._hide_btn.setToolTip("Unpin the window first before hiding")
        else:
            self._pin_btn.setToolTip("Pin window (stay on top)")
            self._hide_btn.setToolTip("Minimize to toolbar — hides main window and shows the overlay toolbar")
        self.pin_toggled.emit(self._pinned)

    def set_pinned(self, pinned: bool) -> None:
        if self._pinned != pinned:
            self._pinned = pinned
            self._update_pin_style()
            self._hide_btn.setEnabled(not pinned)
            if self._pinned:
                self._pin_btn.setToolTip("Unpin window — allow other windows to overlap")
                self._hide_btn.setToolTip("Unpin the window first before hiding")
            else:
                self._pin_btn.setToolTip("Pin window (stay on top)")
                self._hide_btn.setToolTip("Minimize to toolbar — hides main window and shows the overlay toolbar")

    def set_status(self, text: str, ok: bool = True) -> None:
        pass  # Removed per request

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Darker gradient — more pronounced depth
        grad = QLinearGradient(0, 0, self.width(), 0)
        grad.setColorAt(0, QColor(3, 14, 24, 245))   # deep navy
        grad.setColorAt(0.6, QColor(8, 20, 30, 240))
        grad.setColorAt(1, QColor(28, 34, 40, 240))   # dark grey
        painter.fillRect(self.rect(), grad)

        # Bottom border glow line
        pen = QPen(QColor(0, 170, 255, 42), 1)
        painter.setPen(pen)
        painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)

        painter.end()
