from PyQt6.QtWidgets import QSpinBox, QDoubleSpinBox, QSlider, QPushButton, QColorDialog
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor


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


class ColorPickerButton(QPushButton):
    colorChanged = pyqtSignal(str)

    def __init__(self, color_hex: str, parent=None):
        super().__init__(parent)
        self._color = color_hex or "#00AAFF"
        self.setFixedSize(60, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._pick_color)
        self.update_style()

    def color(self) -> str:
        return self._color

    def setColor(self, color_hex: str):
        self._color = color_hex or "#00AAFF"
        self.update_style()

    def _pick_color(self):
        color = QColorDialog.getColor(QColor(self._color), self, "Select Theme Accent Color")
        if color.isValid():
            self._color = color.name().upper()
            self.update_style()
            self.colorChanged.emit(self._color)

    def update_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color};
                border: 1px solid #3E4851;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 1px solid #00AAFF;
            }}
        """)
