"""
src/ui/tabs/org_tab.py
OrganizationTab — displays standalone organization profile information.
Uses GlassCard containers for the Aegis aesthetic.
"""

import os
from PyQt6.QtCore import Qt, pyqtSlot, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QPushButton,
    QFrame, QGridLayout
)

from src.core.events import EventBus
from src.ui.theme import palette as P
from src.ui.theme.fonts import headline_lg, headline_md, font_inter, label_caps
from src.ui.theme.icon_utils import set_button_icon
from src.ui.widgets.avatar_widget import AvatarWidget
from src.ui.widgets.data_field import DataField
from src.ui.widgets.tech_label import TechLabel
from src.ui.widgets.progress_overlay import ProgressOverlay
from src.ui.widgets.search_input import SearchInput
from src.ui.widgets.glass_card import GlassCard
from src.core.settings import SettingsManager


# Known SC manufacturer names mapped to their SVG file names
MANUFACTURER_MAP = {
    "RSI": "rsi",
    "Robert Space Industries": "rsi",
    "Anvil Aerospace": "anvil-aerospace",
    "Anvil": "anvil-aerospace",
    "Drake Interplanetary": "drake",
    "Drake": "drake",
    "Origin Jumpworks": "origin",
    "Origin": "origin",
    "MISC": "misc",
    "Musashi Industrial & Starflight Concern": "misc",
    "Mirai": "mirai",
    "Crusader Industries": "crusader",
    "Crusader": "crusader",
    "Aegis Dynamics": "aegis",
    "Aegis": "aegis",
    "Banu": "banu",
    "Esperia": "esperia",
    "Kruger Intergalactic": "kruger-intergalactic",
    "Kruger": "kruger-intergalactic",
    "Tumbril": "tumbril",
    "Greycat Industrial": "greycat",
    "Greycat": "greycat",
    "Consolidated Outland": "consolidated-outland",
    "Outland": "consolidated-outland",
    "Argo Astronautics": "argo-astronautics",
    "Argo": "argo-astronautics",
    "Gatac": "gatac",
    "Aopoa": "aopoa",
    "Shubin Interstellar": "shubin",
    "Shubin": "shubin",
}


class OrgTab(QWidget):
    """
    Displays standalone organization details using GlassCard containers.
    """
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_sid = ""
        self.mfr_logo_lbl = None
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Top Action Bar — compact ---
        action_bar = QWidget()
        action_bar.setFixedHeight(50)   # was 64
        action_bar.setStyleSheet(
            f"background: {P.SURFACE_CONTAINER_LOW}; border-bottom: 1px solid {P.OUTLINE_VARIANT};"
        )
        ab_layout = QHBoxLayout(action_bar)
        ab_layout.setContentsMargins(16, 7, 16, 7)   # was 24,10,24,10
        ab_layout.setSpacing(8)

        self.search_input = SearchInput("ENTER ORG NAME OR SID...", history_type="org")
        self.search_input.returnPressed.connect(self._on_search)
        self.search_input.setFixedHeight(36)   # was 44
        self.search_input.setToolTip(
            "Enter an organization name or SID (e.g., REBELS) to search for org details"
        )

        from src.core.paths import get_asset_path
        search_icon = get_asset_path("assets/icons/misc/icon_search.svg")

        search_btn = QPushButton()
        search_btn.setProperty("class", "primary")
        search_btn.setFixedSize(44, 36)   # was 56,44
        set_button_icon(search_btn, search_icon, (16, 16))
        search_btn.clicked.connect(self._on_search)
        search_btn.setToolTip("Search for the entered organization name or SID")

        ab_layout.addWidget(self.search_input)
        ab_layout.addWidget(search_btn)

        # --- Scrollable Content ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(16, 16, 16, 16)   # was 24,24,24,24
        self.content_layout.setSpacing(12)                         # was 20
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Empty state
        self.empty_lbl = QLabel("SEARCH FOR AN ORGANIZATION TO VIEW DETAILS")
        self.empty_lbl.setFont(label_caps())
        self.empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_lbl.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent;")
        self.content_layout.addStretch()
        self.content_layout.addWidget(self.empty_lbl)
        self.content_layout.addStretch()

        # Detail content (hidden until data loaded)
        self.detail_container = QWidget()
        self.detail_container.setVisible(False)
        self._build_detail()

        self.content_layout.addWidget(self.detail_container)

        scroll.setWidget(self.content_widget)

        main_layout.addWidget(action_bar)
        main_layout.addWidget(scroll)

        self.overlay = ProgressOverlay(self)

    def _build_detail(self) -> None:
        dl = QVBoxLayout(self.detail_container)
        dl.setContentsMargins(0, 0, 0, 0)
        dl.setSpacing(12)   # was 20

        # Identity card
        self.identity_card = GlassCard(title="ORGANIZATION IDENTITY")
        self.header_layout = QHBoxLayout()
        self.header_layout.setSpacing(14)   # was 20
        self.logo = AvatarWidget(size=90)   # was 120

        name_vbox = QVBoxLayout()
        name_vbox.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        name_vbox.setSpacing(2)   # was 4
        self.name_lbl = QLabel("—")
        self.name_lbl.setFont(headline_lg())
        self.name_lbl.setStyleSheet(
            f"color: {P.ON_SURFACE}; background: transparent; border: none;"
        )
        self.name_lbl.setWordWrap(True)
        self.sid_lbl = QLabel("—")
        self.sid_lbl.setFont(headline_md())
        self.sid_lbl.setStyleSheet(
            f"color: {P.PRIMARY}; background: transparent; border: none;"
        )
        name_vbox.addWidget(self.name_lbl)
        name_vbox.addWidget(self.sid_lbl)

        self.header_layout.addWidget(self.logo)
        self.header_layout.addLayout(name_vbox)
        self.header_layout.addStretch()
        self.identity_card.content_layout.addLayout(self.header_layout)
        dl.addWidget(self.identity_card)

        # Details grid card
        self.grid_card = GlassCard(title="ORGANIZATION DATA")
        grid = QGridLayout()
        grid.setSpacing(8)   # was 12
        self.f_archetype = DataField("ARCHETYPE")
        self.f_language = DataField("LANGUAGE")
        self.f_commitment = DataField("COMMITMENT")
        self.f_members = DataField("MEMBERS")
        self.f_recruiting = DataField("RECRUITING")
        self.f_roleplay = DataField("ROLEPLAY")
        grid.addWidget(self.f_archetype, 0, 0)
        grid.addWidget(self.f_language, 0, 1)
        grid.addWidget(self.f_commitment, 0, 2)
        grid.addWidget(self.f_members, 1, 0)
        grid.addWidget(self.f_recruiting, 1, 1)
        grid.addWidget(self.f_roleplay, 1, 2)
        self.grid_card.content_layout.addLayout(grid)
        dl.addWidget(self.grid_card)

        # Focus card
        self.focus_card = GlassCard(title="PRIMARY & SECONDARY FOCUS")
        focus_layout = QHBoxLayout()
        focus_layout.setSpacing(8)
        self.f_primary = DataField("PRIMARY FOCUS")
        self.f_secondary = DataField("SECONDARY FOCUS")
        focus_layout.addWidget(self.f_primary)
        focus_layout.addWidget(self.f_secondary)
        self.focus_card.content_layout.addLayout(focus_layout)
        dl.addWidget(self.focus_card)

        # Description card
        self.desc_card = GlassCard(title="ORGANIZATION HISTORY / DESCRIPTION")
        self.desc_lbl = QLabel("—")
        self.desc_lbl.setFont(font_inter(12))   # was 14
        self.desc_lbl.setStyleSheet(
            f"color: {P.TEXT_DIM}; background: transparent; border: none;"
        )
        self.desc_lbl.setWordWrap(True)
        self.desc_card.content_layout.addWidget(self.desc_lbl)
        dl.addWidget(self.desc_card)

        dl.addStretch()

    def _get_manufacturer_logo_path(self, org_name: str) -> str | None:
        """Check if org name matches a known SC manufacturer and return logo path."""
        for name_key, file_key in MANUFACTURER_MAP.items():
            if name_key.lower() in org_name.lower():
                from src.core.paths import get_asset_path
                logo_path = get_asset_path(f"assets/icons/manufact-names/sc-logo-{file_key}.svg")
                if os.path.exists(logo_path):
                    return logo_path
        return None

    def _connect_signals(self) -> None:
        bus = EventBus.instance()
        bus.org_loaded.connect(self._on_org_loaded)
        bus.org_candidates_found.connect(self._on_org_candidates)
        bus.status_message.connect(self._on_status_msg)

    def _clear_results(self) -> None:
        """Clear all displayed organization results."""
        self.current_sid = ""
        self._current_data = None
        self.search_input.clear()
        self.detail_container.setVisible(False)
        self.empty_lbl.setVisible(True)

    def _on_search(self) -> None:
        query = self.search_input.text().strip()
        if query:
            self._add_to_search_history(query)
            EventBus.instance().search_org_requested.emit(query)

    def _add_to_search_history(self, query: str) -> None:
        """Add a search query to the history."""
        settings = SettingsManager.instance()
        limit = settings.search_history_limit

        master = settings.search_history
        if query in master:
            master.remove(query)
        master.append(query)
        if limit >= 0 and len(master) > limit:
            master = master[-limit:]
        settings.search_history = master

        org_hist = settings.search_history_org
        if query in org_hist:
            org_hist.remove(query)
        org_hist.append(query)
        if limit >= 0 and len(org_hist) > limit:
            org_hist = org_hist[-limit:]
        settings.search_history_org = org_hist

    @pyqtSlot(list)
    def _on_org_candidates(self, candidates: list) -> None:
        """Show a simple dialog for the user to pick from multiple candidates."""
        from src.ui.widgets.confirm_dialog import ConfirmDialog
        from PyQt6.QtWidgets import QListWidget, QListWidgetItem

        dlg = ConfirmDialog(
            title="SELECT ORGANIZATION",
            message="Multiple organizations match your search. Select one:",
            confirm_text="SELECT",
            cancel_text="CANCEL",
            parent=self.window(),
        )
        list_widget = QListWidget()
        list_widget.setFixedHeight(180)   # was 200
        list_widget.setStyleSheet(f"""
            QListWidget {{
                background: rgba(5, 11, 15, 0.85);
                color: {P.ON_SURFACE};
                border: 1px solid {P.OUTLINE_VARIANT};
                border-radius: 3px;
            }}
            QListWidget::item:selected {{
                background: rgba(0, 170, 255, 0.20);
            }}
        """)
        for c in candidates:
            item = QListWidgetItem(f"{c['name']} ({c['sid']})")
            item.setData(Qt.ItemDataRole.UserRole, c['sid'])
            list_widget.addItem(item)
        list_widget.setCurrentRow(0)

        for child in dlg.findChildren(QLabel):
            if child.wordWrap():
                parent_layout = child.parent().layout()
                idx = parent_layout.indexOf(child)
                parent_layout.removeWidget(child)
                child.deleteLater()
                parent_layout.insertWidget(idx, list_widget)
                break

        if dlg.exec() == ConfirmDialog.DialogCode.Accepted and list_widget.currentItem():
            sid = list_widget.currentItem().data(Qt.ItemDataRole.UserRole)
            EventBus.instance().request_org_scrape.emit(sid)

    @pyqtSlot(str, str)
    def _on_status_msg(self, msg: str, severity: str) -> None:
        if severity == "info" and "RETRIEVING ORG" in msg:
            self.overlay.set_message(msg)
            self.overlay.show_overlay()
        elif severity in ("success", "error"):
            self.overlay.hide_overlay()

    @pyqtSlot(dict)
    def _on_org_loaded(self, data: dict) -> None:
        self.overlay.hide_overlay()
        self.current_sid = data.get("sid", "")
        self.search_input.clear()

        self.empty_lbl.setVisible(False)
        self.detail_container.setVisible(True)

        self.name_lbl.setText(data.get("name", "—"))
        self.sid_lbl.setText(f"@{data.get('sid', '—')}")

        if data.get("logo_local"):
            self.logo.set_image(data["logo_local"])
        else:
            self.logo.clear()

        # Remove any existing manufacturer logo decoration
        if self.mfr_logo_lbl:
            self.header_layout.removeWidget(self.mfr_logo_lbl)
            self.mfr_logo_lbl.deleteLater()
            self.mfr_logo_lbl = None

        # Add manufacturer logo decoration if org name matches a known manufacturer
        org_name = data.get("name", "")
        mfr_logo_path = self._get_manufacturer_logo_path(org_name)
        if mfr_logo_path:
            from src.ui.theme.icon_utils import load_tinted_icon
            tint_color = (0, 170, 255, 140)
            icon_size = 36   # was 48
            tinted_icon = load_tinted_icon(mfr_logo_path, tint_color, icon_size)
            if tinted_icon and not tinted_icon.isNull():
                from PyQt6.QtWidgets import QLabel as QLbl
                self.mfr_logo_lbl = QLbl()
                self.mfr_logo_lbl.setPixmap(tinted_icon.pixmap(icon_size, icon_size))
                self.mfr_logo_lbl.setFixedSize(icon_size, icon_size)
                self.mfr_logo_lbl.setStyleSheet("background: transparent; border: none;")
                self.mfr_logo_lbl.setToolTip(org_name)
                self.header_layout.addWidget(
                    self.mfr_logo_lbl,
                    alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
                )

        # Details
        self.f_archetype.set_value(data.get("archetype"))
        self.f_language.set_value(data.get("language"))
        self.f_commitment.set_value(data.get("commitment"))
        self.f_members.set_value(str(data.get("member_count", 0)))
        self.f_recruiting.set_value("YES" if data.get("recruiting") else "NO")
        self.f_roleplay.set_value("YES" if data.get("roleplay") else "NO")
        self.f_primary.set_value(data.get("focus_primary"))
        self.f_secondary.set_value(data.get("focus_secondary"))

        desc = data.get("description")
        if desc:
            self.desc_lbl.setText(desc)
            self.desc_lbl.setStyleSheet(
                f"color: {P.ON_SURFACE}; background: transparent; border: none;"
            )
        else:
            self.desc_lbl.setText("NO DESCRIPTION PROVIDED.")
            self.desc_lbl.setStyleSheet(
                f"color: {P.TEXT_DIM}; font-style: italic; background: transparent; border: none;"
            )