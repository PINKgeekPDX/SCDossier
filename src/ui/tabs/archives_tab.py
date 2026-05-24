"""
src/ui/tabs/archives_tab.py
ArchivesTab — two-pane layout with collapsible list, filter/sort, and detail pane.
"""

from pathlib import Path
from PyQt6.QtCore import Qt, pyqtSlot, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QSplitter,
    QScrollArea, QFrame, QGridLayout, QComboBox, QLineEdit
)

from src.core.events import EventBus
from src.core.paths import PathManager
from src.services.archive_manager import ArchiveManager
from src.ui.theme import palette as P
from src.ui.theme.fonts import font_inter, label_caps, headline_lg, headline_md, font_mono
from src.ui.widgets.avatar_widget import AvatarWidget
from src.ui.widgets.data_field import DataField
from src.ui.widgets.badge_chip import BadgeChip
from src.ui.widgets.wrap_layout import WrapLayout
from src.ui.widgets.tech_label import TechLabel
from src.ui.widgets.glass_card import GlassCard
from src.ui.widgets.confirm_dialog import show_confirm


class ArchiveItemWidget(QWidget):
    """Compact list item for the archive list pane."""

    def __init__(self, data: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.handle = data.get("handle", "")
        self._data = data
        self._build_ui(data)

    def _build_ui(self, data: dict) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        self.setStyleSheet(f"""
            ArchiveItemWidget {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
            }}
            ArchiveItemWidget:hover {{
                border-color: {P.GLASS_BORDER_SUBTLE};
                background-color: rgba(0, 170, 255, 0.05);
            }}
        """)

        avatar = AvatarWidget(size=40)
        if data.get("avatar_local"):
            avatar.set_image(data["avatar_local"])

        info_vbox = QVBoxLayout()
        info_vbox.setSpacing(2)
        info_vbox.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        moniker = data.get("moniker", "—")
        handle = data.get("handle", "—")
        date_str = data.get("synced_at", data.get("archived_at", "—"))[:10]

        name_lbl = QLabel(f"{moniker}")
        name_lbl.setFont(font_inter(13, QFont.Weight.Bold))
        name_lbl.setStyleSheet(f"color: {P.ON_SURFACE}; background: transparent; border: none;")

        handle_lbl = QLabel(f"@{handle}  •  {date_str}")
        handle_lbl.setFont(font_mono(10))
        handle_lbl.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent; border: none;")

        info_vbox.addWidget(name_lbl)
        info_vbox.addWidget(handle_lbl)

        layout.addWidget(avatar)
        layout.addLayout(info_vbox)
        layout.addStretch()


class ArchivesTab(QWidget):
    """
    Two-pane archive view:
    - Left: collapsible list with filter/sort
    - Right: dossier-style detail pane
    """

    def __init__(self, archive_mgr: ArchiveManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.archive_mgr = archive_mgr
        self._profiles = []
        self._selected_handle = ""
        self._build_ui()
        self.refresh_list()
        EventBus.instance().archive_updated.connect(self.refresh_list)
        EventBus.instance().scrape_completed.connect(self._on_profile_loaded)

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header bar
        header_bar = QWidget()
        header_bar.setFixedHeight(56)
        header_bar.setStyleSheet(f"background: {P.SURFACE_CONTAINER_LOW}; border-bottom: 1px solid {P.OUTLINE_VARIANT};")
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(24, 8, 24, 8)

        header_lbl = QLabel("ARCHIVED PROFILES")
        header_lbl.setFont(label_caps())
        header_lbl.setStyleSheet(f"color: {P.PRIMARY}; letter-spacing: 0.15em; background: transparent; border: none;")
        header_layout.addWidget(header_lbl)
        header_layout.addStretch()

        main_layout.addWidget(header_bar)

        # Splitter for two-pane layout
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1)
        self.splitter.setStyleSheet(f"QSplitter::handle {{ background-color: {P.OUTLINE_VARIANT}; }}")

        # --- LEFT PANE: List ---
        left_widget = QWidget()
        left_widget.setMinimumWidth(200)
        left_widget.setMaximumWidth(320)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        # Filter input
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("FILTER ARCHIVES...")
        self.filter_input.setFont(font_mono(10))
        self.filter_input.setFixedHeight(32)
        self.filter_input.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(10, 20, 30, 0.8);
                color: {P.ON_SURFACE};
                border: 1px solid {P.OUTLINE};
                border-radius: 4px;
                padding: 0 8px;
            }}
            QLineEdit:focus {{
                border: 1px solid {P.PRIMARY};
                background: rgba(15, 30, 45, 0.9);
            }}
        """)
        self.filter_input.textChanged.connect(self._apply_filter)
        left_layout.addWidget(self.filter_input)

        # Sort dropdown
        sort_layout = QHBoxLayout()
        sort_lbl = TechLabel("SORT BY")
        sort_lbl.setFixedWidth(50)
        self.sort_combo = QComboBox()
        self.sort_combo.setFont(font_mono(10))
        self.sort_combo.setFixedHeight(28)
        self.sort_combo.setStyleSheet(f"""
            QComboBox {{
                background: rgba(10, 20, 30, 0.8);
                color: {P.ON_SURFACE};
                border: 1px solid {P.OUTLINE};
                border-radius: 4px;
                padding: 0 8px;
            }}
            QComboBox:focus {{
                border: 1px solid {P.PRIMARY};
            }}
            QComboBox::drop-down {{ border: none; }}
        """)
        self.sort_combo.addItem("Name A-Z", "name_asc")
        self.sort_combo.addItem("Name Z-A", "name_desc")
        self.sort_combo.addItem("Date Archived", "date_archived")
        self.sort_combo.addItem("Last Synced", "date_synced")
        self.sort_combo.currentIndexChanged.connect(self._apply_sort)
        sort_layout.addWidget(sort_lbl)
        sort_layout.addWidget(self.sort_combo)
        left_layout.addLayout(sort_layout)

        # List
        self.list_widget = QListWidget()
        self.list_widget.setFrameShape(QListWidget.Shape.NoFrame)
        self.list_widget.setStyleSheet("QListWidget { background: transparent; outline: none; } QListWidget::item { background: transparent; }")
        self.list_widget.setSpacing(4)
        self.list_widget.currentRowChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self.list_widget)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        import os
        from PyQt6.QtGui import QIcon
        _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        sync_icon = os.path.join(_PROJECT_ROOT, "assets", "icons", "Icons", "Refresh.png")
        export_icon = os.path.join(_PROJECT_ROOT, "assets", "icons", "misc", "icon_file.svg")
        delete_icon = os.path.join(_PROJECT_ROOT, "assets", "icons", "Icons", "No_Access.png")

        self.sync_btn = QPushButton()
        self.sync_btn.setProperty("class", "ghost")
        self.sync_btn.setFixedHeight(36)
        if os.path.exists(sync_icon):
            self.sync_btn.setIcon(QIcon(sync_icon))
            self.sync_btn.setIconSize(QSize(20, 20))
        self.sync_btn.setEnabled(False)
        self.sync_btn.clicked.connect(self._on_sync)
        self.sync_btn.setToolTip("Sync Archive")

        self.export_btn = QPushButton()
        self.export_btn.setProperty("class", "ghost")
        self.export_btn.setFixedHeight(36)
        if os.path.exists(export_icon):
            self.export_btn.setIcon(QIcon(export_icon))
            self.export_btn.setIconSize(QSize(20, 20))
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._on_export)
        self.export_btn.setToolTip("Export Archive")

        self.delete_btn = QPushButton()
        self.delete_btn.setProperty("class", "danger")
        self.delete_btn.setFixedHeight(36)
        if os.path.exists(delete_icon):
            self.delete_btn.setIcon(QIcon(delete_icon))
            self.delete_btn.setIconSize(QSize(20, 20))
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._on_delete)
        self.delete_btn.setToolTip("Delete Archive")

        btn_layout.addWidget(self.sync_btn)
        btn_layout.addWidget(self.export_btn)
        btn_layout.addWidget(self.delete_btn)
        left_layout.addLayout(btn_layout)

        # --- RIGHT PANE: Detail ---
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_scroll.setStyleSheet("background: transparent;")

        self.detail_widget = QWidget()
        self.detail_layout = QVBoxLayout(self.detail_widget)
        self.detail_layout.setContentsMargins(24, 24, 24, 24)
        self.detail_layout.setSpacing(20)
        self.detail_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Empty state
        self.empty_state = QLabel("SELECT AN ARCHIVED PROFILE TO VIEW DETAILS")
        self.empty_state.setFont(label_caps())
        self.empty_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent;")
        self.detail_layout.addStretch()
        self.detail_layout.addWidget(self.empty_state)
        self.detail_layout.addStretch()

        # Detail content (hidden until selection)
        self.detail_content = QWidget()
        self.detail_content.setVisible(False)
        self._build_detail_content()

        # CRITICAL FIX: add detail_content to detail_layout so archive detail view works
        self.detail_layout.addWidget(self.detail_content)

        right_scroll.setWidget(self.detail_widget)

        self.splitter.addWidget(left_widget)
        self.splitter.addWidget(right_scroll)
        self.splitter.setSizes([260, 800])

        main_layout.addWidget(self.splitter)

    def _build_detail_content(self) -> None:
        """Build the dossier-style detail view."""
        dl = QVBoxLayout(self.detail_content)
        dl.setContentsMargins(0, 0, 0, 0)
        dl.setSpacing(20)

        # Profile header card
        self.detail_header_card = GlassCard(title="IDENTITY CORE")
        header_layout = QHBoxLayout()
        header_layout.setSpacing(20)

        self.detail_avatar = AvatarWidget(size=120)
        self.detail_moniker = QLabel("—")
        self.detail_moniker.setFont(headline_lg())
        self.detail_moniker.setStyleSheet(f"color: {P.ON_SURFACE}; background: transparent; border: none;")
        self.detail_handle = QLabel("—")
        self.detail_handle.setFont(headline_md())
        self.detail_handle.setStyleSheet(f"color: {P.PRIMARY}; background: transparent; border: none;")

        info_vbox = QVBoxLayout()
        info_vbox.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        info_vbox.setSpacing(4)
        info_vbox.addWidget(self.detail_moniker)
        info_vbox.addWidget(self.detail_handle)

        header_layout.addWidget(self.detail_avatar)
        header_layout.addLayout(info_vbox)
        header_layout.addStretch()

        self.detail_header_card.content_layout.addLayout(header_layout)
        dl.addWidget(self.detail_header_card)

        # Details grid
        self.detail_grid_card = GlassCard(title="PROFILE DATA")
        grid = QGridLayout()
        grid.setSpacing(12)
        self.detail_enlisted = DataField("ENLISTED")
        self.detail_location = DataField("LOCATION")
        self.detail_fluency = DataField("FLUENCY")
        self.detail_archived = DataField("ARCHIVED")
        self.detail_synced = DataField("LAST SYNCED")
        grid.addWidget(self.detail_enlisted, 0, 0)
        grid.addWidget(self.detail_location, 0, 1)
        grid.addWidget(self.detail_fluency, 0, 2)
        grid.addWidget(self.detail_archived, 1, 0)
        grid.addWidget(self.detail_synced, 1, 1)
        self.detail_grid_card.content_layout.addLayout(grid)
        dl.addWidget(self.detail_grid_card)

        # Bio card
        self.detail_bio_card = GlassCard(title="BIOGRAPHY")
        self.detail_bio = QLabel("—")
        self.detail_bio.setFont(font_inter(14))
        self.detail_bio.setStyleSheet(f"color: {P.ON_SURFACE}; background: transparent; border: none;")
        self.detail_bio.setWordWrap(True)
        self.detail_bio_card.content_layout.addWidget(self.detail_bio)
        dl.addWidget(self.detail_bio_card)

        # Badges card
        self.detail_badges_card = GlassCard(title="ACCREDITATIONS")
        self.detail_badges_wrap = WrapLayout()
        self.detail_badges_wrap.setMinimumHeight(40)
        self.detail_badges_card.content_layout.addWidget(self.detail_badges_wrap)
        dl.addWidget(self.detail_badges_card)

        # Orgs card
        self.detail_orgs_card = GlassCard(title="ORGANIZATIONS")
        self.detail_orgs_layout = QVBoxLayout()
        self.detail_orgs_layout.setSpacing(12)
        self.detail_orgs_card.content_layout.addLayout(self.detail_orgs_layout)
        dl.addWidget(self.detail_orgs_card)

        dl.addStretch()

    @pyqtSlot()
    def refresh_list(self) -> None:
        self._profiles = self.archive_mgr.list_archived_profiles()
        self._refresh_display()

    def _apply_filter(self) -> None:
        """Legacy wrapper — delegates to consolidated _refresh_display."""
        self._refresh_display()

    def _apply_sort(self) -> None:
        """Legacy wrapper — delegates to consolidated _refresh_display."""
        self._refresh_display()

    def _refresh_display(self) -> None:
        """Consolidated filter + sort method."""
        query = self.filter_input.text().lower()
        profiles = [p for p in self._profiles if query in p.get("handle", "").lower() or query in p.get("moniker", "").lower()]

        sort_key = self.sort_combo.currentData()
        if sort_key == "name_asc":
            profiles.sort(key=lambda p: p.get("moniker", p.get("handle", "")).lower())
        elif sort_key == "name_desc":
            profiles.sort(key=lambda p: p.get("moniker", p.get("handle", "")).lower(), reverse=True)
        elif sort_key == "date_archived":
            profiles.sort(key=lambda p: p.get("archived_at", ""), reverse=True)
        elif sort_key == "date_synced":
            profiles.sort(key=lambda p: p.get("synced_at", ""), reverse=True)

        self._populate_list(profiles)

    def _populate_list(self, profiles: list) -> None:
        self.list_widget.clear()
        for p in profiles:
            item = QListWidgetItem(self.list_widget)
            widget = ArchiveItemWidget(p)
            item.setSizeHint(QSize(0, 72))
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)

    def _on_selection_changed(self, row: int) -> None:
        if row < 0:
            return
        item = self.list_widget.item(row)
        widget = self.list_widget.itemWidget(item)
        if widget and hasattr(widget, "handle"):
            self._selected_handle = widget.handle
            self._load_detail(self._selected_handle)
            self.sync_btn.setEnabled(True)
            self.export_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)

    def _load_detail(self, handle: str) -> None:
        data = self.archive_mgr.load_archived_profile(handle)
        if not data:
            return

        self.empty_state.setVisible(False)
        self.detail_content.setVisible(True)

        self.detail_moniker.setText(data.get("moniker", "—"))
        self.detail_handle.setText(f"@{data.get('handle', '—')}")

        if data.get("avatar_local"):
            self.detail_avatar.set_image(data["avatar_local"])
        else:
            self.detail_avatar.clear()

        self.detail_enlisted.set_value(data.get("enlisted"))
        self.detail_location.set_value(data.get("location"))
        fluency = data.get("fluency", [])
        self.detail_fluency.set_value(", ".join(fluency) if fluency else "—")
        self.detail_archived.set_value(data.get("archived_at", "—")[:10])
        self.detail_synced.set_value(data.get("synced_at", "—")[:10])

        bio = data.get("bio")
        if bio:
            self.detail_bio.setText(bio)
            self.detail_bio.setStyleSheet(f"color: {P.ON_SURFACE}; background: transparent; border: none;")
        else:
            self.detail_bio.setText("NO BIOGRAPHY PROVIDED.")
            self.detail_bio.setStyleSheet(f"color: {P.TEXT_DIM}; font-style: italic; background: transparent; border: none;")

        # Badges
        self._clear_layout(self.detail_badges_wrap.layout() if self.detail_badges_wrap.layout() else None)
        self.detail_badges_wrap.clear()
        for b in data.get("badges", []):
            chip = BadgeChip(name=b.get("name", ""), image_path=b.get("image_local"))
            self.detail_badges_wrap.addWidget(chip)

        # Orgs
        self._clear_layout(self.detail_orgs_layout)
        orgs = data.get("orgs", [])
        if orgs:
            for o in orgs:
                self._add_org_card(o)
        else:
            lbl = QLabel("NO AFFILIATIONS FOUND.")
            lbl.setFont(font_inter(13))
            lbl.setStyleSheet(f"color: {P.TEXT_DIM}; font-style: italic; background: transparent; border: none;")
            self.detail_orgs_layout.addWidget(lbl)

    def _add_org_card(self, org: dict) -> None:
        card = GlassCard()
        inner = QWidget()
        layout = QHBoxLayout(inner)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        avatar = AvatarWidget(size=48)
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
        sub_lbl.setFont(font_mono(11))
        sub_lbl.setStyleSheet(f"color: {P.PRIMARY if org.get('is_main') else P.TEXT_DIM}; background: transparent; border: none;")

        info_vbox.addWidget(name_lbl)
        info_vbox.addWidget(sub_lbl)
        layout.addWidget(avatar)
        layout.addLayout(info_vbox)
        layout.addStretch()

        card.content_layout.addWidget(inner)
        self.detail_orgs_layout.addWidget(card)

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_sync(self) -> None:
        if self._selected_handle:
            EventBus.instance().request_sync.emit(self._selected_handle)

    def _on_export(self) -> None:
        if not self._selected_handle:
            return
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Export Directory", str(PathManager.instance().documents_root)
        )
        if dir_path:
            EventBus.instance().request_export_archive.emit(self._selected_handle, dir_path)

    def _on_delete(self) -> None:
        if not self._selected_handle:
            return
        msg = f"Permanently delete archived profile for {self._selected_handle}?"
        if show_confirm("DELETE ARCHIVE", msg, parent=self.window(), danger=True):
            EventBus.instance().request_delete_archive.emit(self._selected_handle)

    @pyqtSlot(dict)
    def _on_profile_loaded(self, data: dict) -> None:
        """Refresh list when a profile is loaded/scraped."""
        self.refresh_list()
        # If the synced/loaded profile is currently selected, update detail view
        if data.get("handle") == self._selected_handle:
            self._load_detail(self._selected_handle)
