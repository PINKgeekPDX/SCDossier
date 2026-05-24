"""
src/ui/tabs/search_tab.py
SearchTab — Landing page with player/org mode toggle for starting searches.
"""

import os
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGraphicsDropShadowEffect
)

from src.core.events import EventBus
from src.ui.theme import palette as P
from src.ui.theme.fonts import headline_xl, font_inter, label_caps
from src.ui.widgets.search_input import SearchInput

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
_USER_ICON = os.path.join(_PROJECT_ROOT, "assets", "icons", "Icons", "USER.png")
_RIGHT_ICON = os.path.join(_PROJECT_ROOT, "assets", "icons", "Icons", "RIGHT.png")
_INFO_ICON = os.path.join(_PROJECT_ROOT, "assets", "icons", "misc", "info.png")


class SearchTab(QWidget):
    """
    Initial landing view with player/org mode toggle.
    """
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mode = "player"  # "player" or "org"
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(32)

        # --- Title ---
        title_hbox = QHBoxLayout()
        title_hbox.setSpacing(16)
        title_hbox.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel()
        if os.path.exists(_USER_ICON):
            pix = QPixmap(_USER_ICON).scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon_lbl.setPixmap(pix)
        
        title_lbl = QLabel("CITIZEN DOSSIER")
        font = headline_xl()
        font.setUnderline(True)
        title_lbl.setFont(font)
        title_lbl.setStyleSheet(f"color: {P.ON_SURFACE}; letter-spacing: 0.15em;")
        
        glow_title = QGraphicsDropShadowEffect()
        glow_title.setBlurRadius(15)
        glow_title.setColor(QColor(0, 170, 255, 100))
        glow_title.setOffset(0, 0)
        title_lbl.setGraphicsEffect(glow_title)

        title_hbox.addWidget(icon_lbl)
        title_hbox.addWidget(title_lbl)

        # --- Mode Toggle ---
        mode_widget = QWidget()
        mode_layout = QHBoxLayout(mode_widget)
        mode_layout.setSpacing(12)
        mode_layout.setContentsMargins(0, 0, 0, 0)

        btn_style = f"""
            QPushButton {{
                background: rgba(0, 170, 255, 0.1);
                color: {P.TEXT_DIM};
                border: 1px solid rgba(0, 170, 255, 0.3);
                border-radius: 4px;
                font-weight: bold;
                transition: all 0.2s;
            }}
            QPushButton:hover {{
                background: rgba(0, 170, 255, 0.2);
                border: 1px solid rgba(0, 170, 255, 0.6);
                color: {P.ON_SURFACE};
            }}
            QPushButton[class="primary"] {{
                background: rgba(0, 170, 255, 0.4);
                color: {P.ON_SURFACE};
                border: 1px solid {P.PRIMARY};
            }}
        """

        self.player_btn = QPushButton("SEARCH PLAYER")
        self.player_btn.setProperty("class", "primary")
        self.player_btn.setFixedHeight(40)
        self.player_btn.setMinimumWidth(160)
        self.player_btn.setStyleSheet(btn_style)
        self.player_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.player_btn.clicked.connect(lambda: self._set_mode("player"))

        self.org_btn = QPushButton("SEARCH ORG")
        self.org_btn.setProperty("class", "ghost")
        self.org_btn.setFixedHeight(40)
        self.org_btn.setMinimumWidth(160)
        self.org_btn.setStyleSheet(btn_style)
        self.org_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.org_btn.clicked.connect(lambda: self._set_mode("org"))

        mode_layout.addStretch()
        mode_layout.addWidget(self.player_btn)
        mode_layout.addWidget(self.org_btn)
        mode_layout.addStretch()

        # --- Search Bar ---
        search_container = QFrame()
        search_container.setFixedWidth(540)
        search_container.setStyleSheet("background: transparent;")
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(12)

        self.search_input = SearchInput("IDENTIFY SUBJECT (RSI HANDLE)...")
        self.search_input.setFixedHeight(56)
        self.search_input.setFont(font_inter(16))
        self.search_input.returnPressed.connect(self._on_search)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(10, 20, 30, 0.8);
                color: {P.ON_SURFACE};
                border: 2px solid {P.OUTLINE};
                border-radius: 8px;
                padding: 0 16px;
            }}
            QLineEdit:focus {{
                border: 2px solid {P.PRIMARY};
                background: rgba(15, 30, 45, 0.9);
            }}
            QLineEdit:hover {{
                border: 2px solid {P.PRIMARY_CONTAINER};
            }}
        """)

        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(20)
        glow.setColor(QColor(0, 170, 255, 60))
        glow.setOffset(0, 0)
        self.search_input.setGraphicsEffect(glow)

        self.search_btn = QPushButton()
        self.search_btn.setFixedSize(56, 56)
        self.search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if os.path.exists(_RIGHT_ICON):
            self.search_btn.setIcon(QIcon(_RIGHT_ICON))
            self.search_btn.setIconSize(QSize(24, 24))
        self.search_btn.setStyleSheet(f"""
            QPushButton {{
                background: {P.PRIMARY};
                border: none;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background: {P.PRIMARY_CONTAINER};
            }}
            QPushButton:pressed {{
                background: {P.ON_SURFACE};
            }}
        """)
        self.search_btn.clicked.connect(self._on_search)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)

        # --- Footer ---
        hint_hbox = QHBoxLayout()
        hint_hbox.setSpacing(8)
        hint_hbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        info_icon = QLabel()
        if os.path.exists(_INFO_ICON):
            pix = QPixmap(_INFO_ICON).scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            info_icon.setPixmap(pix)
            
        self.hint_lbl = QLabel("Enter player name or RSI dossier URL to find information")
        self.hint_lbl.setFont(font_inter(12))
        self.hint_lbl.setStyleSheet(f"color: {P.TEXT_DIM};")
        
        hint_hbox.addWidget(info_icon)
        hint_hbox.addWidget(self.hint_lbl)

        # Assembly
        layout.addStretch(1)
        layout.addLayout(title_hbox)
        layout.addWidget(mode_widget, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(search_container, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(hint_hbox)
        layout.addStretch(2)

    def _set_mode(self, mode: str) -> None:
        self._mode = mode
        if mode == "player":
            self.player_btn.setProperty("class", "primary")
            self.org_btn.setProperty("class", "ghost")
            self.search_input.setPlaceholderText("IDENTIFY SUBJECT (RSI HANDLE)...")
        else:
            self.org_btn.setProperty("class", "primary")
            self.player_btn.setProperty("class", "ghost")
            self.search_input.setPlaceholderText("ENTER ORG NAME OR SID...")
        # Force style refresh
        self.player_btn.style().unpolish(self.player_btn)
        self.player_btn.style().polish(self.player_btn)
        self.org_btn.style().unpolish(self.org_btn)
        self.org_btn.style().polish(self.org_btn)

    def _on_search(self) -> None:
        query = self.search_input.text().strip()
        if not query:
            return
        if self._mode == "player":
            EventBus.instance().search_player_requested.emit(query)
            EventBus.instance().navigate_to_tab.emit("dossier")
        else:
            EventBus.instance().search_org_requested.emit(query)
            EventBus.instance().navigate_to_tab.emit("organization")
        self.search_input.clear()
