"""
src/ui/theme/icon_utils.py
Icon utility functions for loading SVG and PNG icons properly
across all UI components. Handles the quirks of PyQt6 icon rendering.
"""

import os
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer


def load_icon(path: str, size: int = 22) -> QIcon:
    """
    Load an icon from a file path, properly handling SVG files.
    Falls back to QIcon for PNG files.

    Args:
        path: Absolute or relative path to the icon file
        size: Default icon size in pixels

    Returns:
        QIcon instance (may be empty if file doesn't exist)
    """
    if not os.path.exists(path):
        return QIcon()

    icon = QIcon()

    if path.lower().endswith('.svg'):
        # Use QSvgRenderer for reliable SVG rendering
        renderer = QSvgRenderer(path)
        if renderer.isValid():
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            icon.addPixmap(pixmap)
            return icon

    # Fallback: QIcon handles PNG and other formats natively
    icon = QIcon(path)
    return icon


def load_tinted_icon(path: str, color: tuple[int, int, int, int], size: int = 22) -> QIcon:
    """
    Load an icon and tint it with the specified color.

    Args:
        path: Path to the icon file
        color: RGBA tuple (r, g, b, a) for the tint color
        size: Icon size in pixels

    Returns:
        Tinted QIcon
    """
    from PyQt6.QtGui import QColor

    base_icon = load_icon(path, size)
    if base_icon.isNull():
        return base_icon

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    base_pixmap = base_icon.pixmap(size, size)
    painter.drawPixmap(0, 0, base_pixmap)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
    painter.fillRect(0, 0, size, size, QColor(*color))
    painter.end()

    tinted_icon = QIcon()
    tinted_icon.addPixmap(pixmap)
    return tinted_icon


def set_button_icon(button, path: str, size: tuple[int, int] = (20, 20)) -> None:
    """
    Set a button's icon from a file path, properly handling SVGs.

    Args:
        button: QPushButton or QAction instance
        path: Path to the icon file
        size: Icon size as (width, height) tuple
    """
    icon = load_icon(path, max(size))
    if not icon.isNull():
        button.setIcon(icon)
        button.setIconSize(QSize(*size))