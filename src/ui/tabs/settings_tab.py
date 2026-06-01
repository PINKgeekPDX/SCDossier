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
from src.ui.widgets.smart_inputs import NoScrollSpinBox, NoScrollSlider, ColorPickerButton
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
        lbl.setFixedWidth(110)
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
        lbl.setFixedWidth(110)
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

        self.theme_accent_btn = ColorPickerButton(self.sm.theme_accent_override or "")
        fr = self._row("ACCENT COLOR", self.theme_accent_btn,
            "Override the default blue accent color")
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
            "Adjust overlay toolbar transparency (30% very transparent, 100% solid)"))

        ac.content_layout.addLayout(af)
        lo.addWidget(ac, 1, 0)

        # --- SCRAPER -------------------------------------------------
        sc_card = GlassCard(title="SCRAPER")
        sf = QVBoxLayout()
        sf.setContentsMargins(0, 2, 0, 2)
        sf.setSpacing(2)

        self.delay_spin = NoScrollSpinBox()
        self.delay_spin.setRange(0, 10000)
        self.delay_spin.setSingleStep(100)
        self.delay_spin.setSuffix(" ms")
        self.delay_spin.setStyleSheet(self._compact_input_style())
        sf.addWidget(self._row("REQUEST DELAY", self.delay_spin,
            "Delay between HTTP requests to RSI to avoid rate limiting (0-10,000ms)"))

        self.timeout_spin = NoScrollSpinBox()
        self.timeout_spin.setRange(5, 120)
        self.timeout_spin.setSuffix(" sec")
        self.timeout_spin.setStyleSheet(self._compact_input_style())
        sf.addWidget(self._row("TIMEOUT", self.timeout_spin,
            "Maximum time to wait for a scraper request before timing out (5-120 seconds)"))

        self.proxy_input = QLineEdit()
        self.proxy_input.setFont(font_inter(10))
        self.proxy_input.setStyleSheet(self._compact_input_style())
        self.proxy_input.setPlaceholderText("http://proxy:8080 (blank = direct)")
        sf.addWidget(self._row("PROXY", self.proxy_input,
            "Optional HTTP proxy URL for scraper requests (leave blank for direct connection)"))

        self.ua_input = QLineEdit()
        self.ua_input.setFont(font_inter(10))
        self.ua_input.setStyleSheet(self._compact_input_style())
        sf.addWidget(self._row("USER AGENT", self.ua_input,
            "Custom User-Agent string sent with scraper HTTP requests"))

        sc_card.content_layout.addLayout(sf)
        lo.addWidget(sc_card, 1, 1)

        # --- OCR -----------------------------------------------------
        oc = GlassCard(title="OCR")
        of = QVBoxLayout()
        of.setContentsMargins(0, 2, 0, 2)
        of.setSpacing(2)

        self.ocr_combo = QComboBox()
        self.ocr_combo.setFont(font_inter(10))
        self.ocr_combo.setStyleSheet(self._compact_input_style())
        self.ocr_combo.addItem("RapidOCR", "rapidocr")
        of.addWidget(self._row("ENGINE", self.ocr_combo, "OCR engine used for screen capture text recognition"))

        self.ocr_slider = NoScrollSlider(Qt.Orientation.Horizontal)
        self.ocr_slider.setRange(10, 99)
        self.ocr_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.ocr_slider.setTickInterval(10)
        self.ocr_slider.setStyleSheet("background:transparent;border:none;")
        self.ocr_val_lbl = QLabel("50%")
        self.ocr_val_lbl.setFont(font_inter(10))
        self.ocr_val_lbl.setStyleSheet(f"color:{P.PRIMARY};background:transparent;border:none;min-width:36px;")
        of.addWidget(self._slider_row("CONFIDENCE", self.ocr_slider, self.ocr_val_lbl,
            "Minimum confidence threshold (10-99%) for OCR text detection"))

        self.ocr_thread_spin = NoScrollSpinBox()
        self.ocr_thread_spin.setRange(1, 8)
        self.ocr_thread_spin.setStyleSheet(self._compact_input_style())
        of.addWidget(self._row("THREADS", self.ocr_thread_spin,
            "Number of CPU threads dedicated to OCR processing (1-8)"))

        hk = QHBoxLayout()
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
        hk_w = QWidget()
        hk_w.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        hk_lo = QHBoxLayout(hk_w)
        hk_lo.setContentsMargins(0, 1, 0, 1)
        hk_lo.setSpacing(6)
        hk_lo.addWidget(TechLabel("GLOBAL HOTKEY"))
        hk_lo.addLayout(hk, 1)
        of.addWidget(hk_w)

        oc.content_layout.addLayout(of)
        lo.addWidget(oc, 2, 0)

        # --- SYNC & CACHE --------------------------------------------
        scc = GlassCard(title="SYNC & CACHE")
        scf = QVBoxLayout()
        scf.setContentsMargins(0, 2, 0, 2)
        scf.setSpacing(2)

        self.sync_interval_spin = NoScrollSpinBox()
        self.sync_interval_spin.setRange(1, 168)
        self.sync_interval_spin.setSuffix(" hours")
        self.sync_interval_spin.setStyleSheet(self._compact_input_style())
        scf.addWidget(self._row("SYNC INTERVAL", self.sync_interval_spin,
            "How often archived profiles are auto-re-synced with RSI (1-168 hours)"))

        self.sync_on_load_cb = QCheckBox()
        self.sync_on_load_cb.setStyleSheet(self._cb_style())
        scf.addWidget(self._cb_row("AUTO-SYNC ON LOAD", self.sync_on_load_cb,
            "Automatically re-sync archived profiles when loading them in the archive viewer"))

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

        self.dl_concurrency_spin = NoScrollSpinBox()
        self.dl_concurrency_spin.setRange(1, 10)
        self.dl_concurrency_spin.setStyleSheet(self._compact_input_style())
        scf.addWidget(self._row("DL CONCURRENCY", self.dl_concurrency_spin,
            "Number of simultaneous image downloads (1-10)"))

        scc.content_layout.addLayout(scf)
        lo.addWidget(scc, 2, 1)

        # --- UPDATE BEHAVIOR -----------------------------------------
        lo.addWidget(self._build_update_card(), 3, 0)

        # --- ARCHIVE & EXPORT ----------------------------------------
        lo.addWidget(self._build_archive_card(), 3, 1)

        # --- DIAGNOSTICS & LOGS --------------------------------------
        lo.addWidget(self._build_diagnostics_card(), 4, 0)

        # --- COMMUNITY REPUTATION ------------------------------------
        lo.addWidget(self._build_reputation_card(), 4, 1)

        # --- DATA PATHS ----------------------------------------------
        lo.addWidget(self._build_paths_card(), 5, 0)

        # --- ABOUT ---------------------------------------------------
        lo.addWidget(self._build_about_card(), 5, 1)

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

    def _build_archive_card(self) -> GlassCard:
        card = GlassCard(title="ARCHIVE & EXPORT")
        lo = QVBoxLayout()
        lo.setContentsMargins(0, 2, 0, 2)
        lo.setSpacing(2)

        er = QHBoxLayout()
        er.setSpacing(4)
        self.export_dest_input = QLineEdit()
        self.export_dest_input.setFont(font_inter(10))
        self.export_dest_input.setStyleSheet(self._compact_input_style())
        self.export_dest_input.setPlaceholderText("Default export folder...")
        browse_btn = QPushButton("BROWSE")
        browse_btn.setFixedHeight(24)
        browse_btn.setStyleSheet(self._btn_style())
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.clicked.connect(self._on_browse_export_dest)
        er.addWidget(self.export_dest_input)
        er.addWidget(browse_btn)
        er_w = QWidget()
        er_w.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        er_lo = QHBoxLayout(er_w)
        er_lo.setContentsMargins(0, 1, 0, 1)
        er_lo.setSpacing(6)
        er_lo.addWidget(TechLabel("EXPORT FOLDER"))
        er_lo.addLayout(er, 1)
        lo.addWidget(er_w)

        self.remember_export_cb = QCheckBox()
        self.remember_export_cb.setStyleSheet(self._cb_style())
        lo.addWidget(self._cb_row("REMEMBER FOLDER", self.remember_export_cb,
            "Reuse the last export folder you selected next time you export"))

        self.archive_sort_combo = QComboBox()
        self.archive_sort_combo.setFont(font_inter(10))
        self.archive_sort_combo.setStyleSheet(self._compact_input_style())
        self.archive_sort_combo.addItem("Date (newest first)", "date_desc")
        self.archive_sort_combo.addItem("Date (oldest first)", "date_asc")
        self.archive_sort_combo.addItem("Name (A-Z)", "name_asc")
        self.archive_sort_combo.addItem("Name (Z-A)", "name_desc")
        lo.addWidget(self._row("DEFAULT SORT", self.archive_sort_combo,
            "Default sort order for the archive list"))

        card.content_layout.addLayout(lo)
        return card

    def _build_diagnostics_card(self) -> GlassCard:
        card = GlassCard(title="DIAGNOSTICS & LOGS")
        lo = QVBoxLayout()
        lo.setContentsMargins(0, 2, 0, 2)
        lo.setSpacing(2)

        self.log_level_combo = QComboBox()
        self.log_level_combo.setFont(font_inter(10))
        self.log_level_combo.setStyleSheet(self._compact_input_style())
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

        sr = QWidget()
        sr.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        sr_lo = QHBoxLayout(sr)
        sr_lo.setContentsMargins(0, 1, 0, 1)
        sr_lo.setSpacing(6)
        srk = TechLabel("CONNECTION STATUS")
        srk.setFixedWidth(110)
        self.rep_status_lbl = QLabel("CHECKING..." if self.sm.reputation_enabled else "DISABLED")
        self.rep_status_lbl.setFont(font_inter(10, QFont.Weight.Bold))
        self.rep_status_lbl.setStyleSheet(f"color:{P.TEXT_DIM};background:transparent;border:none;")
        sr_lo.addWidget(srk)
        sr_lo.addWidget(self.rep_status_lbl)
        sr_lo.addStretch()
        lo.addWidget(sr)

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
            row = QHBoxLayout()
            row.setSpacing(6)
            lbl = TechLabel(label)
            lbl.setFixedWidth(80)
            pl = QLabel(path)
            pl.setFont(font_inter(9))
            pl.setStyleSheet(f"color:{P.TEXT_DIM};background:transparent;border:none;")
            pl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            row.addWidget(lbl)
            row.addWidget(pl, 1)
            rw = QWidget()
            rw.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
            rw.setLayout(row)
            lo.addWidget(rw)

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

        gh = QWidget()
        gh.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        gh_lo = QHBoxLayout(gh)
        gh_lo.setContentsMargins(0, 1, 0, 1)
        gh_lo.setSpacing(6)
        ghk = TechLabel("GITHUB")
        ghk.setFixedWidth(100)
        ghv = QLabel('<a href="https://github.com/pinkgeekpdx" style="color:#00AAFF;">github.com/pinkgeekpdx</a>')
        ghv.setFont(font_inter(10))
        ghv.setStyleSheet("background:transparent;border:none;")
        ghv.setTextFormat(Qt.TextFormat.RichText)
        ghv.setOpenExternalLinks(True)
        gh_lo.addWidget(ghk)
        gh_lo.addWidget(ghv)
        lo.addWidget(gh)

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
        lbl.setFixedWidth(100)
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
        self._load_values()
        EventBus.instance().settings_changed.emit("font_size_scaling", self.sm.font_size_scaling)
        EventBus.instance().settings_changed.emit("theme_accent_override", self.sm.theme_accent_override)
        QMessageBox.information(self, "Settings Reset", "All settings have been restored to factory defaults.")

    # ------------------------------------------------------------------
    # Load values
    # ------------------------------------------------------------------

    def _load_values(self) -> None:
        self.delay_spin.setValue(self.sm.scraper_delay_ms)
        self.timeout_spin.setValue(self.sm.scraper_timeout_sec)
        self.proxy_input.setText(self.sm.scraper_proxy)
        self.ua_input.setText(self.sm.user_agent)

        conf = int(self.sm.ocr_confidence_threshold * 100)
        self.ocr_slider.setValue(conf)
        self.ocr_val_lbl.setText(f"{conf}%")
        self.ocr_combo.setCurrentText("RapidOCR")
        self.ocr_thread_spin.setValue(self.sm.ocr_thread_count)

        hotkey = self.sm.ocr_hotkey
        self.hotkey_lbl.setText(hotkey.upper() if hotkey else "None")

        self.font_scaling_slider.setValue(self.sm.font_size_scaling)
        self.font_scaling_lbl.setText(f"{self.sm.font_size_scaling}%")

        self.sync_interval_spin.setValue(self.sm.sync_interval_hours)
        self.sync_on_load_cb.setChecked(self.sm.sync_on_load)

        self.cache_spin.setValue(self.sm.temp_cache_max_age_days)
        self.cache_auto_cb.setChecked(self.sm.temp_cache_auto_clear)
        self.dl_concurrency_spin.setValue(self.sm.image_download_concurrency)

        opacity = int(self.sm.toolbar_opacity * 100)
        self.toolbar_slider.setValue(opacity)
        self.toolbar_val_lbl.setText(f"{opacity}%")

        self.theme_accent_btn.setColor(self.sm.theme_accent_override or "")

        self.minimize_tray_cb.setChecked(self.sm.minimize_to_tray_on_close)
        self.pin_startup_cb.setChecked(self.sm.pin_on_startup)
        self.tray_notif_cb.setChecked(self.sm.show_tray_notifications)
        self.auto_hide_toolbar_cb.setChecked(self.sm.auto_hide_toolbar_without_game)

        self.auto_check_cb.setChecked(self.sm.auto_check_updates)
        self.auto_download_cb.setChecked(self.sm.auto_download_updates)

        self.export_dest_input.setText(self.sm.export_destination)
        self.remember_export_cb.setChecked(self.sm.remember_export_folder)
        idx = self.archive_sort_combo.findData(self.sm.archive_default_sort)
        if idx >= 0:
            self.archive_sort_combo.setCurrentIndex(idx)

        idx = self.log_level_combo.findData(self.sm.log_level)
        if idx >= 0:
            self.log_level_combo.setCurrentIndex(idx)
        self.debug_diag_cb.setChecked(self.sm.include_debug_in_diagnostics)
        self.history_limit_spin.setValue(self.sm.search_history_limit)

        self.rep_enabled_cb.setChecked(self.sm.reputation_enabled)
        self.rep_auto_check_cb.setChecked(self.sm.reputation_auto_check)
        self.rep_prefetch_cb.setChecked(self.sm.reputation_prefetch_archived)

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
        self.theme_accent_btn.colorChanged.connect(self._on_accent_changed)
        self.toolbar_slider.valueChanged.connect(self._on_toolbar_opacity_changed)

        # Scraper
        self.delay_spin.valueChanged.connect(lambda v: setattr(self.sm, 'scraper_delay_ms', v))
        self.timeout_spin.valueChanged.connect(lambda v: setattr(self.sm, 'scraper_timeout_sec', v))
        self.proxy_input.editingFinished.connect(lambda: setattr(self.sm, 'scraper_proxy', self.proxy_input.text()))
        self.ua_input.editingFinished.connect(lambda: setattr(self.sm, 'user_agent', self.ua_input.text()))

        # OCR
        self.ocr_slider.valueChanged.connect(self._on_ocr_changed)
        self.ocr_combo.currentIndexChanged.connect(
            lambda: setattr(self.sm, 'ocr_engine', self.ocr_combo.currentData()))
        self.ocr_thread_spin.valueChanged.connect(lambda v: setattr(self.sm, 'ocr_thread_count', v))
        self.hotkey_btn.clicked.connect(self._on_detect_hotkey)

        # Sync & Cache
        self.sync_interval_spin.valueChanged.connect(lambda v: setattr(self.sm, 'sync_interval_hours', v))
        self.sync_on_load_cb.toggled.connect(lambda v: setattr(self.sm, 'sync_on_load', v))
        self.cache_spin.valueChanged.connect(lambda v: setattr(self.sm, 'temp_cache_max_age_days', v))
        self.cache_auto_cb.toggled.connect(lambda v: setattr(self.sm, 'temp_cache_auto_clear', v))
        self.dl_concurrency_spin.valueChanged.connect(lambda v: setattr(self.sm, 'image_download_concurrency', v))

        # Updater
        self.auto_check_cb.toggled.connect(lambda v: setattr(self.sm, 'auto_check_updates', v))
        self.auto_download_cb.toggled.connect(lambda v: setattr(self.sm, 'auto_download_updates', v))

        # Archive & Export
        self.export_dest_input.editingFinished.connect(
            lambda: setattr(self.sm, 'export_destination', self.export_dest_input.text()))
        self.remember_export_cb.toggled.connect(lambda v: setattr(self.sm, 'remember_export_folder', v))
        self.archive_sort_combo.currentIndexChanged.connect(
            lambda: setattr(self.sm, 'archive_default_sort', self.archive_sort_combo.currentData()))

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

    def _on_ocr_changed(self, value: int) -> None:
        self.ocr_val_lbl.setText(f"{value}%")
        self.sm.ocr_confidence_threshold = value / 100.0

    def _on_toolbar_opacity_changed(self, value: int) -> None:
        self.toolbar_val_lbl.setText(f"{value}%")
        self.sm.toolbar_opacity = value / 100.0

    def _on_font_scaling_changed(self, value: int) -> None:
        self.font_scaling_lbl.setText(f"{value}%")
        self.sm.font_size_scaling = value
        self._rebuild_stylesheet()

    def _on_accent_changed(self, hex_color: str) -> None:
        self.sm.theme_accent_override = hex_color
        self._rebuild_stylesheet()

    def _rebuild_stylesheet(self) -> None:
        app = QApplication.instance()
        if app:
            app.setStyleSheet(build_stylesheet(
                accent_override=self.sm.theme_accent_override,
                font_scale=self.sm.font_size_scaling
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

    def _on_browse_export_dest(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Select Default Export Folder",
            self.export_dest_input.text() or self.paths.export_root)
        if path:
            self.export_dest_input.setText(path)
            self.sm.export_destination = path

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
