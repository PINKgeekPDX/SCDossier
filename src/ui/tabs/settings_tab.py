"""
src/ui/tabs/settings_tab.py
SettingsTab — comprehensive settings interface with GlassCard sections.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSpinBox,
    QFormLayout, QCheckBox, QPushButton, QComboBox, QLineEdit, QScrollArea, QFrame
)

from src.core.settings import SettingsManager
from src.core.paths import PathManager
from src.ui.theme import palette as P
from src.ui.theme.fonts import label_caps, font_inter
from src.ui.widgets.tech_label import TechLabel
from src.ui.widgets.glass_card import GlassCard


class SettingsTab(QWidget):
    """
    Comprehensive settings interface grouped into GlassCard sections.
    All changes auto-save via SettingsManager debouncer.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.sm = SettingsManager.instance()
        self.paths = PathManager.instance()
        self._build_ui()
        self._load_values()
        self._connect_signals()

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
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- Section: Scraper ---
        scraper_card = GlassCard(title="SCRAPER")
        scraper_form = QFormLayout()
        scraper_form.setSpacing(12)
        scraper_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 10000)
        self.delay_spin.setSingleStep(100)
        self.delay_spin.setSuffix(" ms")
        self.delay_spin.setStyleSheet(self._input_style())
        scraper_form.addRow(TechLabel("REQUEST DELAY"), self.delay_spin)

        self.ua_input = QLineEdit()
        self.ua_input.setFont(font_inter(12))
        self.ua_input.setStyleSheet(self._input_style())
        scraper_form.addRow(TechLabel("USER AGENT"), self.ua_input)

        scraper_card.content_layout.addLayout(scraper_form)
        layout.addWidget(scraper_card)

        # --- Section: OCR ---
        ocr_card = GlassCard(title="OCR")
        ocr_form = QFormLayout()
        ocr_form.setSpacing(12)
        ocr_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.ocr_combo = QComboBox()
        self.ocr_combo.setFont(font_inter(12))
        self.ocr_combo.setStyleSheet(self._input_style())
        self.ocr_combo.addItem("RapidOCR", "rapidocr")
        ocr_form.addRow(TechLabel("ENGINE"), self.ocr_combo)

        ocr_hbox = QHBoxLayout()
        self.ocr_slider = QSlider(Qt.Orientation.Horizontal)
        self.ocr_slider.setRange(10, 99)
        self.ocr_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.ocr_slider.setTickInterval(10)
        self.ocr_slider.setStyleSheet("background: transparent; border: none;")
        self.ocr_val_lbl = QLabel("50%")
        self.ocr_val_lbl.setFont(font_inter(12))
        self.ocr_val_lbl.setStyleSheet(f"color: {P.PRIMARY}; background: transparent; border: none; min-width: 40px;")
        ocr_hbox.addWidget(self.ocr_slider)
        ocr_hbox.addWidget(self.ocr_val_lbl)
        ocr_form.addRow(TechLabel("CONFIDENCE"), ocr_hbox)

        ocr_card.content_layout.addLayout(ocr_form)
        layout.addWidget(ocr_card)

        # --- Section: Sync ---
        sync_card = GlassCard(title="SYNC")
        sync_form = QFormLayout()
        sync_form.setSpacing(12)
        sync_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.sync_interval_spin = QSpinBox()
        self.sync_interval_spin.setRange(1, 168)
        self.sync_interval_spin.setSuffix(" hours")
        self.sync_interval_spin.setStyleSheet(self._input_style())
        sync_form.addRow(TechLabel("INTERVAL"), self.sync_interval_spin)

        self.sync_on_load_cb = QCheckBox("Auto-sync on archive load")
        self.sync_on_load_cb.setStyleSheet(f"color: {P.ON_SURFACE}; background: transparent; border: none;")
        sync_form.addRow(TechLabel("ON LOAD"), self.sync_on_load_cb)

        sync_card.content_layout.addLayout(sync_form)
        layout.addWidget(sync_card)

        # --- Section: Cache ---
        cache_card = GlassCard(title="CACHE")
        cache_form = QFormLayout()
        cache_form.setSpacing(12)
        cache_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.cache_spin = QSpinBox()
        self.cache_spin.setRange(1, 365)
        self.cache_spin.setSuffix(" days")
        self.cache_spin.setStyleSheet(self._input_style())
        cache_form.addRow(TechLabel("MAX AGE"), self.cache_spin)

        self.cache_auto_cb = QCheckBox("Auto-clear expired temp cache")
        self.cache_auto_cb.setStyleSheet(f"color: {P.ON_SURFACE}; background: transparent; border: none;")
        cache_form.addRow(TechLabel("AUTO CLEAR"), self.cache_auto_cb)

        cache_card.content_layout.addLayout(cache_form)
        layout.addWidget(cache_card)

        # --- Section: Toolbar ---
        toolbar_card = GlassCard(title="TOOLBAR")
        toolbar_form = QFormLayout()
        toolbar_form.setSpacing(12)
        toolbar_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.toolbar_slider = QSlider(Qt.Orientation.Horizontal)
        self.toolbar_slider.setRange(30, 100)
        self.toolbar_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.toolbar_slider.setTickInterval(10)
        self.toolbar_slider.setStyleSheet("background: transparent; border: none;")
        self.toolbar_val_lbl = QLabel("100%")
        self.toolbar_val_lbl.setFont(font_inter(12))
        self.toolbar_val_lbl.setStyleSheet(f"color: {P.PRIMARY}; background: transparent; border: none; min-width: 40px;")
        toolbar_hbox = QHBoxLayout()
        toolbar_hbox.addWidget(self.toolbar_slider)
        toolbar_hbox.addWidget(self.toolbar_val_lbl)
        toolbar_form.addRow(TechLabel("OPACITY"), toolbar_hbox)

        toolbar_card.content_layout.addLayout(toolbar_form)
        layout.addWidget(toolbar_card)

        # --- Section: Paths ---
        paths_card = GlassCard(title="DATA PATHS")
        paths_layout = QVBoxLayout()
        paths_layout.setSpacing(6)
        path_labels = [
            ("Config", str(self.paths.config_dir)),
            ("Logs", str(self.paths.logs_dir)),
            ("Temp Cache", str(self.paths.temp_root)),
            ("Archived", str(self.paths.archived_root)),
        ]
        for label, path in path_labels:
            row = QHBoxLayout()
            lbl = TechLabel(label)
            lbl.setFixedWidth(100)
            path_lbl = QLabel(path)
            path_lbl.setFont(font_inter(11))
            path_lbl.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent; border: none;")
            path_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            row.addWidget(lbl)
            row.addWidget(path_lbl)
            paths_layout.addLayout(row)
        paths_card.content_layout.addLayout(paths_layout)
        layout.addWidget(paths_card)

        # --- Section: About ---
        about_card = GlassCard(title="ABOUT")
        about_layout = QVBoxLayout()
        about_layout.setSpacing(6)
        from src.app.constants import APP_NAME, APP_VERSION
        about_layout.addWidget(self._about_row("APPLICATION", f"{APP_NAME} v{APP_VERSION}"))
        about_layout.addWidget(self._about_row("FRAMEWORK", "PyQt6"))
        about_layout.addWidget(self._about_row("DESIGN", "Aegis Liquid Interface"))
        about_card.content_layout.addLayout(about_layout)
        layout.addWidget(about_card)

        layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _about_row(self, label: str, value: str) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 4, 0, 4)
        lbl = TechLabel(label)
        lbl.setFixedWidth(100)
        val = QLabel(value)
        val.setFont(font_inter(13))
        val.setStyleSheet(f"color: {P.ON_SURFACE}; background: transparent; border: none;")
        layout.addWidget(lbl)
        layout.addWidget(val)
        return row

    def _input_style(self) -> str:
        return f"""
            background: rgba(5, 11, 15, 0.85);
            color: {P.ON_SURFACE};
            border: 1px solid {P.OUTLINE_VARIANT};
            border-radius: 4px;
            padding: 6px 10px;
        """

    def _load_values(self) -> None:
        self.delay_spin.setValue(self.sm.scraper_delay_ms)
        self.ua_input.setText(self.sm.user_agent)

        conf = int(self.sm.ocr_confidence_threshold * 100)
        self.ocr_slider.setValue(conf)
        self.ocr_val_lbl.setText(f"{conf}%")
        self.ocr_combo.setCurrentText("RapidOCR" if self.sm.ocr_engine == "rapidocr" else "EasyOCR")

        self.sync_interval_spin.setValue(self.sm.sync_interval_hours)
        self.sync_on_load_cb.setChecked(self.sm.sync_on_load)

        self.cache_spin.setValue(self.sm.temp_cache_max_age_days)
        self.cache_auto_cb.setChecked(self.sm.temp_cache_auto_clear)

        opacity = int(self.sm.toolbar_opacity * 100)
        self.toolbar_slider.setValue(opacity)
        self.toolbar_val_lbl.setText(f"{opacity}%")

    def _connect_signals(self) -> None:
        self.delay_spin.valueChanged.connect(lambda v: setattr(self.sm, 'scraper_delay_ms', v))
        self.ua_input.editingFinished.connect(lambda: setattr(self.sm, 'user_agent', self.ua_input.text()))

        self.ocr_slider.valueChanged.connect(self._on_ocr_changed)
        self.ocr_combo.currentIndexChanged.connect(
            lambda: setattr(self.sm, 'ocr_engine', self.ocr_combo.currentData())
        )

        self.sync_interval_spin.valueChanged.connect(lambda v: setattr(self.sm, 'sync_interval_hours', v))
        self.sync_on_load_cb.toggled.connect(lambda v: setattr(self.sm, 'sync_on_load', v))

        self.cache_spin.valueChanged.connect(lambda v: setattr(self.sm, 'temp_cache_max_age_days', v))
        self.cache_auto_cb.toggled.connect(lambda v: setattr(self.sm, 'temp_cache_auto_clear', v))

        self.toolbar_slider.valueChanged.connect(self._on_toolbar_opacity_changed)

    def _on_ocr_changed(self, value: int) -> None:
        self.ocr_val_lbl.setText(f"{value}%")
        self.sm.ocr_confidence_threshold = value / 100.0

    def _on_toolbar_opacity_changed(self, value: int) -> None:
        self.toolbar_val_lbl.setText(f"{value}%")
        self.sm.toolbar_opacity = value / 100.0
