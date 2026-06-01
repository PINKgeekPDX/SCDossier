"""
src/ui/tabs/dossier_tab.py
DossierTab — the primary view displaying scraped citizen and organization information.
Uses GlassCard containers for the SCPINK aesthetic.

T4: Structural refactor — added DossierSubTabBar and QStackedWidget.
The action bar and all existing content widgets are UNCHANGED.
The scroll area is moved into stack page 0; page 1 holds the ReputationTab (added in T5).
"""

from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QSize
from PyQt6.QtGui import QColor, QPainter, QFont, QIcon, QPixmap, QPen
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QPushButton,
    QFrame, QSizePolicy, QStackedWidget
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
from src.ui.tabs.reputation_tab import ReputationTab
import os
from src.core.settings import SettingsManager


# ---------------------------------------------------------------------------
# DossierSubTabBar
# ---------------------------------------------------------------------------

class DossierSubTabBar(QWidget):
    """
    Custom sub-tab bar for the DossierTab with two buttons: DOSSIER and REPUTATION.

    Uses QPainter for rendering to avoid QSS conflicts with the existing stylesheet.
    Signal tab_changed emits "dossier" or "reputation" when the user clicks a tab.
    """

    tab_changed = pyqtSignal(str)   # "dossier" | "reputation"

    _TAB_IDS = ["dossier", "reputation"]
    _TAB_LABELS = {"dossier": "DOSSIER", "reputation": "REPUTATION"}

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._active: str = "dossier"
        self._hovered: str | None = None
        self.setFixedHeight(32)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_active(self, tab_id: str) -> None:
        """
        Switch the active visual state without emitting tab_changed.
        Called programmatically (e.g. after scrape completes).
        """
        if tab_id in self._TAB_IDS and tab_id != self._active:
            self._active = tab_id
            self.update()

    # ------------------------------------------------------------------
    # Hit testing
    # ------------------------------------------------------------------

    def _tab_rects(self) -> dict[str, "QRect"]:
        """Return bounding rect for each tab button."""
        from PyQt6.QtCore import QRect
        w = self.width()
        tab_w = w // 2
        return {
            "dossier":    QRect(0,         0, tab_w,      self.height()),
            "reputation": QRect(tab_w,     0, w - tab_w,  self.height()),
        }

    def _tab_at(self, x: int) -> str | None:
        for tid, rect in self._tab_rects().items():
            if rect.contains(x, self.height() // 2):
                return tid
        return None

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            tid = self._tab_at(event.position().toPoint().x())
            if tid and tid != self._active:
                self._active = tid
                self.update()
                self.tab_changed.emit(tid)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        hovered = self._tab_at(event.position().toPoint().x())
        if hovered != self._hovered:
            self._hovered = hovered
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        if self._hovered is not None:
            self._hovered = None
            self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor(P.SURFACE_CONTAINER_LOW))

        # Border bottom
        pen = QPen(QColor(P.OUTLINE_VARIANT))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)

        rects = self._tab_rects()
        font = label_caps()
        font.setPointSize(9)

        for tid, rect in rects.items():
            is_active = tid == self._active
            is_hovered = tid == self._hovered and not is_active

            # Tab fill
            if is_active:
                painter.fillRect(rect, QColor(P.SURFACE_CONTAINER))
            elif is_hovered:
                painter.fillRect(rect, QColor(0, 170, 255, 15))
            else:
                painter.fillRect(rect, QColor(0, 0, 0, 0))

            # Separator between tabs
            if tid == "reputation":
                sep_pen = QPen(QColor(P.OUTLINE_VARIANT))
                sep_pen.setWidth(1)
                painter.setPen(sep_pen)
                painter.drawLine(rect.left(), 4, rect.left(), self.height() - 5)

            # Active indicator bar (top edge)
            if is_active:
                bar_pen = QPen(QColor(P.PRIMARY))
                bar_pen.setWidth(2)
                painter.setPen(bar_pen)
                painter.drawLine(rect.left() + 2, 0, rect.right() - 2, 0)

            # Label
            if is_active:
                painter.setPen(QPen(QColor(P.PRIMARY)))
            elif is_hovered:
                painter.setPen(QPen(QColor(P.ON_SURFACE)))
            else:
                painter.setPen(QPen(QColor(P.TEXT_DIM)))

            painter.setFont(font)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._TAB_LABELS[tid])

        painter.end()


# ---------------------------------------------------------------------------
# ClickableOrgCard (unchanged)
# ---------------------------------------------------------------------------

class ClickableOrgCard(GlassCard):
    """
    A GlassCard that represents an organization affiliation. Clicking anywhere
    on the card (except the avatar which handles its own clicks) switches to the
    Organization tab and searches for this organization's SID.
    """
    def __init__(self, sid: str, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.sid = sid
        self._hovered = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"Click card to view organization @{sid} profile")
        self.setMouseTracking(True)

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            from PyQt6.QtCore import QTimer
            from src.core.events import EventBus
            
            def _handle_click():
                EventBus.instance().navigate_to_tab.emit("organization")
                EventBus.instance().request_org_scrape.emit(self.sid)
                
            QTimer.singleShot(0, _handle_click)
            event.accept()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self._hovered:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = self.rect()
            painter.fillRect(rect, QColor(0, 170, 255, 12))
            painter.end()


# ---------------------------------------------------------------------------
# DossierTab
# ---------------------------------------------------------------------------

class DossierTab(QWidget):
    """
    Displays the active profile using GlassCard containers.

    T4 structural changes:
      - DossierSubTabBar inserted below the action bar
      - QStackedWidget holds page 0 (existing scroll) and page 1 (ReputationTab placeholder)
      - All existing action bar widgets and self.* content references are UNCHANGED
      - ProgressOverlay remains a child of DossierTab (covers the full tab including sub-bar)
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        from src.services.cache_manager import CacheManager
        self.cache_mgr = CacheManager()
        self.current_handle = ""
        self._current_data = None
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Top Action Bar — compact (UNCHANGED) ---
        action_bar = QWidget()
        action_bar.setFixedHeight(50)   # was 64
        action_bar.setStyleSheet(
            f"background: {P.SURFACE_CONTAINER_LOW}; border-bottom: 1px solid {P.OUTLINE_VARIANT};"
        )
        ab_layout = QHBoxLayout(action_bar)
        ab_layout.setContentsMargins(16, 7, 16, 7)   # was 24,10,24,10
        ab_layout.setSpacing(8)                        # was 12

        self.search_input = SearchInput("ENTER RSI HANDLE...", history_type="player")
        self.search_input.returnPressed.connect(self._on_search)
        self.search_input.setFixedHeight(36)   # was 44
        self.search_input.setToolTip(
            "Enter an RSI handle (e.g., PINKgeekPDX) to search for a citizen profile"
        )

        from src.core.paths import get_asset_path
        search_icon = get_asset_path("assets/icons/misc/icon_search.svg")
        archive_icon = get_asset_path("assets/icons/misc/icon_save.svg")

        search_btn = QPushButton()
        search_btn.setProperty("class", "primary")
        search_btn.setFixedSize(44, 36)   # was 56,44
        set_button_icon(search_btn, search_icon, (16, 16))
        search_btn.clicked.connect(self._on_search)
        search_btn.setToolTip("Search for the entered RSI handle")

        self.archive_btn = QPushButton()
        self.archive_btn.setProperty("class", "ghost")
        self.archive_btn.setFixedSize(44, 36)
        set_button_icon(self.archive_btn, archive_icon, (16, 16))
        self.archive_btn.setEnabled(False)
        self.archive_btn.clicked.connect(self._on_archive_clicked)
        self.archive_btn.setToolTip("Save the current profile to the archive")

        ab_layout.addWidget(self.search_input)
        ab_layout.addWidget(search_btn)
        ab_layout.addWidget(self.archive_btn)

        # --- Sub-Tab Bar (NEW, T4) ---
        self.sub_tab_bar = DossierSubTabBar()

        # --- Stacked Widget (NEW, T4) ---
        self.stack = QStackedWidget()

        # Page 0: Existing scrollable dossier content (moved, not recreated)
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

        self.content_layout.addWidget(self.detail_container)

        scroll.setWidget(self.content_widget)
        self.stack.addWidget(scroll)   # index 0 — dossier

        # Page 1: ReputationTab (T5)
        self.reputation_tab = ReputationTab()
        self.stack.addWidget(self.reputation_tab)   # index 1 — reputation

        # Assemble main layout
        main_layout.addWidget(action_bar)
        main_layout.addWidget(self.sub_tab_bar)
        main_layout.addWidget(self.stack)

        # ProgressOverlay MUST be last — covers the full DossierTab (not the stack)
        self.overlay = ProgressOverlay(self)

    def _build_detail(self) -> None:
        dl = QVBoxLayout(self.detail_container)
        dl.setContentsMargins(0, 0, 0, 0)
        dl.setSpacing(12)   # was 20

        # Identity card
        self.identity_card = GlassCard(title="IDENTITY CORE")
        header_layout = QHBoxLayout()
        header_layout.setSpacing(14)   # was 20
        self.avatar = AvatarWidget(size=90)   # was 120

        name_vbox = QVBoxLayout()
        name_vbox.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        name_vbox.setSpacing(2)   # was 4
        self.moniker_lbl = QLabel("—")
        self.moniker_lbl.setFont(headline_lg())
        self.moniker_lbl.setStyleSheet(
            f"color: {P.ON_SURFACE}; background: transparent; border: none;"
        )
        self.moniker_lbl.setWordWrap(True)
        self.handle_lbl = QLabel("—")
        self.handle_lbl.setFont(headline_md())
        self.handle_lbl.setStyleSheet(
            f"color: {P.PRIMARY}; background: transparent; border: none;"
        )
        name_vbox.addWidget(self.moniker_lbl)
        name_vbox.addWidget(self.handle_lbl)

        header_layout.addWidget(self.avatar)
        header_layout.addLayout(name_vbox)
        header_layout.addStretch()

        # RSI brand icon decoration
        from src.core.paths import get_asset_path
        rsi_logo_path = get_asset_path("assets/icons/brand-icons/sc-icon-brand-rsi.svg")
        if os.path.exists(rsi_logo_path):
            from src.ui.theme.icon_utils import load_tinted_icon
            tint_color = (0, 170, 255, 140)
            icon_size = 36   # was 48
            tinted_icon = load_tinted_icon(rsi_logo_path, tint_color, icon_size)
            if tinted_icon and not tinted_icon.isNull():
                from PyQt6.QtWidgets import QLabel as QLbl
                rsi_logo_lbl = QLbl()
                rsi_logo_lbl.setPixmap(tinted_icon.pixmap(icon_size, icon_size))
                rsi_logo_lbl.setFixedSize(icon_size, icon_size)
                rsi_logo_lbl.setStyleSheet("background: transparent; border: none;")
                rsi_logo_lbl.setToolTip("RSI")
                header_layout.addWidget(
                    rsi_logo_lbl,
                    alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
                )
        self.identity_card.content_layout.addLayout(header_layout)
        dl.addWidget(self.identity_card)

        # Details grid card
        self.grid_card = GlassCard(title="PROFILE DATA")
        grid_layout = QVBoxLayout()
        grid_row1 = QHBoxLayout()
        grid_row1.setSpacing(8)   # was 12
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
        self.bio_lbl.setFont(font_inter(12))   # was 14
        self.bio_lbl.setStyleSheet(
            f"color: {P.TEXT_DIM}; background: transparent; border: none;"
        )
        self.bio_lbl.setWordWrap(True)
        self.bio_card.content_layout.addWidget(self.bio_lbl)
        dl.addWidget(self.bio_card)

        # Badges card
        self.badges_card = GlassCard(title="ACCREDITATIONS & CLEARANCES")
        self.badges_wrap = WrapLayout()
        self.badges_wrap.setMinimumHeight(36)   # was 44
        self.badges_card.content_layout.addWidget(self.badges_wrap)
        dl.addWidget(self.badges_card)

        # Orgs card
        self.orgs_card = GlassCard(title="AFFILIATED ORGANIZATIONS")
        self.orgs_layout = QVBoxLayout()
        self.orgs_layout.setSpacing(8)   # was 12
        self.orgs_card.content_layout.addLayout(self.orgs_layout)
        dl.addWidget(self.orgs_card)

        dl.addStretch()
        self._setup_archive_glow()

    def _connect_signals(self) -> None:
        bus = EventBus.instance()
        bus.scrape_completed.connect(self._on_scrape_completed)
        bus.image_downloaded.connect(self._on_image_downloaded)
        bus.status_message.connect(self._on_status_msg)
        bus.archive_updated.connect(self._on_archive_updated)
        # Sub-tab navigation
        self.sub_tab_bar.tab_changed.connect(self._on_sub_tab_changed)

    # ------------------------------------------------------------------
    # Sub-tab navigation (NEW, T4)
    # ------------------------------------------------------------------

    @pyqtSlot(str)
    def _on_sub_tab_changed(self, tab_id: str) -> None:
        """Switch the stacked widget page in response to sub-tab clicks."""
        if tab_id == "dossier":
            self.stack.setCurrentIndex(0)
        elif tab_id == "reputation":
            self.stack.setCurrentIndex(1)

    # ------------------------------------------------------------------
    # Existing public / slot methods (UNCHANGED — extended where needed)
    # ------------------------------------------------------------------

    def _clear_results(self) -> None:
        """Clear all displayed dossier results."""
        self.current_handle = ""
        self._current_data = None
        self.search_input.clear()
        self.detail_container.setVisible(False)
        self.empty_lbl.setVisible(True)
        self.archive_btn.setEnabled(False)
        if hasattr(self, '_archive_pulse_anim'):
            self._archive_pulse_anim.stop()
        # Reset to dossier sub-tab
        self.sub_tab_bar.set_active("dossier")
        self.stack.setCurrentIndex(0)
        # Clear reputation tab if present (T5 adds this reference)
        if hasattr(self, 'reputation_tab'):
            self.reputation_tab.clear()

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

        self.empty_lbl.setVisible(False)
        self.detail_container.setVisible(True)

        self.moniker_lbl.setText(data.get("moniker", "—"))
        self.handle_lbl.setText(f"@{data.get('handle', '—')}")

        if data.get("avatar_local"):
            self.avatar.set_image(data["avatar_local"])
        else:
            self.avatar.clear()

        self.f_enlisted.set_value(data.get("enlisted"))
        self.f_location.set_value(data.get("location"))
        fluency = data.get("fluency", [])
        self.f_fluency.set_value(", ".join(fluency) if fluency else "—")

        bio = data.get("bio")
        if bio:
            self.bio_lbl.setText(bio)
            self.bio_lbl.setStyleSheet(
                f"color: {P.ON_SURFACE}; background: transparent; border: none;"
            )
        else:
            self.bio_lbl.setText("NO BIOGRAPHY PROVIDED.")
            self.bio_lbl.setStyleSheet(
                f"color: {P.TEXT_DIM}; font-style: italic; background: transparent; border: none;"
            )

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
            lbl.setFont(font_inter(11))
            lbl.setStyleSheet(
                f"color: {P.TEXT_DIM}; font-style: italic; background: transparent; border: none;"
            )
            self.orgs_layout.addWidget(lbl)

        self._update_archive_glow()

        # Trigger reputation fetch if available (T5 sets self.reputation_tab)
        if hasattr(self, 'reputation_tab') and self.current_handle:
            self.reputation_tab.load_player(self.current_handle)
            EventBus.instance().request_reputation_fetch.emit(self.current_handle)

    def _clear_orgs(self) -> None:
        while self.orgs_layout.count():
            item = self.orgs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _add_org_widget(self, org: dict) -> None:
        sid = org.get("sid", "")
        card = ClickableOrgCard(sid, self)
        inner = QWidget()
        layout = QHBoxLayout(inner)
        layout.setContentsMargins(8, 6, 8, 6)   # was 12,8,12,8
        layout.setSpacing(10)                     # was 16

        avatar = AvatarWidget(size=42)   # was 52
        if org.get("logo_local"):
            avatar.set_image(org["logo_local"])

        info_vbox = QVBoxLayout()
        info_vbox.setSpacing(1)   # was 2
        info_vbox.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        name_lbl = QLabel(org.get("name", ""))
        name_lbl.setFont(font_inter(12, QFont.Weight.Bold))   # was 14
        name_lbl.setStyleSheet(
            f"color: {P.ON_SURFACE}; background: transparent; border: none;"
        )

        sid_rank = f"{org.get('sid', '')} • {org.get('rank', '')}"
        if org.get("is_main"):
            sid_rank += " (MAIN)"
        sub_lbl = QLabel(sid_rank)
        sub_lbl.setFont(font_inter(10))   # was 12
        sub_lbl.setStyleSheet(
            f"color: {P.PRIMARY if org.get('is_main') else P.TEXT_DIM}; "
            f"background: transparent; border: none;"
        )

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

        if data.get("avatar_local") == local_path:
            self.avatar.set_image(local_path)
            return

        for b in data.get("badges", []):
            if b.get("image_local") == local_path:
                self.badges_wrap.clear()
                for badge in data.get("badges", []):
                    chip = BadgeChip(name=badge.get("name", ""), image_path=badge.get("image_local"))
                    self.badges_wrap.addWidget(chip)
                return

        for o in data.get("orgs", []):
            if o.get("logo_local") == local_path:
                self._clear_orgs()
                for org in data.get("orgs", []):
                    self._add_org_widget(org)
                return

    def _setup_archive_glow(self) -> None:
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        from PyQt6.QtCore import QPropertyAnimation, QEasingCurve
        from PyQt6.QtGui import QColor

        self._archive_glow_shadow = QGraphicsDropShadowEffect(self.archive_btn)
        self._archive_glow_shadow.setBlurRadius(0)
        self._archive_glow_shadow.setColor(QColor(0, 170, 255, 180))
        self._archive_glow_shadow.setOffset(0, 0)
        self.archive_btn.setGraphicsEffect(self._archive_glow_shadow)

        self._archive_pulse_anim = QPropertyAnimation(self._archive_glow_shadow, b"blurRadius")
        self._archive_pulse_anim.setDuration(1500)
        self._archive_pulse_anim.setStartValue(0)
        self._archive_pulse_anim.setKeyValueAt(0.5, 10)
        self._archive_pulse_anim.setEndValue(0)
        self._archive_pulse_anim.setLoopCount(-1)
        self._archive_pulse_anim.setEasingCurve(QEasingCurve.Type.InOutSine)

    @pyqtSlot()
    def _on_archive_updated(self) -> None:
        self._update_archive_glow()

    def _update_archive_glow(self) -> None:
        if not self.current_handle:
            self._archive_pulse_anim.stop()
            self._archive_glow_shadow.setBlurRadius(0)
            return

        if self.cache_mgr.is_archived(self.current_handle):
            self._archive_pulse_anim.stop()
            self._archive_glow_shadow.setBlurRadius(0)
        else:
            self._archive_pulse_anim.start()
