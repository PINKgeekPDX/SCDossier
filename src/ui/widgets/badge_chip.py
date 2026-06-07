"""
src/ui/widgets/badge_chip.py
BadgeChip — badge image + name displayed as a pill-shaped chip widget.
Used in the Dossier tab under "Accreditations & Clearances".
"""

from pathlib import Path
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel

from src.ui.theme import palette as P
from src.ui.theme.fonts import label_caps, data_point
from src.core.events import EventBus


class BadgeChip(QWidget):
    """
    A horizontal chip showing a small badge image and the badge name.

    Args:
        name:   Badge display name.
        image_path: Local path to badge image (optional).
        parent: Parent widget.
    """

    def __init__(
        self,
        name: str = "",
        image_path: str | Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._name = name
        self._image_path = image_path
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setFixedHeight(28)        # was 36
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build_ui(name, image_path)
        EventBus.instance().theme_changed.connect(self._refresh_theme)

    def _refresh_theme(self) -> None:
        """Re-apply inline styles and repaint for theme changes."""
        self._name_label.setStyleSheet(f"color: {P.ON_SURFACE}; background: transparent;")
        if not self._image_path:
            self._img_label.setStyleSheet(
                f"color: {P.PRIMARY_CONTAINER}; background: transparent; font-size: 11px;"
            )
        self.update()

    def _build_ui(self, name: str, image_path: str | Path | None) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 10, 2)   # was 8,4,12,4
        layout.setSpacing(5)                       # was 6

        # Badge image
        self._img_label = QLabel()
        self._img_label.setFixedSize(18, 18)       # was 24,24
        self._img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_label.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._set_image(image_path)

        # Badge name
        self._name_label = QLabel(name)
        self._name_label.setFont(data_point())
        self._name_label.setStyleSheet(f"color: {P.ON_SURFACE}; background: transparent;")
        self._name_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        layout.addWidget(self._img_label)
        layout.addWidget(self._name_label)

    def _set_image(self, path: str | Path | None) -> None:
        self._image_path = path
        if path:
            pix = QPixmap(str(path))
            if not pix.isNull():
                self._img_label.setPixmap(
                    pix.scaled(18, 18, Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
                )
                return
        # Placeholder glyph
        self._img_label.setText("◈")
        self._img_label.setStyleSheet(
            f"color: {P.PRIMARY_CONTAINER}; background: transparent; font-size: 11px;"
        )

    def update_image(self, path: str | Path | None) -> None:
        """Refresh the badge image from a new path."""
        self._set_image(path)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._image_path:
            pix = QPixmap(str(self._image_path))
            if not pix.isNull():
                from src.ui.widgets.image_preview import show_image_preview
                origin = self.mapToGlobal(self.rect().center())
                show_image_preview(pix, self, origin)
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        """Paint pill-shaped border."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(0, 0, -1, -1)
        pill_radius = rect.height() // 2
        # Pill background
        painter.setBrush(P.qcolor(P.PRIMARY_CONTAINER, 12))
        painter.setPen(QPen(P.qcolor(P.PRIMARY_CONTAINER, 45), 1))
        painter.drawRoundedRect(rect, pill_radius, pill_radius)
        painter.end()
