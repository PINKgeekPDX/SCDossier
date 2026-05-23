"""
src/ui/widgets/wrap_layout.py
WrapLayout — a simple flow/wrap layout for badge chips and similar items.
Extracted from dossier_tab.py for reuse across tabs.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget


class WrapLayout(QWidget):
    """A simple flow/wrap layout for badge chips and similar items."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._widgets = []
        self._spacing = 8
        self._margin = 0

    def addWidget(self, widget):
        self._widgets.append(widget)
        widget.setParent(self)
        self._do_layout()

    def clear(self):
        for w in self._widgets:
            w.deleteLater()
        self._widgets = []

    def _do_layout(self):
        if not self._widgets:
            return
        w = self.width()
        x, y = self._margin, self._margin
        max_h = 0
        for widget in self._widgets:
            widget_w = widget.sizeHint().width()
            if x + widget_w > w and x > self._margin:
                x = self._margin
                y += max_h + self._spacing
                max_h = 0
            widget.move(x, y)
            widget.show()
            x += widget_w + self._spacing
            max_h = max(max_h, widget.sizeHint().height())
        self.setMinimumHeight(y + max_h + self._margin)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._do_layout()