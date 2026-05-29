"""
src/ui/widgets/search_input.py
SearchInput — styled QLineEdit with animated blue glow on focus and search history dropdown.
"""

from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QLineEdit, QGraphicsDropShadowEffect, QWidget, QCompleter

from src.ui.theme import palette as P
from src.core.settings import SettingsManager
from src.core.events import EventBus


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

    def __init__(self, placeholder: str = "", parent: QWidget | None = None, history_type: str = "all") -> None:
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self._focused = False
        self._settings = SettingsManager.instance()
        self.history_type = history_type
        self._setup_glow()
        self._apply_style(False)
        self.setMinimumHeight(36)   # was 44
        
        # Configure case-insensitive auto-completion list for history
        self.update_history_completer()
        # Dynamically refresh autocomplete suggestions when history changes
        EventBus.instance().settings_changed.connect(self._on_settings_changed)

    def _apply_style(self, focused: bool) -> None:
        """Apply QSS based on focus state."""
        if focused:
            self.setStyleSheet(f"""
                QLineEdit {{
                    background-color: rgba(0, 10, 20, 0.95);
                    color: {P.ON_SURFACE};
                    border: 1px solid {P.PRIMARY_CONTAINER};
                    border-radius: 4px;
                    padding: 7px 12px;
                    font-family: "Inter", "Segoe UI", Arial, sans-serif;
                    font-size: 12px;
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
                    border-radius: 4px;
                    padding: 7px 12px;
                    font-family: "Inter", "Segoe UI", Arial, sans-serif;
                    font-size: 12px;
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
        if event.button() == Qt.MouseButton.LeftButton:
            completer = self.completer()
            if completer:
                # Force showing the completer dropdown listing history items
                completer.setCompletionPrefix(self.text())
                completer.complete()

    def _on_settings_changed(self, key: str, value: object) -> None:
        if key in ("search_history_limit", "search_history", "search_history_player", "search_history_org"):
            QTimer.singleShot(0, self.update_history_completer)

    def update_history_completer(self) -> None:
        """Update the QCompleter with the latest search history."""
        if self.history_type == "player":
            history = self._settings.search_history_player
        elif self.history_type == "org":
            history = self._settings.search_history_org
        else:
            history = self._settings.search_history
            
        if not history:
            self.setCompleter(None)
            return

        # Unique list, reversed to show most recent first
        seen = set()
        unique_history = []
        for x in reversed(history):
            if x not in seen:
                seen.add(x)
                unique_history.append(x)
                
        limit = self._settings.search_history_limit
        if limit > 0:
            unique_history = unique_history[:limit]
        else:
            self.setCompleter(None)
            return

        if not unique_history:
            self.setCompleter(None)
            return

        completer = QCompleter(unique_history, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        
        # Style the completer popup view (QListView)
        popup = completer.popup()
        popup.setStyleSheet(f"""
            QListView {{
                background-color: rgba(10, 20, 30, 0.95);
                color: {P.ON_SURFACE};
                border: 1px solid {P.PRIMARY_CONTAINER};
                border-radius: 6px;
                padding: 4px;
                font-family: "Inter", "Segoe UI", Arial, sans-serif;
                font-size: 13px;
                outline: 0;
            }}
            QListView::item {{
                padding: 6px 12px;
                border-radius: 4px;
            }}
            QListView::item:hover, QListView::item:selected {{
                background-color: rgba(0, 170, 255, 0.25);
                color: #FFFFFF;
            }}
        """)
        
        # Style the popup's vertical scrollbar
        popup.verticalScrollBar().setStyleSheet(f"""
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {P.PRIMARY};
                min-height: 20px;
                border-radius: 3px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        
        self.setCompleter(completer)
