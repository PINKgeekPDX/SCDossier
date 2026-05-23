"""
src/ui/widgets/title_bar.py
CustomTitleBar — draggable window chrome for the main window.

Layout:
  [App Name // Tagline]    [Status]    [Pin Btn] [Hide Btn]

Features:
- 48px fixed height
- Drag-to-reposition the parent window
- Pin button: toggles always-on-top + disables hide while pinned
- Hide button: collapses main window back to toolbar
- 1px bottom border in rgba(0,170,255,0.15)
"""

import logging
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton

from src.ui.theme import palette as P
from src.ui.theme.fonts import label_caps
from src.app.constants import APP_NAME, TITLEBAR_HEIGHT

log = logging.getLogger(__name__)

import os

# Shared button base style
_BTN_BASE = (
    "QPushButton {{ color: {color}; font-size: 16px; border: none; "
    "background: {bg}; border-radius: 6px; }}"
    "QPushButton:hover {{ background: {hover_bg}; color: {hover_color}; }}"
    "QPushButton:pressed {{ background: {pressed_bg}; }}"
    "QPushButton:disabled {{ opacity: 0.4; }}"
)

# Resolve icon paths
_ICONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "icons")
_PIN_ICON = os.path.join(_ICONS_DIR, "pin.svg")
_HIDE_ICON = os.path.join(_ICONS_DIR, "hide.svg")


class CustomTitleBar(QWidget):
    """
    Custom title bar widget for the SC Dossier main window.

    Signals:
        pin_toggled(bool):  Emitted when pin state changes.
        hide_requested():   Emitted when hide button is clicked.
    """

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

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 12, 0)
        layout.setSpacing(0)

        # --- Left: App name + tagline ---
        app_label = QLabel(APP_NAME.upper())
        app_label.setFont(label_caps())
        app_label.setStyleSheet(f"color: {P.PRIMARY}; background: transparent; letter-spacing: 0.15em;")
        app_label.setObjectName("AppTitleLabel")

        sub_label = QLabel("// CITIZEN INTEL")
        sub_label.setFont(label_caps())
        sub_label.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent; margin-left: 8px;")

        layout.addWidget(app_label)
        layout.addWidget(sub_label)
        layout.addStretch(1)

        # --- Center: Connection status dot ---
        self._status_dot = QLabel("●")
        self._status_dot.setFont(label_caps())
        self._status_dot.setStyleSheet("color: #00FF88; background: transparent; font-size: 10px;")
        self._status_dot.setToolTip("System Online")

        self._status_label = QLabel("SYSTEM NOMINAL")
        self._status_label.setFont(label_caps())
        self._status_label.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent; margin-left: 6px;")

        layout.addWidget(self._status_dot)
        layout.addWidget(self._status_label)
        layout.addStretch(1)

        # --- Right: Pin + Hide buttons ---
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

    # ------------------------------------------------------------------
    # Button Styles (deduplicated via template)
    # ------------------------------------------------------------------

    def _load_button_icon(self, btn: QPushButton, icon_path: str, fallback_text: str) -> None:
        """Load SVG icon from path with text fallback."""
        from PyQt6.QtCore import QSize
        from PyQt6.QtGui import QIcon
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            btn.setIcon(icon)
            btn.setIconSize(QSize(18, 18))
            btn.setText("")
        else:
            btn.setText(fallback_text)
            btn.setIcon(QIcon())

    def _update_pin_style(self) -> None:
        """Update pin button appearance based on state."""
        self._load_button_icon(self._pin_btn, _PIN_ICON, "◈" if self._pinned else "◇")
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
        """Update hide button appearance."""
        self._load_button_icon(self._hide_btn, _HIDE_ICON, "⊟")
        self._hide_btn.setStyleSheet(_BTN_BASE.format(
            color=P.TEXT_DIM, bg="transparent",
            hover_bg="rgba(255,59,59,0.15)", hover_color=P.HAZARD_RED,
            pressed_bg="rgba(255,59,59,0.25)",
        ))

    # ------------------------------------------------------------------
    # Pin Logic
    # ------------------------------------------------------------------

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
        """Programmatically set pin state."""
        if self._pinned != pinned:
            self._pinned = pinned
            self._update_pin_style()
            self._hide_btn.setEnabled(not pinned)

    # ------------------------------------------------------------------
    # Status Update
    # ------------------------------------------------------------------

    def set_status(self, text: str, ok: bool = True) -> None:
        """Update the center status indicator."""
        self._status_label.setText(text.upper())
        color = "#00FF88" if ok else P.HAZARD_RED
        self._status_dot.setStyleSheet(f"color: {color}; background: transparent; font-size: 10px;")

    # ------------------------------------------------------------------
    # Drag
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor(10, 29, 41, 200))

        # Bottom border
        pen = QPen(QColor(0, 170, 255, 38), 1)
        painter.setPen(pen)
        painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)

        painter.end()
