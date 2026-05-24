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
        self.setFixedHeight(36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build_ui(name, image_path)

    def _build_ui(self, name: str, image_path: str | Path | None) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 12, 4)
        layout.setSpacing(6)

        # Badge image
        self._img_label = QLabel()
        self._img_label.setFixedSize(24, 24)
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
                    pix.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
                )
                return
        # Placeholder glyph
        self._img_label.setText("◈")
        self._img_label.setStyleSheet(
            f"color: {P.PRIMARY_CONTAINER}; background: transparent; font-size: 14px;"
        )

    def update_image(self, path: str | Path | None) -> None:
        """Refresh the badge image from a new path."""
        self._set_image(path)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._image_path:
            pix = QPixmap(str(self._image_path))
            if not pix.isNull():
                from src.ui.widgets.image_preview import ImagePreviewDialog
                dlg = ImagePreviewDialog(pix, self)
                dlg.exec()
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        """Paint pill-shaped border."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(0, 0, -1, -1)
        pill_radius = rect.height() // 2
        # Pill background
        painter.setBrush(QColor(0, 170, 255, 13))  # rgba(0,170,255,0.05)
        painter.setPen(QPen(QColor(0, 170, 255, 51), 1))  # rgba(0,170,255,0.20)
        painter.drawRoundedRect(rect, pill_radius, pill_radius)
        painter.end()
