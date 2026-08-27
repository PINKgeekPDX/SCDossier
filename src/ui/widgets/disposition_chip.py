"""
src/ui/widgets/disposition_chip.py
DispositionChip — aggregate disposition marker (HOSTILE / FRIENDLY / UNKNOWN).

Derived from players.hostile_count vs players.friendly_count.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel

from src.ui.theme import palette as P
from src.ui.theme.fonts import label_caps
from src.app.constants import COLOR_HOSTILE, COLOR_FRIENDLY


class DispositionChip(QWidget):
    """
    A pill-shaped chip showing the aggregate disposition.

    Args:
        disposition: One of "hostile", "friendly", "unknown".
        hostile_count: Number of hostile reports (for tooltip).
        friendly_count: Number of friendly reports (for tooltip).
        parent: Parent widget.
    """

    def __init__(
        self,
        disposition: str = "unknown",
        hostile_count: int = 0,
        friendly_count: int = 0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._disposition = disposition
        self._hostile_count = hostile_count
        self._friendly_count = friendly_count
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setFixedHeight(24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build_ui()
        # Theme changes require repaint
        from src.core.events import EventBus
        EventBus.instance().theme_changed.connect(self._refresh_theme)

    def _refresh_theme(self) -> None:
        """Re-apply inline styles and repaint for theme changes."""
        self._label.setStyleSheet(f"color: {self._text_color()}; background: transparent;")
        self.update()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(4)

        # Disposition label
        self._label = QLabel(self._display_text())
        self._label.setFont(label_caps())
        self._label.setStyleSheet(f"color: {self._text_color()}; background: transparent;")
        self._label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        layout.addWidget(self._label)

    def _display_text(self) -> str:
        return self._disposition.upper()

    def _text_color(self) -> str:
        if self._disposition == "hostile":
            return COLOR_HOSTILE  # Red
        elif self._disposition == "friendly":
            return COLOR_FRIENDLY  # Green
        else:
            return P.TEXT_DIM  # Gray

    def _bg_color(self) -> QColor:
        if self._disposition == "hostile":
            return QColor(COLOR_HOSTILE)
        elif self._disposition == "friendly":
            return QColor(COLOR_FRIENDLY)
        else:
            return QColor(P.OUTLINE_VARIANT)

    def _border_color(self) -> QColor:
        if self._disposition == "hostile":
            return QColor(COLOR_HOSTILE)
        elif self._disposition == "friendly":
            return QColor(COLOR_FRIENDLY)
        else:
            return QColor(P.OUTLINE_VARIANT)

    def set_disposition(self, disposition: str, hostile_count: int = 0, friendly_count: int = 0) -> None:
        """Update the disposition and counts."""
        self._disposition = disposition
        self._hostile_count = hostile_count
        self._friendly_count = friendly_count
        self._label.setText(self._display_text())
        self._label.setStyleSheet(f"color: {self._text_color()}; background: transparent;")
        self._update_tooltip()
        self.update()

    def _update_tooltip(self) -> None:
        if self._disposition == "hostile":
            self.setToolTip(f"HOSTILE — {self._hostile_count} hostile report(s), {self._friendly_count} friendly report(s)")
        elif self._disposition == "friendly":
            self.setToolTip(f"FRIENDLY — {self._friendly_count} friendly report(s), {self._hostile_count} hostile report(s)")
        else:
            self.setToolTip(f"UNKNOWN — {self._hostile_count} hostile, {self._friendly_count} friendly")

    def paintEvent(self, event) -> None:
        """Paint pill-shaped border with disposition color."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(0, 0, -1, -1)
        pill_radius = rect.height() // 2

        # Pill background (subtle tint)
        bg = self._bg_color()
        bg.setAlpha(20)
        painter.setBrush(bg)
        painter.setPen(QPen(self._border_color(), 1))
        painter.drawRoundedRect(rect, pill_radius, pill_radius)
        painter.end()