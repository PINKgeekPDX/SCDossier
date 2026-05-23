"""
src/ui/widgets/tech_label.py
TechLabel — a QLabel styled in label-caps (JetBrains Mono, uppercase, tracked).
"""

from PyQt6.QtWidgets import QLabel, QWidget
from PyQt6.QtCore import Qt
from src.ui.theme import palette as P
from src.ui.theme.fonts import label_caps


class TechLabel(QLabel):
    """
    Uppercase monospaced label using label-caps type style.
    Used for field labels, section headers, status readouts.
    """

    def __init__(self, text: str = "", dim: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(text.upper(), parent)
        color = P.TEXT_DIM if dim else P.ON_SURFACE_VARIANT
        self.setFont(label_caps())
        self.setStyleSheet(
            f"color: {color}; background: transparent; letter-spacing: 0.15em;"
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
