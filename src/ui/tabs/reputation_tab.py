"""
src/ui/tabs/reputation_tab.py
ReputationTab — community reputation display and report submission UI.

Components:
    AnimatedProgressBar — smooth-animated progress bar with glow effect
    ReputationBar     — renders a single category score (progress bar + labels)
    ReportDialog      — modal tag-selection dialog (max 5 tags, chip toggle UI)
    ReputationTab     — main 7-state widget (disabled|empty|loading|no_data|loaded|offline|self)

State machine:
    disabled  → reputation system is off in settings
    empty     → no player searched yet
    loading   → fetch in progress
    no_data   → player exists but no reports yet
    loaded    → 7 category bars + report button
    offline   → Supabase unavailable
    self      → self-report restricted

Signal flow:
    DossierTab._on_scrape_completed → reputation_tab.load_player(handle)
    reputation_tab → ReportDialog → EventBus.reputation_report_requested
    AppController → EventBus.reputation_loaded / reputation_load_failed
    reputation_tab._on_reputation_loaded / _on_reputation_failed
"""

import logging
import time
from PyQt6.QtCore import Qt, QPoint, pyqtSlot, QTimer, QRectF, QSize
from PyQt6.QtGui import QColor, QPainter, QPen, QFont, QGuiApplication, QPainterPath, QBrush
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QScrollArea, QFrame, QStackedWidget, QGridLayout,
    QSizePolicy
)

from src.core.events import EventBus
from src.core.settings import SettingsManager
from src.ui.theme import palette as P
from src.ui.theme.fonts import label_caps, font_inter, font_sora, font_mono, headline_md, body_md, data_point
from src.ui.widgets.progress_overlay import ProgressOverlay
from src.ui.widgets.glass_card import GlassCard
from src.app.constants import REPUTATION_TAGS, REPUTATION_CATEGORIES, REPUTATION_MAX_TAGS

log = logging.getLogger(__name__)

_COOLDOWN_COLOR = "#FFAA00"
_SUCCESS_COLOR = "#00FF88"
_SUBMITTING_COLOR = "#93CCFF"


# ---------------------------------------------------------------------------
# Helper: verdict label from score percentage
# ---------------------------------------------------------------------------

def _verdict_for_score(category_id: str, score_pct: int) -> str:
    """Return the appropriate verdict label for a given category and score %."""
    cat = REPUTATION_CATEGORIES.get(category_id, {})
    thresholds = cat.get("thresholds", [])
    verdict = ""
    for min_pct, label in thresholds:
        if score_pct >= min_pct:
            verdict = label
    return verdict


# ---------------------------------------------------------------------------
# AnimatedProgressBar — smooth animated fill with glow
# ---------------------------------------------------------------------------

class AnimatedProgressBar(QWidget):
    """A smooth-animated progress bar with glow effect."""

    def __init__(self, color_hex: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color_hex = color_hex
        self._target_value = 0
        self._current_value = 0.0
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(30)
        self._anim_timer.timeout.connect(self._tick_anim)
        self._anim_start = 0.0
        self._anim_end = 0.0
        self._anim_elapsed = 0
        self._anim_duration = 800
        self.setFixedHeight(10)
        self.setMinimumWidth(100)

    def _tick_anim(self) -> None:
        self._anim_elapsed += 30
        t = min(1.0, self._anim_elapsed / self._anim_duration)
        # OutCubic easing
        t = 1 - (1 - t) ** 3
        self._current_value = self._anim_start + (self._anim_end - self._anim_start) * t
        self.update()
        if t >= 1.0:
            self._anim_timer.stop()

    def setValue(self, value: int) -> None:
        self._target_value = max(0, min(100, value))
        self._anim_start = self._current_value
        self._anim_end = float(self._target_value)
        self._anim_elapsed = 0
        self._anim_timer.start()

    def paintEvent(self, event) -> None:
        rect = self.rect()
        if rect.width() <= 0 or rect.height() <= 0 or not self.isVisible():
            return
        painter = QPainter(self)
        if not painter.isActive():
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = rect.width()
        h = rect.height()

        # Track
        track_path = QPainterPath()
        track_path.addRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)
        painter.fillPath(track_path, QBrush(P.qcolor(P.ON_SURFACE, 12)))

        # Fill
        fill_w = int(w * self._current_value / 100)
        if fill_w > 0:
            fill_path = QPainterPath()
            fill_path.addRoundedRect(QRectF(0, 0, fill_w, h), h / 2, h / 2)
            c = QColor(self._color_hex)
            painter.fillPath(fill_path, QBrush(c))

            # Glow dot at end
            if fill_w > 4:
                glow_c = QColor(self._color_hex)
                glow_c.setAlpha(180)
                painter.setBrush(QBrush(glow_c))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPoint(fill_w, h // 2), 4, 4)

        painter.end()


# ---------------------------------------------------------------------------
# ReputationBar — single category row with animated bar
# ---------------------------------------------------------------------------

class ReputationBar(QWidget):
    """
    Renders a single reputation category row:
        [Category Label]  [Percentage%]  [Animated Progress Bar]  [Verdict]
        [Report count sub-label]
    """

    def __init__(self, category_id: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._category_id = category_id
        cat_def = REPUTATION_CATEGORIES.get(category_id, {})
        self._color = cat_def.get("color_hex", P.PRIMARY)
        self._build_ui(cat_def.get("label", category_id.upper()))

    def _build_ui(self, cat_label: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(3)

        # Top row: label + pct + bar + verdict
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self._cat_lbl = QLabel(cat_label)
        self._cat_lbl.setFont(font_inter(11, QFont.Weight.Bold))
        self._cat_lbl.setStyleSheet(
            f"color: {self._color}; background: transparent; border: none;"
        )
        self._cat_lbl.setFixedWidth(140)

        self._pct_lbl = QLabel("0%")
        self._pct_lbl.setFont(data_point())
        self._pct_lbl.setStyleSheet(
            f"color: {P.ON_SURFACE}; background: transparent; border: none;"
        )
        self._pct_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._pct_lbl.setFixedWidth(42)

        self._bar = AnimatedProgressBar(self._color)

        self._verdict_lbl = QLabel("—")
        self._verdict_lbl.setFont(font_inter(10))
        self._verdict_lbl.setStyleSheet(
            f"color: {P.TEXT_DIM}; background: transparent; border: none;"
        )
        self._verdict_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._verdict_lbl.setFixedWidth(200)

        top_row.addWidget(self._cat_lbl)
        top_row.addWidget(self._pct_lbl)
        top_row.addWidget(self._bar, 1)
        top_row.addWidget(self._verdict_lbl)

        # Sub-label: report count
        self._count_lbl = QLabel("")
        self._count_lbl.setFont(font_inter(9))
        self._count_lbl.setStyleSheet(
            f"color: {P.TEXT_DIM}; background: transparent; border: none; padding-left: 150px;"
        )

        layout.addLayout(top_row)
        layout.addWidget(self._count_lbl)

    def set_value(self, score_pct: int, report_count: int, verdict: str) -> None:
        """Update the bar with new score data."""
        self._bar.setValue(score_pct)
        self._pct_lbl.setText(f"{score_pct}%")
        self._verdict_lbl.setText(verdict)
        if report_count == 0:
            self._count_lbl.setText("No reports")
        elif report_count == 1:
            self._count_lbl.setText("Based on 1 report")
        else:
            self._count_lbl.setText(f"Based on {report_count} reports")

    def reset(self) -> None:
        """Reset the bar to the zero state."""
        self._bar.setValue(0)
        self._pct_lbl.setText("0%")
        self._verdict_lbl.setText("—")
        self._count_lbl.setText("")


# ---------------------------------------------------------------------------
# ReportDialog — redesigned to match SCPINK design system
# ---------------------------------------------------------------------------

class ReportDialog(QDialog):
    """
    Modal dialog for selecting interaction tags when submitting a report.
    Redesigned to match the SCPINK design system with glassmorphism,
    tech brackets, and polished chip interactions.
    """

    def __init__(self, handle: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._handle = handle
        self._selected: set[str] = set()
        self._chip_btns: dict[str, QPushButton] = {}
        self._drag_active = False
        self._drag_start_pos = QPoint()
        self._drag_start_window_pos = QPoint()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setMinimumWidth(580)
        self._build_ui()
        self._center_on_screen()

    def _chip_style(self, category_id: str, selected: bool, disabled: bool) -> str:
        cat = REPUTATION_CATEGORIES.get(category_id, {})
        color = cat.get("color_hex", P.PRIMARY)
        if disabled and not selected:
            return f"""
                QPushButton {{
                    background: {P.rgba(P.ON_SURFACE, 0.03)};
                    color: {P.rgba(P.TEXT_DIM, 0.4)};
                    border: 1px solid {P.rgba(P.ON_SURFACE, 0.06)};
                    border-radius: 4px;
                    padding: 8px 12px;
                    font-size: 11px;
                    text-align: left;
                }}
            """
        if selected:
            return f"""
                QPushButton {{
                    background: {P.rgba(color, 0.18)};
                    color: {color};
                    border: 2px solid {color};
                    border-radius: 4px;
                    padding: 8px 12px;
                    font-size: 11px;
                    font-weight: bold;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background: {P.rgba(color, 0.28)};
                }}
            """
        return f"""
            QPushButton {{
                background: {P.rgba(P.ON_SURFACE, 0.04)};
                color: {P.ON_SURFACE_VARIANT};
                border: 1px solid {P.rgba(color, 0.25)};
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 11px;
                text-align: left;
            }}
            QPushButton:hover {{
                background: {P.rgba(color, 0.10)};
                border-color: {P.rgba(color, 0.5)};
                color: {P.ON_SURFACE};
            }}
        """

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        container = QWidget(self)
        container.setObjectName("ReportContainer")
        container.setStyleSheet(f"""
            #ReportContainer {{
                background-color: {P.rgba(P.SURFACE_CONTAINER_LOW, 0.97)};
                border: 1px solid {P.rgba(P.PRIMARY_CONTAINER, 0.25)};
                border-radius: 6px;
            }}
        """)
        outer.addWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Title
        title_lbl = QLabel(f"REPORT INTERACTION — @{self._handle.upper()}")
        title_lbl.setFont(label_caps())
        title_lbl.setStyleSheet(
            f"color: {P.PRIMARY}; background: transparent; letter-spacing: 0.15em;"
        )
        layout.addWidget(title_lbl)

        # Divider
        divider = QWidget()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: {P.rgba(P.PRIMARY_CONTAINER, 0.15)};")
        layout.addWidget(divider)

        # Header
        header_lbl = QLabel(
            f"Select up to {REPUTATION_MAX_TAGS} tags that describe your interaction with "
            f"@{self._handle}. This report is anonymous."
        )
        header_lbl.setFont(font_inter(11))
        header_lbl.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent; border: none;")
        header_lbl.setWordWrap(True)
        layout.addWidget(header_lbl)

        # Counter
        self._counter_lbl = QLabel(f"0 / {REPUTATION_MAX_TAGS} selected")
        self._counter_lbl.setFont(data_point())
        self._counter_lbl.setStyleSheet(f"color: {P.PRIMARY}; background: transparent; border: none;")
        layout.addWidget(self._counter_lbl)

        # Tag chips grid — scrollable for many tags
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(320)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: {P.rgba(P.SPACE_VOID, 0.0)};
                width: 6px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {P.rgba(P.PRIMARY_CONTAINER, 0.2)};
                border-radius: 3px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {P.rgba(P.PRIMARY_CONTAINER, 0.4)};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        grid = QGridLayout(scroll_widget)
        grid.setSpacing(6)
        grid.setContentsMargins(0, 4, 0, 4)

        ordered_tags = []
        for cat_id in REPUTATION_CATEGORIES:
            for tag_id, tag_def in REPUTATION_TAGS.items():
                if tag_def["category"] == cat_id:
                    ordered_tags.append((tag_id, tag_def))

        col_count = 2
        for i, (tag_id, tag_def) in enumerate(ordered_tags):
            row = i // col_count
            col = i % col_count
            cat_id = tag_def["category"]
            label_text = tag_def["label"]

            btn = QPushButton(label_text)
            btn.setCheckable(False)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self._chip_style(cat_id, selected=False, disabled=False))
            btn.setToolTip(f"Category: {REPUTATION_CATEGORIES[cat_id]['label']} (+{tag_def['points']} pts)")
            btn.clicked.connect(lambda checked, tid=tag_id, cid=cat_id: self._on_chip_clicked(tid, cid))
            self._chip_btns[tag_id] = btn
            grid.addWidget(btn, row, col)

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        layout.addSpacing(4)

        # Button row
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("CANCEL")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setMinimumWidth(90)
        cancel_btn.setMinimumHeight(32)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {P.TEXT_DIM};
                border: 1px solid {P.OUTLINE_VARIANT};
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: {P.ON_SURFACE};
                border-color: {P.OUTLINE};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self._submit_btn = QPushButton("SUBMIT REPORT")
        self._submit_btn.setEnabled(False)
        self._submit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._submit_btn.setMinimumWidth(120)
        self._submit_btn.setMinimumHeight(32)
        self._submit_btn.setStyleSheet(f"""
            QPushButton {{
                background: {P.rgba(P.PRIMARY_CONTAINER, 0.12)};
                color: {P.PRIMARY};
                border: 1px solid {P.PRIMARY};
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {P.rgba(P.PRIMARY_CONTAINER, 0.22)}; }}
            QPushButton:disabled {{
                color: {P.rgba(P.TEXT_DIM, 0.4)};
                border-color: {P.rgba(P.OUTLINE_VARIANT, 0.3)};
                background: transparent;
            }}
        """)
        self._submit_btn.clicked.connect(self.accept)
        btn_row.addWidget(self._submit_btn)

        layout.addLayout(btn_row)

    def _on_chip_clicked(self, tag_id: str, category_id: str) -> None:
        if tag_id in self._selected:
            self._selected.discard(tag_id)
            self._chip_btns[tag_id].setStyleSheet(
                self._chip_style(category_id, selected=False, disabled=False)
            )
            self._chip_btns[tag_id].setEnabled(True)
        elif len(self._selected) < REPUTATION_MAX_TAGS:
            self._selected.add(tag_id)
            self._chip_btns[tag_id].setStyleSheet(
                self._chip_style(category_id, selected=True, disabled=False)
            )
        else:
            return

        at_max = len(self._selected) >= REPUTATION_MAX_TAGS
        for tid, btn in self._chip_btns.items():
            if tid not in self._selected:
                btn.setEnabled(not at_max)
                cat_id = REPUTATION_TAGS.get(tid, {}).get("category", "dangerous")
                btn.setStyleSheet(self._chip_style(cat_id, selected=False, disabled=at_max))

        self._counter_lbl.setText(f"{len(self._selected)} / {REPUTATION_MAX_TAGS} selected")
        self._submit_btn.setEnabled(len(self._selected) > 0)

    def paintEvent(self, event) -> None:
        """Paint bracket corners on the dialog border."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        s = 8
        pen = QPen(QColor(P.BRACKET_COLOR), 1.5)
        painter.setPen(pen)
        x0, y0 = rect.left(), rect.top()
        x1, y1 = rect.right(), rect.bottom()
        for px, py, dx, dy in [(x0,y0,1,1),(x1,y0,-1,1),(x0,y1,1,-1),(x1,y1,-1,-1)]:
            painter.drawLine(px, py, px + dx*s, py)
            painter.drawLine(px, py, px, py + dy*s)
        painter.end()

    @property
    def selected_tags(self) -> list[str]:
        """Return the list of selected tag IDs."""
        return list(self._selected)

    @property
    def selected_disposition(self) -> str:
        """Return the inferred disposition from selected tags."""
        hostile_tags = {"killed_me", "killed_us", "ambushed", "griefer", "scammed", "lied", "manipulated", "pirate_act", "pirate_confirmed"}
        friendly_tags = {"trustworthy", "helpful", "fair_fight", "friendly"}
        has_hostile = any(t in hostile_tags for t in self._selected)
        has_friendly = any(t in friendly_tags for t in self._selected)
        if has_hostile and not has_friendly:
            return "hostile"
        elif has_friendly and not has_hostile:
            return "friendly"
        return "unknown"

    def _center_on_screen(self) -> None:
        """Center the dialog on the primary screen."""
        screen = QGuiApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(x, y)
        else:
            self.move(200, 200)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() < 50:
            self._drag_active = True
            self._drag_start_pos = event.globalPosition().toPoint()
            self._drag_start_window_pos = self.pos()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_active:
            delta = event.globalPosition().toPoint() - self._drag_start_pos
            self.move(self._drag_start_window_pos + delta)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._drag_active:
            self._drag_active = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)


# ---------------------------------------------------------------------------
# SubmissionStatusCard — animated overlay using scanline animation (matches dossier/org)
# ---------------------------------------------------------------------------

from src.ui.widgets.progress_overlay import ProgressOverlay


# ---------------------------------------------------------------------------
# ReputationTab — 7-state widget
# ---------------------------------------------------------------------------

_STATE_DISABLED = 0
_STATE_EMPTY    = 1
_STATE_LOADING  = 2
_STATE_NO_DATA  = 3
_STATE_LOADED   = 4
_STATE_OFFLINE  = 5
_STATE_SELF     = 6


class ReputationTab(QWidget):
    """The reputation sub-tab panel — 7-state QStackedWidget driven by EventBus signals."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_handle: str = ""
        self._bars: dict[str, ReputationBar] = {}
        self._cooldown_end_time: float = 0.0
        self._cooldown_reason: str = ""
        self._cooldown_timer = QTimer(self)
        self._cooldown_timer.setInterval(1000)
        self._cooldown_timer.timeout.connect(self._tick_cooldown)
        self._build_ui()
        self._connect_signals()
        sm = SettingsManager.instance()
        if not sm.reputation_enabled:
            self._set_state("disabled")
        else:
            self._set_state("empty")

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._stack = QStackedWidget()

        self._stack.addWidget(self._build_disabled_page())   # 0
        self._stack.addWidget(self._build_empty_page())      # 1
        self._stack.addWidget(self._build_loading_page())    # 2
        self._stack.addWidget(self._build_no_data_page())    # 3
        self._stack.addWidget(self._build_loaded_page())     # 4
        self._stack.addWidget(self._build_offline_page())    # 5
        self._stack.addWidget(self._build_self_page())       # 6

        main_layout.addWidget(self._stack)

        # ProgressOverlay — unified scanline animation (matches dossier/org tabs)
        self._progress_overlay = ProgressOverlay(self)
        self._progress_overlay.hide()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Re-sync with settings in case enabled state changed while hidden
        try:
            from src.core.settings import SettingsManager
            sm = SettingsManager.instance()
            if sm.reputation_enabled and self._stack.currentIndex() == _STATE_DISABLED:
                self._set_state("empty")
            elif not sm.reputation_enabled and self._stack.currentIndex() != _STATE_DISABLED:
                self._set_state("disabled")
        except Exception:
            pass

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, '_progress_overlay'):
            self._progress_overlay.setGeometry(self.rect())

    def _centered_card_page(
        self, icon_text: str, heading: str, body: str, button_text: str | None = None
    ) -> QWidget:
        """Helper: build a simple centered GlassCard page with optional action button."""
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(32, 32, 32, 32)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = GlassCard()
        card.setMaximumWidth(480)
        card_layout = QVBoxLayout()
        card_layout.setSpacing(10)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel(icon_text)
        icon_lbl.setFont(font_inter(32))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("background: transparent; border: none;")

        head_lbl = QLabel(heading)
        head_lbl.setFont(label_caps())
        head_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        head_lbl.setStyleSheet(f"color: {P.ON_SURFACE}; background: transparent; border: none;")
        head_lbl.setWordWrap(True)

        body_lbl = QLabel(body)
        body_lbl.setFont(font_inter(11))
        body_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body_lbl.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent; border: none;")
        body_lbl.setWordWrap(True)

        card_layout.addWidget(icon_lbl)
        card_layout.addWidget(head_lbl)
        card_layout.addWidget(body_lbl)

        result = {"page": page, "card": card, "card_layout": card_layout}

        if button_text:
            btn = QPushButton(button_text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(32)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {P.rgba(P.PRIMARY_CONTAINER, 0.12)};
                    color: {P.PRIMARY};
                    border: 1px solid {P.PRIMARY};
                    border-radius: 4px;
                    padding: 4px 16px;
                    font-size: 11px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ background: {P.rgba(P.PRIMARY_CONTAINER, 0.22)}; }}
                QPushButton:disabled {{
                    color: {P.TEXT_DIM};
                    border-color: {P.OUTLINE_VARIANT};
                    background: transparent;
                }}
            """)
            card_layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
            result["button"] = btn

        card.content_layout.addLayout(card_layout)
        outer.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)
        return result

    def _build_disabled_page(self) -> QWidget:
        r = self._centered_card_page(
            "🚫",
            "REPUTATION SYSTEM DISABLED",
            "Enable the Community Reputation System in Settings to view and submit player reputation reports.",
            "OPEN SETTINGS",
        )
        self._disabled_open_settings_btn = r["button"]
        self._disabled_open_settings_btn.clicked.connect(
            lambda: EventBus.instance().navigate_to_tab.emit("settings")
        )
        return r["page"]

    def _build_empty_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel("SEARCH FOR A CITIZEN TO VIEW REPUTATION")
        lbl.setFont(label_caps())
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent;")
        layout.addWidget(lbl)
        return page

    def _build_loading_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        msg_lbl = QLabel("CHECKING REPUTATION DATABASE...")
        msg_lbl.setFont(label_caps())
        msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_lbl.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent;")

        layout.addWidget(msg_lbl)
        return page

    def _build_no_data_page(self) -> QWidget:
        r = self._centered_card_page(
            "📋",
            "NO REPORTS YET",
            "This citizen has no community reputation data. Be the first to report an interaction.",
            "REPORT INTERACTION",
        )
        self._no_data_report_btn = r["button"]
        self._no_data_report_btn.clicked.connect(self._on_report_clicked)
        return r["page"]

    def _build_loaded_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)
        outer.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Handle header
        self._loaded_handle_lbl = QLabel("")
        self._loaded_handle_lbl.setFont(headline_md())
        self._loaded_handle_lbl.setStyleSheet(
            f"color: {P.PRIMARY}; background: transparent; border: none;"
        )
        outer.addWidget(self._loaded_handle_lbl)

        # Reputation card
        rep_card = GlassCard(title="COMMUNITY REPUTATION SCORES")
        bars_layout = QVBoxLayout()
        bars_layout.setSpacing(8)
        bars_layout.setContentsMargins(0, 4, 0, 4)

        for cat_id in REPUTATION_CATEGORIES:
            bar = ReputationBar(cat_id)
            self._bars[cat_id] = bar
            bars_layout.addWidget(bar)

        rep_card.content_layout.addLayout(bars_layout)
        outer.addWidget(rep_card)

        # Total report count label
        self._total_reports_lbl = QLabel("")
        self._total_reports_lbl.setFont(font_inter(10))
        self._total_reports_lbl.setStyleSheet(
            f"color: {P.TEXT_DIM}; background: transparent; border: none;"
        )
        outer.addWidget(self._total_reports_lbl)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._report_btn = QPushButton("⊕  REPORT INTERACTION")
        self._report_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._report_btn.setFixedHeight(32)
        self._report_btn.setStyleSheet(f"""
            QPushButton {{
                background: {P.rgba(P.PRIMARY_CONTAINER, 0.12)};
                color: {P.PRIMARY};
                border: 1px solid {P.PRIMARY};
                border-radius: 4px;
                padding: 4px 16px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {P.rgba(P.PRIMARY_CONTAINER, 0.22)}; }}
            QPushButton:disabled {{
                color: {P.TEXT_DIM};
                border-color: {P.OUTLINE_VARIANT};
                background: transparent;
            }}
        """)
        self._report_btn.clicked.connect(self._on_report_clicked)

        self._refresh_btn = QPushButton("↻  REFRESH")
        self._refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_btn.setFixedHeight(32)
        self._refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {P.TEXT_DIM};
                border: 1px solid {P.OUTLINE_VARIANT};
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{ color: {P.ON_SURFACE}; border-color: {P.OUTLINE}; }}
        """)
        self._refresh_btn.clicked.connect(self._on_refresh_clicked)

        btn_row.addWidget(self._report_btn)
        btn_row.addWidget(self._refresh_btn)
        btn_row.addStretch()
        outer.addLayout(btn_row)

        outer.addStretch()
        return page

    def _build_offline_page(self) -> QWidget:
        r = self._centered_card_page(
            "📡",
            "REPUTATION DATABASE UNAVAILABLE",
            "Cannot connect to the reputation database. Check your internet connection or try again later.",
            "RETRY",
        )
        self._offline_retry_btn = r["button"]
        self._offline_retry_btn.clicked.connect(self._on_retry_clicked)
        return r["page"]

    def _build_self_page(self) -> QWidget:
        r = self._centered_card_page(
            "👤",
            "SELF-REPORT RESTRICTED",
            "You cannot create an interaction report for your own player profile. "
            "Community reputation reports are submitted by other citizens who have interacted with you in-game.",
            None,
        )
        return r["page"]

    def _connect_signals(self) -> None:
        bus = EventBus.instance()
        bus.reputation_loaded.connect(self._on_reputation_loaded)
        bus.reputation_load_failed.connect(self._on_reputation_failed)
        bus.reputation_report_submitted.connect(self._on_report_submitted)
        bus.reputation_report_failed.connect(self._on_report_failed)
        bus.reputation_system_status.connect(self._on_system_status)
        bus.settings_changed.connect(self._on_settings_changed)

    def _set_state(self, state: str) -> None:
        """Switch to a named state page."""
        state_map = {
            "disabled": _STATE_DISABLED,
            "empty":    _STATE_EMPTY,
            "loading":  _STATE_LOADING,
            "no_data":  _STATE_NO_DATA,
            "loaded":   _STATE_LOADED,
            "offline":  _STATE_OFFLINE,
            "self":     _STATE_SELF,
        }
        idx = state_map.get(state, _STATE_EMPTY)
        self._stack.setCurrentIndex(idx)

        # Show/hide progress overlay based on state — hide stack to prevent card stacking
        if state == "loading":
            self._stack.hide()
            self._progress_overlay.set_message("CHECKING REPUTATION DATABASE...")
            self._progress_overlay.show_overlay()
        else:
            self._progress_overlay.hide_overlay()
            self._stack.show()

    def load_player(self, handle: str) -> None:
        """Called when a new player search completes."""
        sm = SettingsManager.instance()
        if not sm.reputation_enabled:
            self._set_state("disabled")
            return

        self._current_handle = handle

        from src.services.reputation_service import ReputationService
        is_self = False
        try:
            if ReputationService.is_initialized():
                svc = ReputationService.instance()
                local_handle = svc.local_player_handle or ""
                if local_handle and handle.lower() == local_handle.lower():
                    is_self = True
        except Exception:
            pass

        if is_self:
            self._set_state("self")
            return

        self._set_state("loading")
        self._loaded_handle_lbl.setText(f"@{handle.upper()}")
        self._cooldown_timer.stop()
        self._cooldown_end_time = 0.0
        self._cooldown_reason = ""
        # Hide any existing overlay when loading a player
        if hasattr(self, '_progress_overlay'):
            self._progress_overlay.hide_overlay()

        # Immediate local cooldown check — show disabled state instantly
        # (server check will follow and correct if needed)
        try:
            sm = SettingsManager.instance()
            hist = sm.reputation_history.get(handle.lower(), [])
            now = time.time()
            # Daily: 1 report per 24h
            if hist:
                last = max(hist)
                elapsed = now - last
                if elapsed < 86400:
                    remaining = int(86400 - elapsed)
                    self._cooldown_reason = "You already reported this player today (local)"
                    self._cooldown_end_time = last + 86400
                    self._cooldown_timer.start()
                    # Pre-render disabled button so it's visible immediately after load
                    self._update_cooldown_display()
                    log.info("ReputationTab: local daily cooldown for %s — %ds remaining", handle, remaining)
                # Monthly: 2 per 30 days
                recent_30d = [t for t in hist if now - t < 30 * 24 * 3600]
                if len(recent_30d) >= 2:
                    # Find earliest of the last 2 to compute cooldown (oldest of the 2 still within window)
                    oldest = sorted(recent_30d)[-2] if len(recent_30d) >= 2 else min(recent_30d)
                    remaining_m = int((oldest + 30*24*3600) - now)
                    if remaining_m > 0:
                        self._cooldown_reason = "Monthly limit reached (local)"
                        self._cooldown_end_time = max(self._cooldown_end_time, oldest + 30*24*3600)
                        self._cooldown_timer.start()
                        self._update_cooldown_display()
                        log.info("ReputationTab: local monthly limit for %s — %ds remaining", handle, remaining_m)
        except Exception as e:
            log.debug("Local cooldown pre-check failed: %s", e)

        self._check_rate_limit_server(handle)

    def _check_rate_limit_server(self, handle: str) -> None:
        """Check rate limit via server-side Edge Function in background."""
        from src.services.reputation_service import ReputationService
        from src.services.reputation_worker import ReputationCheckRateLimitWorker

        if not ReputationService.is_initialized():
            return

        if hasattr(self, '_rate_limit_worker') and self._rate_limit_worker:
            try:
                if self._rate_limit_worker.isRunning():
                    pass
                else:
                    self._rate_limit_worker.deleteLater()
            except RuntimeError:
                pass
            self._rate_limit_worker = None

        # Don't parent worker to self — prevents QThread crash when widget is destroyed
        worker = ReputationCheckRateLimitWorker(handle)
        self._rate_limit_worker = worker
        worker.finished_success.connect(self._on_rate_limit_checked)
        worker.finished_error.connect(self._on_rate_limit_check_failed)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(lambda: setattr(self, '_rate_limit_worker', None) if getattr(self, '_rate_limit_worker', None) is worker else None)
        worker.start()

    @pyqtSlot(dict)
    def _on_rate_limit_checked(self, result: dict) -> None:
        """Handle server-side rate limit check result."""
        if not result:
            self._set_report_buttons_enabled()
            return

        allowed = result.get("allowed", True)
        cooldown_seconds = result.get("cooldown_seconds", 0)
        monthly_remaining = result.get("monthly_remaining", 2)
        reports_used = result.get("reports_used", 0)
        monthly_limit = result.get("monthly_limit", 2)
        reason = result.get("reason", "")
        reason_detail = result.get("reasonDetail", "")

        if allowed:
            self._set_report_buttons_enabled()
            log.info("ReputationTab: rate limit check PASSED for %s — report submission allowed.", self._current_handle)
        else:
            if reason_detail:
                display_msg = reason_detail
            elif cooldown_seconds > 0:
                display_msg = f"COOLDOWN ACTIVE — wait {self._format_duration(cooldown_seconds)}"
            else:
                display_msg = f"Reporting blocked. Try again later."

            log.info(
                "ReputationTab: rate limit check BLOCKED for %s — reason: %s | detail: %s | cooldown: %ds | monthly: %d/%d",
                self._current_handle, reason, reason_detail, cooldown_seconds, reports_used, monthly_limit,
            )

            if cooldown_seconds > 0:
                self._cooldown_reason = reason_detail or reason
                self._cooldown_end_time = time.time() + cooldown_seconds
                self._cooldown_timer.start()
                self._update_cooldown_display()
            else:
                self._set_report_buttons_disabled(True, display_msg)

    @staticmethod
    def _format_duration(seconds: int) -> str:
        """Format seconds into a human-readable duration string."""
        if seconds <= 0:
            return "0s"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if secs > 0 and hours == 0:
            parts.append(f"{secs}s")
        return " ".join(parts) if parts else "0s"

    @pyqtSlot(str)
    def _on_rate_limit_check_failed(self, error_msg: str) -> None:
        """Handle server-side rate limit check failure — fail open."""
        log.warning("Rate limit check failed, allowing submission: %s", error_msg)
        self._set_report_buttons_enabled()

    def _tick_cooldown(self) -> None:
        """Update countdown display every second."""
        remaining = self._cooldown_end_time - time.time()
        if remaining <= 0:
            self._cooldown_timer.stop()
            self._cooldown_end_time = 0.0
            self._set_report_buttons_enabled()
            return
        self._update_cooldown_display()

    def _update_cooldown_display(self) -> None:
        """Update button text with remaining cooldown time and reason."""
        remaining = max(0, self._cooldown_end_time - time.time())
        time_str = self._format_duration(int(remaining))
        reason = getattr(self, "_cooldown_reason", "")
        if reason:
            msg = f"⏳ {time_str} — {reason}"
        else:
            msg = f"COOLDOWN {time_str}"
        self._set_report_buttons_disabled(True, msg, cooldown=True)

    def _set_report_buttons_enabled(self) -> None:
        """Enable both report buttons with normal styling."""
        self._report_btn.setEnabled(True)
        self._report_btn.setText("⊕  REPORT INTERACTION")
        self._report_btn.setToolTip("")
        self._report_btn.setStyleSheet(f"""
            QPushButton {{
                background: {P.rgba(P.PRIMARY_CONTAINER, 0.12)};
                color: {P.PRIMARY};
                border: 1px solid {P.PRIMARY};
                border-radius: 4px;
                padding: 4px 16px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {P.rgba(P.PRIMARY_CONTAINER, 0.22)}; }}
            QPushButton:disabled {{
                color: {P.TEXT_DIM};
                border-color: {P.OUTLINE_VARIANT};
                background: transparent;
            }}
        """)
        self._no_data_report_btn.setEnabled(True)
        self._no_data_report_btn.setText("REPORT INTERACTION")
        self._no_data_report_btn.setToolTip("")

    def _set_report_buttons_disabled(self, disabled: bool, tooltip: str = "", cooldown: bool = False) -> None:
        """Disable/enable both report buttons with appropriate styling."""
        if disabled and cooldown:
            btn_style = f"""
                QPushButton {{
                    background: {P.rgba(_COOLDOWN_COLOR, 0.08)};
                    color: {P.rgba(_COOLDOWN_COLOR, 0.8)};
                    border: 1px solid {P.rgba(_COOLDOWN_COLOR, 0.3)};
                    border-radius: 4px;
                    padding: 4px 12px;
                    font-size: 10px;
                    font-weight: bold;
                    font-family: 'JetBrains Mono', monospace;
                }}
            """
            self._report_btn.setStyleSheet(btn_style)
            self._no_data_report_btn.setStyleSheet(btn_style)
        elif disabled:
            btn_style = f"""
                QPushButton {{
                    color: {P.TEXT_DIM};
                    border-color: {P.OUTLINE_VARIANT};
                    background: transparent;
                    border: 1px solid {P.OUTLINE_VARIANT};
                    border-radius: 4px;
                    padding: 4px 16px;
                    font-size: 11px;
                }}
            """
            self._report_btn.setStyleSheet(btn_style)
            self._no_data_report_btn.setStyleSheet(btn_style)
        else:
            self._set_report_buttons_enabled()
            return

        self._report_btn.setEnabled(not disabled)
        self._no_data_report_btn.setEnabled(not disabled)

        if tooltip:
            self._report_btn.setToolTip(tooltip)
            self._no_data_report_btn.setToolTip(tooltip)

        if cooldown and disabled:
            # Use shorter text for button, full message in tooltip
            short_text = tooltip if len(tooltip) <= 35 else tooltip[:32] + "..."
            self._report_btn.setText(short_text)
            self._no_data_report_btn.setText(short_text)

    def clear(self) -> None:
        """Reset to empty state (called when DossierTab clears results)."""
        self._current_handle = ""
        self._cooldown_timer.stop()
        self._cooldown_end_time = 0.0
        sm = SettingsManager.instance()
        if not sm.reputation_enabled:
            self._set_state("disabled")
        else:
            self._set_state("empty")

    @pyqtSlot(str, dict)
    def _on_reputation_loaded(self, handle: str, scores: dict) -> None:
        """Handle reputation data arriving from AppController."""
        if handle.lower() != self._current_handle.lower():
            log.debug(
                "ReputationTab: discarding stale signal for %s (current: %s)",
                handle, self._current_handle,
            )
            return

        # Hide status card if showing
        if hasattr(self, '_progress_overlay'):
            self._progress_overlay.hide_overlay()

        sm = SettingsManager.instance()
        if not sm.reputation_enabled:
            self._set_state("disabled")
            return

        if not scores:
            self._set_state("no_data")
            # Preserve cooldown on no_data page as well
            if self._cooldown_end_time > 0 and self._cooldown_end_time > time.time():
                self._update_cooldown_display()
            return

        # Populate bars
        total_reports = 0
        for cat_id, bar in self._bars.items():
            row = scores.get(cat_id, {})
            s = row.get("score", 0)
            rc = row.get("report_count", 0)
            from src.services.reputation_service import ReputationService
            pct = ReputationService._normalize_score(s, rc, cat_id)
            verdict = _verdict_for_score(cat_id, pct)
            bar.set_value(pct, rc, verdict)
            total_reports = max(total_reports, rc)

        # Total tag submissions (sum of all report_counts / categories)
        all_counts = [scores.get(c, {}).get("report_count", 0) for c in REPUTATION_CATEGORIES]
        max_count = max(all_counts) if all_counts else 0
        if max_count == 0:
            self._total_reports_lbl.setText("No interaction reports submitted yet.")
        elif max_count == 1:
            self._total_reports_lbl.setText("Based on 1 interaction report.")
        else:
            self._total_reports_lbl.setText(f"Based on {max_count} interaction reports.")

        self._set_state("loaded")
        # Ensure cooldown button is still visible after reload
        if self._cooldown_end_time > 0 and self._cooldown_end_time > time.time():
            self._update_cooldown_display()

    @pyqtSlot(str, str)
    def _on_reputation_failed(self, handle: str, error_msg: str) -> None:
        """Handle reputation fetch failure."""
        if handle.lower() != self._current_handle.lower():
            return
        log.warning("ReputationTab: fetch failed for %s: %s", handle, error_msg)
        self._set_state("offline")

    @pyqtSlot(str)
    def _on_report_submitted(self, handle: str) -> None:
        """Re-trigger loading state after a successful report submission."""
        if handle.lower() != self._current_handle.lower():
            return

        # Record report timestamp in local history
        from src.core.settings import SettingsManager
        sm = SettingsManager.instance()
        history = sm.reputation_history
        now = time.time()
        handle_lower = handle.lower()
        if handle_lower not in history:
            history[handle_lower] = []
        history[handle_lower].append(now)
        history[handle_lower] = [t for t in history[handle_lower] if now - t < 30 * 24 * 3600]
        sm.reputation_history = history
        sm.force_save()

        # Immediately disable the report button with cooldown state
        self._cooldown_reason = "Report submitted — cooldown active"
        self._cooldown_end_time = time.time() + 86400  # 24h placeholder, will be updated by server
        self._cooldown_timer.start()
        self._update_cooldown_display()

        # Show overlay and hide cards to prevent stacking
        if hasattr(self, '_progress_overlay'):
            self._stack.hide()
            self._progress_overlay.hide_overlay()
            self._progress_overlay.set_message('RELOADING REPUTATION...')
            self._progress_overlay.show_overlay()

        # Re-check rate limit server-side to get accurate cooldown
        self._check_rate_limit_server(handle)

        # AppController will re-emit reputation after submit
        # Do NOT switch to loading state - stay on loaded page so cooldown button is visible

    @pyqtSlot(str, str)
    def _on_report_failed(self, handle: str, error_msg: str) -> None:
        """Handle reputation report submission failure."""
        if handle.lower() != self._current_handle.lower():
            return
        if hasattr(self, '_progress_overlay'):
            self._progress_overlay.hide_overlay()
        self._set_state("loading")
        EventBus.instance().request_reputation_fetch.emit(self._current_handle)

        from src.ui.widgets.confirm_dialog import show_error_dialog
        show_error_dialog("REPORT SUBMISSION FAILED", error_msg, parent=self.window())

    @pyqtSlot(str)
    def _on_system_status(self, status: str) -> None:
        """React to reputation system going online, offline, error, or disabled."""
        if status in ("offline", "error") and self._stack.currentIndex() == _STATE_LOADING:
            self._set_state("offline")
        elif status == "disabled":
            self._set_state("disabled")

    @pyqtSlot(str, object)
    def _on_settings_changed(self, key: str, value: object) -> None:
        """React to reputation_enabled toggle in settings."""
        if key == "reputation_enabled":
            if value:
                if self._current_handle:
                    self._set_state("loading")
                    EventBus.instance().request_reputation_fetch.emit(self._current_handle)
                    self._check_rate_limit_server(self._current_handle)
                else:
                    self._set_state("empty")
            else:
                self._set_state("disabled")

    def _on_report_clicked(self) -> None:
        """Open the ReportDialog and emit reputation_report_requested on accept."""
        if not self._current_handle:
            return

        from src.services.reputation_service import ReputationService
        if ReputationService.is_initialized():
            svc = ReputationService.instance()
            local_handle = svc.local_player_handle or ""
            if local_handle and self._current_handle.lower() == local_handle.lower():
                self._set_state("self")
                return

        dialog = ReportDialog(self._current_handle, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            tags = dialog.selected_tags
            if tags:
                disposition = dialog.selected_disposition
                # Hide cards and show submitting overlay
                if hasattr(self, '_progress_overlay'):
                    self._stack.hide()
                    self._progress_overlay.hide_overlay()
                    self._progress_overlay.set_message('SUBMITTING REPORT...')
                    self._progress_overlay.show_overlay()
                EventBus.instance().reputation_report_requested.emit(
                    self._current_handle, tags, disposition
                )

    def _on_refresh_clicked(self) -> None:
        """Manually re-trigger a reputation fetch for the current handle."""
        if self._current_handle:
            self._set_state("loading")
            EventBus.instance().request_reputation_fetch.emit(self._current_handle)

    def _on_retry_clicked(self) -> None:
        """Retry after offline — attempt a re-fetch."""
        if self._current_handle:
            self._set_state("loading")
            from src.services.reputation_service import ReputationService
            from src.services.reputation_worker import ReputationStartupWorker
            if ReputationService.is_initialized():
                EventBus.instance().search_player_requested.emit(self._current_handle)
            else:
                self._set_state("offline")
