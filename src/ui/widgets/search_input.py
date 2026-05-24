"""
src/ui/widgets/search_input.py
SearchInput — styled QLineEdit with animated blue glow on focus and search history dropdown.
"""

from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QTimer
from PyQt6.QtGui import QColor, QAction
from PyQt6.QtWidgets import QLineEdit, QGraphicsDropShadowEffect, QWidget, QMenu

from src.ui.theme import palette as P
from src.core.settings import SettingsManager


class SearchInput(QLineEdit):
    """
    Styled search/input field with:
    - Dark recessed background
    - Blue border glow on focus (animated via QGraphicsDropShadowEffect)
    - Placeholder text in TEXT_DIM color
    - Search history dropdown on focus

    Args:
        placeholder: Placeholder text.
        parent:      Parent widget.
    """

    def __init__(self, placeholder: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self._focused = False
        self._settings = SettingsManager.instance()
        self._history_menu = None
        self._setup_glow()
        self._apply_style(False)
        self.setMinimumHeight(44)

    def _apply_style(self, focused: bool) -> None:
        """Apply QSS based on focus state."""
        if focused:
            self.setStyleSheet(f"""
                QLineEdit {{
                    background-color: rgba(0, 10, 20, 0.95);
                    color: {P.ON_SURFACE};
                    border: 1px solid {P.PRIMARY_CONTAINER};
                    border-radius: 6px;
                    padding: 10px 14px;
                    font-family: "Inter", "Segoe UI", Arial, sans-serif;
                    font-size: 14px;
                    selection-background-color: {P.PRIMARY_CONTAINER};
                    selection-color: #FFFFFF;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QLineEdit {{
                    background-color: rgba(5, 11, 15, 0.90);
                    color: {P.ON_SURFACE};
                    border: 1px solid {P.OUTLINE_VARIANT};
                    border-radius: 6px;
                    padding: 10px 14px;
                    font-family: "Inter", "Segoe UI", Arial, sans-serif;
                    font-size: 14px;
                    selection-background-color: {P.PRIMARY_CONTAINER};
                    selection-color: #FFFFFF;
                }}
                QLineEdit:hover {{
                    border-color: {P.OUTLINE};
                }}
            """)

    def _setup_glow(self) -> None:
        """Set up the drop shadow used for focus glow animation."""
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(0)
        self._shadow.setColor(QColor(0, 170, 255, 180))
        self._shadow.setOffset(0, 0)
        self.setGraphicsEffect(self._shadow)

        # Animate blur radius for glow in/out
        self._glow_in = QPropertyAnimation(self._shadow, b"blurRadius")
        self._glow_in.setDuration(200)
        self._glow_in.setStartValue(0)
        self._glow_in.setEndValue(14)
        self._glow_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._glow_out = QPropertyAnimation(self._shadow, b"blurRadius")
        self._glow_out.setDuration(200)
        self._glow_out.setStartValue(14)
        self._glow_out.setEndValue(0)
        self._glow_out.setEasingCurve(QEasingCurve.Type.InCubic)

    def focusInEvent(self, event) -> None:
        self._focused = True
        self._apply_style(True)
        self._glow_out.stop()
        self._glow_in.start()
        super().focusInEvent(event)
        # Don't automatically show menu on focus - let user click down arrow or handle differently
        # Menu will be shown via other means if needed

    def focusOutEvent(self, event) -> None:
        self._focused = False
        self._apply_style(False)
        self._glow_in.stop()
        self._glow_out.start()
        super().focusOutEvent(event)

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        self.setFocus()
        # Show history on mouse click (more intuitive than on focus)
        if event.button() == Qt.MouseButton.LeftButton:
            # Use single shot to avoid interfering with the click event
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1, self._show_history_menu)

    def _show_history_menu(self) -> None:
        """Show a dropdown menu with recent search history."""
        # Get search history from settings
        history = self._settings.search_history
        limit = self._settings.search_history_limit
        
        # Limit history to the specified number
        if limit > 0:
            history = history[-limit:] if history else []
            history = list(reversed(history))  # Show most recent first
        
        # Don't show menu if no history or limit is 0
        if not history or limit == 0:
            return
            
        # Create and show the menu
        self._history_menu = QMenu(self)
        self._history_menu.setStyleSheet(f"""
            QMenu {{{{
                background-color: rgba(10, 20, 30, 0.95);
                border: 1px solid {P.PRIMARY_CONTAINER};
                border-radius: 4px;
                padding: 4px;
            }}}}
            QMenu::item {{{{
                color: {P.ON_SURFACE};
                padding: 6px 12px;
                border-radius: 2px;
                font-family: "Inter", "Segoe UI", Arial, sans-serif;
                font-size: 13px;
            }}}}
            QMenu::item:selected {{{{
                background-color: rgba(0, 170, 255, 0.2);
                color: #FFFFFF;
            }}}}
        """)
        
        # Add history items
        for item_text in history:
            action = QAction(item_text, self)
            action.triggered.connect(lambda checked, text=item_text: self._on_history_item_clicked(text))
            self._history_menu.addAction(action)
            
        # Position menu below the search input
        pos = self.mapToGlobal(QPoint(0, self.height()))
        # Don't steal focus when showing the popup - use proper Qt flags
        self._history_menu.setWindowFlag(Qt.WindowType.Popup, True)
        self._history_menu.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, False)  # Keep shadow
        self._history_menu.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self._history_menu.popup(pos)

    def _on_history_item_clicked(self, text: str) -> None:
        """Handle clicking on a history item."""
        self.setText(text)
        self._focused = True
        self.setFocus()
        # Hide the menu
        if self._history_menu:
            self._history_menu.hide()
