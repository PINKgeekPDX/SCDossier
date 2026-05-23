"""
src/ui/tabs/search_tab.py
SearchTab — Landing page with player/org mode toggle for starting searches.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGraphicsDropShadowEffect
)

from src.core.events import EventBus
from src.ui.theme import palette as P
from src.ui.theme.fonts import headline_xl, font_inter, label_caps
from src.ui.widgets.search_input import SearchInput


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
        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(8)
        title_vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_lbl = QLabel("CITIZEN DOSSIER")
        title_lbl.setFont(headline_xl())
        title_lbl.setStyleSheet(f"color: {P.ON_SURFACE}; letter-spacing: 0.15em;")

        sub_lbl = QLabel("AEGIS LIQUID INTERFACE • RSI NETWORK ACCESS")
        sub_lbl.setFont(label_caps())
        sub_lbl.setStyleSheet(f"color: {P.PRIMARY}; letter-spacing: 0.25em;")

        title_vbox.addWidget(title_lbl, 0, Qt.AlignmentFlag.AlignCenter)
        title_vbox.addWidget(sub_lbl, 0, Qt.AlignmentFlag.AlignCenter)

        # --- Mode Toggle ---
        mode_widget = QWidget()
        mode_layout = QHBoxLayout(mode_widget)
        mode_layout.setSpacing(0)
        mode_layout.setContentsMargins(0, 0, 0, 0)

        self.player_btn = QPushButton("SEARCH PLAYER")
        self.player_btn.setProperty("class", "primary")
        self.player_btn.setFixedHeight(40)
        self.player_btn.setMinimumWidth(160)
        self.player_btn.clicked.connect(lambda: self._set_mode("player"))

        self.org_btn = QPushButton("SEARCH ORG")
        self.org_btn.setProperty("class", "ghost")
        self.org_btn.setFixedHeight(40)
        self.org_btn.setMinimumWidth(160)
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

        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(20)
        glow.setColor(QColor(0, 170, 255, 40))
        glow.setOffset(0, 0)
        self.search_input.setGraphicsEffect(glow)

        self.search_btn = QPushButton("INITIATE")
        self.search_btn.setProperty("class", "primary")
        self.search_btn.setFixedSize(120, 56)
        self.search_btn.setFont(label_caps())
        self.search_btn.clicked.connect(self._on_search)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)

        # --- Footer ---
        self.hint_lbl = QLabel("ENTER HANDLE OR URL TO BEGIN RETRIEVAL")
        self.hint_lbl.setFont(font_inter(12))
        self.hint_lbl.setStyleSheet(f"color: {P.TEXT_DIM};")

        # Assembly
        layout.addStretch(1)
        layout.addLayout(title_vbox)
        layout.addWidget(mode_widget, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(search_container, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.hint_lbl, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(2)

    def _set_mode(self, mode: str) -> None:
        self._mode = mode
        if mode == "player":
            self.player_btn.setProperty("class", "primary")
            self.org_btn.setProperty("class", "ghost")
            self.search_input.setPlaceholderText("IDENTIFY SUBJECT (RSI HANDLE)...")
            self.hint_lbl.setText("ENTER HANDLE TO BEGIN CITIZEN DOSSIER RETRIEVAL")
        else:
            self.org_btn.setProperty("class", "primary")
            self.player_btn.setProperty("class", "ghost")
            self.search_input.setPlaceholderText("ENTER ORG NAME OR SID...")
            self.hint_lbl.setText("ENTER ORG NAME OR SID TO LOOK UP ORGANIZATION")
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
