"""
src/ui/widgets/data_field.py
DataField — a label+value pair widget for displaying player/org profile data.

Layout (vertical):
  FIELD LABEL         ← label-caps, dimmed
  Field Value Text    ← data-point, JetBrains Mono, white
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame

from src.ui.theme import palette as P
from src.ui.theme.fonts import label_caps, data_point


class DataField(QWidget):
    """
    A two-row display widget: uppercase label + monospaced value.

    Args:
        label:   Field name (uppercased automatically).
        value:   Initial value string. Empty string shows nothing.
        parent:  Parent widget.
    """

    def __init__(self, label: str, value: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._build_ui(label, value)

    def _build_ui(self, label: str, value: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)   # was 8,6,8,6
        layout.setSpacing(1)                      # was 2

        # Background container
        self.setStyleSheet(
            f"background: {P.rgba(P.SURFACE_CONTAINER_LOWEST, 0.5)}; border-radius: 3px;"
        )

        # Label row
        self._label_lbl = QLabel(label.upper())
        self._label_lbl.setFont(label_caps())
        self._label_lbl.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent;")

        # Value row
        self._value_lbl = QLabel(value or "—")
        self._value_lbl.setFont(data_point())
        self._value_lbl.setStyleSheet(f"color: {P.ON_SURFACE}; background: transparent;")
        self._value_lbl.setWordWrap(True)
        self._value_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        layout.addWidget(self._label_lbl)
        layout.addWidget(self._value_lbl)

    def set_value(self, value: str | None) -> None:
        """Update the displayed value. None or empty → '—'"""
        display = value if value else "—"
        self._value_lbl.setText(display)

    def get_value(self) -> str:
        return self._value_lbl.text()

    def set_label(self, label: str) -> None:
        self._label_lbl.setText(label.upper())
