"""
src/ui/tabs/theme_editor_dialog.py
Dialog for customizing all theme colors.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen
from src.ui.theme import palette as P
from src.ui.theme.fonts import label_caps, font_inter
from src.ui.widgets.smart_inputs import ColorPickerButton
from src.core.settings import SettingsManager
from src.ui.widgets.glass_card import GlassCard
from collections import defaultdict

class ThemeEditorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setWindowTitle("Theme Editor")
        self.setMinimumSize(480, 680)
        
        self.sm = SettingsManager.instance()
        self._pending_overrides = dict(self.sm.theme_palette_overrides)
        
        self._drag_active = False
        self._drag_start_pos = QPoint()
        self._drag_start_window_pos = QPoint()
        
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        container = QWidget(self)
        container.setObjectName("ThemeEditorContainer")
        container.setStyleSheet(f"""
            #ThemeEditorContainer {{
                background-color: rgba(10, 29, 41, 0.97);
                border: 1px solid rgba(0, 170, 255, 0.30);
                border-radius: 6px;
            }}
        """)
        outer.addWidget(container)

        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # Header Row
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("THEME COLOR CONFIGURATION")
        title.setFont(label_caps())
        title.setStyleSheet(f"color: {P.PRIMARY}; letter-spacing: 0.15em; background: transparent; border: none;")
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(f"""
            QPushButton {{ color: {P.TEXT_DIM}; font-size: 16px; border: none; background: transparent; border-radius: 4px; }}
            QPushButton:hover {{ background: rgba(255, 68, 68, 0.2); color: {P.HAZARD_RED}; }}
        """)
        close_btn.clicked.connect(self.reject)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        main_layout.addLayout(header_layout)

        divider = QWidget()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: {P.OUTLINE_VARIANT};")
        main_layout.addWidget(divider)

        desc = QLabel("Customize the application's entire color palette. Changes apply immediately to some UI elements, but a full restart is required to apply all changes.")
        desc.setWordWrap(True)
        desc.setFont(font_inter(10))
        desc.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent; border: none;")
        main_layout.addWidget(desc)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")
        scroll.viewport().setStyleSheet("background-color: transparent;")
        
        content = QWidget()
        content.setStyleSheet("background-color: transparent;")
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(0, 0, 10, 0)
        self.content_layout.setSpacing(8)

        # Group colors logically
        groups = defaultdict(list)
        self._pickers = {}
        
        for k, v in P._DEFAULTS.items():
            if k.startswith("SURFACE") or k in ("SPACE_VOID", "BACKGROUND"):
                groups["SURFACES"].append((k, v))
            elif k.startswith("PRIMARY"):
                groups["PRIMARY ACCENTS"].append((k, v))
            elif k.startswith("SECONDARY"):
                groups["SECONDARY ACCENTS"].append((k, v))
            elif k.startswith("TERTIARY"):
                groups["TERTIARY ACCENTS"].append((k, v))
            elif "TEXT" in k or k.startswith("ON_"):
                groups["TEXT & CONTENT"].append((k, v))
            elif "ERROR" in k or "HAZARD" in k or "POSITIVE" in k:
                groups["STATUS & ALERTS"].append((k, v))
            elif k.startswith("OUTLINE"):
                groups["BORDERS"].append((k, v))
            else:
                groups["MISC"].append((k, v))

        order = [
            "PRIMARY ACCENTS", "SECONDARY ACCENTS", "TERTIARY ACCENTS", 
            "SURFACES", "TEXT & CONTENT", "BORDERS", "STATUS & ALERTS", "MISC"
        ]

        for gname in order:
            if gname not in groups or not groups[gname]:
                continue
                
            card = GlassCard(title=gname)
            card_lo = QVBoxLayout()
            card_lo.setContentsMargins(0, 4, 0, 4)
            card_lo.setSpacing(4)
            
            g_colors = sorted(groups[gname], key=lambda x: x[0])
            for key, default_val in g_colors:
                row = QWidget()
                row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
                row.setStyleSheet("background-color: transparent;")
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(8, 2, 8, 2)
                row_layout.setSpacing(8)
                
                lbl = QLabel(key)
                lbl.setFont(font_inter(10))
                lbl.setStyleSheet(f"color: {P.ON_SURFACE}; background-color: transparent !important; border: none;")
                
                current_val = self._pending_overrides.get(key, default_val)
                btn = ColorPickerButton(current_val)
                btn.colorChanged.connect(lambda color, k=key: self._on_color_changed(k, color))
                self._pickers[key] = btn
                
                row_layout.addWidget(lbl)
                row_layout.addStretch()
                row_layout.addWidget(btn)
                
                card_lo.addWidget(row)
                
            card.content_layout.addLayout(card_lo)
            self.content_layout.addWidget(card)

        self.content_layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        reset_btn = QPushButton("RESET DEFAULTS")
        reset_btn.setProperty("class", "danger-ghost")
        reset_btn.clicked.connect(self._reset_defaults)
        
        cancel_btn = QPushButton("CANCEL")
        cancel_btn.setProperty("class", "ghost")
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("SAVE")
        save_btn.setProperty("class", "primary")
        save_btn.clicked.connect(self._save_changes)
        
        btn_layout.addWidget(reset_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        main_layout.addLayout(btn_layout)

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

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            # Only allow drag from top area
            if event.pos().y() < 50:
                self._drag_active = True
                self._drag_start_pos = event.globalPosition().toPoint()
                self._drag_start_window_pos = self.pos()
                event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_active:
            delta = event.globalPosition().toPoint() - self._drag_start_pos
            self.move(self._drag_start_window_pos + delta)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._drag_active:
            self._drag_active = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _on_color_changed(self, key: str, color: str):
        self._pending_overrides[key] = color

    def _reset_defaults(self):
        self._pending_overrides.clear()
        self._update_pickers()

    def _update_pickers(self):
        for k, btn in self._pickers.items():
            btn.setColor(P._DEFAULTS.get(k, "#00AAFF"))
        self.sm.theme_palette_overrides = {}
        P.apply_overrides({})
        from src.core.events import EventBus
        EventBus.instance().settings_changed.emit("theme_palette_overrides", {})
        self._prompt_restart("Theme defaults restored.\n\nA restart is required to fully apply the defaults to all UI elements.")

    def _save_changes(self):
        self.sm.theme_palette_overrides = self._pending_overrides
        P.apply_overrides(self._pending_overrides)
        from src.core.events import EventBus
        EventBus.instance().settings_changed.emit("theme_palette_overrides", self._pending_overrides)
        self._prompt_restart("Theme overrides saved.\n\nA restart is required to apply the new colors to all elements.")

    def _prompt_restart(self, msg: str):
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtWidgets import QDialog
        import sys, subprocess
        from src.ui.widgets.confirm_dialog import ConfirmDialog
        
        dlg = ConfirmDialog(
            title="RESTART REQUIRED",
            message=f"{msg}\n\nWould you like to restart the application now?",
            confirm_text="RESTART NOW",
            cancel_text="LATER",
            danger=False,
            parent=self
        )
        self.accept()
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
