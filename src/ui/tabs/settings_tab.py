import json

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSpinBox,
    QCheckBox, QPushButton, QComboBox, QLineEdit, QScrollArea, QFrame,
    QGridLayout, QProgressBar, QFileDialog, QApplication, QMessageBox
)

from src.core.settings import SettingsManager
from src.core.paths import PathManager
from src.core.events import EventBus
from src.ui.theme import palette as P
from src.ui.theme.fonts import label_caps, font_inter
from src.ui.theme.stylesheet import build_stylesheet
from src.ui.widgets.tech_label import TechLabel
from src.ui.widgets.smart_inputs import NoScrollSpinBox, NoScrollSlider, ColorPickerButton, NoScrollComboBox
from src.ui.widgets.glass_card import GlassCard
from src.ui.widgets.keybind_dialog import KeybindDetectDialog
from src.services.updater_service import UpdaterService
from src.app.constants import APP_NAME, APP_VERSION


class SettingsTab(QWidget):

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.sm = SettingsManager.instance()
        self.paths = PathManager.instance()
        self._updater = None
        self._staged_update_path = ""
        self._build_ui()
        self._load_values()
        self._init_updater()
        self._connect_signals()

    # ------------------------------------------------------------------
    # Style helpers
    # ------------------------------------------------------------------

    def _input_style(self) -> str:
        return f"""
            background: rgba(5, 11, 15, 0.85);
            color: {P.ON_SURFACE};
            border: 1px solid {P.OUTLINE_VARIANT};
            border-radius: 4px;
            padding: 4px 8px;
            min-height: 24px;
        """

    def _compact_input_style(self) -> str:
        return f"""
            background: rgba(5, 11, 15, 0.85);
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
                background: rgba(0,0,0,0.3);
            }}
            QCheckBox::indicator:hover {{
                border: 2px solid {P.PRIMARY_CONTAINER};
                background: rgba(0,170,255,0.1);
            }}
            QCheckBox::indicator:checked {{
                border: 2px solid {P.PRIMARY};
                background: {P.PRIMARY};
            }}
        """

    def _btn_style(self, accent: bool = False) -> str:
        c = "#00FF88" if accent else P.PRIMARY_CONTAINER
        return f"""
            QPushButton {{
                background: rgba({', '.join(str(int(c[i:i+2],16)) for i in (1,3,5))}, 0.12);
                color: {P.ON_SURFACE};
                border: 1px solid {c};
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 10px;
                font-weight: 600;
                min-height: 24px;
            }}
            QPushButton:hover {{ background: rgba({', '.join(str(int(c[i:i+2],16)) for i in (1,3,5))}, 0.25); }}
            QPushButton:pressed {{ background: rgba({', '.join(str(int(c[i:i+2],16)) for i in (1,3,5))}, 0.35); }}
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
        hdr = QWidget()
        hdr.setFixedHeight(40)
        hdr.setStyleSheet(f"background:{P.SURFACE_CONTAINER_LOW};border-bottom:1px solid {P.OUTLINE_VARIANT};")
        hdr_lo = QHBoxLayout(hdr)
        hdr_lo.setContentsMargins(14, 4, 14, 4)
        hl = QLabel("SYSTEM PREFERENCES")
        hl.setFont(label_caps())
        hl.setStyleSheet(f"color:{P.PRIMARY};letter-spacing:0.15em;background:transparent;border:none;")
        hdr_lo.addWidget(hl)
        hdr_lo.addStretch()
        main_lo.addWidget(hdr)

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

        from src.ui.widgets.smart_inputs import NoScrollComboBox
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
        lo.addWidget(hc, 2, 0)

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
        lo.addWidget(self._build_update_card(), 3, 0)

        # --- COMMUNITY REPUTATION ------------------------------------
        lo.addWidget(self._build_reputation_card(), 2, 1)

        # --- DIAGNOSTICS & LOGS --------------------------------------
        lo.addWidget(self._build_diagnostics_card(), 4, 0)

        # --- DATA PATHS ----------------------------------------------
        lo.addWidget(self._build_paths_card(), 3, 1)

        # --- ABOUT ---------------------------------------------------
        lo.addWidget(self._build_about_card(), 4, 1)

        # --- RESET ALL ------------------------------------------------
        reset_card = GlassCard(title="RESET")
        reset_lo = QVBoxLayout()
        reset_lo.setContentsMargins(0, 2, 0, 2)
        reset_lo.setSpacing(4)
        reset_btn = QPushButton("RESET ALL SETTINGS TO DEFAULT")
        reset_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255, 59, 59, 0.12);
                color: #FF3B3B;
                border: 1px solid #FF3B3B;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.05em;
                min-height: 28px;
            }}
            QPushButton:hover {{ background: rgba(255, 59, 59, 0.25); }}
            QPushButton:pressed {{ background: rgba(255, 59, 59, 0.35); }}
        """)
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.clicked.connect(self._on_reset_all)
        reset_lo.addWidget(reset_btn)
        reset_desc = QLabel("Reverts all preferences, appearance, scraper, and cache settings to factory defaults. This cannot be undone.")
        reset_desc.setFont(font_inter(9))
        reset_desc.setStyleSheet(f"color:{P.TEXT_DIM};background:transparent;border:none;")
        reset_desc.setWordWrap(True)
        reset_lo.addWidget(reset_desc)
        reset_card.content_layout.addLayout(reset_lo)
        lo.addWidget(reset_card, 6, 0, 1, 2)

        lo.setRowStretch(lo.rowCount(), 1)
        sc.setWidget(ct)
        main_lo.addWidget(sc)

    def _build_update_card(self) -> GlassCard:
        card = GlassCard(title="UPDATE BEHAVIOR")
        lo = QVBoxLayout()
        lo.setContentsMargins(0, 2, 0, 2)
        lo.setSpacing(2)

        self.auto_check_cb = QCheckBox()
        self.auto_check_cb.setStyleSheet(self._cb_style())
        lo.addWidget(self._cb_row("AUTO-CHECK", self.auto_check_cb,
            "Check GitHub for a newer version when the app launches"))

        self.auto_download_cb = QCheckBox()
        self.auto_download_cb.setStyleSheet(self._cb_style())
        lo.addWidget(self._cb_row("AUTO-DOWNLOAD", self.auto_download_cb,
            "Download newly detected updates automatically in the background"))

        self.update_status_lbl = QLabel("Ready")
        self.update_status_lbl.setFont(font_inter(10))
        self.update_status_lbl.setStyleSheet(f"color:{P.TEXT_DIM};background:transparent;border:none;")
        lo.addWidget(self._row("STATUS", self.update_status_lbl, "Current update status"))

        self.update_progress = QProgressBar()
        self.update_progress.setVisible(False)
        self.update_progress.setFixedHeight(12)
        self.update_progress.setStyleSheet(f"""
            QProgressBar {{
                background: rgba(5,11,15,0.85); border:1px solid {P.OUTLINE_VARIANT};
                border-radius:3px; text-align:center; font-size:10px; color:{P.ON_SURFACE};
            }}
            QProgressBar::chunk {{ background:{P.PRIMARY}; border-radius:2px; }}
        """)
        lo.addWidget(self.update_progress)

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
        self.rep_status_lbl.setFont(font_inter(10, QFont.Weight.Bold))
        self.rep_status_lbl.setStyleSheet(f"color:{P.TEXT_DIM};background:transparent;border:none;")
        lo.addWidget(self._row("CONNECTION STATUS", self.rep_status_lbl, "Current status of the connection to the reputation network"))

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
        lo.setSpacing(2)

        for label, path in [
            ("Config", str(self.paths.config_dir)),
            ("Logs", str(self.paths.logs_dir)),
            ("Temp Cache", str(self.paths.temp_root)),
            ("Archived", str(self.paths.archived_root)),
        ]:
            pl = QLabel(path)
            pl.setFont(font_inter(9))
            pl.setStyleSheet(f"color:{P.TEXT_DIM};background:transparent;border:none;")
            pl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            lo.addWidget(self._row(label.upper(), pl, f"Storage path for {label.lower()}"))

        card.content_layout.addLayout(lo)
        return card

    def _build_about_card(self) -> GlassCard:
        card = GlassCard(title="ABOUT")
        lo = QVBoxLayout()
        lo.setContentsMargins(0, 2, 0, 2)
        lo.setSpacing(2)

        lo.addWidget(self._about_row("APPLICATION", f"{APP_NAME} v{APP_VERSION}"))
        lo.addWidget(self._about_row("DEVELOPER", "PINKgeekPDX"))
        lo.addWidget(self._about_row("FRAMEWORK", "PyQt6"))
        lo.addWidget(self._about_row("LICENSE", "MIT License"))

        ghv = QLabel('<a href="https://github.com/pinkgeekpdx" style="color:#00AAFF;">github.com/pinkgeekpdx</a>')
        ghv.setFont(font_inter(10))
        ghv.setStyleSheet("background:transparent;border:none;")
        ghv.setTextFormat(Qt.TextFormat.RichText)
        ghv.setOpenExternalLinks(True)
        gh_wrap = QWidget()
        gh_lo = QHBoxLayout(gh_wrap)
        gh_lo.setContentsMargins(0, 0, 0, 0)
        gh_lo.addWidget(ghv)
        gh_lo.addStretch()
        lo.addWidget(self._row("GITHUB", gh_wrap, "View the project on GitHub"))

        bio = QLabel(
            'Developed by <a href="https://github.com/pinkgeekpdx" style="color:#00AAFF;">PINKgeekPDX</a> '
            "- a community fan project for Star Citizen players. Not affiliated with Cloud Imperium Games."
        )
        bio.setFont(font_inter(9))
        bio.setStyleSheet(f"color:{P.TEXT_DIM};background:transparent;border:none;")
        bio.setWordWrap(True)
        bio.setTextFormat(Qt.TextFormat.RichText)
        bio.setOpenExternalLinks(True)
        lo.addWidget(bio)

        lic = QLabel("LICENSE: MIT License - Open Source. See LICENSE file for full terms.")
        lic.setFont(font_inter(8))
        lic.setStyleSheet(f"color:{P.TEXT_DIM};background:transparent;")
        lic.setWordWrap(True)
        lo.addWidget(lic)

        disc = QLabel(
            "DISCLAIMER: This is an unofficial tool and is not affiliated with the "
            "Cloud Imperium group of companies."
        )
        disc.setFont(font_inter(8))
        disc.setStyleSheet(f"color:{P.TEXT_DIM};background:transparent;")
        disc.setWordWrap(True)
        lo.addWidget(disc)

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
        reply = QMessageBox.question(
            self,
            "Reset All Settings",
            "This will revert ALL preferences, appearance, scraper, and cache settings to factory defaults.\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        from src.core.settings import DEFAULT_SETTINGS
        self.sm._data = json.loads(json.dumps(DEFAULT_SETTINGS))
        self.sm.force_save()
        
        from src.ui.theme import palette as P
        P.apply_overrides({})
        
        self._load_values()
        EventBus.instance().settings_changed.emit("font_size_scaling", self.sm.font_size_scaling)
        EventBus.instance().settings_changed.emit("theme_accent_override", self.sm.theme_accent_override)
        EventBus.instance().settings_changed.emit("theme_palette_overrides", {})
        
        QMessageBox.information(self, "Settings Reset", "All settings have been restored to factory defaults.")

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

        pass

        self.minimize_tray_cb.setChecked(self.sm.minimize_to_tray_on_close)
        self.pin_startup_cb.setChecked(self.sm.pin_on_startup)
        self.tray_notif_cb.setChecked(self.sm.show_tray_notifications)
        self.auto_hide_toolbar_cb.setChecked(self.sm.auto_hide_toolbar_without_game)

        self.auto_check_cb.setChecked(self.sm.auto_check_updates)
        self.auto_download_cb.setChecked(self.sm.auto_download_updates)



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
            os._exit(0)

    def _open_theme_editor(self) -> None:
        from src.ui.tabs.theme_editor_dialog import ThemeEditorDialog
        dlg = ThemeEditorDialog(self)
        dlg.exec()

    def _rebuild_stylesheet(self) -> None:
        app = QApplication.instance()
        if app:
            app.setStyleSheet(build_stylesheet(
                accent_override=self.sm.theme_accent_override,
                font_scale=self.sm.font_size_scaling,
                app_font_family=self.sm.app_font_family
            ))

    def _init_updater(self) -> None:
        self._updater = UpdaterService()
        self._updater.update_status.connect(self._on_update_status)
        self._updater.update_checked.connect(self._on_update_checked)
        self._updater.update_ready_to_install.connect(self._on_update_ready)
        if self.auto_check_cb.isChecked():
            self._updater.check_for_updates(silent=True)

    def _on_check_updates(self) -> None:
        if self._updater:
            self._updater.check_for_updates(silent=False)

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
            f"Update channel: {'Auto' if self.sm.auto_check_updates else 'Manual'}",
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
        else:
            self._update_rep_status_lbl("CHECKING...", P.TEXT_DIM)
            from src.services.reputation_service import ReputationService
            if not ReputationService.is_initialized():
                from src.app.constants import REP_SUPABASE_URL, REP_ANON_KEY
                url = self.sm.get("reputation_supabase_url") or REP_SUPABASE_URL
                key = self.sm.get("reputation_anon_key") or REP_ANON_KEY
                if url and key:
                    try:
                        ReputationService.initialize(url, key)
                    except Exception:
                        pass
            if ReputationService.is_initialized():
                from src.services.reputation_worker import ReputationStartupWorker
                self._rep_startup = ReputationStartupWorker()
                self._rep_startup.start()

    def _update_rep_status_lbl(self, text: str, color: str | None = None) -> None:
        self.rep_status_lbl.setText(text)
        if color:
            self.rep_status_lbl.setStyleSheet(f"color:{color};background:transparent;border:none;")

    @pyqtSlot(str)
    def _on_reputation_status(self, status: str) -> None:
        if status == "online":
            self._update_rep_status_lbl("CONNECTED", P.PRIMARY)
        elif status == "offline":
            self._update_rep_status_lbl("OFFLINE", P.HAZARD_RED)
        elif status == "disabled":
            self._update_rep_status_lbl("DISABLED", P.TEXT_DIM)
