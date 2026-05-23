"""
src/ui/widgets/search_input.py
SearchInput — styled QLineEdit with animated blue glow on focus.
"""

from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QLineEdit, QGraphicsDropShadowEffect, QWidget

from src.ui.theme import palette as P


class SearchInput(QLineEdit):
    """
    Styled search/input field with:
    - Dark recessed background
    - Blue border glow on focus (animated via QGraphicsDropShadowEffect)
    - Placeholder text in TEXT_DIM color

    Args:
        placeholder: Placeholder text.
        parent:      Parent widget.
    """

    def __init__(self, placeholder: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self._focused = False
        self._setup_glow()
        self._apply_style(False)
        self.setMinimumHeight(44)

    def _apply_style(self, focused: bool) -> None:
        """Apply QSS based on focus state."""
        if focused:
            self.setStyleSheet(f"""
                QLineEdit {{
                    background-color: rgba(0, 10, 20, 0.95);
                    color: {P.ON_SURFACE};
                    border: 1px solid {P.PRIMARY_CONTAINER};
                    border-radius: 6px;
                    padding: 10px 14px;
                    font-family: "Inter", "Segoe UI", Arial, sans-serif;
                    font-size: 14px;
                    selection-background-color: {P.PRIMARY_CONTAINER};
                    selection-color: #FFFFFF;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QLineEdit {{
                    background-color: rgba(5, 11, 15, 0.90);
                    color: {P.ON_SURFACE};
                    border: 1px solid {P.OUTLINE_VARIANT};
                    border-radius: 6px;
                    padding: 10px 14px;
                    font-family: "Inter", "Segoe UI", Arial, sans-serif;
                    font-size: 14px;
                    selection-background-color: {P.PRIMARY_CONTAINER};
                    selection-color: #FFFFFF;
                }}
                QLineEdit:hover {{
                    border-color: {P.OUTLINE};
                }}
            """)

    def _setup_glow(self) -> None:
        """Set up the drop shadow used for focus glow animation."""
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(0)
        self._shadow.setColor(QColor(0, 170, 255, 180))
        self._shadow.setOffset(0, 0)
        self.setGraphicsEffect(self._shadow)

        # Animate blur radius for glow in/out
        self._glow_in = QPropertyAnimation(self._shadow, b"blurRadius")
        self._glow_in.setDuration(200)
        self._glow_in.setStartValue(0)
        self._glow_in.setEndValue(14)
        self._glow_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._glow_out = QPropertyAnimation(self._shadow, b"blurRadius")
        self._glow_out.setDuration(200)
        self._glow_out.setStartValue(14)
        self._glow_out.setEndValue(0)
        self._glow_out.setEasingCurve(QEasingCurve.Type.InCubic)

    def focusInEvent(self, event) -> None:
        self._focused = True
        self._apply_style(True)
        self._glow_out.stop()
        self._glow_in.start()
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:
        self._focused = False
        self._apply_style(False)
        self._glow_in.stop()
        self._glow_out.start()
        super().focusOutEvent(event)
