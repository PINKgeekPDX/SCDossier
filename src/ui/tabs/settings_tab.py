import json

from PyQt6.QtCore import Qt, QUrl, pyqtSlot
from PyQt6.QtGui import QColor, QFont, QDesktopServices, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSpinBox,
    QCheckBox, QPushButton, QComboBox, QLineEdit, QScrollArea, QFrame,
    QGridLayout, QProgressBar, QFileDialog, QApplication,
    QListWidget, QListWidgetItem, QSplitter, QTextBrowser
)

from src.core.settings import SettingsManager
from src.core.paths import PathManager, get_asset_path
from src.core.events import EventBus
from src.ui.theme import palette as P
from src.ui.theme.fonts import label_caps, font_inter, font_mono, font_sora
from src.ui.theme.stylesheet import build_stylesheet
from src.ui.widgets.tech_label import TechLabel
from src.ui.widgets.smart_inputs import NoScrollSpinBox, NoScrollSlider, ColorPickerButton, NoScrollComboBox  # noqa: F401 (NoScrollComboBox re-used below)
from src.ui.widgets.glass_card import GlassCard
from src.ui.widgets.keybind_dialog import KeybindDetectDialog
from src.services.updater_service import UpdaterService, _parse_version_parts
from src.app.constants import APP_NAME, APP_VERSION

_STATUS_SUCCESS = "#00FF88"
_STATUS_WARNING = "#FFAA00"


class SettingsTab(QWidget):

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.sm = SettingsManager.instance()
        self.paths = PathManager.instance()
        self._updater = None
        self._staged_update_path = ""
        self._releases: list = []
        self._version_installer_expanded = False
        self._build_ui()
        self._load_values()
        self._init_updater()
        self._connect_signals()
        EventBus.instance().theme_changed.connect(self._refresh_styles)

    # ------------------------------------------------------------------
    # Style helpers
    # ------------------------------------------------------------------

    def _input_style(self) -> str:
        return f"""
            background: {P.rgba(P.SPACE_VOID, 0.85)};
            color: {P.ON_SURFACE};
            border: 1px solid {P.OUTLINE_VARIANT};
            border-radius: 4px;
            padding: 4px 8px;
            min-height: 24px;
        """

    def _compact_input_style(self) -> str:
        return f"""
            background: {P.rgba(P.SPACE_VOID, 0.85)};
            color: {P.ON_SURFACE};
            border: 1px solid {P.OUTLINE_VARIANT};
            border-radius: 4px;
            padding: 2px 6px;
            min-height: 22px;
            max-height: 26px;
            font-size: 11px;
        """

    def _cb_style(self) -> str:
        return f"""
            QCheckBox {{
                color: {P.ON_SURFACE};
                background: transparent;
                border: none;
                spacing: 8px;
                font-weight: 500;
                font-size: 11px;
            }}
            QCheckBox::indicator {{
                width: 16px; height: 16px;
                border: 2px solid {P.OUTLINE};
                border-radius: 3px;
                background: {P.rgba(P.SPACE_VOID, 0.3)};
            }}
            QCheckBox::indicator:hover {{
                border: 2px solid {P.PRIMARY_CONTAINER};
                background: {P.rgba(P.PRIMARY_CONTAINER, 0.1)};
            }}
            QCheckBox::indicator:checked {{
                border: 2px solid {P.PRIMARY};
                background: {P.PRIMARY};
            }}
        """

    def _btn_style(self, accent: bool = False) -> str:
        # accent uses SECONDARY_CONTAINER (teal-green); normal uses PRIMARY_CONTAINER (blue)
        c = P.SECONDARY_CONTAINER if accent else P.PRIMARY_CONTAINER
        bg_rgba = P.rgba(c, 0.12)
        bg_hover_rgba = P.rgba(c, 0.25)
        bg_pressed_rgba = P.rgba(c, 0.35)
        return f"""
            QPushButton {{
                background: {bg_rgba};
                color: {P.ON_SURFACE};
                border: 1px solid {c};
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 10px;
                font-weight: 600;
                min-height: 24px;
            }}
            QPushButton:hover {{ background: {bg_hover_rgba}; }}
            QPushButton:pressed {{ background: {bg_pressed_rgba}; }}
            QPushButton:disabled {{ color: {P.TEXT_DIM}; border-color: {P.OUTLINE_VARIANT}; background: transparent; }}
        """

    def _row(self, label: str, widget: QWidget, tip: str = "") -> QWidget:
        row = QWidget()
        row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        lo = QHBoxLayout(row)
        lo.setContentsMargins(0, 1, 0, 1)
        lo.setSpacing(6)
        lbl = TechLabel(label)
        lbl.setFixedWidth(135)
        if tip:
            lbl.setToolTip(tip)
            widget.setToolTip(tip)
        lo.addWidget(lbl)
        lo.addWidget(widget, 1)
        return row

    def _cb_row(self, label: str, cb: QCheckBox, tip: str = "") -> QWidget:
        row = QWidget()
        row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        lo = QHBoxLayout(row)
        lo.setContentsMargins(0, 1, 0, 1)
        lo.setSpacing(6)
        cb.setText(label)
        if tip:
            cb.setToolTip(tip)
        lo.addWidget(cb, 1)
        return row

    def _slider_row(self, label: str, slider: NoScrollSlider, val_lbl: QLabel, tip: str = "") -> QWidget:
        row = QWidget()
        row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        lo = QHBoxLayout(row)
        lo.setContentsMargins(0, 1, 0, 1)
        lo.setSpacing(6)
        lbl = TechLabel(label)
        lbl.setFixedWidth(135)
        if tip:
            lbl.setToolTip(tip)
            slider.setToolTip(tip)
            val_lbl.setToolTip(tip)
        lo.addWidget(lbl)
        lo.addWidget(slider, 1)
        lo.addWidget(val_lbl)
        return row

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        main_lo = QVBoxLayout(self)
        main_lo.setContentsMargins(0, 0, 0, 0)
        main_lo.setSpacing(0)

        # Header
        self._hdr = QWidget()
        self._hdr.setFixedHeight(40)
        self._hdr.setStyleSheet(f"background:{P.SURFACE_CONTAINER_LOW};border-bottom:1px solid {P.OUTLINE_VARIANT};")
        hdr_lo = QHBoxLayout(self._hdr)
        hdr_lo.setContentsMargins(14, 4, 14, 4)
        self._hdr_lbl = QLabel("SYSTEM PREFERENCES")
        self._hdr_lbl.setFont(label_caps())
        self._hdr_lbl.setStyleSheet(f"color:{P.PRIMARY};letter-spacing:0.15em;background:transparent;border:none;")
        hdr_lo.addWidget(self._hdr_lbl)
        hdr_lo.addStretch()
        main_lo.addWidget(self._hdr)

        # Scroll area
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setFrameShape(QFrame.Shape.NoFrame)
        sc.setStyleSheet("background:transparent;")

        ct = QWidget()
        lo = QGridLayout(ct)
        lo.setContentsMargins(10, 8, 10, 8)
        lo.setSpacing(6)
        lo.setAlignment(Qt.AlignmentFlag.AlignTop)
        lo.setColumnStretch(0, 1)
        lo.setColumnStretch(1, 1)

        # --- GENERAL -------------------------------------------------
        gc = GlassCard(title="GENERAL")
        gf = QVBoxLayout()
        gf.setContentsMargins(0, 2, 0, 2)
        gf.setSpacing(2)

        cb_top = QHBoxLayout()
        cb_top.setSpacing(16)
        self.minimize_tray_cb = QCheckBox()
        self.minimize_tray_cb.setStyleSheet(self._cb_style())
        cb_top.addWidget(self._cb_row("MINIMIZE TO TRAY", self.minimize_tray_cb,
            "When closing the window, minimize to system tray instead of quitting"))
        self.pin_startup_cb = QCheckBox()
        self.pin_startup_cb.setStyleSheet(self._cb_style())
        cb_top.addWidget(self._cb_row("PIN ON STARTUP", self.pin_startup_cb,
            "Automatically set the window to stay on top when the application starts"))
        gf.addLayout(cb_top)

        cb_bot = QHBoxLayout()
        cb_bot.setSpacing(16)
        self.tray_notif_cb = QCheckBox()
        self.tray_notif_cb.setStyleSheet(self._cb_style())
        cb_bot.addWidget(self._cb_row("TRAY NOTIFICATIONS", self.tray_notif_cb,
            "Display system tray notification bubbles for events"))
        self.auto_hide_toolbar_cb = QCheckBox()
        self.auto_hide_toolbar_cb.setStyleSheet(self._cb_style())
        cb_bot.addWidget(self._cb_row("GAME-AWARE TOOLBAR", self.auto_hide_toolbar_cb,
            "Hide the overlay toolbar automatically when StarCitizen.exe is not running"))
        gf.addLayout(cb_bot)

        gc.content_layout.addLayout(gf)
        lo.addWidget(gc, 0, 0, 1, 2)

        # --- APPEARANCE ----------------------------------------------
        ac = GlassCard(title="APPEARANCE")
        af = QVBoxLayout()
        af.setContentsMargins(0, 2, 0, 2)
        af.setSpacing(2)

        self.font_scaling_slider = NoScrollSlider(Qt.Orientation.Horizontal)
        self.font_scaling_slider.setRange(80, 150)
        self.font_scaling_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.font_scaling_slider.setTickInterval(10)
        self.font_scaling_slider.setStyleSheet("background:transparent;border:none;")
        self.font_scaling_lbl = QLabel("100%")
        self.font_scaling_lbl.setFont(font_inter(10))
        self.font_scaling_lbl.setStyleSheet(f"color:{P.PRIMARY};background:transparent;border:none;min-width:36px;")
        af.addWidget(self._slider_row("FONT SCALE", self.font_scaling_slider, self.font_scaling_lbl,
            "Scale UI font size from 80% to 150%"))

        self.theme_editor_btn = QPushButton("OPEN THEME EDITOR...")
        self.theme_editor_btn.setStyleSheet(self._btn_style(accent=True))
        self.theme_editor_btn.clicked.connect(self._open_theme_editor)
        fr = self._row("THEME COLORS", self.theme_editor_btn,
            "Customize the entire application color palette")
        af.addWidget(fr)

        self.toolbar_slider = NoScrollSlider(Qt.Orientation.Horizontal)
        self.toolbar_slider.setRange(30, 100)
        self.toolbar_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.toolbar_slider.setTickInterval(10)
        self.toolbar_slider.setStyleSheet("background:transparent;border:none;")
        self.toolbar_val_lbl = QLabel("100%")
        self.toolbar_val_lbl.setFont(font_inter(10))
        self.toolbar_val_lbl.setStyleSheet(f"color:{P.PRIMARY};background:transparent;border:none;min-width:36px;")
        af.addWidget(self._slider_row("TOOLBAR OPACITY", self.toolbar_slider, self.toolbar_val_lbl,
            "Adjust overlay toolbar idle transparency (30% very transparent, 100% solid)"))

        # NoScrollComboBox already imported at module level
        self.app_font_combo = NoScrollComboBox()
        self.app_font_combo.addItems(["Default", "Sora", "Inter", "JetBrains Mono"])
        self.app_font_combo.setStyleSheet(self._input_style())
        af.addWidget(self._row("APP FONT", self.app_font_combo, "Change the global font family used throughout the app"))

        ac.content_layout.addLayout(af)
        lo.addWidget(ac, 1, 0)

        # --- HOTKEYS -------------------------------------------------
        hc = GlassCard(title="HOTKEYS")
        hf = QVBoxLayout()
        hf.setContentsMargins(0, 2, 0, 2)
        hf.setSpacing(2)

        # Interact Hotkey
        ihk_wrap = QWidget()
        ihk = QHBoxLayout(ihk_wrap)
        ihk.setContentsMargins(0, 0, 0, 0)
        ihk.setSpacing(6)
        self.interact_hk_lbl = QLabel("None")
        self.interact_hk_lbl.setFont(font_inter(10))
        self.interact_hk_lbl.setStyleSheet(f"color:{P.PRIMARY};background:transparent;border:none;")
        self.interact_hk_btn = QPushButton("DETECT")
        self.interact_hk_btn.setFixedWidth(64)
        self.interact_hk_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.interact_hk_btn.setStyleSheet(self._btn_style())
        ihk.addWidget(self.interact_hk_lbl)
        ihk.addWidget(self.interact_hk_btn)
        ihk.addStretch()
        hf.addWidget(self._row("INTERACT KEY", ihk_wrap, "Global hotkey used to confirm interactions and selections"))

        # Drag Hotkey
        dhk_wrap = QWidget()
        dhk = QHBoxLayout(dhk_wrap)
        dhk.setContentsMargins(0, 0, 0, 0)
        dhk.setSpacing(6)
        self.drag_hk_lbl = QLabel("None")
        self.drag_hk_lbl.setFont(font_inter(10))
        self.drag_hk_lbl.setStyleSheet(f"color:{P.PRIMARY};background:transparent;border:none;")
        self.drag_hk_btn = QPushButton("DETECT")
        self.drag_hk_btn.setFixedWidth(64)
        self.drag_hk_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.drag_hk_btn.setStyleSheet(self._btn_style())
        dhk.addWidget(self.drag_hk_lbl)
        dhk.addWidget(self.drag_hk_btn)
        dhk.addStretch()
        hf.addWidget(self._row("DRAG KEY", dhk_wrap, "Hold this key to click and drag the overlay toolbar across the screen"))

        # Snipping Tool Hotkey
        hk_wrap = QWidget()
        hk = QHBoxLayout(hk_wrap)
        hk.setContentsMargins(0, 0, 0, 0)
        hk.setSpacing(6)
        self.hotkey_lbl = QLabel("None")
        self.hotkey_lbl.setFont(font_inter(10))
        self.hotkey_lbl.setStyleSheet(f"color:{P.PRIMARY};background:transparent;border:none;")
        self.hotkey_btn = QPushButton("DETECT")
        self.hotkey_btn.setFixedWidth(64)
        self.hotkey_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hotkey_btn.setStyleSheet(self._btn_style())
        hk.addWidget(self.hotkey_lbl)
        hk.addWidget(self.hotkey_btn)
        hk.addStretch()
        hf.addWidget(self._row("SNIPPING KEY", hk_wrap, "Global hotkey to activate the screen capture selection tool"))

        hc.content_layout.addLayout(hf)
        lo.addWidget(hc, 3, 1)

        # --- SYNC & CACHE --------------------------------------------
        scc = GlassCard(title="CACHE")
        scf = QVBoxLayout()
        scf.setContentsMargins(0, 2, 0, 2)
        scf.setSpacing(2)

        self.cache_spin = NoScrollSpinBox()
        self.cache_spin.setRange(1, 365)
        self.cache_spin.setSuffix(" days")
        self.cache_spin.setStyleSheet(self._compact_input_style())
        scf.addWidget(self._row("CACHE MAX AGE", self.cache_spin,
            "Maximum age in days for temporary cached profile data before cleanup"))

        self.cache_auto_cb = QCheckBox()
        self.cache_auto_cb.setStyleSheet(self._cb_style())
        scf.addWidget(self._cb_row("AUTO-CLEAR CACHE", self.cache_auto_cb,
            "Automatically delete temp cache files that have exceeded the maximum age"))

        scc.content_layout.addLayout(scf)
        lo.addWidget(scc, 1, 1)

        # --- UPDATE BEHAVIOR -----------------------------------------
        lo.addWidget(self._build_update_card(), 2, 0)

        # --- DATA PATHS ----------------------------------------------
        lo.addWidget(self._build_paths_card(), 2, 1)

        # --- DIAGNOSTICS & LOGS --------------------------------------
        lo.addWidget(self._build_diagnostics_card(), 3, 0)

        # --- COMMUNITY REPUTATION (full width) -----------------------
        lo.addWidget(self._build_reputation_card(), 4, 0, 1, 2)

        # --- ABOUT (full width) --------------------------------------
        lo.addWidget(self._build_about_card(), 5, 0, 1, 2)

        # --- RESET ALL ------------------------------------------------
        reset_card = GlassCard(title="RESET")
        reset_lo = QVBoxLayout()
        reset_lo.setContentsMargins(0, 2, 0, 2)
        reset_lo.setSpacing(4)
        self._reset_btn = QPushButton("RESET ALL SETTINGS TO DEFAULT")
        self._reset_btn.setStyleSheet(f"""
            QPushButton {{
                background: {P.rgba(P.HAZARD_RED, 0.12)};
                color: {P.HAZARD_RED};
                border: 1px solid {P.HAZARD_RED};
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.05em;
                min-height: 28px;
            }}
            QPushButton:hover {{ background: {P.rgba(P.HAZARD_RED, 0.25)}; }}
            QPushButton:pressed {{ background: {P.rgba(P.HAZARD_RED, 0.35)}; }}
        """)
        self._reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset_btn.clicked.connect(self._on_reset_all)
        reset_lo.addWidget(self._reset_btn)
        self._reset_desc = QLabel("Reverts all preferences, appearance, scraper, and cache settings to factory defaults. This cannot be undone.")
        self._reset_desc.setFont(font_inter(9))
        self._reset_desc.setStyleSheet(f"color:{P.TEXT_DIM};background:transparent;border:none;")
        self._reset_desc.setWordWrap(True)
        reset_lo.addWidget(self._reset_desc)
        reset_card.content_layout.addLayout(reset_lo)
        lo.addWidget(reset_card, 6, 0, 1, 2)

        lo.setRowStretch(lo.rowCount(), 1)
        sc.setWidget(ct)
        main_lo.addWidget(sc)

    def _build_update_card(self) -> GlassCard:
        card = GlassCard(title="UPDATE BEHAVIOR")
        lo = QVBoxLayout()
        lo.setContentsMargins(0, 2, 0, 2)
        lo.setSpacing(4)

        # --- Build Channel Selector ---
        ch_row = QWidget()
        ch_row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        ch_lo = QHBoxLayout(ch_row)
        ch_lo.setContentsMargins(0, 1, 0, 1)
        ch_lo.setSpacing(6)
        ch_lbl = TechLabel("BUILD CHANNEL")
        ch_lbl.setFixedWidth(135)
        ch_lbl.setToolTip("Select which release channel to track for updates")
        ch_lo.addWidget(ch_lbl)

        self.channel_combo = NoScrollComboBox()
        self.channel_combo.addItems(["Live Release", "Beta Release"])
        self.channel_combo.setStyleSheet(self._input_style())
        self.channel_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.channel_combo.setToolTip("Live = stable releases | Beta = pre-release / in-development builds")
        ch_lo.addWidget(self.channel_combo, 1)
        lo.addWidget(ch_row)

        # --- Version Info ---
        self.version_info_lbl = QLabel(f"Current: v{APP_VERSION}")
        self.version_info_lbl.setFont(font_inter(10))
        self.version_info_lbl.setStyleSheet(f"color:{P.TEXT_DIM};background:transparent;border:none;")
        lo.addWidget(self.version_info_lbl)

        # --- Auto-check / Auto-download ---
        cb_row = QHBoxLayout()
        cb_row.setSpacing(16)
        self.auto_check_cb = QCheckBox()
        self.auto_check_cb.setStyleSheet(self._cb_style())
        cb_row.addWidget(self._cb_row("AUTO-CHECK", self.auto_check_cb,
            "Check GitHub for a newer version when the app launches"))
        self.auto_download_cb = QCheckBox()
        self.auto_download_cb.setStyleSheet(self._cb_style())
        cb_row.addWidget(self._cb_row("AUTO-DOWNLOAD", self.auto_download_cb,
            "Download newly detected updates automatically in the background"))
        lo.addLayout(cb_row)

        # --- Status ---
        self.update_status_lbl = QLabel("Ready")
        self.update_status_lbl.setFont(font_inter(10))
        self.update_status_lbl.setStyleSheet(f"color:{P.TEXT_DIM};background:transparent;border:none;")
        lo.addWidget(self._row("STATUS", self.update_status_lbl, "Current update status"))

        # --- Progress Bar ---
        self.update_progress = QProgressBar()
        self.update_progress.setVisible(False)
        self.update_progress.setFixedHeight(12)
        self.update_progress.setStyleSheet(f"""
            QProgressBar {{
                background: {P.rgba(P.SPACE_VOID, 0.85)}; border:1px solid {P.OUTLINE_VARIANT};
                border-radius:3px; text-align:center; font-size:10px; color:{P.ON_SURFACE};
            }}
            QProgressBar::chunk {{ background:{P.PRIMARY}; border-radius:2px; }}
        """)
        lo.addWidget(self.update_progress)

        # --- Action Buttons ---
        btns = QHBoxLayout()
        btns.setSpacing(6)
        self.check_update_btn = QPushButton("CHECK")
        self.check_update_btn.setStyleSheet(self._btn_style())
        self.check_update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.check_update_btn.clicked.connect(self._on_check_updates)
        btns.addWidget(self.check_update_btn)

        self.download_update_btn = QPushButton("DOWNLOAD")
        self.download_update_btn.setVisible(False)
        self.download_update_btn.setStyleSheet(self._btn_style(accent=True))
        self.download_update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_update_btn.clicked.connect(self._on_download_update)
        btns.addWidget(self.download_update_btn)

        self.install_update_btn = QPushButton("INSTALL")
        self.install_update_btn.setEnabled(False)
        self.install_update_btn.setStyleSheet(self._btn_style(accent=True))
        self.install_update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.install_update_btn.clicked.connect(self._on_install_update)
        btns.addWidget(self.install_update_btn)

        btns.addStretch()
        lo.addLayout(btns)

        # --- Install Specific Version (expandable) ---
        self._version_installer_frame = QFrame()
        self._version_installer_frame.setFrameShape(QFrame.Shape.NoFrame)
        self._version_installer_frame.setStyleSheet("background:transparent;border:none;")
        self._version_installer_frame.setVisible(False)
        vi_lo = QVBoxLayout(self._version_installer_frame)
        vi_lo.setContentsMargins(0, 4, 0, 0)
        vi_lo.setSpacing(4)

        # Version list
        self.version_list = QListWidget()
        self.version_list.setFixedHeight(140)
        self.version_list.setStyleSheet(f"""
            QListWidget {{
                background: {P.rgba(P.SPACE_VOID, 0.85)};
                color: {P.ON_SURFACE};
                border: 1px solid {P.OUTLINE_VARIANT};
                border-radius: 4px;
                font-size: 11px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 4px 8px;
                border-bottom: 1px solid {P.rgba(P.OUTLINE_VARIANT, 0.3)};
            }}
            QListWidget::item:selected {{
                background: {P.rgba(P.PRIMARY_CONTAINER, 0.15)};
                color: {P.PRIMARY};
            }}
            QListWidget::item:hover {{
                background: {P.rgba(P.PRIMARY_CONTAINER, 0.08)};
            }}
        """)
        vi_lo.addWidget(self.version_list)

        # Description area
        self.version_desc = QTextBrowser()
        self.version_desc.setFixedHeight(80)
        self.version_desc.setOpenExternalLinks(True)
        self.version_desc.setStyleSheet(f"""
            QTextBrowser {{
                background: {P.rgba(P.SPACE_VOID, 0.85)};
                color: {P.TEXT_DIM};
                border: 1px solid {P.OUTLINE_VARIANT};
                border-radius: 4px;
                font-size: 10px;
                padding: 4px 8px;
            }}
        """)
        vi_lo.addWidget(self.version_desc)

        # Download & Install for specific version
        sv_btns = QHBoxLayout()
        sv_btns.setSpacing(6)
        self.sv_download_btn = QPushButton("DOWNLOAD")
        self.sv_download_btn.setStyleSheet(self._btn_style())
        self.sv_download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sv_download_btn.setEnabled(False)
        self.sv_download_btn.clicked.connect(self._on_download_specific_version)
        sv_btns.addWidget(self.sv_download_btn)

        self.sv_install_btn = QPushButton("INSTALL")
        self.sv_install_btn.setStyleSheet(self._btn_style(accent=True))
        self.sv_install_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sv_install_btn.setEnabled(False)
        self.sv_install_btn.clicked.connect(self._on_install_specific_version)
        sv_btns.addWidget(self.sv_install_btn)

        self.sv_retry_btn = QPushButton("RETRY")
        self.sv_retry_btn.setStyleSheet(self._btn_style())
        self.sv_retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sv_retry_btn.setEnabled(False)
        self.sv_retry_btn.clicked.connect(self._load_releases)
        sv_btns.addWidget(self.sv_retry_btn)

        self.sv_status_lbl = QLabel("")
        self.sv_status_lbl.setFont(font_inter(9))
        self.sv_status_lbl.setStyleSheet(f"color:{P.TEXT_DIM};background:transparent;border:none;")
        sv_btns.addWidget(self.sv_status_lbl, 1)
        vi_lo.addLayout(sv_btns)

        lo.addWidget(self._version_installer_frame)

        # Toggle button for version installer
        self._toggle_vi_btn = QPushButton("▼ INSTALL SPECIFIC VERSION")
        self._toggle_vi_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {P.PRIMARY};
                border: 1px solid {P.OUTLINE_VARIANT};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 10px;
                font-weight: 600;
                text-align: left;
            }}
            QPushButton:hover {{
                background: {P.rgba(P.PRIMARY_CONTAINER, 0.08)};
                border-color: {P.PRIMARY};
            }}
        """)
        self._toggle_vi_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_vi_btn.clicked.connect(self._on_toggle_version_installer)
        lo.addWidget(self._toggle_vi_btn)

        card.content_layout.addLayout(lo)
        return card



    def _build_diagnostics_card(self) -> GlassCard:
        card = GlassCard(title="DIAGNOSTICS & LOGS")
        lo = QVBoxLayout()
        lo.setContentsMargins(0, 2, 0, 2)
        lo.setSpacing(2)

        self.log_level_combo = NoScrollComboBox()
        self.log_level_combo.setStyleSheet(self._input_style())
        self.log_level_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.log_level_combo.addItem("Normal", "normal")
        self.log_level_combo.addItem("Debug (verbose)", "debug")
        lo.addWidget(self._row("LOG LEVEL", self.log_level_combo,
            "Control whether the app writes normal or debug-level detail to logs"))

        self.debug_diag_cb = QCheckBox()
        self.debug_diag_cb.setStyleSheet(self._cb_style())
        lo.addWidget(self._cb_row("DEBUG DETAIL", self.debug_diag_cb,
            "Include additional troubleshooting detail in diagnostics"))

        self.history_limit_spin = NoScrollSpinBox()
        self.history_limit_spin.setRange(0, 15)
        self.history_limit_spin.setSuffix(" items")
        self.history_limit_spin.setStyleSheet(self._compact_input_style())
        lo.addWidget(self._row("SEARCH HISTORY", self.history_limit_spin,
            "Number of recent searches to remember (0 disables history)"))

        btns = QHBoxLayout()
        btns.setSpacing(6)
        open_logs = QPushButton("OPEN LOGS FOLDER")
        open_logs.setStyleSheet(self._btn_style())
        open_logs.setCursor(Qt.CursorShape.PointingHandCursor)
        open_logs.clicked.connect(self._on_open_logs_folder)
        btns.addWidget(open_logs)

        copy_diag = QPushButton("COPY DIAGNOSTICS")
        copy_diag.setStyleSheet(self._btn_style())
        copy_diag.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_diag.clicked.connect(self._on_copy_diagnostics)
        btns.addWidget(copy_diag)
        btns.addStretch()
        lo.addLayout(btns)

        card.content_layout.addLayout(lo)
        return card

    def _build_reputation_card(self) -> GlassCard:
        card = GlassCard(title="COMMUNITY REPUTATION")
        lo = QVBoxLayout()
        lo.setContentsMargins(0, 2, 0, 2)
        lo.setSpacing(2)

        desc = QLabel(
            "Community-sourced reputation scores for players. "
            "Anonymous, privacy-preserving, no account required."
        )
        desc.setFont(font_inter(9))
        desc.setStyleSheet(f"color:{P.TEXT_DIM};background:transparent;border:none;")
        desc.setWordWrap(True)
        lo.addWidget(desc)

        self.rep_enabled_cb = QCheckBox()
        self.rep_enabled_cb.setStyleSheet(self._cb_style())
        lo.addWidget(self._cb_row("ENABLE REPUTATION", self.rep_enabled_cb,
            "Enable to fetch and submit community reputation scores for players"))

        self.rep_auto_check_cb = QCheckBox()
        self.rep_auto_check_cb.setStyleSheet(self._cb_style())
        lo.addWidget(self._cb_row("AUTO-CHECK ON SEARCH", self.rep_auto_check_cb,
            "Automatically fetch reputation data after each player search completes"))

        self.rep_prefetch_cb = QCheckBox()
        self.rep_prefetch_cb.setStyleSheet(self._cb_style())
        lo.addWidget(self._cb_row("PRE-FETCH AT STARTUP", self.rep_prefetch_cb,
            "Fetch reputation scores for all archived players when the app starts"))

        self.rep_status_lbl = QLabel("CHECKING..." if self.sm.reputation_enabled else "DISABLED")
        self.rep_status_lbl.setFont(font_mono(8, QFont.Weight.Bold))
        self.rep_status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rep_status_lbl.setMinimumWidth(80)
        self._update_rep_status_pill("CHECKING..." if self.sm.reputation_enabled else "DISABLED", P.TEXT_DIM)

        conn_wrap = QWidget()
        conn_lo = QVBoxLayout(conn_wrap)
        conn_lo.setContentsMargins(0, 0, 0, 0)
        conn_lo.setSpacing(4)
        conn_lbl = TechLabel("CONNECTION STATUS")
        conn_lo.addWidget(conn_lbl)
        conn_lo.addWidget(self.rep_status_lbl)
        lo.addWidget(conn_wrap)

        priv = QLabel(
            "Privacy: Your public IP is SHA-256 hashed locally before being sent. "
            "Raw IPs are never transmitted or stored."
        )
        priv.setFont(font_inter(8))
        priv.setStyleSheet(f"color:{P.TEXT_DIM};background:transparent;border:none;")
        priv.setWordWrap(True)
        lo.addWidget(priv)

        card.content_layout.addLayout(lo)
        return card

    def _build_paths_card(self) -> GlassCard:
        card = GlassCard(title="DATA PATHS")
        lo = QVBoxLayout()
        lo.setContentsMargins(0, 2, 0, 2)
        lo.setSpacing(4)

        paths = [
            ("CONFIG", str(self.paths.config_dir)),
            ("LOGS", str(self.paths.logs_dir)),
            ("TEMP CACHE", str(self.paths.temp_root)),
            ("ARCHIVED", str(self.paths.archived_root)),
        ]

        for label, path in paths:
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self._btn_style())
            btn.setToolTip(path)
            btn.clicked.connect(
                lambda _checked, p=path: QDesktopServices.openUrl(QUrl.fromLocalFile(p))
            )
            lo.addWidget(btn)

        card.content_layout.addLayout(lo)
        return card

    # ------------------------------------------------------------------
    # About card (redesigned)
    # ------------------------------------------------------------------

    def _fetch_github_contributors(self) -> str:
        """Fetch contributor logins from the GitHub repo. Returns comma-separated names."""
        try:
            import requests as _req
            resp = _req.get(
                "https://api.github.com/repos/PINKgeekPDX/SCDossier/contributors",
                timeout=5,
            )
            if resp.ok:
                data = resp.json()
                names = [c["login"] for c in data if c.get("login")]
                return ", ".join(names) if names else "PINKgeekPDX"
        except Exception:
            pass
        return "PINKgeekPDX"

    def _make_link_label(self, text: str, url: str, font: QFont | None = None) -> QLabel:
        """Create a clickable QLabel that opens *url* in the default browser."""
        lbl = QLabel(f'<a href="{url}" style="color:{P.PRIMARY};text-decoration:none;">{text}</a>')
        lbl.setFont(font or font_inter(10))
        lbl.setStyleSheet("background:transparent;border:none;")
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setOpenExternalLinks(True)
        lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        return lbl

    def _make_about_link_btn(self, label: str, url: str) -> QPushButton:
        """Standard themed link button for the About section."""
        btn = QPushButton(label)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(self._btn_style())
        btn.clicked.connect(lambda _checked, u=url: QDesktopServices.openUrl(QUrl(u)))
        return btn

    def _make_bmc_button(self) -> QPushButton:
        """Buy Me a Coffee button with custom idle/hover/click assets."""
        btn = QPushButton()
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip("Buy PINKgeekPDX a coffee!")
        btn.setStyleSheet(self._btn_style())

        idle_path = get_asset_path("assets/buttons/bmc-idle.png").replace("\\", "/")
        hover_path = get_asset_path("assets/buttons/bmc-onhover.png").replace("\\", "/")
        click_path = get_asset_path("assets/buttons/bmc-onclick.png").replace("\\", "/")

        pm_idle = QPixmap(idle_path)
        pm_hover = QPixmap(hover_path)
        pm_click = QPixmap(click_path)

        target_h = 24
        idle_sz = pm_idle.size()
        hover_sz = pm_hover.size()
        click_sz = pm_click.size()
        pm_idle = pm_idle.scaled(
            int(idle_sz.width() * target_h / idle_sz.height()), target_h,
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation,
        )
        pm_hover = pm_hover.scaled(
            int(hover_sz.width() * target_h / hover_sz.height()), target_h,
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation,
        )
        pm_click = pm_click.scaled(
            int(click_sz.width() * target_h / click_sz.height()), target_h,
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation,
        )

        btn.setIcon(QIcon(pm_idle))
        btn.setIconSize(pm_idle.size())
        btn.setFixedSize(pm_idle.size().width() + 16, target_h + 8)

        btn.setStyleSheet(f"""
            QPushButton {{
                border: none;
                background: transparent;
                padding: 2px 8px;
            }}
            QPushButton:hover {{
                background: {P.rgba(P.ON_SURFACE, 0.05)};
                border-radius: 4px;
            }}
            QPushButton:pressed {{
                background: {P.rgba(P.ON_SURFACE, 0.10)};
                border-radius: 4px;
            }}
        """)

        btn._bmc_idle = QIcon(pm_idle)
        btn._bmc_hover = QIcon(pm_hover)
        btn._bmc_click = QIcon(pm_click)

        original_enter = btn.enterEvent
        original_leave = btn.leaveEvent
        original_press = btn.mousePressEvent
        original_release = btn.mouseReleaseEvent

        def _enter(e):
            btn.setIcon(btn._bmc_hover)
            original_enter(e)
        def _leave(e):
            btn.setIcon(btn._bmc_idle)
            original_leave(e)
        def _press(e):
            btn.setIcon(btn._bmc_click)
            original_press(e)
        def _release(e):
            btn.setIcon(btn._bmc_hover)
            original_release(e)

        btn.enterEvent = _enter
        btn.leaveEvent = _leave
        btn.mousePressEvent = _press
        btn.mouseReleaseEvent = _release

        btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://www.buymeacoffee.com/pinkgeekpdx"))
        )
        return btn

    def _build_about_card(self) -> GlassCard:
        card = GlassCard(title="ABOUT")
        lo = QVBoxLayout()
        lo.setContentsMargins(0, 2, 0, 2)
        lo.setSpacing(4)

        # -- Application version --
        lo.addWidget(self._about_row("APPLICATION", f"{APP_NAME} v{APP_VERSION}"))

        # -- Developer (clickable link) --
        dev_row = QWidget()
        dev_lo = QHBoxLayout(dev_row)
        dev_lo.setContentsMargins(0, 0, 0, 0)
        dev_lo.setSpacing(6)
        dev_lbl = TechLabel("DEVELOPER")
        dev_lbl.setFixedWidth(135)
        dev_link = self._make_link_label(
            "PINKgeekPDX", "https://github.com/PINKgeekPDX",
            font_sora(11, QFont.Weight.Bold),
        )
        dev_lo.addWidget(dev_lbl)
        dev_lo.addWidget(dev_link)
        dev_lo.addStretch()
        lo.addWidget(dev_row)

        # -- Contributors (from GitHub API) --
        contrib_row = QWidget()
        contrib_lo = QHBoxLayout(contrib_row)
        contrib_lo.setContentsMargins(0, 0, 0, 0)
        contrib_lo.setSpacing(6)
        contrib_lbl = TechLabel("CONTRIBUTORS")
        contrib_lbl.setFixedWidth(135)
        contrib_names = self._fetch_github_contributors()
        contrib_val = QLabel(contrib_names)
        contrib_val.setFont(font_inter(10))
        contrib_val.setStyleSheet(f"color:{P.ON_SURFACE};background:transparent;border:none;")
        contrib_lo.addWidget(contrib_lbl)
        contrib_lo.addWidget(contrib_val)
        contrib_lo.addStretch()
        lo.addWidget(contrib_row)

        # -- Framework & Dependencies --
        dep_row = QWidget()
        dep_lo = QHBoxLayout(dep_row)
        dep_lo.setContentsMargins(0, 0, 0, 0)
        dep_lo.setSpacing(6)
        dep_lbl = TechLabel("DEPENDENCIES")
        dep_lbl.setFixedWidth(135)
        dep_wrap = QWidget()
        dep_flow = QHBoxLayout(dep_wrap)
        dep_flow.setContentsMargins(0, 0, 0, 0)
        dep_flow.setSpacing(8)
        dependencies = [
            ("PyQt6", "https://www.riverbankcomputing.com/software/pyqt/"),
            ("requests", "https://requests.readthedocs.io/"),
            ("BeautifulSoup4", "https://www.crummy.com/software/BeautifulSoup/"),
            ("lxml", "https://lxml.de/"),
            ("Pillow", "https://python-pillow.org/"),
            ("RapidOCR", "https://github.com/RapidAI/RapidOCR"),
            ("Supabase", "https://supabase.com/"),
            ("Keyboard", "https://github.com/boppreh/keyboard"),
        ]
        for i, (name, url) in enumerate(dependencies):
            dep_flow.addWidget(self._make_link_label(name, url, font_inter(9)))
            if i < len(dependencies) - 1:
                sep = QLabel("\u00b7")
                sep.setFont(font_inter(9))
                sep.setStyleSheet(f"color:{P.TEXT_DIM};background:transparent;border:none;")
                dep_flow.addWidget(sep)
        dep_flow.addStretch()
        dep_lo.addWidget(dep_lbl)
        dep_lo.addWidget(dep_wrap, 1)
        lo.addWidget(dep_row)

        # -- Separator --
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet(f"color:{P.OUTLINE_VARIANT};background:transparent;")
        sep1.setFixedHeight(1)
        lo.addWidget(sep1)

        # -- License --
        lic_row = QWidget()
        lic_lo = QHBoxLayout(lic_row)
        lic_lo.setContentsMargins(0, 0, 0, 0)
        lic_lo.setSpacing(6)
        lic_lbl = TechLabel("LICENSE")
        lic_lbl.setFixedWidth(135)
        lic_val = QLabel("MIT License \u2014 Open Source. See LICENSE file for full terms.")
        lic_val.setFont(font_inter(10))
        lic_val.setStyleSheet(f"color:{P.ON_SURFACE};background:transparent;border:none;")
        lic_lo.addWidget(lic_lbl)
        lic_lo.addWidget(lic_val, 1)
        lo.addWidget(lic_row)

        disc = QLabel(
            "DISCLAIMER: This is an unofficial tool and is not affiliated with the "
            "Cloud Imperium group of companies."
        )
        disc.setFont(font_inter(9))
        disc.setStyleSheet(f"color:{P.TEXT_DIM};background:transparent;border:none;")
        disc.setWordWrap(True)
        lo.addWidget(disc)

        # -- Separator --
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color:{P.OUTLINE_VARIANT};background:transparent;")
        sep2.setFixedHeight(1)
        lo.addWidget(sep2)

        # -- Link Buttons Row --
        btn_row = QWidget()
        btn_lo = QHBoxLayout(btn_row)
        btn_lo.setContentsMargins(0, 0, 0, 0)
        btn_lo.setSpacing(6)
        btn_lo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_lo.addWidget(self._make_about_link_btn("GITHUB", "https://github.com/PINKgeekPDX/SCDossier"))
        btn_lo.addWidget(self._make_about_link_btn("RELEASES", "https://github.com/PINKgeekPDX/SCDossier/releases"))
        btn_lo.addWidget(self._make_about_link_btn("ISSUES", "https://github.com/PINKgeekPDX/SCDossier/issues"))
        btn_lo.addWidget(self._make_about_link_btn("WIKI", "https://github.com/PINKgeekPDX/SCDossier/wiki"))
        btn_lo.addWidget(self._make_about_link_btn("FORK", "https://github.com/PINKgeekPDX/SCDossier/fork"))

        discord_btn = self._make_about_link_btn("DISCORD", "https://discord.gg/placeholder")
        discord_btn.clicked.disconnect()
        discord_btn.clicked.connect(
            lambda: EventBus.instance().status_push.emit(
                "Official project discord coming soon!", "", "#93CCFF", 30000
            )
        )
        btn_lo.addWidget(discord_btn)

        btn_lo.addWidget(self._make_about_link_btn("WEBSITE", "http://www.scdossier.com"))

        btn_lo.addWidget(self._make_bmc_button())

        lo.addWidget(btn_row)

        card.content_layout.addLayout(lo)
        return card

    def _about_row(self, label: str, value: str) -> QWidget:
        row = QWidget()
        row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        lo = QHBoxLayout(row)
        lo.setContentsMargins(0, 1, 0, 1)
        lo.setSpacing(6)
        lbl = TechLabel(label)
        lbl.setFixedWidth(135)
        val = QLabel(value)
        val.setFont(font_inter(11))
        val.setStyleSheet(f"color:{P.ON_SURFACE};background:transparent;border:none;")
        lo.addWidget(lbl)
        lo.addWidget(val)
        return row

    # ------------------------------------------------------------------
    # Reset to factory defaults
    # ------------------------------------------------------------------

    @pyqtSlot()
    def _on_reset_all(self) -> None:
        from PyQt6.QtWidgets import QDialog
        from src.ui.widgets.confirm_dialog import ConfirmDialog
        dlg = ConfirmDialog(
            title="RESET ALL SETTINGS",
            message="This will revert ALL preferences, appearance, scraper, and cache settings to factory defaults.\n\nThis cannot be undone.",
            confirm_text="RESET ALL",
            cancel_text="CANCEL",
            danger=True,
            parent=self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        # Use the public reset API — no direct _data access
        self.sm.reset_to_defaults()

        from src.ui.theme import palette as P
        P.apply_overrides({})

        self._load_values()
        EventBus.instance().settings_changed.emit("font_size_scaling", self.sm.font_size_scaling)
        EventBus.instance().settings_changed.emit("theme_palette_overrides", {})
        EventBus.instance().settings_changed.emit("reputation_enabled", self.sm.reputation_enabled)

        from PyQt6.QtWidgets import QDialog
        from src.ui.widgets.confirm_dialog import ConfirmDialog
        dlg = ConfirmDialog(
            title="SETTINGS RESET",
            message="All settings have been restored to factory defaults.",
            confirm_text="OK",
            cancel_text="",
            danger=False,
            parent=self,
        )
        dlg.exec()

    # ------------------------------------------------------------------
    # Load values
    # ------------------------------------------------------------------

    def _load_values(self) -> None:

        hotkey = self.sm.ocr_hotkey
        self.hotkey_lbl.setText(hotkey.upper() if hotkey else "None")

        self.font_scaling_slider.setValue(self.sm.font_size_scaling)
        self.font_scaling_lbl.setText(f"{self.sm.font_size_scaling}%")

        font_fam = self.sm.app_font_family
        idx = self.app_font_combo.findText(font_fam)
        if idx >= 0:
            self.app_font_combo.setCurrentIndex(idx)

        self.cache_spin.setValue(self.sm.temp_cache_max_age_days)
        self.cache_auto_cb.setChecked(self.sm.temp_cache_auto_clear)
        self.cache_spin.setEnabled(self.sm.temp_cache_auto_clear)

        opacity = int(self.sm.toolbar_idle_opacity * 100)
        self.toolbar_slider.setValue(opacity)
        self.toolbar_val_lbl.setText(f"{opacity}%")

        ihk_val = self.sm.toolbar_interact_hotkey
        self.interact_hk_lbl.setText(ihk_val.upper() if ihk_val else "None")

        dhk_val = self.sm.toolbar_drag_hotkey
        self.drag_hk_lbl.setText(dhk_val.upper() if dhk_val else "None")

        self.minimize_tray_cb.setChecked(self.sm.minimize_to_tray_on_close)
        self.pin_startup_cb.setChecked(self.sm.pin_on_startup)
        self.tray_notif_cb.setChecked(self.sm.show_tray_notifications)
        self.auto_hide_toolbar_cb.setChecked(self.sm.auto_hide_toolbar_without_game)

        self.auto_check_cb.setChecked(self.sm.auto_check_updates)
        self.auto_download_cb.setChecked(self.sm.auto_download_updates)

        ch_idx = self.channel_combo.findText(
            "Beta Release" if self.sm.updater_channel == "beta" else "Live Release"
        )
        if ch_idx >= 0:
            self.channel_combo.setCurrentIndex(ch_idx)


        idx = self.log_level_combo.findData(self.sm.log_level)
        if idx >= 0:
            self.log_level_combo.setCurrentIndex(idx)
        self.debug_diag_cb.setChecked(self.sm.include_debug_in_diagnostics)
        self.history_limit_spin.setValue(self.sm.search_history_limit)

        self.rep_enabled_cb.setChecked(self.sm.reputation_enabled)
        self.rep_auto_check_cb.setChecked(self.sm.reputation_auto_check)
        self.rep_prefetch_cb.setChecked(self.sm.reputation_prefetch_archived)
        
        self.rep_auto_check_cb.setEnabled(self.sm.reputation_enabled)
        self.rep_prefetch_cb.setEnabled(self.sm.reputation_enabled)

    # ------------------------------------------------------------------
    # Connect signals
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        # General
        self.minimize_tray_cb.toggled.connect(lambda v: setattr(self.sm, 'minimize_to_tray_on_close', v))
        self.pin_startup_cb.toggled.connect(lambda v: setattr(self.sm, 'pin_on_startup', v))
        self.tray_notif_cb.toggled.connect(lambda v: setattr(self.sm, 'show_tray_notifications', v))
        self.auto_hide_toolbar_cb.toggled.connect(lambda v: setattr(self.sm, 'auto_hide_toolbar_without_game', v))

        # Appearance
        self.font_scaling_slider.valueChanged.connect(self._on_font_scaling_changed)
        self.app_font_combo.currentTextChanged.connect(self._on_app_font_changed)
        self.toolbar_slider.valueChanged.connect(self._on_toolbar_opacity_changed)
        self.interact_hk_btn.clicked.connect(self._on_detect_interact_hotkey)
        self.drag_hk_btn.clicked.connect(self._on_detect_drag_hotkey)


        # Hotkeys
        self.hotkey_btn.clicked.connect(self._on_detect_hotkey)

        # Cache
        self.cache_spin.valueChanged.connect(lambda v: setattr(self.sm, 'temp_cache_max_age_days', v))
        self.cache_auto_cb.toggled.connect(lambda v: setattr(self.sm, 'temp_cache_auto_clear', v))
        self.cache_auto_cb.toggled.connect(self.cache_spin.setEnabled)

        # Updater
        self.auto_check_cb.toggled.connect(lambda v: setattr(self.sm, 'auto_check_updates', v))
        self.auto_download_cb.toggled.connect(lambda v: setattr(self.sm, 'auto_download_updates', v))
        self.channel_combo.currentTextChanged.connect(self._on_channel_changed)
        self.version_list.currentRowChanged.connect(self._on_version_selected)

        # Diagnostics
        self.log_level_combo.currentIndexChanged.connect(
            lambda: setattr(self.sm, 'log_level', self.log_level_combo.currentData()))
        self.debug_diag_cb.toggled.connect(lambda v: setattr(self.sm, 'include_debug_in_diagnostics', v))
        self.history_limit_spin.valueChanged.connect(lambda v: setattr(self.sm, 'search_history_limit', v))

        # Reputation
        self.rep_enabled_cb.toggled.connect(self._on_rep_enabled_toggled)
        self.rep_auto_check_cb.toggled.connect(lambda v: setattr(self.sm, 'reputation_auto_check', v))
        self.rep_prefetch_cb.toggled.connect(lambda v: setattr(self.sm, 'reputation_prefetch_archived', v))

        EventBus.instance().reputation_system_status.connect(self._on_reputation_status)

    def _refresh_styles(self) -> None:
        """Re-apply inline styles that depend on palette colors after a theme change."""
        # Header
        self._hdr.setStyleSheet(f"background:{P.SURFACE_CONTAINER_LOW};border-bottom:1px solid {P.OUTLINE_VARIANT};")
        self._hdr_lbl.setStyleSheet(f"color:{P.PRIMARY};letter-spacing:0.15em;background:transparent;border:none;")
        # Reset button
        self._reset_btn.setStyleSheet(f"""
            QPushButton {{
                background: {P.rgba(P.HAZARD_RED, 0.12)};
                color: {P.HAZARD_RED};
                border: 1px solid {P.HAZARD_RED};
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.05em;
                min-height: 28px;
            }}
            QPushButton:hover {{ background: {P.rgba(P.HAZARD_RED, 0.25)}; }}
            QPushButton:pressed {{ background: {P.rgba(P.HAZARD_RED, 0.35)}; }}
        """)
        # Reset description
        self._reset_desc.setStyleSheet(f"color:{P.TEXT_DIM};background:transparent;border:none;")
        # Progress bar
        self.update_progress.setStyleSheet(f"""
            QProgressBar {{
                background: {P.rgba(P.SPACE_VOID, 0.85)}; border:1px solid {P.OUTLINE_VARIANT};
                border-radius:3px; text-align:center; font-size:10px; color:{P.ON_SURFACE};
            }}
            QProgressBar::chunk {{ background:{P.PRIMARY}; border-radius:2px; }}
        """)
        # Version installer toggle
        self._toggle_vi_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {P.PRIMARY};
                border: 1px solid {P.OUTLINE_VARIANT};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 10px;
                font-weight: 600;
                text-align: left;
            }}
            QPushButton:hover {{
                background: {P.rgba(P.PRIMARY_CONTAINER, 0.08)};
                border-color: {P.PRIMARY};
            }}
        """)
        # Version list
        self.version_list.setStyleSheet(f"""
            QListWidget {{
                background: {P.rgba(P.SPACE_VOID, 0.85)};
                color: {P.ON_SURFACE};
                border: 1px solid {P.OUTLINE_VARIANT};
                border-radius: 4px;
                font-size: 11px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 4px 8px;
                border-bottom: 1px solid {P.rgba(P.OUTLINE_VARIANT, 0.3)};
            }}
            QListWidget::item:selected {{
                background: {P.rgba(P.PRIMARY_CONTAINER, 0.15)};
                color: {P.PRIMARY};
            }}
            QListWidget::item:hover {{
                background: {P.rgba(P.PRIMARY_CONTAINER, 0.08)};
            }}
        """)
        # Version description
        self.version_desc.setStyleSheet(f"""
            QTextBrowser {{
                background: {P.rgba(P.SPACE_VOID, 0.85)};
                color: {P.TEXT_DIM};
                border: 1px solid {P.OUTLINE_VARIANT};
                border-radius: 4px;
                font-size: 10px;
                padding: 4px 8px;
            }}
        """)
        # About section link
        self._about_github_lbl.setStyleSheet("background:transparent;border:none;")

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------



    def _on_toolbar_opacity_changed(self, value: int) -> None:
        self.toolbar_val_lbl.setText(f"{value}%")
        self.sm.toolbar_idle_opacity = value / 100.0

    def _on_font_scaling_changed(self, value: int) -> None:
        self.font_scaling_lbl.setText(f"{value}%")
        self.sm.font_size_scaling = value
        self._rebuild_stylesheet()

    def _on_app_font_changed(self, value: str) -> None:
        self.sm.app_font_family = value
        from src.core.events import EventBus
        EventBus.instance().settings_changed.emit("app_font_family", value)
        
        from PyQt6.QtWidgets import QApplication, QDialog
        import sys, subprocess
        from src.ui.widgets.confirm_dialog import ConfirmDialog
        
        dlg = ConfirmDialog(
            title="RESTART REQUIRED",
            message="App font saved.\n\nA restart is required to apply the new font to all elements.\n\nWould you like to restart the application now?",
            confirm_text="RESTART NOW",
            cancel_text="LATER",
            danger=False,
            parent=self
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if hasattr(app, '_single_instance_lock'):
                app._single_instance_lock.detach()

            restarter = [
                sys.executable, "-c",
                "import time, subprocess, sys; time.sleep(1.0); subprocess.Popen(sys.argv[1:], creationflags=0x08000000)"
            ]
            import os
            target_cmd = [sys.executable] + sys.argv
            subprocess.Popen(restarter + target_cmd, creationflags=0x08000000)
            # Emit app_exit for cleanup before hard exit
            from src.core.events import EventBus
            try:
                self.sm.force_save()
                EventBus.instance().app_exit.emit()
            except Exception:
                pass
            os._exit(0)

    def _open_theme_editor(self) -> None:
        from src.ui.tabs.theme_editor_dialog import ThemeEditorDialog
        dlg = ThemeEditorDialog(self)
        dlg.exec()

    def _rebuild_stylesheet(self) -> None:
        app = QApplication.instance()
        if app:
            app.setStyleSheet(build_stylesheet(
                font_scale=self.sm.font_size_scaling,
                app_font_family=self.sm.app_font_family
            ))

    def _init_updater(self) -> None:
        self._updater = UpdaterService()
        self._updater.update_status.connect(self._on_update_status)
        self._updater.update_checked.connect(self._on_update_checked)
        self._updater.update_ready_to_install.connect(self._on_update_ready)
        if self.auto_check_cb.isChecked():
            channel = self.sm.updater_channel
            self._updater.check_for_updates(channel=channel, silent=True)

    def _on_check_updates(self) -> None:
        if self._updater:
            channel = self.sm.updater_channel
            self._updater.check_for_updates(channel=channel, silent=False)

    def _on_download_update(self) -> None:
        if self._updater and hasattr(self._updater, '_asset_url') and self._updater._asset_url:
            self._updater.download_update(self._updater._asset_url)
            self.download_update_btn.setVisible(False)
            self.check_update_btn.setEnabled(False)

    def _on_install_update(self) -> None:
        if self._updater and self._staged_update_path:
            self._updater.install_update(self._staged_update_path)
            self.install_update_btn.setEnabled(False)
            self.install_update_btn.setText("INSTALLING...")

    @pyqtSlot(str)
    def _on_update_status(self, status: str) -> None:
        self.update_status_lbl.setText(status)
        if "DOWNLOADING" in status and "%" in status:
            self.update_progress.setVisible(True)
            try:
                pct = int(status.split("%")[0].split()[-1])
                self.update_progress.setValue(pct)
            except (ValueError, IndexError):
                self.update_progress.setValue(0)
        elif "FAILED" in status:
            self.update_progress.setVisible(False)
            self.download_update_btn.setVisible(False)
            self.check_update_btn.setEnabled(True)
        else:
            self.update_progress.setVisible(False)
            self.update_progress.setValue(0)

    @pyqtSlot(bool, str)
    def _on_update_checked(self, available: bool, version_or_msg: str) -> None:
        self.download_update_btn.setVisible(available)

    @pyqtSlot(str)
    def _on_update_ready(self, staged_path: str) -> None:
        self._staged_update_path = staged_path
        self.install_update_btn.setEnabled(True)
        self.check_update_btn.setEnabled(True)
        # Also enable the specific version install button if visible
        if self._version_installer_expanded and self.version_list.currentRow() >= 0:
            self.sv_install_btn.setEnabled(True)
            self.sv_status_lbl.setText("Ready to install")

    # ------------------------------------------------------------------
    # Channel & Version Installer Slots
    # ------------------------------------------------------------------

    def _on_channel_changed(self, text: str) -> None:
        channel = "beta" if "Beta" in text else "live"
        if channel == self.sm.updater_channel:
            return

        if channel == "beta":
            if not self._show_beta_warning_dialog():
                # Revert combo selection
                self.channel_combo.blockSignals(True)
                self.channel_combo.setCurrentText("Live Release")
                self.channel_combo.blockSignals(False)
                return

        self.sm.updater_channel = channel
        self._staged_update_path = ""
        self._releases = []

        if self._version_installer_expanded:
            self._load_releases()

    def _show_beta_warning_dialog(self) -> bool:
        from src.ui.widgets.confirm_dialog import ConfirmDialog
        from PyQt6.QtWidgets import QDialog
        dlg = ConfirmDialog(
            title="SWITCH TO BETA BUILDS",
            message=(
                "You are about to switch to the Beta release channel.\n\n"
                "Beta builds are active in-development versions used for testing "
                "new upcoming features. They may contain bugs, instability, or "
                "incomplete features that are not indicative of the final release.\n\n"
                "Are you sure you want to switch to Beta builds?"
            ),
            confirm_text="YES, I ACKNOWLEDGE",
            cancel_text="NEVERMIND",
            danger=True,
            parent=self,
        )
        return dlg.exec() == QDialog.DialogCode.Accepted

    def _on_toggle_version_installer(self) -> None:
        self._version_installer_expanded = not self._version_installer_expanded
        self._version_installer_frame.setVisible(self._version_installer_expanded)
        if self._version_installer_expanded:
            self._toggle_vi_btn.setText("▲ HIDE SPECIFIC VERSION")
            self._load_releases()
        else:
            self._toggle_vi_btn.setText("▼ INSTALL SPECIFIC VERSION")

    def _load_releases(self) -> None:
        if not self._updater:
            return
        channel = self.sm.updater_channel
        self.sv_status_lbl.setText("Loading releases...")
        self.version_list.clear()
        self.version_desc.clear()
        self.sv_download_btn.setEnabled(False)
        self.sv_install_btn.setEnabled(False)
        # Disconnect old connections to avoid duplicates
        try:
            self._updater.releases_loaded.disconnect(self._on_releases_loaded)
        except (TypeError, RuntimeError):
            pass
        try:
            self._updater.release_list_error.disconnect(self._on_release_list_error)
        except (TypeError, RuntimeError):
            pass
        self._updater.releases_loaded.connect(self._on_releases_loaded)
        self._updater.release_list_error.connect(self._on_release_list_error)
        self._updater.fetch_all_releases(channel=channel)

    @pyqtSlot(list)
    def _on_releases_loaded(self, releases: list) -> None:
        self._releases = releases
        self.version_list.clear()
        self.sv_status_lbl.setText("")
        self.sv_retry_btn.setEnabled(False)

        current_clean = APP_VERSION.lstrip("bv")
        for ri in releases:
            label = ri.tag
            ri_clean = ri.version.lstrip("b")
            if ri_clean == current_clean:
                label += "  (current)"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, ri)
            self.version_list.addItem(item)

        if not releases:
            self.sv_status_lbl.setText("No releases found for this channel.")
            self.sv_retry_btn.setEnabled(True)
        else:
            self.sv_status_lbl.setText(f"{len(releases)} release(s) loaded")

    @pyqtSlot(str)
    def _on_release_list_error(self, error_msg: str) -> None:
        self.sv_status_lbl.setText("Load failed")
        self.sv_retry_btn.setEnabled(True)
        self.version_desc.setPlainText(f"Error: {error_msg}")

    def _on_version_selected(self, row: int) -> None:
        if row < 0 or row >= len(self._releases):
            self.version_desc.clear()
            self.sv_download_btn.setEnabled(False)
            self.sv_install_btn.setEnabled(False)
            return

        ri = self._releases[row]
        self.version_desc.setPlainText(
            f"Version: {ri.version}\n"
            f"Tag: {ri.tag}\n"
            f"Published: {ri.published_at[:10] if ri.published_at else 'N/A'}\n\n"
            f"{ri.body[:500] if ri.body else 'No release notes.'}"
        )

        has_asset = ri.asset_url is not None and ri.asset_url != ""
        self.sv_download_btn.setEnabled(has_asset)
        self.sv_install_btn.setEnabled(False)
        self.sv_status_lbl.setText("")
        self._staged_update_path = ""

    def _on_download_specific_version(self) -> None:
        row = self.version_list.currentRow()
        if row < 0 or row >= len(self._releases):
            return

        ri = self._releases[row]
        if not ri.asset_url:
            return

        # Check if this is a rollback (older version)
        current_clean = APP_VERSION.lstrip("bv")
        selected_clean = ri.version.lstrip("b")
        if not self._version_is_newer_or_equal(selected_clean, current_clean):
            if not self._show_rollback_dialog(ri.version):
                return

        self.sv_download_btn.setEnabled(False)
        self.sv_status_lbl.setText("Downloading...")
        if self._updater:
            self._updater.download_update(ri.asset_url)

    def _version_is_newer_or_equal(self, v1: str, v2: str) -> bool:
        """Return True if v1 >= v2."""
        parts1 = _parse_version_parts(v1)
        parts2 = _parse_version_parts(v2)
        for a, b in zip(parts1, parts2):
            if a > b:
                return True
            elif a < b:
                return False
        return len(parts1) >= len(parts2)

    def _show_rollback_dialog(self, target_version: str) -> bool:
        from src.ui.widgets.confirm_dialog import ConfirmDialog
        from PyQt6.QtWidgets import QDialog
        dlg = ConfirmDialog(
            title="INSTALL OLDER VERSION",
            message=(
                f"You are about to install v{target_version}, which is older than "
                f"the current version (v{APP_VERSION}).\n\n"
                "Rolling back to an older version may cause you to lose features "
                "or fixes included in newer releases.\n\n"
                "Are you sure you want to rollback?"
            ),
            confirm_text="YES, ROLLBACK",
            cancel_text="CANCEL",
            danger=True,
            parent=self,
        )
        return dlg.exec() == QDialog.DialogCode.Accepted

    def _on_install_specific_version(self) -> None:
        if self._updater and self._staged_update_path:
            self._updater.install_update(self._staged_update_path)
            self.sv_install_btn.setEnabled(False)
            self.sv_status_lbl.setText("Installing...")

    def _on_detect_hotkey(self) -> None:
        dlg = KeybindDetectDialog(self, current_keybind=self.sm.ocr_hotkey)
        if dlg.exec():
            new_bind = dlg.get_keybind()
            if new_bind:
                self.sm.ocr_hotkey = new_bind
                self.hotkey_lbl.setText(new_bind.upper())

    def _on_detect_interact_hotkey(self) -> None:
        dlg = KeybindDetectDialog(self, current_keybind=self.sm.toolbar_interact_hotkey)
        if dlg.exec():
            new_bind = dlg.get_keybind()
            if new_bind:
                self.sm.toolbar_interact_hotkey = new_bind
                self.interact_hk_lbl.setText(new_bind.upper())

    def _on_detect_drag_hotkey(self) -> None:
        dlg = KeybindDetectDialog(self, current_keybind=self.sm.toolbar_drag_hotkey)
        if dlg.exec():
            new_bind = dlg.get_keybind()
            if new_bind:
                self.sm.toolbar_drag_hotkey = new_bind
                self.drag_hk_lbl.setText(new_bind.upper())


    def _on_open_logs_folder(self) -> None:
        import os, platform
        if platform.system() == "Windows":
            os.startfile(self.paths.logs_dir)
        else:
            import subprocess
            subprocess.Popen(['xdg-open', self.paths.logs_dir])

    def _on_copy_diagnostics(self) -> None:
        import sys, platform
        from PyQt6.QtWidgets import QApplication
        diag = [
            f"SC Dossier version: {APP_VERSION}",
            f"Python version: {sys.version}",
            f"OS: {platform.system()} {platform.release()}",
            f"Update channel: {self.sm.updater_channel}",
            f"Auto-check: {'Enabled' if self.sm.auto_check_updates else 'Disabled'}",
        ]
        if self.debug_diag_cb.isChecked():
            diag.append("--- DEBUG INFO ---")
            diag.append(f"App Root: {self.paths.app_root}")
            diag.append(f"Settings Path: {self.paths.settings_file}")
            diag.append(f"Logs Path: {self.paths.logs_dir}")
        QApplication.clipboard().setText("\n".join(diag))

    def _on_rep_enabled_toggled(self, enabled: bool) -> None:
        self.sm.reputation_enabled = enabled
        self.rep_auto_check_cb.setEnabled(enabled)
        self.rep_prefetch_cb.setEnabled(enabled)
        if not enabled:
            self._update_rep_status_lbl("DISABLED", P.TEXT_DIM)
            EventBus.instance().reputation_system_status.emit("disabled")
        else:
            self._update_rep_status_lbl("CHECKING...", P.TEXT_DIM)
            from src.services.reputation_service import ReputationService
            if not ReputationService.is_initialized():
                from src.app.constants import REP_SUPABASE_URL, REP_ANON_KEY
                url = REP_SUPABASE_URL
                key = REP_ANON_KEY
                if url and key:
                    try:
                        ReputationService.initialize(url, key)
                    except Exception as e:
                        log.error("Failed to initialize ReputationService: %s", e)
                        self._update_rep_status_lbl("ERROR", _STATUS_WARNING)
                        EventBus.instance().reputation_system_status.emit("error")
                        return
                else:
                    self._update_rep_status_lbl("ERROR", P.HAZARD_RED)
                    EventBus.instance().reputation_system_status.emit("error")
                    return
            if ReputationService.is_initialized():
                from src.services.reputation_worker import ReputationStartupWorker
                self._rep_startup = ReputationStartupWorker()
                self._rep_startup.start()
            else:
                self._update_rep_status_lbl("ERROR", P.HAZARD_RED)
                EventBus.instance().reputation_system_status.emit("error")

    def _update_rep_status_lbl(self, text: str, color: str | None = None) -> None:
        self._update_rep_status_pill(text, color or P.TEXT_DIM)

    def _update_rep_status_pill(self, text: str, color: str) -> None:
        self.rep_status_lbl.setText(text)
        c = QColor(color)
        bg = f"rgba({c.red()}, {c.green()}, {c.blue()}, 0.12)"
        border = f"rgba({c.red()}, {c.green()}, {c.blue()}, 0.35)"
        self.rep_status_lbl.setStyleSheet(f"""
            QLabel {{
                color: {color};
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 3px;
                padding: 2px 8px;
            }}
        """)

    @pyqtSlot(str)
    def _on_reputation_status(self, status: str) -> None:
        if status == "online":
            self._update_rep_status_lbl("CONNECTED", _STATUS_SUCCESS)
            self.rep_status_lbl.setToolTip("Successfully connected to the reputation network.")
        elif status == "offline":
            self._update_rep_status_lbl("OFFLINE", P.HAZARD_RED)
            self.rep_status_lbl.setToolTip(
                "Reputation server is offline or unreachable.\n"
                "The Supabase free-tier may be sleeping. Try again in a few minutes."
            )
        elif status == "error":
            self._update_rep_status_lbl("ERROR", _STATUS_WARNING)
            self.rep_status_lbl.setToolTip(
                "Connected to the server but authorization failed.\n"
                "Check that REP_SUPABASE_URL and REP_ANON_KEY are valid.\n"
                "See logs for detailed error information."
            )
        elif status == "disabled":
            self._update_rep_status_lbl("DISABLED", P.TEXT_DIM)
            self.rep_status_lbl.setToolTip("Reputation system is disabled. Enable it in the toggle above.")
