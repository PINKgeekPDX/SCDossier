from PyQt6.QtCore import Qt, QSize
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
        self.setFixedHeight(0)
        self.updateGeometry()

    def _do_layout(self):
        if not self._widgets:
            if self.height() != 0:
                self.setFixedHeight(0)
                self.updateGeometry()
            return

        w = self.width()
        # Fallback to parent's width if width hasn't been set yet
        if w <= 100 and self.parentWidget():
            w = self.parentWidget().width() - 32
        w = max(100, w)

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

        new_h = y + max_h + self._margin
        if self.height() != new_h or self.minimumHeight() != new_h:
            self.setFixedHeight(new_h)
            self.updateGeometry()

    def sizeHint(self) -> QSize:
        if not self._widgets:
            return QSize(100, 0)
        return QSize(self.width(), self.minimumHeight())

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._do_layout()