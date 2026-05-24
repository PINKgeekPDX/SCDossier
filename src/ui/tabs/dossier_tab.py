"""
src/ui/tabs/dossier_tab.py
DossierTab — the primary view displaying scraped citizen and organization information.
Uses GlassCard containers for the Aegis aesthetic.
"""

from PyQt6.QtCore import Qt, pyqtSlot, QSize
from PyQt6.QtGui import QColor, QPainter, QFont, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QPushButton,
    QFrame, QSizePolicy
)

from src.core.events import EventBus
from src.ui.theme import palette as P
from src.ui.theme.fonts import headline_lg, headline_md, font_inter, label_caps
from src.ui.theme.icon_utils import set_button_icon, load_icon
from src.ui.widgets.avatar_widget import AvatarWidget
from src.ui.widgets.data_field import DataField
from src.ui.widgets.badge_chip import BadgeChip
from src.ui.widgets.tech_label import TechLabel
from src.ui.widgets.progress_overlay import ProgressOverlay
from src.ui.widgets.search_input import SearchInput
from src.ui.widgets.glass_card import GlassCard
from src.ui.widgets.wrap_layout import WrapLayout
import os

class DossierTab(QWidget):
    """
    Displays the active profile using GlassCard containers.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_handle = ""
        self._current_data = None
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Top Action Bar ---
        action_bar = QWidget()
        action_bar.setFixedHeight(64)
        action_bar.setStyleSheet(f"background: {P.SURFACE_CONTAINER_LOW}; border-bottom: 1px solid {P.OUTLINE_VARIANT};")
        ab_layout = QHBoxLayout(action_bar)
        ab_layout.setContentsMargins(24, 10, 24, 10)
        ab_layout.setSpacing(12)

        self.search_input = SearchInput("ENTER RSI HANDLE...")
        self.search_input.returnPressed.connect(self._on_search)
        self.search_input.setFixedHeight(44)
        self.search_input.setToolTip("Enter an RSI handle (e.g., PINKgeekPDX) to search for a citizen profile")
        # Base styling is handled by SearchInput class - remove redundant inline style

        _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        search_icon = os.path.join(_PROJECT_ROOT, "assets", "icons", "misc", "icon_search.svg")
        archive_icon = os.path.join(_PROJECT_ROOT, "assets", "icons", "misc", "icon_save.svg")

        search_btn = QPushButton()
        search_btn.setProperty("class", "primary")
        search_btn.setFixedSize(56, 44)
        set_button_icon(search_btn, search_icon, (20, 20))
        search_btn.clicked.connect(self._on_search)
        search_btn.setToolTip("Search for the entered RSI handle")

        self.archive_btn = QPushButton()
        self.archive_btn.setProperty("class", "ghost")
        self.archive_btn.setFixedSize(56, 44)
        set_button_icon(self.archive_btn, archive_icon, (20, 20))
        self.archive_btn.setEnabled(False)
        self.archive_btn.clicked.connect(self._on_archive_clicked)
        self.archive_btn.setToolTip("Save the current profile to the archive")

        ab_layout.addWidget(self.search_input)
        ab_layout.addWidget(search_btn)
        ab_layout.addWidget(self.archive_btn)

        # --- Scrollable Content ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(24, 24, 24, 24)
        self.content_layout.setSpacing(20)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Empty state
        self.empty_lbl = QLabel("SEARCH FOR A CITIZEN TO VIEW THEIR DOSSIER")
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

        # CRITICAL FIX: add detail_container to content_layout so scraped data appears
        self.content_layout.addWidget(self.detail_container)

        scroll.setWidget(self.content_widget)

        main_layout.addWidget(action_bar)
        main_layout.addWidget(scroll)

        self.overlay = ProgressOverlay(self)

    def _build_detail(self) -> None:
        dl = QVBoxLayout(self.detail_container)
        dl.setContentsMargins(0, 0, 0, 0)
        dl.setSpacing(20)

        # Identity card
        self.identity_card = GlassCard(title="IDENTITY CORE")
        header_layout = QHBoxLayout()
        header_layout.setSpacing(20)
        self.avatar = AvatarWidget(size=120)

        name_vbox = QVBoxLayout()
        name_vbox.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        name_vbox.setSpacing(4)
        self.moniker_lbl = QLabel("—")
        self.moniker_lbl.setFont(headline_lg())
        self.moniker_lbl.setStyleSheet(f"color: {P.ON_SURFACE}; background: transparent; border: none;")
        self.moniker_lbl.setWordWrap(True)
        self.handle_lbl = QLabel("—")
        self.handle_lbl.setFont(headline_md())
        self.handle_lbl.setStyleSheet(f"color: {P.PRIMARY}; background: transparent; border: none;")
        name_vbox.addWidget(self.moniker_lbl)
        name_vbox.addWidget(self.handle_lbl)

        header_layout.addWidget(self.avatar)
        header_layout.addLayout(name_vbox)
        header_layout.addStretch()

        # Add RSI brand icon decoration
        rsi_logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "icons", "brand-icons", "sc-icon-brand-rsi.svg")
        if os.path.exists(rsi_logo_path):
            from PyQt6.QtGui import QPixmap
            rsi_pixmap = QPixmap(rsi_logo_path)
            if not rsi_pixmap.isNull():
                from PyQt6.QtWidgets import QLabel as QLbl
                rsi_logo_lbl = QLbl()
                rsi_logo_lbl.setPixmap(rsi_pixmap.scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                rsi_logo_lbl.setStyleSheet("background: transparent; border: none;")
                rsi_logo_lbl.setToolTip("RSI")
                header_layout.addWidget(rsi_logo_lbl)
        self.identity_card.content_layout.addLayout(header_layout)
        dl.addWidget(self.identity_card)

        # Details grid card
        self.grid_card = GlassCard(title="PROFILE DATA")
        grid_layout = QVBoxLayout()
        grid_row1 = QHBoxLayout()
        grid_row1.setSpacing(12)
        self.f_enlisted = DataField("ENLISTED")
        self.f_location = DataField("LOCATION")
        self.f_fluency = DataField("FLUENCY")
        grid_row1.addWidget(self.f_enlisted)
        grid_row1.addWidget(self.f_location)
        grid_row1.addWidget(self.f_fluency)
        grid_layout.addLayout(grid_row1)
        self.grid_card.content_layout.addLayout(grid_layout)
        dl.addWidget(self.grid_card)

        # Bio card
        self.bio_card = GlassCard(title="BIOGRAPHY")
        self.bio_lbl = QLabel("—")
        self.bio_lbl.setFont(font_inter(14))
        self.bio_lbl.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent; border: none;")
        self.bio_lbl.setWordWrap(True)
        self.bio_card.content_layout.addWidget(self.bio_lbl)
        dl.addWidget(self.bio_card)

        # Badges card
        self.badges_card = GlassCard(title="ACCREDITATIONS & CLEARANCES")
        self.badges_wrap = WrapLayout()
        self.badges_wrap.setMinimumHeight(40)
        self.badges_card.content_layout.addWidget(self.badges_wrap)
        dl.addWidget(self.badges_card)

        # Orgs card
        self.orgs_card = GlassCard(title="AFFILIATED ORGANIZATIONS")
        self.orgs_layout = QVBoxLayout()
        self.orgs_layout.setSpacing(12)
        self.orgs_card.content_layout.addLayout(self.orgs_layout)
        dl.addWidget(self.orgs_card)

        dl.addStretch()

    def _connect_signals(self) -> None:
        bus = EventBus.instance()
        bus.scrape_completed.connect(self._on_scrape_completed)
        bus.image_downloaded.connect(self._on_image_downloaded)
        bus.status_message.connect(self._on_status_msg)

    def _on_search(self) -> None:
        handle = self.search_input.text().strip()
        if handle:
            EventBus.instance().search_player_requested.emit(handle)

    def _on_archive_clicked(self) -> None:
        if self.current_handle:
            EventBus.instance().request_archive.emit(self.current_handle)

    @pyqtSlot(str, str)
    def _on_status_msg(self, msg: str, severity: str) -> None:
        if severity == "info" and ("INITIALIZING" in msg or "RETRIEVING" in msg):
            self.overlay.set_message(msg)
            self.overlay.show_overlay()
        elif severity in ("success", "error"):
            self.overlay.hide_overlay()

    @pyqtSlot(dict)
    def _on_scrape_completed(self, data: dict) -> None:
        self.overlay.hide_overlay()
        self.current_handle = data.get("handle", "")
        self._current_data = data
        self.search_input.clear()
        self.archive_btn.setEnabled(bool(self.current_handle))

        # Show detail, hide empty state
        self.empty_lbl.setVisible(False)
        self.detail_container.setVisible(True)

        # Header
        self.moniker_lbl.setText(data.get("moniker", "—"))
        self.handle_lbl.setText(f"@{data.get('handle', '—')}")

        if data.get("avatar_local"):
            self.avatar.set_image(data["avatar_local"])
        else:
            self.avatar.clear()

        # Details
        self.f_enlisted.set_value(data.get("enlisted"))
        self.f_location.set_value(data.get("location"))
        fluency = data.get("fluency", [])
        self.f_fluency.set_value(", ".join(fluency) if fluency else "—")

        bio = data.get("bio")
        if bio:
            self.bio_lbl.setText(bio)
            self.bio_lbl.setStyleSheet(f"color: {P.ON_SURFACE}; background: transparent; border: none;")
        else:
            self.bio_lbl.setText("NO BIOGRAPHY PROVIDED.")
            self.bio_lbl.setStyleSheet(f"color: {P.TEXT_DIM}; font-style: italic; background: transparent; border: none;")

        # Badges
        self.badges_wrap.clear()
        for b in data.get("badges", []):
            chip = BadgeChip(name=b.get("name", ""), image_path=b.get("image_local"))
            self.badges_wrap.addWidget(chip)

        # Orgs
        self._clear_orgs()
        orgs = data.get("orgs", [])
        if orgs:
            for o in orgs:
                self._add_org_widget(o)
        else:
            lbl = QLabel("NO AFFILIATIONS FOUND.")
            lbl.setFont(font_inter(13))
            lbl.setStyleSheet(f"color: {P.TEXT_DIM}; font-style: italic; background: transparent; border: none;")
            self.orgs_layout.addWidget(lbl)

    def _clear_orgs(self) -> None:
        while self.orgs_layout.count():
            item = self.orgs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _add_org_widget(self, org: dict) -> None:
        card = GlassCard()
        inner = QWidget()
        layout = QHBoxLayout(inner)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(16)

        avatar = AvatarWidget(size=52)
        if org.get("logo_local"):
            avatar.set_image(org["logo_local"])

        info_vbox = QVBoxLayout()
        info_vbox.setSpacing(2)
        info_vbox.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        name_lbl = QLabel(org.get("name", ""))
        name_lbl.setFont(font_inter(14, QFont.Weight.Bold))
        name_lbl.setStyleSheet(f"color: {P.ON_SURFACE}; background: transparent; border: none;")

        sid_rank = f"{org.get('sid', '')} • {org.get('rank', '')}"
        if org.get("is_main"):
            sid_rank += " (MAIN)"
        sub_lbl = QLabel(sid_rank)
        sub_lbl.setFont(font_inter(12))
        sub_lbl.setStyleSheet(f"color: {P.PRIMARY if org.get('is_main') else P.TEXT_DIM}; background: transparent; border: none;")

        info_vbox.addWidget(name_lbl)
        info_vbox.addWidget(sub_lbl)
        layout.addWidget(avatar)
        layout.addLayout(info_vbox)
        layout.addStretch()

        card.content_layout.addWidget(inner)
        self.orgs_layout.addWidget(card)

    @pyqtSlot(str, str)
    def _on_image_downloaded(self, url: str, local_path: str) -> None:
        """Refresh UI when images finish downloading, but only the specific image."""
        if not self._current_data:
            return

        data = self._current_data

        # Check if this is the avatar
        if data.get("avatar_local") == local_path:
            self.avatar.set_image(local_path)
            return

        # Check if this is a badge image
        for b in data.get("badges", []):
            if b.get("image_local") == local_path:
                # Re-populate badges to show the new images
                self.badges_wrap.clear()
                for badge in data.get("badges", []):
                    chip = BadgeChip(name=badge.get("name", ""), image_path=badge.get("image_local"))
                    self.badges_wrap.addWidget(chip)
                return

        # Check if this is an org logo
        for o in data.get("orgs", []):
            if o.get("logo_local") == local_path:
                self._clear_orgs()
                for org in data.get("orgs", []):
                    self._add_org_widget(org)
                return
