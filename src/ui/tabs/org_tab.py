"""
src/ui/tabs/org_tab.py
OrganizationTab — displays standalone organization profile information.
Uses GlassCard containers for the SCPINK aesthetic.
"""

import os
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QSize, QRectF, QRect, QModelIndex, QTimer
from PyQt6.QtGui import QFont, QFontMetrics, QIcon, QPixmap, QPainter, QPainterPath, QColor, QBrush, QPen
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QPushButton,
    QFrame, QGridLayout, QStackedWidget, QSizePolicy
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
from src.core.paths import get_asset_path


class _BannerBg(QWidget):
    """Full-size background widget that paints a pixmap covering its area (cover-fit)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    def set_pixmap(self, pixmap):
        self._pixmap = pixmap
        self.update()

    def clear_pixmap(self):
        self._pixmap = None
        self.update()

    def paintEvent(self, event):
        if self._pixmap is None or self._pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        cw, ch = self.width(), self.height()
        if cw <= 0 or ch <= 0:
            painter.end()
            return
        scaled = self._pixmap.scaled(
            cw, ch,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )
        if scaled.width() > cw or scaled.height() > ch:
            x = (scaled.width() - cw) // 2
            y = (scaled.height() - ch) // 2
            scaled = scaled.copy(x, y, cw, ch)
        painter.drawPixmap(0, 0, scaled)
        painter.end()


class _MemberCard(QWidget):
    """
    Compact member card with avatar image (or initial fallback), moniker,
    handle, rank badge, and role chip. Matches the GlassCard aesthetic.
    """

    CARD_WIDTH = 210
    CARD_HEIGHT = 80

    def __init__(self, member: dict, parent=None):
        super().__init__(parent)
        self.member = member
        self.handle = member.get("handle", "")
        self.setFixedHeight(self.CARD_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setMouseTracking(True)
        self._hovered = False
        self._avatar_pixmap: QPixmap | None = None
        self._load_avatar()

    def _load_avatar(self) -> None:
        """Load avatar pixmap from local cache path if available."""
        local = self.member.get("avatar_local", "")
        if local and os.path.exists(local):
            pix = QPixmap(local)
            if not pix.isNull():
                self._avatar_pixmap = pix
                return
        self._avatar_pixmap = None

    def update_avatar(self, url: str, local_path: str) -> None:
        """Called when an avatar download completes — refresh if it's ours."""
        if url == self.member.get("avatar_url") or local_path == self.member.get("avatar_local"):
            self.member["avatar_local"] = local_path
            self._load_avatar()
            self.update()

    def mouseDoubleClickEvent(self, event) -> None:
        if self.handle:
            EventBus.instance().navigate_to_tab.emit("dossier")
            EventBus.instance().capture_completed.emit(self.handle)
        super().mouseDoubleClickEvent(event)

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        moniker = self.member.get("moniker", "")
        handle = self.member.get("handle", "")
        rank = self.member.get("rank", "")
        role = self.member.get("role", "")
        initial = moniker[0].upper() if moniker else (handle[0].upper() if handle else "?")

        rect = self.rect()

        # Background — glass effect
        bg_alpha = 200 if self._hovered else 120
        bg = QColor(P.SURFACE_CONTAINER_LOW)
        bg.setAlpha(bg_alpha)
        painter.fillRect(rect, bg)

        # Border
        border_col = QColor(P.PRIMARY_CONTAINER)
        border_col.setAlpha(60 if self._hovered else 30)
        painter.setPen(QPen(border_col, 1))
        painter.drawRect(rect.adjusted(0, 0, -1, -1))

        # Bracket corners
        self._draw_brackets(painter, rect)

        # Avatar area
        cx, cy = 32, rect.height() // 2
        radius = 17
        circle_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)

        if self._avatar_pixmap and not self._avatar_pixmap.isNull():
            # Draw avatar image clipped to circle
            clip = QPainterPath()
            clip.addEllipse(circle_rect)
            painter.setClipPath(clip)
            scaled = self._avatar_pixmap.scaled(
                int(radius * 2), int(radius * 2),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            ox = cx - radius + (radius * 2 - scaled.width()) // 2
            oy = cy - radius + (radius * 2 - scaled.height()) // 2
            painter.drawPixmap(int(ox), int(oy), scaled)
            painter.setClipping(False)
            # Circle border
            painter.setPen(QPen(QColor(P.PRIMARY), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(circle_rect)
        else:
            # Fallback: colored circle with initial
            clip = QPainterPath()
            clip.addEllipse(circle_rect)
            painter.setClipPath(clip)
            painter.fillRect(circle_rect, QColor(P.rgba(P.PRIMARY_CONTAINER, 0.08)))
            painter.setClipping(False)
            painter.setPen(QPen(QColor(P.PRIMARY), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(circle_rect)
            f = QFont("JetBrains Mono", 13, QFont.Weight.Bold)
            painter.setFont(f)
            painter.setPen(QColor(P.PRIMARY))
            painter.drawText(circle_rect, Qt.AlignmentFlag.AlignCenter, initial)

        # Moniker
        f = QFont("Inter", 11, QFont.Weight.Bold)
        painter.setFont(f)
        painter.setPen(QColor(P.ON_SURFACE))
        painter.drawText(
            QRectF(62, 8, self.width() - 68, 20),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            moniker or handle
        )

        # Handle
        f = QFont("Inter", 9)
        painter.setFont(f)
        painter.setPen(QColor(P.TEXT_DIM))
        painter.drawText(
            QRectF(62, 27, self.width() - 68, 16),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            f"@{handle}" if handle else ""
        )

        # Rank badge (left) + Role chip (right)
        badge_x = 60
        badge_h = 20
        spacer = 6

        if rank:
            f = QFont("JetBrains Mono", 8, QFont.Weight.Medium)
            painter.setFont(f)
            fm = QFontMetrics(f)
            rank_text = rank.upper()
            rank_w = fm.horizontalAdvance(rank_text) + 16 # 8px padding each side

            # Prevent overflowing the card
            if badge_x + rank_w > self.width() - 8:
                rank_w = max(0, self.width() - badge_x - 8)

            r_path = QPainterPath()
            r_path.addRoundedRect(badge_x, 52, rank_w, badge_h, 3, 3)
            painter.fillPath(r_path, QColor(P.rgba(P.PRIMARY_CONTAINER, 0.05)))
            painter.setPen(QPen(QColor(P.PRIMARY), 1))
            painter.drawRoundedRect(badge_x, 52, rank_w, badge_h, 3, 3)
            painter.setPen(QColor(P.PRIMARY))
            painter.drawText(
                QRectF(badge_x, 52, rank_w, badge_h),
                Qt.AlignmentFlag.AlignCenter,
                rank_text
            )
            badge_x += rank_w + spacer

        if role:
            f = QFont("Inter", 8, QFont.Weight.Medium)
            painter.setFont(f)
            fm = QFontMetrics(f)
            role_text = role.upper()
            role_w = fm.horizontalAdvance(role_text) + 16 # 8px padding each side
            
            # Prevent overflowing the card
            if badge_x + role_w > self.width() - 8:
                role_w = max(0, self.width() - badge_x - 8)

            if role_w > 10:
                painter.setBrush(QColor(P.PRIMARY_FIXED_DIM))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(badge_x, 52, role_w, badge_h, badge_h // 2, badge_h // 2)
                painter.setPen(QColor(P.ON_PRIMARY))
                painter.drawText(
                    QRectF(badge_x, 52, role_w, badge_h),
                    Qt.AlignmentFlag.AlignCenter,
                    role_text
                )

        painter.end()

    @staticmethod
    def _draw_brackets(painter: QPainter, rect: QRect) -> None:
        size = 4
        pen = QPen(QColor(P.BRACKET_COLOR), P.BRACKET_WIDTH)
        pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        x0, y0 = rect.left(), rect.top()
        x1, y1 = rect.right(), rect.bottom()

        painter.drawLine(x0, y0, x0 + size, y0)
        painter.drawLine(x0, y0, x0, y0 + size)
        painter.drawLine(x1 - size, y0, x1, y0)
        painter.drawLine(x1, y0, x1, y0 + size)
        painter.drawLine(x0, y1, x0 + size, y1)
        painter.drawLine(x0, y1 - size, x0, y1)
        painter.drawLine(x1 - size, y1, x1, y1)
        painter.drawLine(x1, y1 - size, x1, y1)


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


class OrgSubTabBar(QWidget):
    """
    Custom sub-tab bar for OrgTab with two buttons: OVERVIEW and MEMBERS.
    Uses QPainter for rendering to match the DossierSubTabBar aesthetic.
    Signal tab_changed emits the tab id string when the user clicks a tab.
    """

    tab_changed = pyqtSignal(str)  # "overview" | "members"

    _TAB_IDS = ["overview", "members"]
    _TAB_LABELS = {"overview": "OVERVIEW", "members": "MEMBERS"}

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._active: str = "overview"
        self._hovered: str | None = None
        self.setFixedHeight(32)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    def set_active(self, tab_id: str) -> None:
        """Switch the active visual state without emitting tab_changed."""
        if tab_id in self._TAB_IDS and tab_id != self._active:
            self._active = tab_id
            self.update()

    def _tab_rects(self) -> dict[str, QRect]:
        w = self.width()
        tab_w = w // 2
        return {
            "overview": QRect(0, 0, tab_w, self.height()),
            "members":  QRect(tab_w, 0, w - tab_w, self.height()),
        }

    def _tab_at(self, x: int) -> str | None:
        for tid, rect in self._tab_rects().items():
            if rect.contains(x, self.height() // 2):
                return tid
        return None

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

        # Bottom border
        pen = QPen(QColor(P.OUTLINE_VARIANT))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)

        rects = self._tab_rects()
        font = label_caps()
        font.setPointSize(9)

        for tid, tab_rect in rects.items():
            is_active = tid == self._active
            is_hovered = tid == self._hovered and not is_active

            # Tab fill
            if is_active:
                painter.fillRect(tab_rect, QColor(P.SURFACE_CONTAINER))
            elif is_hovered:
                painter.fillRect(tab_rect, QColor(P.rgba(P.PRIMARY_CONTAINER, 0.06)))
            else:
                painter.fillRect(tab_rect, QColor(0, 0, 0, 0))

            # Separator between tabs
            if tid == "members":
                sep_pen = QPen(QColor(P.OUTLINE_VARIANT))
                sep_pen.setWidth(1)
                painter.setPen(sep_pen)
                painter.drawLine(tab_rect.left(), 4, tab_rect.left(), self.height() - 5)

            # Active indicator bar (top edge)
            if is_active:
                bar_pen = QPen(QColor(P.PRIMARY))
                bar_pen.setWidth(2)
                painter.setPen(bar_pen)
                painter.drawLine(tab_rect.left() + 2, 0, tab_rect.right() - 2, 0)

            # Label color
            if is_active:
                painter.setPen(QPen(QColor(P.PRIMARY)))
            elif is_hovered:
                painter.setPen(QPen(QColor(P.ON_SURFACE)))
            else:
                painter.setPen(QPen(QColor(P.TEXT_DIM)))

            painter.setFont(font)
            painter.drawText(tab_rect, Qt.AlignmentFlag.AlignCenter, self._TAB_LABELS[tid])

        painter.end()


class OrgTab(QWidget):
    """
    Displays standalone organization details using GlassCard containers.
    """
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_sid = ""
        self.mfr_logo_lbl = None
        self._current_data = None
        self._member_cards: list[_MemberCard] = []
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Top Action Bar — compact ---
        action_bar = QWidget()
        action_bar.setFixedHeight(50)
        action_bar.setStyleSheet(
            f"background: {P.SURFACE_CONTAINER_LOW}; border-bottom: 1px solid {P.OUTLINE_VARIANT};"
        )
        ab_layout = QHBoxLayout(action_bar)
        ab_layout.setContentsMargins(16, 7, 16, 7)
        ab_layout.setSpacing(8)

        self.search_input = SearchInput("ENTER ORG NAME OR SID...", history_type="org")
        self.search_input.returnPressed.connect(self._on_search)
        self.search_input.setFixedHeight(36)
        self.search_input.setToolTip(
            "Enter an organization name or SID (e.g., REBELS) to search for org details"
        )

        search_icon = get_asset_path("assets/icons/misc/icon_search.svg")

        search_btn = QPushButton()
        search_btn.setProperty("class", "primary")
        search_btn.setFixedSize(44, 36)
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
        self.content_layout.setContentsMargins(16, 16, 16, 16)
        self.content_layout.setSpacing(12)
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
        dl.setSpacing(12)

        # Identity card
        self.identity_card = GlassCard(title="ORGANIZATION IDENTITY")

        # --- Banner container ---
        self.banner_container = QWidget()
        self.banner_container.setStyleSheet(
            f"background: {P.rgba(P.PRIMARY_CONTAINER, 0.04)};"
            f"border-bottom: 1px solid {P.rgba(P.PRIMARY_CONTAINER, 0.15)};"
        )
        banner_grid = QGridLayout(self.banner_container)
        banner_grid.setContentsMargins(14, 14, 14, 14)
        banner_grid.setSpacing(14)

        self.banner_lbl = _BannerBg()
        self.banner_lbl.setVisible(False)
        banner_grid.addWidget(self.banner_lbl, 0, 0)

        overlay_widget = QWidget()
        overlay_widget.setStyleSheet("background: transparent; border: none;")
        self.header_layout = QHBoxLayout(overlay_widget)
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.setSpacing(14)
        self.logo = AvatarWidget(size=90)

        name_vbox = QVBoxLayout()
        name_vbox.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        name_vbox.setSpacing(2)
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

        self.tags_layout = QHBoxLayout()
        self.tags_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.tags_layout.setSpacing(4)

        name_vbox.addWidget(self.name_lbl)
        name_vbox.addWidget(self.sid_lbl)
        name_vbox.addLayout(self.tags_layout)

        self.header_layout.addWidget(self.logo)
        self.header_layout.addLayout(name_vbox)

        self.badges_layout = QHBoxLayout()
        self.badges_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.badges_layout.setSpacing(8)
        self.header_layout.addLayout(self.badges_layout)
        self.header_layout.addStretch()

        banner_grid.addWidget(overlay_widget, 0, 0)

        self.identity_card.content_layout.addWidget(self.banner_container)
        dl.addWidget(self.identity_card)

        # --- Sub Tab Bar (custom painted, matching dossier style) ---
        self.sub_tab_bar = OrgSubTabBar()
        dl.addWidget(self.sub_tab_bar)

        # --- Stacked Widget for tab content ---
        self.stack = QStackedWidget()
        dl.addWidget(self.stack)

        _TAB_INDEX = {"overview": 0, "members": 1}
        self.sub_tab_bar.tab_changed.connect(
            lambda tid: self.stack.setCurrentIndex(_TAB_INDEX[tid])
        )

        # --- OVERVIEW TAB (unchanged) ---
        self.overview_tab = QWidget()
        overview_layout = QVBoxLayout(self.overview_tab)
        overview_layout.setContentsMargins(0, 16, 0, 0)
        overview_layout.setSpacing(12)

        # Details grid card
        self.grid_card = GlassCard(title="ORGANIZATION DATA")
        grid = QGridLayout()
        grid.setSpacing(8)
        self.f_members = DataField("MEMBERS")
        grid.addWidget(self.f_members, 0, 0)
        self.grid_card.content_layout.addLayout(grid)
        overview_layout.addWidget(self.grid_card)

        # Focus card
        self.focus_card = GlassCard(title="PRIMARY & SECONDARY FOCUS")
        focus_layout = QHBoxLayout()
        focus_layout.setSpacing(24)
        focus_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        primary_vbox = QVBoxLayout()
        primary_vbox.setSpacing(4)
        primary_vbox.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.focus_primary_icon = QLabel()
        self.focus_primary_icon.setFixedSize(48, 48)
        self.focus_primary_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.focus_primary_icon.setStyleSheet(
            f"background: {P.rgba(P.PRIMARY_CONTAINER, 0.08)}; border: 1px solid {P.rgba(P.PRIMARY_CONTAINER, 0.25)};"
            "border-radius: 24px;"
        )
        lbl_primary_cap = QLabel("PRIMARY FOCUS")
        lbl_primary_cap.setFont(label_caps())
        lbl_primary_cap.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent; border: none;")
        self.focus_primary_lbl = QLabel("—")
        self.focus_primary_lbl.setFont(font_inter(13, QFont.Weight.Bold))
        self.focus_primary_lbl.setStyleSheet(f"color: {P.ON_SURFACE}; background: transparent; border: none;")
        primary_vbox.addWidget(self.focus_primary_icon, alignment=Qt.AlignmentFlag.AlignHCenter)
        primary_vbox.addWidget(lbl_primary_cap)
        primary_vbox.addWidget(self.focus_primary_lbl)

        secondary_vbox = QVBoxLayout()
        secondary_vbox.setSpacing(4)
        secondary_vbox.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.focus_secondary_icon = QLabel()
        self.focus_secondary_icon.setFixedSize(48, 48)
        self.focus_secondary_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.focus_secondary_icon.setStyleSheet(
            f"background: {P.rgba(P.PRIMARY_CONTAINER, 0.08)}; border: 1px solid {P.rgba(P.PRIMARY_CONTAINER, 0.25)};"
            "border-radius: 24px;"
        )
        lbl_secondary_cap = QLabel("SECONDARY FOCUS")
        lbl_secondary_cap.setFont(label_caps())
        lbl_secondary_cap.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent; border: none;")
        self.focus_secondary_lbl = QLabel("—")
        self.focus_secondary_lbl.setFont(font_inter(13, QFont.Weight.Bold))
        self.focus_secondary_lbl.setStyleSheet(f"color: {P.ON_SURFACE}; background: transparent; border: none;")
        secondary_vbox.addWidget(self.focus_secondary_icon, alignment=Qt.AlignmentFlag.AlignHCenter)
        secondary_vbox.addWidget(lbl_secondary_cap)
        secondary_vbox.addWidget(self.focus_secondary_lbl)

        focus_layout.addLayout(primary_vbox)
        focus_layout.addLayout(secondary_vbox)
        focus_layout.addStretch()
        self.focus_card.content_layout.addLayout(focus_layout)
        overview_layout.addWidget(self.focus_card)

        # History / Description card
        self.desc_card = GlassCard(title="HISTORY & DESCRIPTION")
        self.desc_lbl = QLabel("—")
        self.desc_lbl.setFont(font_inter(12))
        self.desc_lbl.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent; border: none;")
        self.desc_lbl.setWordWrap(True)
        self.desc_card.content_layout.addWidget(self.desc_lbl)
        overview_layout.addWidget(self.desc_card)

        # Manifesto card
        self.manifesto_card = GlassCard(title="MANIFESTO")
        self.manifesto_lbl = QLabel("—")
        self.manifesto_lbl.setFont(font_inter(12))
        self.manifesto_lbl.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent; border: none;")
        self.manifesto_lbl.setWordWrap(True)
        self.manifesto_card.content_layout.addWidget(self.manifesto_lbl)
        overview_layout.addWidget(self.manifesto_card)

        # Charter card
        self.charter_card = GlassCard(title="CHARTER")
        self.charter_lbl = QLabel("—")
        self.charter_lbl.setFont(font_inter(12))
        self.charter_lbl.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent; border: none;")
        self.charter_lbl.setWordWrap(True)
        self.charter_card.content_layout.addWidget(self.charter_lbl)
        overview_layout.addWidget(self.charter_card)

        overview_layout.addStretch()
        self.stack.addWidget(self.overview_tab)

        # --- MEMBERS TAB (redesigned: card grid with refresh button) ---
        self.members_tab = QWidget()
        members_layout = QVBoxLayout(self.members_tab)
        members_layout.setContentsMargins(0, 16, 0, 0)
        members_layout.setSpacing(0)

        self.members_card = GlassCard(title="MEMBERSHIP ROSTER — 0")

        # Header row inside card: title + refresh button
        members_header = QWidget()
        members_header.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        members_header.setFixedHeight(32)
        mh_layout = QHBoxLayout(members_header)
        mh_layout.setContentsMargins(0, 0, 0, 0)
        mh_layout.setSpacing(4)

        mh_layout.addStretch()

        self.refresh_btn = QPushButton()
        self.refresh_btn.setFixedSize(28, 28)
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setToolTip("Re-scan members for this organization")
        refresh_icon = get_asset_path("assets/icons/misc/arrow-clockwise.svg")
        set_button_icon(self.refresh_btn, refresh_icon, (16, 16))
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {P.OUTLINE_VARIANT};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background: {P.rgba(P.PRIMARY, 0.1)};
                border-color: {P.PRIMARY};
            }}
            QPushButton:disabled {{
                opacity: 0.3;
            }}
        """)
        self.refresh_btn.clicked.connect(self._on_refresh_members)
        mh_layout.addWidget(self.refresh_btn)

        # Scroll area for member cards
        self.members_scroll = QScrollArea()
        self.members_scroll.setWidgetResizable(True)
        self.members_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.members_scroll.setStyleSheet("background: transparent;")
        self.members_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.members_grid_widget = QWidget()
        self.members_grid_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.members_grid = QGridLayout(self.members_grid_widget)
        self.members_grid.setContentsMargins(4, 4, 4, 4)
        self.members_grid.setSpacing(6)
        self.members_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.members_scroll.setWidget(self.members_grid_widget)

        # Empty state label (hidden when members present)
        self.members_empty_lbl = QLabel("NO MEMBERS FOUND")
        self.members_empty_lbl.setFont(label_caps())
        self.members_empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.members_empty_lbl.setStyleSheet(
            f"color: {P.TEXT_DIM}; background: transparent; padding: 32px; border: none;"
        )
        self.members_empty_lbl.setVisible(False)

        # The card content order: header row, scroll area, empty label
        self.members_card.content_layout.addWidget(members_header)
        self.members_card.content_layout.addWidget(self.members_scroll)
        self.members_card.content_layout.addWidget(self.members_empty_lbl)
        members_layout.addWidget(self.members_card)

        self.stack.addWidget(self.members_tab)

    def _get_manufacturer_logo_path(self, org_name: str) -> str | None:
        """Check if org name matches a known SC manufacturer and return logo path."""
        for name_key, file_key in MANUFACTURER_MAP.items():
            if name_key.lower() in org_name.lower():
                logo_path = get_asset_path(f"assets/icons/manufact-names/sc-logo-{file_key}.svg")
                if os.path.exists(logo_path):
                    return logo_path
        return None

    def _connect_signals(self) -> None:
        bus = EventBus.instance()
        bus.org_loaded.connect(self._on_org_loaded)
        bus.org_candidates_found.connect(self._on_org_candidates)
        bus.status_message.connect(self._on_status_msg)
        bus.image_downloaded.connect(self._on_image_downloaded)

    def _set_banner_pixmap(self, path: str) -> None:
        """Load and display the banner image as cover-fit background."""
        if not path or not os.path.exists(path):
            self.banner_lbl.setVisible(False)
            self.banner_lbl.clear_pixmap()
            return
        pix = QPixmap(path)
        if pix.isNull():
            self.banner_lbl.setVisible(False)
            self.banner_lbl.clear_pixmap()
            return
        self.banner_lbl.set_pixmap(pix)
        self.banner_lbl.setVisible(True)

    def _set_focus_icon(self, icon_lbl: "QLabel", text_lbl: "QLabel",
                        focus_name: "str | None", local_path: str) -> None:
        """Populate a focus icon label and its text label."""
        text_lbl.setText(focus_name or "—")
        icon_lbl.clear()
        if local_path and os.path.exists(local_path):
            pix = QPixmap(local_path).scaled(
                36, 36,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            icon_lbl.setPixmap(pix)

    @pyqtSlot(str, str)
    def _on_image_downloaded(self, url: str, local_path: str) -> None:
        """Refresh banner or focus icons when their images finish downloading."""
        if not self._current_data:
            return
        data = self._current_data
        if data.get("banner_local") == local_path:
            self._set_banner_pixmap(local_path)
            return
        if data.get("focus_primary_local") == local_path:
            self._set_focus_icon(self.focus_primary_icon, self.focus_primary_lbl,
                                 data.get("focus_primary"), local_path)
            return
        if data.get("focus_secondary_local") == local_path:
            self._set_focus_icon(self.focus_secondary_icon, self.focus_secondary_lbl,
                                 data.get("focus_secondary"), local_path)
            return
        # Notify any member card whose avatar just finished downloading
        for card in self._member_cards:
            card.update_avatar(url, local_path)

    def _clear_results(self) -> None:
        """Clear all displayed organization results."""
        self.current_sid = ""
        self._current_data = None
        self.search_input.clear()
        self.detail_container.setVisible(False)
        self.empty_lbl.setVisible(True)

    def clear(self) -> None:
        """Public alias for _clear_results — called by MainWindow clear button."""
        self._clear_results()

    def _on_search(self) -> None:
        query = self.search_input.text().strip()
        if query:
            self._add_to_search_history(query)
            EventBus.instance().search_org_requested.emit(query)

    def _add_to_search_history(self, query: str) -> None:
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
        list_widget.setFixedHeight(180)
        list_widget.setStyleSheet(f"""
            QListWidget {{
                background: rgba(5, 11, 15, 0.85);
                color: {P.ON_SURFACE};
                border: 1px solid {P.OUTLINE_VARIANT};
                border-radius: 3px;
            }}
            QListWidget::item:selected {{
                background: {P.rgba(P.PRIMARY_CONTAINER, 0.20)};
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

    def _on_refresh_members(self) -> None:
        """Re-trigger org scrape for the currently loaded org SID."""
        if self.current_sid:
            EventBus.instance().request_org_scrape.emit(self.current_sid)

    @pyqtSlot(dict)
    def _on_org_loaded(self, data: dict) -> None:
        self._on_org_loaded_impl(data)

    def _populate_member_grid(self, members: list[dict]) -> None:
        """Clear and rebuild the member card grid from a list of member dicts."""
        # Remove existing cards
        for card in self._member_cards:
            card.deleteLater()
        self._member_cards.clear()

        # Clear grid
        while self.members_grid.count():
            item = self.members_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        count = len(members)
        # Update title directly via painting attribute without replacing layout
        self.members_card._title = f"MEMBERSHIP ROSTER — {count}"
        self.members_card.update()

        if count == 0:
            self.members_scroll.setVisible(False)
            self.members_empty_lbl.setVisible(True)
            return

        self.members_scroll.setVisible(True)
        self.members_empty_lbl.setVisible(False)

        # Calculate columns based on available width
        scroll_width = self.members_scroll.viewport().width()
        if scroll_width < 100:
            scroll_width = self.members_scroll.width()
            
        # Target an ideal card width of ~300px
        ideal_width = 300
        cols = max(1, scroll_width // ideal_width)

        for i, member in enumerate(members):
            card = _MemberCard(member)
            self._member_cards.append(card)
            row = i // cols
            col = i % cols
            self.members_grid.addWidget(card, row, col)

    def _on_org_loaded_impl(self, data: dict) -> None:
        self._current_data = data
        self.overlay.hide_overlay()
        self.current_sid = data.get("sid", "")
        self.search_input.clear()

        # Enable refresh button now that we have an SID
        self.refresh_btn.setEnabled(bool(self.current_sid))

        self.empty_lbl.setVisible(False)
        self.detail_container.setVisible(True)

        self.name_lbl.setText(data.get("name", "—"))
        self.sid_lbl.setText(f"@{data.get('sid', '—')}")

        # Banner
        banner_path = data.get("banner_local")
        if banner_path and os.path.exists(banner_path):
            self._set_banner_pixmap(banner_path)
        else:
            self.banner_lbl.clear_pixmap()
            self.banner_lbl.setVisible(False)

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
            icon_size = 36
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
        self.f_members.set_value(str(data.get("member_count", 0)))

        # Focus icons
        self._set_focus_icon(self.focus_primary_icon, self.focus_primary_lbl,
                             data.get("focus_primary"), data.get("focus_primary_local", ""))
        self._set_focus_icon(self.focus_secondary_icon, self.focus_secondary_lbl,
                             data.get("focus_secondary"), data.get("focus_secondary_local", ""))

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

        # History
        history = data.get("history")
        if history:
            self.desc_lbl.setText(self.desc_lbl.text() + "\n\n" + history)
            self.desc_card.setVisible(True)
        elif not desc:
            self.desc_card.setVisible(False)

        # Manifesto
        manifesto = data.get("manifesto")
        if manifesto:
            self.manifesto_lbl.setText(manifesto)
            self.manifesto_card.setVisible(True)
        else:
            self.manifesto_card.setVisible(False)

        # Charter
        charter = data.get("charter")
        if charter:
            self.charter_lbl.setText(charter)
            self.charter_card.setVisible(True)
        else:
            self.charter_card.setVisible(False)

        # Tags
        while self.tags_layout.count():
            item = self.tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for tag in data.get("tags", []):
            lbl = QLabel(tag.upper())
            lbl.setFont(font_inter(10, QFont.Weight.Bold))
            lbl.setStyleSheet(f"background: {P.PRIMARY_CONTAINER}; color: {P.ON_PRIMARY}; padding: 2px 6px; border-radius: 4px;")
            self.tags_layout.addWidget(lbl)

        # Badges
        while self.badges_layout.count():
            item = self.badges_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for badge in data.get("badges", []):
            path = badge.get("image_local")
            if path and os.path.exists(path):
                img_lbl = QLabel()
                pix = QPixmap(path).scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                img_lbl.setPixmap(pix)
                img_lbl.setToolTip(badge.get("name", ""))
                img_lbl.setStyleSheet("background: transparent; border: none;")
                self.badges_layout.addWidget(img_lbl)

        # Members — populate card grid (replaces old QTableWidget)
        members = data.get("members", [])
        import logging as _log2
        _log2.getLogger(__name__).info("ORG LOADED: %d members received in data for %s", len(members), data.get("sid"))
        self._populate_member_grid(members)

        # Reset tab to overview
        self.sub_tab_bar.set_active("overview")
        self.stack.setCurrentIndex(0)
        QTimer.singleShot(0, self.members_scroll.viewport().update)