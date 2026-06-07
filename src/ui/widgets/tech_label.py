"""
src/ui/widgets/tech_label.py
TechLabel — a QLabel styled in label-caps (JetBrains Mono, uppercase, tracked).
"""

from PyQt6.QtWidgets import QLabel, QWidget
from PyQt6.QtCore import Qt
from src.ui.theme import palette as P
from src.ui.theme.fonts import label_caps
from src.core.events import EventBus


class TechLabel(QLabel):
    """
    Uppercase monospaced label using label-caps type style.
    Used for field labels, section headers, status readouts.
    """

    def __init__(self, text: str = "", dim: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(text.upper(), parent)
        self._dim = dim
        self.setFont(label_caps())
        self._refresh_theme()
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        EventBus.instance().theme_changed.connect(self._refresh_theme)

    def _refresh_theme(self) -> None:
        color = P.TEXT_DIM if self._dim else P.ON_SURFACE_VARIANT
        self.setStyleSheet(
            f"color: {color}; background: transparent; letter-spacing: 0.15em;"
        )
