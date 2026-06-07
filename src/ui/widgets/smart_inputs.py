from PyQt6.QtWidgets import QSpinBox, QDoubleSpinBox, QSlider, QPushButton, QColorDialog, QComboBox
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor

from src.ui.theme import palette as P


class NoScrollSpinBox(QSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event):
        if not self.hasFocus():
            event.ignore()
        else:
            super().wheelEvent(event)


class NoScrollDoubleSpinBox(QDoubleSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event):
        if not self.hasFocus():
            event.ignore()
        else:
            super().wheelEvent(event)


class NoScrollSlider(QSlider):
    def __init__(self, orientation=Qt.Orientation.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event):
        if not self.hasFocus():
            event.ignore()
        else:
            super().wheelEvent(event)


class NoScrollComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event):
        if not self.hasFocus():
            event.ignore()
        else:
            super().wheelEvent(event)


class ColorPickerButton(QPushButton):
    colorChanged = pyqtSignal(str)

    def __init__(self, color_hex: str, parent=None):
        super().__init__(parent)
        self._color = color_hex or P.PRIMARY_CONTAINER
        self.setFixedSize(60, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._pick_color)
        self.update_style()

    def color(self) -> str:
        return self._color

    def setColor(self, color_hex: str):
        self._color = color_hex or P.PRIMARY_CONTAINER
        self.update_style()

    def _parse_color(self, c: str) -> QColor:
        if c.startswith("rgba"):
            import re
            m = re.match(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)", c)
            if m:
                return QColor(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(float(m.group(4)) * 255))
        return QColor(c)

    def _pick_color(self):
        initial = self._parse_color(self._color)
        color = QColorDialog.getColor(initial, self, "Select Theme Color", QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            if color.alpha() < 255 or len(self._color) > 7 or self._color.startswith("rgba"):
                self._color = color.name(QColor.NameFormat.HexArgb).upper()
            else:
                self._color = color.name().upper()
            self.update_style()
            self.colorChanged.emit(self._color)

    def update_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color};
                border: 1px solid {P.OUTLINE_VARIANT};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 1px solid {P.PRIMARY_CONTAINER};
            }}
        """)
