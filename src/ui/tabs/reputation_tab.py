"""
src/ui/tabs/reputation_tab.py
ReputationTab — community reputation display and report submission UI.

Components:
    ReputationBar     — renders a single category score (progress bar + labels)
    ReportDialog      — modal tag-selection dialog (max 5 tags, chip toggle UI)
    ReputationTab     — main 6-state widget (disabled|empty|loading|no_data|loaded|offline)

State machine:
    disabled  → reputation system is off in settings
    empty     → no player searched yet
    loading   → fetch in progress
    no_data   → player found but no reports yet
    loaded    → 5 category bars + report button
    offline   → Supabase unavailable

Signal flow:
    DossierTab._on_scrape_completed → reputation_tab.load_player(handle)
    reputation_tab → ReportDialog → EventBus.reputation_report_requested
    AppController → EventBus.reputation_loaded / reputation_load_failed
    reputation_tab._on_reputation_loaded / _on_reputation_failed
"""

import logging
from PyQt6.QtCore import Qt, pyqtSlot, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QColor, QPainter, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QDialog, QDialogButtonBox, QScrollArea, QFrame,
    QStackedWidget, QGridLayout, QSizePolicy
)

from src.core.events import EventBus
from src.core.settings import SettingsManager
from src.ui.theme import palette as P
from src.ui.theme.fonts import label_caps, font_inter, headline_md
from src.ui.widgets.glass_card import GlassCard
from src.app.constants import REPUTATION_TAGS, REPUTATION_CATEGORIES, REPUTATION_MAX_TAGS

log = logging.getLogger(__name__)


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
# ReputationBar
# ---------------------------------------------------------------------------

class ReputationBar(QWidget):
    """
    Renders a single reputation category row:
        [Category Label]  [Percentage%]  [Progress Bar]  [Verdict]
        [Report count sub-label]

    Colors derived from REPUTATION_CATEGORIES[category_id]["color_hex"].
    """

    def __init__(self, category_id: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._category_id = category_id
        cat_def = REPUTATION_CATEGORIES.get(category_id, {})
        self._color = cat_def.get("color_hex", P.PRIMARY)
        self._build_ui(cat_def.get("label", category_id.upper()))

    def _build_ui(self, cat_label: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(2)

        # Top row: label + pct + bar + verdict
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self._cat_lbl = QLabel(cat_label)
        self._cat_lbl.setFont(font_inter(11, QFont.Weight.Bold))
        self._cat_lbl.setStyleSheet(
            f"color: {self._color}; background: transparent; border: none; min-width: 120px;"
        )
        self._cat_lbl.setFixedWidth(130)

        self._pct_lbl = QLabel("0%")
        self._pct_lbl.setFont(font_inter(11, QFont.Weight.Bold))
        self._pct_lbl.setStyleSheet(
            f"color: {P.ON_SURFACE}; background: transparent; border: none; min-width: 36px;"
        )
        self._pct_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._pct_lbl.setFixedWidth(40)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(8)
        self._bar.setStyleSheet(f"""
            QProgressBar {{
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background: {self._color};
                border-radius: 3px;
            }}
        """)

        self._verdict_lbl = QLabel("—")
        self._verdict_lbl.setFont(font_inter(10))
        self._verdict_lbl.setStyleSheet(
            f"color: {P.TEXT_DIM}; background: transparent; border: none;"
        )
        self._verdict_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._verdict_lbl.setFixedWidth(220)

        top_row.addWidget(self._cat_lbl)
        top_row.addWidget(self._pct_lbl)
        top_row.addWidget(self._bar, 1)
        top_row.addWidget(self._verdict_lbl)

        # Sub-label: report count
        self._count_lbl = QLabel("")
        self._count_lbl.setFont(font_inter(9))
        self._count_lbl.setStyleSheet(
            f"color: {P.TEXT_DIM}; background: transparent; border: none; padding-left: 130px;"
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
# ReportDialog
# ---------------------------------------------------------------------------

class ReportDialog(QDialog):
    """
    Modal dialog for selecting interaction tags when submitting a report.

    - 2-column grid of 15 tag toggle chips
    - Max REPUTATION_MAX_TAGS (5) selections enforced client-side
    - Chips for un-selected become disabled (not just styled) once limit reached
    - Submit button disabled until ≥1 tag selected
    """

    def __init__(self, handle: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._handle = handle
        self._selected: set[str] = set()
        self._chip_btns: dict[str, QPushButton] = {}
        self.setWindowTitle(f"REPORT INTERACTION — @{handle.upper()}")
        self.setModal(True)
        self.setMinimumWidth(560)
        self.setStyleSheet(f"""
            QDialog {{
                background: {P.SURFACE_CONTAINER_LOW};
                color: {P.ON_SURFACE};
            }}
        """)
        self._build_ui()

    def _chip_style(self, category_id: str, selected: bool, disabled: bool) -> str:
        cat = REPUTATION_CATEGORIES.get(category_id, {})
        color = cat.get("color_hex", P.PRIMARY)
        if disabled and not selected:
            return f"""
                QPushButton {{
                    background: rgba(255,255,255,0.03);
                    color: {P.TEXT_DIM};
                    border: 1px solid rgba(255,255,255,0.07);
                    border-radius: 4px;
                    padding: 6px 10px;
                    font-size: 11px;
                    text-align: left;
                }}
            """
        if selected:
            return f"""
                QPushButton {{
                    background: {color}30;
                    color: {color};
                    border: 2px solid {color};
                    border-radius: 4px;
                    padding: 6px 10px;
                    font-size: 11px;
                    font-weight: bold;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background: {color}50;
                }}
            """
        return f"""
            QPushButton {{
                background: rgba(255,255,255,0.05);
                color: {P.ON_SURFACE};
                border: 1px solid {color}60;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 11px;
                text-align: left;
            }}
            QPushButton:hover {{
                background: {color}20;
                border-color: {color};
            }}
        """

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Header
        header_lbl = QLabel(
            f"Select up to {REPUTATION_MAX_TAGS} tags that describe your interaction with "
            f"@{self._handle}. This report is anonymous."
        )
        header_lbl.setFont(font_inter(11))
        header_lbl.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent; border: none;")
        header_lbl.setWordWrap(True)
        layout.addWidget(header_lbl)

        # Selection counter
        self._counter_lbl = QLabel(f"0 / {REPUTATION_MAX_TAGS} selected")
        self._counter_lbl.setFont(label_caps())
        self._counter_lbl.setStyleSheet(f"color: {P.PRIMARY}; background: transparent; border: none;")
        layout.addWidget(self._counter_lbl)

        # Tag chips grid
        grid = QGridLayout()
        grid.setSpacing(6)
        grid.setContentsMargins(0, 4, 0, 4)

        # Group tags by category for visual ordering
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

        layout.addLayout(grid)

        # Buttons
        btn_box = QDialogButtonBox()
        self._submit_btn = QPushButton("SUBMIT REPORT")
        self._submit_btn.setEnabled(False)
        self._submit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._submit_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(0, 170, 255, 0.15);
                color: {P.PRIMARY};
                border: 1px solid {P.PRIMARY};
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: rgba(0, 170, 255, 0.25); }}
            QPushButton:disabled {{
                color: {P.TEXT_DIM};
                border-color: {P.OUTLINE_VARIANT};
                background: transparent;
            }}
        """)
        self._submit_btn.clicked.connect(self.accept)

        cancel_btn = QPushButton("CANCEL")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {P.TEXT_DIM};
                border: 1px solid {P.OUTLINE_VARIANT};
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 11px;
            }}
            QPushButton:hover {{ color: {P.ON_SURFACE}; border-color: {P.OUTLINE}; }}
        """)
        cancel_btn.clicked.connect(self.reject)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self._submit_btn)
        layout.addLayout(btn_row)

    def _on_chip_clicked(self, tag_id: str, category_id: str) -> None:
        if tag_id in self._selected:
            # Deselect
            self._selected.discard(tag_id)
            self._chip_btns[tag_id].setStyleSheet(
                self._chip_style(category_id, selected=False, disabled=False)
            )
            self._chip_btns[tag_id].setEnabled(True)
        elif len(self._selected) < REPUTATION_MAX_TAGS:
            # Select
            self._selected.add(tag_id)
            self._chip_btns[tag_id].setStyleSheet(
                self._chip_style(category_id, selected=True, disabled=False)
            )
        else:
            # Already at max — ignore click
            return

        # Update disabled state for un-selected chips
        at_max = len(self._selected) >= REPUTATION_MAX_TAGS
        for tid, btn in self._chip_btns.items():
            if tid not in self._selected:
                btn.setEnabled(not at_max)
                # Get category for style
                cat_id = REPUTATION_TAGS.get(tid, {}).get("category", "dangerous")
                btn.setStyleSheet(self._chip_style(cat_id, selected=False, disabled=at_max))

        # Update counter and submit button
        self._counter_lbl.setText(f"{len(self._selected)} / {REPUTATION_MAX_TAGS} selected")
        self._submit_btn.setEnabled(len(self._selected) > 0)

    @property
    def selected_tags(self) -> list[str]:
        """Return the list of selected tag IDs."""
        return list(self._selected)


# ---------------------------------------------------------------------------
# ReputationTab — 6-state widget
# ---------------------------------------------------------------------------

# State indices in QStackedWidget
_STATE_DISABLED = 0
_STATE_EMPTY    = 1
_STATE_LOADING  = 2
_STATE_NO_DATA  = 3
_STATE_LOADED   = 4
_STATE_OFFLINE  = 5


class ReputationTab(QWidget):
    """
    The reputation sub-tab panel — 6-state QStackedWidget driven by EventBus signals.

    States:
        disabled → reputation is off in settings
        empty    → no player loaded
        loading  → fetch in progress for _current_handle
        no_data  → player exists but no reports yet
        loaded   → 5 ReputationBars + report button
        offline  → Supabase unreachable

    EventBus connections:
        reputation_loaded → _on_reputation_loaded
        reputation_load_failed → _on_reputation_failed
        reputation_report_submitted → trigger re-fetch
        reputation_system_status → update state if offline/online
        settings_changed → react to reputation_enabled toggle
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_handle: str = ""
        self._bars: dict[str, ReputationBar] = {}
        self._build_ui()
        self._connect_signals()
        # Initialize state based on current settings
        sm = SettingsManager.instance()
        if not sm.reputation_enabled:
            self._set_state("disabled")
        else:
            self._set_state("empty")

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

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

        main_layout.addWidget(self._stack)

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
                    background: rgba(0, 170, 255, 0.12);
                    color: {P.PRIMARY};
                    border: 1px solid {P.PRIMARY};
                    border-radius: 4px;
                    padding: 4px 16px;
                    font-size: 11px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ background: rgba(0, 170, 255, 0.22); }}
                QPushButton:disabled {{
                    color: rgba(255, 255, 255, 0.3);
                    border-color: rgba(255, 255, 255, 0.15);
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

        self._loading_spinner_lbl = QLabel("◌")
        self._loading_spinner_lbl.setFont(font_inter(36))
        self._loading_spinner_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_spinner_lbl.setStyleSheet(f"color: {P.PRIMARY}; background: transparent;")

        # Animate the spinner character by cycling through states
        self._spinner_timer = QTimer(self)
        self._spinner_timer.setInterval(200)
        self._spinner_chars = ["◌", "○", "◎", "●", "◎", "○"]
        self._spinner_idx = 0
        self._spinner_timer.timeout.connect(self._tick_spinner)

        msg_lbl = QLabel("CHECKING REPUTATION DATABASE...")
        msg_lbl.setFont(label_caps())
        msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_lbl.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent;")

        layout.addWidget(self._loading_spinner_lbl)
        layout.addWidget(msg_lbl)
        return page

    def _tick_spinner(self) -> None:
        self._spinner_idx = (self._spinner_idx + 1) % len(self._spinner_chars)
        self._loading_spinner_lbl.setText(self._spinner_chars[self._spinner_idx])

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

        # Create one bar per category in display order
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
                background: rgba(0, 170, 255, 0.12);
                color: {P.PRIMARY};
                border: 1px solid {P.PRIMARY};
                border-radius: 4px;
                padding: 4px 16px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: rgba(0, 170, 255, 0.22); }}
            QPushButton:disabled {{
                color: rgba(255, 255, 255, 0.3);
                border-color: rgba(255, 255, 255, 0.15);
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

    # ------------------------------------------------------------------
    # Signal connections
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        bus = EventBus.instance()
        bus.reputation_loaded.connect(self._on_reputation_loaded)
        bus.reputation_load_failed.connect(self._on_reputation_failed)
        bus.reputation_report_submitted.connect(self._on_report_submitted)
        bus.reputation_report_failed.connect(self._on_report_failed)
        bus.reputation_system_status.connect(self._on_system_status)
        bus.settings_changed.connect(self._on_settings_changed)

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    def _set_state(self, state: str) -> None:
        """Switch to a named state page."""
        state_map = {
            "disabled": _STATE_DISABLED,
            "empty":    _STATE_EMPTY,
            "loading":  _STATE_LOADING,
            "no_data":  _STATE_NO_DATA,
            "loaded":   _STATE_LOADED,
            "offline":  _STATE_OFFLINE,
        }
        idx = state_map.get(state, _STATE_EMPTY)
        self._stack.setCurrentIndex(idx)

        # Manage spinner timer
        if state == "loading":
            self._spinner_timer.start()
        else:
            self._spinner_timer.stop()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_player(self, handle: str) -> None:
        """
        Called when a new player search completes.
        Sets loading state and records the current handle for stale-signal detection.
        The actual fetch is started by AppController.
        """
        sm = SettingsManager.instance()
        if not sm.reputation_enabled:
            self._set_state("disabled")
            return

        self._current_handle = handle
        self._set_state("loading")
        # Update handle label in case we arrive at 'loaded' state
        self._loaded_handle_lbl.setText(f"@{handle.upper()}")

        # Check self-report restriction
        from src.services.reputation_service import ReputationService
        is_self = False
        try:
            if ReputationService.is_initialized():
                local_handle = ReputationService.instance().local_player_handle
                if local_handle and handle.lower() == local_handle.lower():
                    is_self = True
        except Exception:
            pass

        if is_self:
            self._report_btn.setEnabled(False)
            self._report_btn.setToolTip("You cannot submit a reputation report for yourself.")
            self._no_data_report_btn.setEnabled(False)
            self._no_data_report_btn.setToolTip("You cannot submit a reputation report for yourself.")
        else:
            self._report_btn.setEnabled(True)
            self._report_btn.setToolTip("")
            self._no_data_report_btn.setEnabled(True)
            self._no_data_report_btn.setToolTip("")

    def clear(self) -> None:
        """Reset to empty state (called when DossierTab clears results)."""
        self._current_handle = ""
        sm = SettingsManager.instance()
        if not sm.reputation_enabled:
            self._set_state("disabled")
        else:
            self._set_state("empty")

    # ------------------------------------------------------------------
    # EventBus slots
    # ------------------------------------------------------------------

    @pyqtSlot(str, dict)
    def _on_reputation_loaded(self, handle: str, scores: dict) -> None:
        """Handle reputation data arriving from AppController."""
        # Stale-signal guard: only process data for the current handle
        if handle.lower() != self._current_handle.lower():
            log.debug(
                "ReputationTab: discarding stale signal for %s (current: %s)",
                handle, self._current_handle,
            )
            return

        sm = SettingsManager.instance()
        if not sm.reputation_enabled:
            self._set_state("disabled")
            return

        if not scores:
            # Player exists in DB but has no score rows
            self._set_state("no_data")
            return

        # Populate bars
        total_reports = 0
        for cat_id, bar in self._bars.items():
            row = scores.get(cat_id, {})
            s = row.get("score", 0)
            rc = row.get("report_count", 0)
            from src.services.reputation_service import ReputationService
            pct = ReputationService._normalize_score(s, rc)
            verdict = _verdict_for_score(cat_id, pct)
            bar.set_value(pct, rc, verdict)
            total_reports = max(total_reports, rc)

        # Total tag submissions (sum of all report_counts / 5 categories)
        all_counts = [scores.get(c, {}).get("report_count", 0) for c in REPUTATION_CATEGORIES]
        max_count = max(all_counts) if all_counts else 0
        if max_count == 0:
            self._total_reports_lbl.setText("No interaction reports submitted yet.")
        elif max_count == 1:
            self._total_reports_lbl.setText("Based on 1 interaction report.")
        else:
            self._total_reports_lbl.setText(f"Based on {max_count} interaction reports.")

        self._set_state("loaded")

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
        # AppController will re-emit reputation_loaded after submit
        self._set_state("loading")

    @pyqtSlot(str, str)
    def _on_report_failed(self, handle: str, error_msg: str) -> None:
        """Handle reputation report submission failure."""
        if handle.lower() != self._current_handle.lower():
            return
        # Re-fetch reputation data to restore UI state from loading to loaded
        self._set_state("loading")
        EventBus.instance().search_player_requested.emit(self._current_handle)

        from src.ui.widgets.confirm_dialog import show_error_dialog
        show_error_dialog("REPORT SUBMISSION FAILED", error_msg, parent=self.window())

    @pyqtSlot(str)
    def _on_system_status(self, status: str) -> None:
        """React to reputation system going online or offline."""
        if status == "offline" and self._stack.currentIndex() == _STATE_LOADING:
            self._set_state("offline")
        elif status == "disabled":
            self._set_state("disabled")

    @pyqtSlot(str, object)
    def _on_settings_changed(self, key: str, value: object) -> None:
        """React to reputation_enabled toggle in settings."""
        if key == "reputation_enabled":
            if value:
                # Just enabled — show appropriate state
                if self._current_handle:
                    self._set_state("loading")
                else:
                    self._set_state("empty")
            else:
                self._set_state("disabled")

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_report_clicked(self) -> None:
        """Open the ReportDialog and emit reputation_report_requested on accept."""
        if not self._current_handle:
            return

        # Safeguard: prevent submitting report if it's the local user
        from src.services.reputation_service import ReputationService
        if ReputationService.is_initialized():
            local_handle = ReputationService.instance().local_player_handle
            if local_handle and self._current_handle.lower() == local_handle.lower():
                from src.ui.widgets.confirm_dialog import show_error_dialog
                show_error_dialog("REPORT RESTRICTED", "You cannot submit a reputation report for yourself.", parent=self.window())
                return

        dialog = ReportDialog(self._current_handle, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            tags = dialog.selected_tags
            if tags:
                EventBus.instance().reputation_report_requested.emit(
                    self._current_handle, tags
                )

    def _on_refresh_clicked(self) -> None:
        """Manually re-trigger a reputation fetch for the current handle."""
        if self._current_handle:
            self._set_state("loading")
            EventBus.instance().search_player_requested.emit(self._current_handle)

    def _on_retry_clicked(self) -> None:
        """Retry after offline — attempt a re-fetch."""
        if self._current_handle:
            self._set_state("loading")
            # Trigger a fresh fetch via the startup path
            from src.services.reputation_service import ReputationService
            from src.services.reputation_worker import ReputationStartupWorker
            if ReputationService.is_initialized():
                EventBus.instance().search_player_requested.emit(self._current_handle)
            else:
                self._set_state("offline")
