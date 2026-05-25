"""
src/ui/widgets/glass_card.py
GlassCard — primary panel container for the Aegis Liquid Interface.

Features:
- Semi-transparent dark glass background
- 1px rgba blue border
- Tech-bracket corner ornaments (6×6px #00AAFF L-shapes at all 4 corners)
- Optional title header strip with adaptive height
"""

from PyQt6.QtCore import Qt, QRect, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QWidget

from src.ui.theme import palette as P
from src.ui.theme.fonts import label_caps


# Constants — tightened for compact layout
_HEADER_HEIGHT = 24        # was 32
_BORDER_RADIUS = 3         # was 4
_MARGIN = 10               # was 16
_BRACKET_SIZE = 6          # was 8
_BRACKET_WIDTH = P.BRACKET_WIDTH
_BRACKET_COLOR = QColor(P.BRACKET_COLOR)
_GLASS_BG = QColor(10, 29, 41, 90)        # slightly more transparent
_BORDER_COLOR = QColor(0, 170, 255, 32)   # rgba(0,170,255,0.125)
_HEADER_BG = QColor(0, 170, 255, 14)      # rgba(0,170,255,0.055)
_HEADER_LINE = QColor(0, 170, 255, 20)    # rgba(0,170,255,0.08)


class GlassCard(QFrame):
    """
    A styled container panel with glassmorphism aesthetics and tech-bracket corners.

    Usage:
        card = GlassCard(parent=self)
        card.content_layout.addWidget(my_widget)

    Args:
        title:   Optional label text shown in a thin header strip.
        parent:  Parent widget.
    """

    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = title
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setObjectName("GlassCard")
        self._update_margins()

    @property
    def content_layout(self) -> QVBoxLayout:
        """The inner layout for card content widgets."""
        return self._layout

    def set_title(self, title: str) -> None:
        """Update the card header title text."""
        self._title = title
        self._update_margins()
        self.update()

    def _update_margins(self) -> None:
        """Adjust layout margins based on header presence."""
        top_extra = _HEADER_HEIGHT if self._title else 0
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(_MARGIN, _MARGIN + top_extra, _MARGIN, _MARGIN)
        self._layout.setSpacing(8)   # was 12

    def paintEvent(self, event) -> None:
        """Paint glass background, border, header strip, and bracket ornaments."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        br = _BORDER_RADIUS
        half_pen = _BRACKET_WIDTH / 2

        # Clip path for rounded rect (prevents overflow)
        clip_path = QPainterPath()
        clip_path.addRoundedRect(
            QRectF(
                rect.x() + half_pen, rect.y() + half_pen,
                rect.width() - _BRACKET_WIDTH, rect.height() - _BRACKET_WIDTH
            ),
            br, br
        )
        painter.setClipPath(clip_path)

        # --- Glass background ---
        painter.setBrush(QBrush(_GLASS_BG))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(rect)

        painter.setClipping(False)

        # --- Header strip (if title) ---
        if self._title:
            header_rect = QRect(0, 0, rect.width(), _HEADER_HEIGHT)
            painter.setBrush(QBrush(_HEADER_BG))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(header_rect)

            # Title text
            painter.setPen(QColor(P.TEXT_DIM))
            painter.setFont(label_caps())
            painter.drawText(
                QRectF(_MARGIN, 0, rect.width() - _MARGIN * 2, _HEADER_HEIGHT),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                self._title.upper(),
            )

            # Header bottom border
            painter.setPen(QPen(_HEADER_LINE, 1))
            painter.drawLine(0, _HEADER_HEIGHT, rect.width(), _HEADER_HEIGHT)

        # --- 1px border ---
        painter.setPen(QPen(_BORDER_COLOR, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(
            QRectF(
                rect.x() + half_pen, rect.y() + half_pen,
                rect.width() - _BRACKET_WIDTH, rect.height() - _BRACKET_WIDTH
            ),
            br, br
        )

        # --- Tech bracket corners ---
        self._draw_brackets(painter, rect)

        painter.end()

    def _draw_brackets(self, painter: QPainter, rect: QRect) -> None:
        """Draw L-shaped corner bracket ornaments in primary blue."""
        size = _BRACKET_SIZE
        pen = QPen(_BRACKET_COLOR, _BRACKET_WIDTH)
        pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        x0, y0 = rect.left(), rect.top()
        x1, y1 = rect.right(), rect.bottom()

        # Top-left
        painter.drawLine(x0, y0, x0 + size, y0)
        painter.drawLine(x0, y0, x0, y0 + size)

        # Top-right
        painter.drawLine(x1 - size, y0, x1, y0)
        painter.drawLine(x1, y0, x1, y0 + size)

        # Bottom-left
        painter.drawLine(x0, y1, x0 + size, y1)
        painter.drawLine(x0, y1 - size, x0, y1)

        # Bottom-right
        painter.drawLine(x1 - size, y1, x1, y1)
        painter.drawLine(x1, y1 - size, x1, y1)
