"""
src/ui/tabs/settings_tab.py
SettingsTab — comprehensive settings interface with expanded configuration scope.
All changes auto-save via SettingsManager debouncer.
"""

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSpinBox,
    QFormLayout, QCheckBox, QPushButton, QComboBox, QLineEdit, QScrollArea, QFrame,
    QGroupBox, QGridLayout, QProgressBar, QFileDialog
)

from src.core.settings import SettingsManager
from src.core.paths import PathManager
from src.ui.theme import palette as P
from src.ui.theme.fonts import label_caps, font_inter
from src.ui.widgets.tech_label import TechLabel
from src.ui.widgets.glass_card import GlassCard
from src.services.updater_service import UpdaterService
from src.app.constants import APP_NAME, APP_VERSION, APP_AUTHOR


class SettingsTab(QWidget):
    """
    Comprehensive settings interface grouped into GlassCard sections.
    All changes auto-save via SettingsManager debouncer.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.sm = SettingsManager.instance()
        self.paths = PathManager.instance()
        self._updater = None
        self._staged_update_path = ""
        self._build_ui()
        self._load_values()      # MUST come before _init_updater so checkboxes are set
        self._init_updater()     # reads auto_check_cb.isChecked() — needs _load_values first
        self._connect_signals()

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

    def _checkbox_style(self) -> str:
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
                width: 16px;
                height: 16px;
                border: 2px solid {P.OUTLINE};
                border-radius: 3px;
                background: rgba(0, 0, 0, 0.3);
            }}
            QCheckBox::indicator:hover {{
                border: 2px solid {P.PRIMARY_CONTAINER};
                background: rgba(0, 170, 255, 0.1);
            }}
            QCheckBox::indicator:checked {{
                border: 2px solid {P.PRIMARY};
                background: {P.PRIMARY};
            }}
        """

    def _create_compact_row(self, label: str, widget: QWidget, help_text: str = "") -> QWidget:
        """Create a compact settings row with label and widget."""
        row = QWidget()
        row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        lbl = TechLabel(label)
        lbl.setFixedWidth(120)
        lbl.setToolTip(help_text)
        widget.setToolTip(help_text)

        layout.addWidget(lbl)
        layout.addWidget(widget, 1)
        return row

    def _create_compact_checkrow(self, label: str, cb: QCheckBox, help_text: str = "") -> QWidget:
        """Create a compact settings row with checkbox."""
        row = QWidget()
        row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        cb.setText(label)
        cb.setToolTip(help_text)
        layout.addWidget(cb, 1)
        layout.addStretch()
        return row

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header bar
        header_bar = QWidget()
        header_bar.setFixedHeight(48)
        header_bar.setStyleSheet(f"background: {P.SURFACE_CONTAINER_LOW}; border-bottom: 1px solid {P.OUTLINE_VARIANT};")
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(20, 6, 20, 6)

        header_lbl = QLabel("SYSTEM PREFERENCES")
        header_lbl.setFont(label_caps())
        header_lbl.setStyleSheet(f"color: {P.PRIMARY}; letter-spacing: 0.15em; background: transparent; border: none;")
        header_layout.addWidget(header_lbl)
        header_layout.addStretch()
        main_layout.addWidget(header_bar)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # === SECTION: GENERAL ===
        general_card = GlassCard(title="GENERAL")
        general_form = QFormLayout()
        general_form.setSpacing(6)
        general_form.setContentsMargins(0, 4, 0, 4)
        general_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.minimize_tray_cb = QCheckBox("Minimize to tray on close")
        self.minimize_tray_cb.setStyleSheet(self._checkbox_style())
        general_form.addRow(TechLabel("CLOSE ACTION"), self.minimize_tray_cb)
        self.minimize_tray_cb.setToolTip("When closing the window, minimize to system tray instead of quitting")

        self.pin_startup_cb = QCheckBox("Pin window on startup (always on top)")
        self.pin_startup_cb.setStyleSheet(self._checkbox_style())
        general_form.addRow(TechLabel("PIN ON STARTUP"), self.pin_startup_cb)
        self.pin_startup_cb.setToolTip("Automatically set the window to stay on top of other windows when application starts")

        self.tray_notif_cb = QCheckBox("Show tray notifications")
        self.tray_notif_cb.setStyleSheet(self._checkbox_style())
        general_form.addRow(TechLabel("NOTIFICATIONS"), self.tray_notif_cb)
        self.tray_notif_cb.setToolTip("Display system tray notification bubbles for events like profile syncs and updates")

        general_card.content_layout.addLayout(general_form)
        layout.addWidget(general_card)

        # === SECTION: APPEARANCE ===
        appearance_card = GlassCard(title="APPEARANCE")
        appearance_form = QFormLayout()
        appearance_form.setSpacing(6)
        appearance_form.setContentsMargins(0, 4, 0, 4)
        appearance_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Font size scaling
        font_hbox = QHBoxLayout()
        self.font_scaling_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_scaling_slider.setRange(80, 150)
        self.font_scaling_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.font_scaling_slider.setTickInterval(10)
        self.font_scaling_slider.setStyleSheet("background: transparent; border: none;")
        self.font_scaling_lbl = QLabel("100%")
        self.font_scaling_lbl.setFont(font_inter(11))
        self.font_scaling_lbl.setStyleSheet(f"color: {P.PRIMARY}; background: transparent; border: none; min-width: 40px;")
        font_hbox.addWidget(self.font_scaling_slider)
        font_hbox.addWidget(self.font_scaling_lbl)
        appearance_form.addRow(TechLabel("FONT SCALE"), font_hbox)
        self.font_scaling_slider.setToolTip("Scale UI font size from 80% to 150%")
        self.font_scaling_lbl.setToolTip("Current font scaling percentage")

        # Theme accent override
        self.theme_accent_input = QLineEdit()
        self.theme_accent_input.setFont(font_inter(11))
        self.theme_accent_input.setStyleSheet(self._compact_input_style())
        self.theme_accent_input.setPlaceholderText("e.g., #FF6600 or empty for default")
        appearance_form.addRow(TechLabel("ACCENT COLOR"), self.theme_accent_input)
        self.theme_accent_input.setToolTip("Override the default blue accent color with a hex color code (e.g., #FF6600)")

        # Toolbar opacity
        toolbar_hbox = QHBoxLayout()
        self.toolbar_slider = QSlider(Qt.Orientation.Horizontal)
        self.toolbar_slider.setRange(30, 100)
        self.toolbar_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.toolbar_slider.setTickInterval(10)
        self.toolbar_slider.setStyleSheet("background: transparent; border: none;")
        self.toolbar_val_lbl = QLabel("100%")
        self.toolbar_val_lbl.setFont(font_inter(11))
        self.toolbar_val_lbl.setStyleSheet(f"color: {P.PRIMARY}; background: transparent; border: none; min-width: 40px;")
        toolbar_hbox.addWidget(self.toolbar_slider)
        toolbar_hbox.addWidget(self.toolbar_val_lbl)
        appearance_form.addRow(TechLabel("TOOLBAR OPACITY"), toolbar_hbox)
        self.toolbar_slider.setToolTip("Adjust the overlay toolbar transparency (30% = very transparent, 100% = solid)")

        appearance_card.content_layout.addLayout(appearance_form)
        layout.addWidget(appearance_card)

        # === SECTION: SCRAPER ===
        scraper_card = GlassCard(title="SCRAPER")
        scraper_form = QFormLayout()
        scraper_form.setSpacing(6)
        scraper_form.setContentsMargins(0, 4, 0, 4)
        scraper_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 10000)
        self.delay_spin.setSingleStep(100)
        self.delay_spin.setSuffix(" ms")
        self.delay_spin.setStyleSheet(self._compact_input_style())
        self.delay_spin.setToolTip("Delay between HTTP requests to RSI to avoid rate limiting (0-10000ms)")
        scraper_form.addRow(TechLabel("REQUEST DELAY"), self.delay_spin)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 120)
        self.timeout_spin.setSuffix(" sec")
        self.timeout_spin.setStyleSheet(self._compact_input_style())
        self.timeout_spin.setToolTip("Maximum time to wait for a scraper request before timing out (5-120 seconds)")
        scraper_form.addRow(TechLabel("TIMEOUT"), self.timeout_spin)

        self.proxy_input = QLineEdit()
        self.proxy_input.setFont(font_inter(11))
        self.proxy_input.setStyleSheet(self._compact_input_style())
        self.proxy_input.setPlaceholderText("e.g., http://proxy:8080 or blank")
        self.proxy_input.setToolTip("Optional HTTP proxy URL for scraper requests (leave blank for direct connection)")
        scraper_form.addRow(TechLabel("PROXY"), self.proxy_input)

        self.ua_input = QLineEdit()
        self.ua_input.setFont(font_inter(11))
        self.ua_input.setStyleSheet(self._compact_input_style())
        self.ua_input.setToolTip("Custom User-Agent string sent with scraper HTTP requests")
        scraper_form.addRow(TechLabel("USER AGENT"), self.ua_input)

        scraper_card.content_layout.addLayout(scraper_form)
        layout.addWidget(scraper_card)

        # === SECTION: OCR ===
        ocr_card = GlassCard(title="OCR")
        ocr_form = QFormLayout()
        ocr_form.setSpacing(6)
        ocr_form.setContentsMargins(0, 4, 0, 4)
        ocr_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.ocr_combo = QComboBox()
        self.ocr_combo.setFont(font_inter(11))
        self.ocr_combo.setStyleSheet(self._compact_input_style())
        self.ocr_combo.addItem("RapidOCR", "rapidocr")
        self.ocr_combo.setToolTip("OCR engine used for screen capture text recognition")
        ocr_form.addRow(TechLabel("ENGINE"), self.ocr_combo)

        ocr_hbox = QHBoxLayout()
        self.ocr_slider = QSlider(Qt.Orientation.Horizontal)
        self.ocr_slider.setRange(10, 99)
        self.ocr_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.ocr_slider.setTickInterval(10)
        self.ocr_slider.setStyleSheet("background: transparent; border: none;")
        self.ocr_val_lbl = QLabel("50%")
        self.ocr_val_lbl.setFont(font_inter(11))
        self.ocr_val_lbl.setStyleSheet(f"color: {P.PRIMARY}; background: transparent; border: none; min-width: 40px;")
        ocr_hbox.addWidget(self.ocr_slider)
        ocr_hbox.addWidget(self.ocr_val_lbl)
        self.ocr_slider.setToolTip("Minimum confidence threshold (10-99%) for OCR text detection")
        ocr_form.addRow(TechLabel("CONFIDENCE"), ocr_hbox)

        self.ocr_thread_spin = QSpinBox()
        self.ocr_thread_spin.setRange(1, 8)
        self.ocr_thread_spin.setStyleSheet(self._compact_input_style())
        self.ocr_thread_spin.setToolTip("Number of CPU threads dedicated to OCR processing (1-8)")
        ocr_form.addRow(TechLabel("THREADS"), self.ocr_thread_spin)

        ocr_card.content_layout.addLayout(ocr_form)
        layout.addWidget(ocr_card)

        # === SECTION: SYNC & CACHE ===
        sync_cache_card = GlassCard(title="SYNC & CACHE")
        sc_form = QFormLayout()
        sc_form.setSpacing(6)
        sc_form.setContentsMargins(0, 4, 0, 4)
        sc_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.sync_interval_spin = QSpinBox()
        self.sync_interval_spin.setRange(1, 168)
        self.sync_interval_spin.setSuffix(" hours")
        self.sync_interval_spin.setStyleSheet(self._compact_input_style())
        self.sync_interval_spin.setToolTip("How often archived profiles are automatically re-synced with RSI (1-168 hours)")
        sc_form.addRow(TechLabel("SYNC INTERVAL"), self.sync_interval_spin)

        self.sync_on_load_cb = QCheckBox("Auto-sync on archive load")
        self.sync_on_load_cb.setStyleSheet(self._checkbox_style())
        self.sync_on_load_cb.setToolTip("Automatically re-sync archived profiles when loading them in the archive viewer")
        sc_form.addRow(TechLabel("ON LOAD"), self.sync_on_load_cb)

        self.cache_spin = QSpinBox()
        self.cache_spin.setRange(1, 365)
        self.cache_spin.setSuffix(" days")
        self.cache_spin.setStyleSheet(self._compact_input_style())
        self.cache_spin.setToolTip("Maximum age in days for temporary cached profile data before automatic cleanup")
        sc_form.addRow(TechLabel("CACHE MAX AGE"), self.cache_spin)

        self.cache_auto_cb = QCheckBox("Auto-clear expired temp cache")
        self.cache_auto_cb.setStyleSheet(self._checkbox_style())
        self.cache_auto_cb.setToolTip("Automatically delete temporary cache files that have exceeded the maximum age")
        sc_form.addRow(TechLabel("AUTO CLEAR"), self.cache_auto_cb)

        self.dl_concurrency_spin = QSpinBox()
        self.dl_concurrency_spin.setRange(1, 10)
        self.dl_concurrency_spin.setStyleSheet(self._compact_input_style())
        self.dl_concurrency_spin.setToolTip("Number of simultaneous image downloads (1-10)")
        sc_form.addRow(TechLabel("DL CONCURRENCY"), self.dl_concurrency_spin)

        sync_cache_card.content_layout.addLayout(sc_form)
        layout.addWidget(sync_cache_card)

        # === SECTION: DATA PATHS ===
        paths_card = GlassCard(title="DATA PATHS")
        paths_layout = QVBoxLayout()
        paths_layout.setSpacing(4)
        paths_layout.setContentsMargins(0, 4, 0, 4)
        path_labels = [
            ("Config", str(self.paths.config_dir)),
            ("Logs", str(self.paths.logs_dir)),
            ("Temp Cache", str(self.paths.temp_root)),
            ("Archived", str(self.paths.archived_root)),
        ]
        for label, path in path_labels:
            row = QHBoxLayout()
            row.setSpacing(8)
            lbl = TechLabel(label)
            lbl.setFixedWidth(80)
            path_lbl = QLabel(path)
            path_lbl.setFont(font_inter(10))
            path_lbl.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent; border: none;")
            path_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            path_lbl.setToolTip(f"Filesystem path for {label.lower()} storage")
            row.addWidget(lbl)
            row.addWidget(path_lbl, 1)
            paths_layout.addLayout(row)
        paths_card.content_layout.addLayout(paths_layout)
        layout.addWidget(paths_card)

        about_card = GlassCard(title="ABOUT")
        about_layout = QVBoxLayout()
        about_layout.setSpacing(8)
        about_layout.setContentsMargins(0, 4, 0, 4)

        # App info
        about_layout.addWidget(self._about_row("APPLICATION", f"{APP_NAME} v{APP_VERSION}"))
        about_layout.addWidget(self._about_row("DEVELOPER", "PINKgeekPDX"))
        about_layout.addWidget(self._about_row("FRAMEWORK", "PyQt6"))
        about_layout.addWidget(self._about_row("LICENSE", "MIT License"))

        # GitHub link row
        gh_row = QWidget()
        gh_row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        gh_row_layout = QHBoxLayout(gh_row)
        gh_row_layout.setContentsMargins(0, 2, 0, 2)
        gh_row_layout.setSpacing(8)
        from src.ui.theme.fonts import label_caps as _label_caps
        gh_lbl_key = TechLabel("GITHUB")
        gh_lbl_key.setFixedWidth(100)
        gh_lbl_val = QLabel('<a href="https://github.com/pinkgeekpdx" style="color: #00AAFF;">github.com/pinkgeekpdx</a>')
        gh_lbl_val.setFont(font_inter(12))
        gh_lbl_val.setStyleSheet("background: transparent; border: none;")
        gh_lbl_val.setTextFormat(Qt.TextFormat.RichText)
        gh_lbl_val.setOpenExternalLinks(True)
        gh_row_layout.addWidget(gh_lbl_key)
        gh_row_layout.addWidget(gh_lbl_val)
        about_layout.addWidget(gh_row)

        # Developer bio
        dev_bio = QLabel(
            'Developed by <a href="https://github.com/pinkgeekpdx" style="color: #00AAFF;">PINKgeekPDX</a> '
            '— a community fan project for Star Citizen players. Not affiliated with Cloud Imperium Games.'
        )
        dev_bio.setFont(font_inter(10))
        dev_bio.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent; border: none;")
        dev_bio.setWordWrap(True)
        dev_bio.setTextFormat(Qt.TextFormat.RichText)
        dev_bio.setOpenExternalLinks(True)
        about_layout.addWidget(dev_bio)

        # Disclaimer
        about_layout.addSpacing(8)
        license_lbl = QLabel("LICENSE: MIT License — Open Source. See LICENSE file for full terms.")
        license_lbl.setFont(font_inter(9))
        license_lbl.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent;")
        license_lbl.setWordWrap(True)
        about_layout.addWidget(license_lbl)

        disc_lbl = QLabel("DISCLAIMER: This is an unofficial tool and is not affiliated with the Cloud Imperium group of companies. All content, including Star Citizen and Squadron 42 materials, are property of Cloud Imperium Rights LLC and Cloud Imperium Rights Ltd.")
        disc_lbl.setFont(font_inter(9))
        disc_lbl.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent;")
        disc_lbl.setWordWrap(True)
        about_layout.addWidget(disc_lbl)

        about_card.content_layout.addLayout(about_layout)
        layout.addWidget(about_card)

        # === SECTION: UPDATE BEHAVIOR ===
        layout.addWidget(self._build_update_behavior_card())

        # === SECTION: ARCHIVE & EXPORT PREFERENCES ===
        layout.addWidget(self._build_archive_export_card())

        # === SECTION: DIAGNOSTICS & LOGS ===
        layout.addWidget(self._build_diagnostics_card())

        layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        # NOTE: _init_updater() is now called in __init__ AFTER _load_values()
        # Do NOT call it here to avoid the init-order bug.

    def _build_update_behavior_card(self) -> "GlassCard":
        """Build the Update Behavior GlassCard with all update controls."""
        card = GlassCard(title="UPDATE BEHAVIOR")
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(0, 4, 0, 4)

        # Auto-check checkbox
        self.auto_check_cb = QCheckBox("Automatically check for updates on startup")
        self.auto_check_cb.setStyleSheet(self._checkbox_style())
        self.auto_check_cb.setToolTip("Check GitHub for a newer version when the app launches")
        layout.addWidget(self.auto_check_cb)

        # Auto-download checkbox
        self.auto_download_cb = QCheckBox("Automatically download updates when available")
        self.auto_download_cb.setStyleSheet(self._checkbox_style())
        self.auto_download_cb.setToolTip("Download newly detected updates automatically in the background")
        layout.addWidget(self.auto_download_cb)

        # Update status
        self.update_status_lbl = QLabel("Ready")
        self.update_status_lbl.setFont(font_inter(11))
        self.update_status_lbl.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent; border: none; margin-top: 4px;")
        self.update_status_lbl.setToolTip("Shows whether the app is up to date, an update is available, or ready to install")
        layout.addWidget(self.update_status_lbl)

        # Progress bar
        self.update_progress = QProgressBar()
        self.update_progress.setVisible(False)
        self.update_progress.setFixedHeight(14)
        self.update_progress.setStyleSheet(f"""
            QProgressBar {{
                background: rgba(5, 11, 15, 0.85);
                border: 1px solid {P.OUTLINE_VARIANT};
                border-radius: 3px;
                text-align: center;
                font-size: 10px;
                color: {P.ON_SURFACE};
            }}
            QProgressBar::chunk {{
                background: {P.PRIMARY};
                border-radius: 2px;
            }}
        """)
        self.update_progress.setToolTip("Shows background update download progress")
        layout.addWidget(self.update_progress)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.check_update_btn = QPushButton("CHECK FOR UPDATES")
        self.check_update_btn.setFixedHeight(28)
        self.check_update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.check_update_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(0, 170, 255, 0.15);
                color: {P.ON_SURFACE};
                border: 1px solid {P.PRIMARY};
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 11px;
            }}
            QPushButton:hover {{ background: rgba(0, 170, 255, 0.25); }}
            QPushButton:pressed {{ background: rgba(0, 170, 255, 0.35); }}
        """)
        self.check_update_btn.setToolTip("Manually check GitHub for a newer SC Dossier release")
        self.check_update_btn.clicked.connect(self._on_check_updates)

        self.install_update_btn = QPushButton("INSTALL DOWNLOADED UPDATE")
        self.install_update_btn.setFixedHeight(28)
        self.install_update_btn.setEnabled(False)  # enabled only when staged
        self.install_update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.install_update_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(0, 255, 136, 0.10);
                color: #00FF88;
                border: 1px solid #00AA66;
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 11px;
            }}
            QPushButton:hover {{ background: rgba(0, 255, 136, 0.20); }}
            QPushButton:pressed {{ background: rgba(0, 255, 136, 0.30); }}
            QPushButton:disabled {{ color: {P.TEXT_DIM}; border-color: {P.OUTLINE_VARIANT}; background: transparent; }}
        """)
        self.install_update_btn.setToolTip("Install an already-downloaded update when you are ready to close and relaunch the app")
        self.install_update_btn.clicked.connect(self._on_install_update)

        self.download_update_btn = QPushButton("DOWNLOAD & INSTALL")
        self.download_update_btn.setFixedHeight(28)
        self.download_update_btn.setVisible(False)
        self.download_update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_update_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(0, 255, 136, 0.15);
                color: #00FF88;
                border: 1px solid #00FF88;
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 11px;
            }}
            QPushButton:hover {{ background: rgba(0, 255, 136, 0.25); }}
            QPushButton:pressed {{ background: rgba(0, 255, 136, 0.35); }}
        """)
        self.download_update_btn.setToolTip("Download and stage the latest available update for installation")
        self.download_update_btn.clicked.connect(self._on_download_update)

        btn_layout.addWidget(self.check_update_btn)
        btn_layout.addWidget(self.download_update_btn)
        btn_layout.addWidget(self.install_update_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        card.content_layout.addLayout(layout)
        return card

    def _build_archive_export_card(self) -> "GlassCard":
        """Build the Archive & Export Preferences GlassCard."""
        card = GlassCard(title="ARCHIVE & EXPORT PREFERENCES")
        form = QFormLayout()
        form.setSpacing(6)
        form.setContentsMargins(0, 4, 0, 4)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Default export destination
        export_row = QWidget()
        export_row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        export_row_layout = QHBoxLayout(export_row)
        export_row_layout.setContentsMargins(0, 0, 0, 0)
        export_row_layout.setSpacing(6)

        self.export_dest_input = QLineEdit()
        self.export_dest_input.setFont(font_inter(11))
        self.export_dest_input.setStyleSheet(self._compact_input_style())
        self.export_dest_input.setPlaceholderText("Default export folder path...")
        self.export_dest_input.setToolTip("Choose the default folder used when exporting archived profiles")

        browse_btn = QPushButton("BROWSE")
        browse_btn.setFixedHeight(26)
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(0, 170, 255, 0.12);
                color: {P.ON_SURFACE};
                border: 1px solid {P.OUTLINE_VARIANT};
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 10px;
            }}
            QPushButton:hover {{ background: rgba(0, 170, 255, 0.22); }}
        """)
        browse_btn.setToolTip("Open a folder browser to select the default export destination")
        browse_btn.clicked.connect(self._on_browse_export_dest)
        export_row_layout.addWidget(self.export_dest_input)
        export_row_layout.addWidget(browse_btn)
        form.addRow(TechLabel("EXPORT FOLDER"), export_row)

        self.remember_export_cb = QCheckBox("Remember last export folder")
        self.remember_export_cb.setStyleSheet(self._checkbox_style())
        self.remember_export_cb.setToolTip("Reuse the last export folder you selected the next time you export")
        form.addRow(TechLabel("REMEMBER FOLDER"), self.remember_export_cb)

        self.archive_sort_combo = QComboBox()
        self.archive_sort_combo.setFont(font_inter(11))
        self.archive_sort_combo.setStyleSheet(self._compact_input_style())
        self.archive_sort_combo.addItem("Date (newest first)", "date_desc")
        self.archive_sort_combo.addItem("Date (oldest first)", "date_asc")
        self.archive_sort_combo.addItem("Name (A–Z)", "name_asc")
        self.archive_sort_combo.addItem("Name (Z–A)", "name_desc")
        self.archive_sort_combo.setToolTip("Choose how archived profiles are sorted when the Archive tab opens")
        form.addRow(TechLabel("DEFAULT SORT"), self.archive_sort_combo)

        card.content_layout.addLayout(form)
        return card

    def _build_diagnostics_card(self) -> "GlassCard":
        """Build the Diagnostics & Logs GlassCard."""
        card = GlassCard(title="DIAGNOSTICS & LOGS")
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(0, 4, 0, 4)

        form = QFormLayout()
        form.setSpacing(6)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.log_level_combo = QComboBox()
        self.log_level_combo.setFont(font_inter(11))
        self.log_level_combo.setStyleSheet(self._compact_input_style())
        self.log_level_combo.addItem("Normal", "normal")
        self.log_level_combo.addItem("Debug (verbose)", "debug")
        self.log_level_combo.setToolTip("Control whether the app writes normal or debug-level detail to its logs")
        form.addRow(TechLabel("LOG LEVEL"), self.log_level_combo)

        self.debug_diag_cb = QCheckBox("Include debug details in diagnostics")
        self.debug_diag_cb.setStyleSheet(self._checkbox_style())
        self.debug_diag_cb.setToolTip("Include additional troubleshooting detail in user-visible diagnostics and status messages")
        form.addRow(TechLabel("DEBUG DETAIL"), self.debug_diag_cb)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        open_logs_btn = QPushButton("OPEN LOGS FOLDER")
        open_logs_btn.setFixedHeight(28)
        open_logs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_logs_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(0, 170, 255, 0.12);
                color: {P.ON_SURFACE};
                border: 1px solid {P.OUTLINE_VARIANT};
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 11px;
            }}
            QPushButton:hover {{ background: rgba(0, 170, 255, 0.22); }}
        """)
        open_logs_btn.setToolTip("Open the folder that contains SC Dossier log files")
        open_logs_btn.clicked.connect(self._on_open_logs_folder)

        copy_diag_btn = QPushButton("COPY DIAGNOSTIC SUMMARY")
        copy_diag_btn.setFixedHeight(28)
        copy_diag_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_diag_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(0, 170, 255, 0.12);
                color: {P.ON_SURFACE};
                border: 1px solid {P.OUTLINE_VARIANT};
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 11px;
            }}
            QPushButton:hover {{ background: rgba(0, 170, 255, 0.22); }}
        """)
        copy_diag_btn.setToolTip("Copy a recent troubleshooting summary to the clipboard for sharing or support")
        copy_diag_btn.clicked.connect(self._on_copy_diagnostics)

        btn_layout.addWidget(open_logs_btn)
        btn_layout.addWidget(copy_diag_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        card.content_layout.addLayout(layout)
        return card

    def _init_updater(self) -> None:
        """Initialize the updater service and connect signals."""
        self._updater = UpdaterService()
        self._updater.update_status.connect(self._on_update_status)
        self._updater.update_checked.connect(self._on_update_checked)
        self._updater.update_ready_to_install.connect(self._on_update_ready)

        # Auto-check only if setting enabled (requires _load_values() to have run)
        if self.auto_check_cb.isChecked():
            self._updater.check_for_updates(silent=True)

    def _on_check_updates(self) -> None:
        """Manual update check."""
        if self._updater:
            self._updater.check_for_updates(silent=False)

    def _on_download_update(self) -> None:
        """Download the pending update (shows install button when done)."""
        if self._updater and hasattr(self._updater, '_asset_url') and self._updater._asset_url:
            self._updater.download_update(self._updater._asset_url)
            self.download_update_btn.setVisible(False)
            self.check_update_btn.setEnabled(False)

    def _on_install_update(self) -> None:
        """Install the staged update (user-initiated from Settings)."""
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
        elif "READY TO INSTALL" in status:
            self.update_progress.setVisible(False)
            self.update_progress.setValue(0)
        elif "DOWNLOAD COMPLETE" in status or "INSTALL" in status:
            self.update_progress.setVisible(False)
            self.update_progress.setValue(0)
        elif "FAILED" in status:
            self.update_progress.setVisible(False)
            self.download_update_btn.setVisible(False)
            self.check_update_btn.setEnabled(True)

    @pyqtSlot(bool, str)
    def _on_update_checked(self, available: bool, version_or_msg: str) -> None:
        if available:
            self.download_update_btn.setVisible(True)
        else:
            self.download_update_btn.setVisible(False)

    @pyqtSlot(str)
    def _on_update_ready(self, staged_path: str) -> None:
        """Called when update has been downloaded and staged — enable install button."""
        self._staged_update_path = staged_path
        self.install_update_btn.setEnabled(True)
        self.install_update_btn.setToolTip(f"Install the staged update from: {staged_path}")
        self.check_update_btn.setEnabled(True)

    def _on_browse_export_dest(self) -> None:
        """Open directory dialog to pick export folder."""
        path = QFileDialog.getExistingDirectory(self, "Select Default Export Folder", self.export_dest_input.text() or self.paths.export_root)
        if path:
            self.export_dest_input.setText(path)
            self.sm.export_destination = path

    def _on_open_logs_folder(self) -> None:
        """Open the logs directory in the OS file explorer."""
        import os
        import platform
        log_dir = self.paths.logs_dir
        if platform.system() == "Windows":
            os.startfile(log_dir)
        else:
            # Fallback for completeness, though app is Windows-focused
            import subprocess
            subprocess.Popen(['xdg-open', log_dir])

    def _on_copy_diagnostics(self) -> None:
        """Copy a diagnostic summary to the clipboard."""
        from PyQt6.QtWidgets import QApplication
        import sys
        import platform
        
        diag = []
        diag.append(f"SC Dossier version: {APP_VERSION}")
        diag.append(f"Python version: {sys.version}")
        diag.append(f"OS: {platform.system()} {platform.release()}")
        diag.append(f"Update channel: {'Auto' if self.sm.auto_check_updates else 'Manual'}")
        
        if self.debug_diag_cb.isChecked():
            diag.append("--- DEBUG INFO ---")
            diag.append(f"App Root: {self.paths.app_root}")
            diag.append(f"Settings Path: {self.paths.settings_file}")
            diag.append(f"Logs Path: {self.paths.logs_dir}")
            
        clipboard = QApplication.clipboard()
        clipboard.setText("\\n".join(diag))
        
        # We don't have a direct reference to the parent main window status bar here easily,
        # but the copy action will just silently succeed.

    def _about_row(self, label: str, value: str) -> QWidget:
        row = QWidget()
        row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)
        lbl = TechLabel(label)
        lbl.setFixedWidth(100)
        val = QLabel(value)
        val.setFont(font_inter(12))
        val.setStyleSheet(f"color: {P.ON_SURFACE}; background: transparent; border: none;")
        layout.addWidget(lbl)
        layout.addWidget(val)
        return row

    def _load_values(self) -> None:
        self.delay_spin.setValue(self.sm.scraper_delay_ms)
        self.timeout_spin.setValue(getattr(self.sm, 'scraper_timeout_sec', 30))
        self.proxy_input.setText(getattr(self.sm, 'scraper_proxy', ""))
        self.ua_input.setText(self.sm.user_agent)

        conf = int(self.sm.ocr_confidence_threshold * 100)
        self.ocr_slider.setValue(conf)
        self.ocr_val_lbl.setText(f"{conf}%")
        self.ocr_combo.setCurrentText("RapidOCR" if self.sm.ocr_engine == "rapidocr" else "EasyOCR")
        self.ocr_thread_spin.setValue(getattr(self.sm, 'ocr_thread_count', 2))

        self.font_scaling_slider.setValue(getattr(self.sm, 'font_size_scaling', 100))
        self.font_scaling_lbl.setText(f"{self.font_scaling_slider.value()}%")

        self.sync_interval_spin.setValue(self.sm.sync_interval_hours)
        self.sync_on_load_cb.setChecked(self.sm.sync_on_load)

        self.cache_spin.setValue(self.sm.temp_cache_max_age_days)
        self.cache_auto_cb.setChecked(self.sm.temp_cache_auto_clear)
        self.dl_concurrency_spin.setValue(getattr(self.sm, 'image_download_concurrency', 3))

        opacity = int(self.sm.toolbar_opacity * 100)
        self.toolbar_slider.setValue(opacity)
        self.toolbar_val_lbl.setText(f"{opacity}%")

        self.theme_accent_input.setText(self.sm.theme_accent_override or "")

        self.minimize_tray_cb.setChecked(getattr(self.sm, 'minimize_to_tray_on_close', True))
        self.pin_startup_cb.setChecked(getattr(self.sm, 'pin_on_startup', False))
        self.tray_notif_cb.setChecked(getattr(self.sm, 'show_tray_notifications', True))

        self.auto_check_cb.setChecked(getattr(self.sm, 'auto_check_updates', True))
        self.auto_download_cb.setChecked(getattr(self.sm, 'auto_download_updates', False))

        # Archive & Export
        self.export_dest_input.setText(getattr(self.sm, 'export_destination', ''))
        self.remember_export_cb.setChecked(getattr(self.sm, 'remember_export_folder', True))
        sort_val = getattr(self.sm, 'archive_default_sort', 'date_desc')
        idx = self.archive_sort_combo.findData(sort_val)
        if idx >= 0:
            self.archive_sort_combo.setCurrentIndex(idx)

        # Diagnostics & Logs
        log_val = getattr(self.sm, 'log_level', 'normal')
        idx = self.log_level_combo.findData(log_val)
        if idx >= 0:
            self.log_level_combo.setCurrentIndex(idx)
        self.debug_diag_cb.setChecked(getattr(self.sm, 'include_debug_in_diagnostics', False))

    def _connect_signals(self) -> None:
        # General
        self.minimize_tray_cb.toggled.connect(lambda v: setattr(self.sm, 'minimize_to_tray_on_close', v))
        self.pin_startup_cb.toggled.connect(lambda v: setattr(self.sm, 'pin_on_startup', v))
        self.tray_notif_cb.toggled.connect(lambda v: setattr(self.sm, 'show_tray_notifications', v))

        # Appearance
        self.font_scaling_slider.valueChanged.connect(self._on_font_scaling_changed)
        self.theme_accent_input.editingFinished.connect(
            lambda: setattr(self.sm, 'theme_accent_override', self.theme_accent_input.text() or None)
        )
        self.toolbar_slider.valueChanged.connect(self._on_toolbar_opacity_changed)

        # Scraper
        self.delay_spin.valueChanged.connect(lambda v: setattr(self.sm, 'scraper_delay_ms', v))
        self.timeout_spin.valueChanged.connect(lambda v: setattr(self.sm, 'scraper_timeout_sec', v))
        self.proxy_input.editingFinished.connect(lambda: setattr(self.sm, 'scraper_proxy', self.proxy_input.text()))
        self.ua_input.editingFinished.connect(lambda: setattr(self.sm, 'user_agent', self.ua_input.text()))

        # OCR
        self.ocr_slider.valueChanged.connect(self._on_ocr_changed)
        self.ocr_combo.currentIndexChanged.connect(
            lambda: setattr(self.sm, 'ocr_engine', self.ocr_combo.currentData())
        )
        self.ocr_thread_spin.valueChanged.connect(lambda v: setattr(self.sm, 'ocr_thread_count', v))

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
        self.export_dest_input.editingFinished.connect(lambda: setattr(self.sm, 'export_destination', self.export_dest_input.text()))
        self.remember_export_cb.toggled.connect(lambda v: setattr(self.sm, 'remember_export_folder', v))
        self.archive_sort_combo.currentIndexChanged.connect(
            lambda: setattr(self.sm, 'archive_default_sort', self.archive_sort_combo.currentData())
        )

        # Diagnostics & Logs
        self.log_level_combo.currentIndexChanged.connect(
            lambda: setattr(self.sm, 'log_level', self.log_level_combo.currentData())
        )
        self.debug_diag_cb.toggled.connect(lambda v: setattr(self.sm, 'include_debug_in_diagnostics', v))

    def _on_ocr_changed(self, value: int) -> None:
        self.ocr_val_lbl.setText(f"{value}%")
        self.sm.ocr_confidence_threshold = value / 100.0

    def _on_toolbar_opacity_changed(self, value: int) -> None:
        self.toolbar_val_lbl.setText(f"{value}%")
        self.sm.toolbar_opacity = value / 100.0

    def _on_font_scaling_changed(self, value: int) -> None:
        self.font_scaling_lbl.setText(f"{value}%")
        self.sm.font_size_scaling = value