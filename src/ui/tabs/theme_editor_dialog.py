"""
src/ui/tabs/theme_editor_dialog.py
Theme Editor — user-friendly color customization dialog.

Features:
- Human-readable names and descriptions for every palette color
- Grouped by UI purpose (Backgrounds, Accents, Text, Status)
- Comprehensive live preview showing real app UI elements
- Per-color reset to default
- Consistent SCPINK glass-card aesthetic
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QWidget, QPushButton, QFrame, QSizePolicy, QLineEdit,
    QCheckBox, QSlider, QProgressBar, QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QLinearGradient

from src.ui.theme import palette as P
from src.ui.theme.fonts import label_caps, font_inter, font_mono
from src.ui.widgets.smart_inputs import ColorPickerButton
from src.core.settings import SettingsManager
from src.ui.widgets.confirm_dialog import ConfirmDialog


# ---------------------------------------------------------------------------
# Palette key metadata: (friendly_name, description)
# ---------------------------------------------------------------------------
_COLOR_META: dict[str, tuple[str, str]] = {
    # Backgrounds
    "SPACE_VOID":              ("Deep Background",     "The deepest background layer behind everything"),
    "SURFACE":                 ("Base Surface",        "Default surface color for most panels"),
    "SURFACE_DIM":             ("Dim Surface",         "Slightly dimmed surface for recessed areas"),
    "SURFACE_CONTAINER_LOWEST":("Lowest Container",    "Deepest container layer"),
    "SURFACE_CONTAINER_LOW":   ("Card Background",     "Standard glass card and panel background"),
    "SURFACE_CONTAINER":       ("Elevated Surface",    "Slightly raised surfaces and dropdowns"),
    "SURFACE_CONTAINER_HIGH":  ("High Surface",        "Elevated panels like tooltips and menus"),
    # Accent & Interactive
    "PRIMARY_CONTAINER":       ("Accent Color",        "Primary interactive color — buttons, glows, active borders"),
    "PRIMARY":                 ("Accent Highlight",    "Lighter accent for hover states and highlights"),
    "ON_PRIMARY":              ("Accent Button Text",  "Text color on top of the accent color"),
    "SECONDARY_CONTAINER":    ("Secondary Accent",     "Secondary color for hover effects and subtle highlights"),
    "SECONDARY":              ("Secondary Highlight",  "Lighter secondary for text and icons"),
    # Text
    "ON_SURFACE":              ("Main Text",           "Primary readable text color"),
    "ON_SURFACE_VARIANT":      ("Secondary Text",      "Less prominent text — labels, metadata"),
    "TEXT_DIM":                ("Dim Text",            "Tertiary text for placeholders and hints"),
    # Status & Alerts
    "HAZARD_RED":              ("Error / Danger",      "Errors, warnings, and destructive action highlights"),
    "ERROR_CONTAINER":         ("Error Background",    "Background for error badges and containers"),
    "ERROR":                   ("Error Text",          "Text that appears on error backgrounds"),
    "ON_ERROR_CONTAINER":      ("Error Badge Text",    "Text color inside error badges"),
    "ON_ERROR":                ("Error Icon Color",    "Icon color on error backgrounds"),
    # Borders
    "OUTLINE":                 ("Border",              "Standard border and divider color"),
    "OUTLINE_VARIANT":         ("Subtle Border",       "Lighter border for inputs and separators"),
}

# Display order: group_key → list of palette keys
_GROUP_ORDER = [
    ("BACKGROUND", [
        "SPACE_VOID", "SURFACE_CONTAINER_LOW", "SURFACE_CONTAINER",
        "SURFACE_CONTAINER_HIGH", "SURFACE_CONTAINER_LOWEST",
        "SURFACE", "SURFACE_DIM",
    ]),
    ("ACCENT", [
        "PRIMARY_CONTAINER", "PRIMARY", "ON_PRIMARY",
        "SECONDARY_CONTAINER", "SECONDARY",
    ]),
    ("TEXT", [
        "ON_SURFACE", "ON_SURFACE_VARIANT", "TEXT_DIM",
    ]),
    ("STATUS", [
        "HAZARD_RED", "ERROR_CONTAINER", "ERROR",
        "ON_ERROR_CONTAINER", "ON_ERROR",
    ]),
    ("BORDERS", [
        "OUTLINE", "OUTLINE_VARIANT",
    ]),
]

_GROUP_LABELS = {
    "BACKGROUND": "BACKGROUNDS",
    "ACCENT":     "ACCENT & INTERACTIVE",
    "TEXT":       "TEXT & CONTENT",
    "STATUS":     "STATUS & ALERTS",
    "BORDERS":    "BORDERS & DIVIDERS",
}


# ---------------------------------------------------------------------------
# Custom-painted bracket card for the preview
# ---------------------------------------------------------------------------
class _PreviewBracketCard(QFrame):
    """Glass card with L-shaped bracket corners — mirrors GlassCard."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumHeight(80)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        s = 6

        bg = QColor(P.SURFACE_CONTAINER_LOW)
        bg.setAlpha(230)
        painter.fillRect(rect, bg)

        border_color = QColor(P.PRIMARY_CONTAINER)
        border_color.setAlpha(32)
        painter.setPen(QPen(border_color, 1))
        painter.drawRect(rect)

        bracket = QColor(P.BRACKET_COLOR)
        painter.setPen(QPen(bracket, 2))
        x0, y0 = rect.left(), rect.top()
        x1, y1 = rect.right(), rect.bottom()
        for px, py, dx, dy in [(x0,y0,1,1),(x1,y0,-1,1),(x0,y1,1,-1),(x1,y1,-1,-1)]:
            painter.drawLine(px, py, px + dx*s, py)
            painter.drawLine(px, py, px, py + dy*s)

        header_rect = QRect(rect.x(), rect.y(), rect.width(), 22)
        header_bg = QColor(P.PRIMARY_CONTAINER)
        header_bg.setAlpha(14)
        painter.fillRect(header_bg, header_bg)
        header_line = QColor(P.PRIMARY_CONTAINER)
        header_line.setAlpha(20)
        painter.setPen(QPen(header_line, 1))
        painter.drawLine(rect.x(), rect.y() + 22, rect.right(), rect.y() + 22)

        painter.end()


class ThemeEditorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setWindowTitle("Theme Editor")
        self.setMinimumSize(560, 720)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        self.sm = SettingsManager.instance()
        self._pending_overrides = dict(self.sm.theme_palette_overrides)
        self._defaults = dict(P._DEFAULTS)

        self._drag_active = False
        self._drag_start_pos = QPoint()
        self._drag_start_window_pos = QPoint()
        self._pickers: dict[str, ColorPickerButton] = {}
        self._reset_btns: dict[str, QPushButton] = {}

        self._preview_refs: dict[str, QWidget] = {}

        self._build_ui()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        container = QWidget(self)
        container.setObjectName("ThemeEditorContainer")
        self._container = container
        outer.addWidget(container)

        main = QVBoxLayout(container)
        main.setContentsMargins(20, 16, 20, 16)
        main.setSpacing(10)

        self._build_header(main)
        self._build_description(main)
        self._build_preview(main)
        self._build_scroll(main)
        self._build_buttons(main)

        self._apply_container_style()

    def _apply_container_style(self):
        self._container.setStyleSheet(f"""
            #ThemeEditorContainer {{
                background-color: {P.rgba(P.SURFACE_CONTAINER_LOW, 0.97)};
                border: 1px solid {P.rgba(P.PRIMARY_CONTAINER, 0.30)};
                border-radius: 6px;
            }}
        """)

    def _build_header(self, parent: QVBoxLayout):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)

        title = QLabel("THEME EDITOR")
        title.setFont(label_caps())
        title.setStyleSheet(
            f"color: {P.PRIMARY}; letter-spacing: 0.15em; background: transparent; border: none;"
        )

        close_btn = QPushButton("\u2715")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(f"""
            QPushButton {{ color: {P.TEXT_DIM}; font-size: 16px; border: none;
                           background: transparent; border-radius: 4px; }}
            QPushButton:hover {{ background: {P.rgba(P.HAZARD_RED, 0.2)}; color: {P.HAZARD_RED}; }}
        """)
        close_btn.clicked.connect(self.reject)

        row.addWidget(title)
        row.addStretch()
        row.addWidget(close_btn)
        parent.addLayout(row)

        divider = QWidget()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: {P.OUTLINE_VARIANT};")
        parent.addWidget(divider)

    def _build_description(self, parent: QVBoxLayout):
        desc = QLabel(
            "Pick colors to personalize the app. Changes preview live below. "
            "Click SAVE and restart to apply everywhere."
        )
        desc.setWordWrap(True)
        desc.setFont(font_inter(10))
        desc.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent; border: none;")
        parent.addWidget(desc)

    # ------------------------------------------------------------------
    # Live Preview Panel — comprehensive app UI element showcase
    # ------------------------------------------------------------------
    def _build_preview(self, parent: QVBoxLayout):
        outer_frame = QFrame()
        outer_frame.setObjectName("PreviewOuter")
        outer_frame.setStyleSheet(f"""
            #PreviewOuter {{
                border: 1px solid {P.rgba(P.PRIMARY_CONTAINER, 0.18)};
                border-radius: 4px;
                background-color: {P.rgba(P.SPACE_VOID, 0.50)};
            }}
        """)
        outer_lo = QVBoxLayout(outer_frame)
        outer_lo.setContentsMargins(10, 8, 10, 8)
        outer_lo.setSpacing(6)

        hdr = QLabel("LIVE PREVIEW")
        hdr.setFont(label_caps())
        hdr.setStyleSheet(
            f"color: {P.PRIMARY_CONTAINER}; letter-spacing: 0.12em; "
            f"background: transparent; border: none;"
        )
        outer_lo.addWidget(hdr)

        content = QHBoxLayout()
        content.setSpacing(10)

        # --- LEFT COLUMN: Glass card + nav mock ---
        left_col = QVBoxLayout()
        left_col.setSpacing(6)

        # Glass card with bracket corners
        card = _PreviewBracketCard()
        card_lo = QVBoxLayout(card)
        card_lo.setContentsMargins(10, 28, 10, 8)
        card_lo.setSpacing(2)

        card_title = QLabel("Citizen Name")
        card_title.setObjectName("pv_card_title")
        card_title.setFont(font_mono(11, QFont.Weight.Bold))
        card_lo.addWidget(card_title)

        card_handle = QLabel("@handle")
        card_handle.setObjectName("pv_card_handle")
        card_handle.setFont(font_mono(9))
        card_lo.addWidget(card_handle)

        card_divider = QWidget()
        card_divider.setFixedHeight(1)
        card_divider.setObjectName("pv_card_divider")
        card_lo.addWidget(card_divider)

        card_bio = QLabel("Organizational bio and role description")
        card_bio.setObjectName("pv_card_bio")
        card_bio.setFont(font_inter(9))
        card_lo.addWidget(card_bio)

        self._preview_refs["card"] = card
        self._preview_refs["card_title"] = card_title
        self._preview_refs["card_handle"] = card_handle
        self._preview_refs["card_divider"] = card_divider
        self._preview_refs["card_bio"] = card_bio
        left_col.addWidget(card)

        # Data fields row
        fields_row = QHBoxLayout()
        fields_row.setSpacing(4)
        for label_text, val_text in [("ORG", "THEKVLT"), ("RANK", "CITIZEN")]:
            field_frame = QFrame()
            field_frame.setObjectName("pv_data_field")
            fl = QVBoxLayout(field_frame)
            fl.setContentsMargins(6, 4, 6, 4)
            fl.setSpacing(1)
            lbl = QLabel(label_text)
            lbl.setObjectName("pv_field_label")
            lbl.setFont(font_mono(8, QFont.Weight.Bold))
            val = QLabel(val_text)
            val.setObjectName("pv_field_value")
            val.setFont(font_mono(10, QFont.Weight.Medium))
            fl.addWidget(lbl)
            fl.addWidget(val)
            self._preview_refs[f"field_{label_text}"] = field_frame
            self._preview_refs[f"field_{label_text}_lbl"] = lbl
            self._preview_refs[f"field_{label_text}_val"] = val
            fields_row.addWidget(field_frame)
        left_col.addLayout(fields_row)

        # Nav sidebar mock
        nav_frame = QFrame()
        nav_frame.setObjectName("pv_nav_frame")
        nav_frame.setFixedHeight(56)
        nav_lo = QHBoxLayout(nav_frame)
        nav_lo.setContentsMargins(4, 4, 4, 4)
        nav_lo.setSpacing(4)

        for i, (label, active) in enumerate([("\u2302", True), ("\u2637", False), ("\u2699", False)]):
            item = QFrame()
            item.setObjectName(f"pv_nav_{'active' if active else 'inactive'}")
            item.setFixedSize(32, 48)
            il = QVBoxLayout(item)
            il.setContentsMargins(0, 8, 0, 4)
            il.setSpacing(2)
            icon_lbl = QLabel(label)
            icon_lbl.setObjectName(f"pv_nav_icon_{'active' if active else 'inactive'}")
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_lbl.setFont(font_inter(14))
            il.addWidget(icon_lbl)
            nav_lo.addWidget(item)
            self._preview_refs[f"nav_{i}"] = item
            self._preview_refs[f"nav_icon_{i}"] = icon_lbl

        nav_lo.addStretch()
        left_col.addWidget(nav_frame)
        left_col.addStretch()

        content.addLayout(left_col, 1)

        # --- RIGHT COLUMN: Buttons, inputs, tabs, status, progress ---
        right_col = QVBoxLayout()
        right_col.setSpacing(6)

        # Tab bar mock
        tabs_frame = QFrame()
        tabs_frame.setObjectName("pv_tabs_frame")
        tabs_lo = QHBoxLayout(tabs_frame)
        tabs_lo.setContentsMargins(0, 0, 0, 0)
        tabs_lo.setSpacing(0)
        for tab_text, active in [("DOSSIER", True), ("SEARCH", False), ("ARCHIVES", False)]:
            tab_lbl = QLabel(tab_text)
            tab_lbl.setObjectName(f"pv_tab_{'active' if active else 'inactive'}")
            tab_lbl.setFont(font_mono(8, QFont.Weight.Bold))
            tab_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tab_lbl.setFixedHeight(24)
            tabs_lo.addWidget(tab_lbl)
            self._preview_refs[f"tab_{tab_text}"] = tab_lbl
        right_col.addWidget(tabs_frame)

        # Input field
        input_frame = QFrame()
        input_frame.setObjectName("pv_input_frame")
        input_lo = QHBoxLayout(input_frame)
        input_lo.setContentsMargins(0, 0, 0, 0)
        input_field = QLineEdit()
        input_field.setObjectName("pv_input")
        input_field.setPlaceholderText("Search citizens...")
        input_field.setFixedHeight(30)
        input_field.setFont(font_inter(10))
        input_lo.addWidget(input_field)
        self._preview_refs["input"] = input_field
        right_col.addWidget(input_frame)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        btn_primary = QPushButton("PRIMARY")
        btn_primary.setObjectName("pv_btn_primary")
        btn_primary.setFixedHeight(26)
        btn_row.addWidget(btn_primary)
        self._preview_refs["btn_primary"] = btn_primary

        btn_ghost = QPushButton("GHOST")
        btn_ghost.setObjectName("pv_btn_ghost")
        btn_ghost.setFixedHeight(26)
        btn_row.addWidget(btn_ghost)
        self._preview_refs["btn_ghost"] = btn_ghost

        btn_danger = QPushButton("DELETE")
        btn_danger.setObjectName("pv_btn_danger")
        btn_danger.setFixedHeight(26)
        btn_row.addWidget(btn_danger)
        self._preview_refs["btn_danger"] = btn_danger

        right_col.addLayout(btn_row)

        # Danger ghost + icon button row
        btn_row2 = QHBoxLayout()
        btn_row2.setSpacing(6)

        btn_danger_ghost = QPushButton("DANGER")
        btn_danger_ghost.setObjectName("pv_btn_danger_ghost")
        btn_danger_ghost.setFixedHeight(26)
        btn_row2.addWidget(btn_danger_ghost)
        self._preview_refs["btn_danger_ghost"] = btn_danger_ghost

        btn_icon = QPushButton("\u21bb")
        btn_icon.setObjectName("pv_btn_icon")
        btn_icon.setFixedSize(26, 26)
        btn_row2.addWidget(btn_icon)
        self._preview_refs["btn_icon"] = btn_icon

        btn_row2.addStretch()
        right_col.addLayout(btn_row2)

        # Checkbox + slider row
        opt_row = QHBoxLayout()
        opt_row.setSpacing(8)

        cb = QCheckBox("Enabled")
        cb.setObjectName("pv_checkbox")
        cb.setChecked(True)
        cb.setFont(font_inter(9))
        opt_row.addWidget(cb)
        self._preview_refs["checkbox"] = cb

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setObjectName("pv_slider")
        slider.setRange(0, 100)
        slider.setValue(65)
        slider.setFixedHeight(20)
        opt_row.addWidget(slider, 1)
        self._preview_refs["slider"] = slider

        right_col.addLayout(opt_row)

        # Progress bar
        progress = QProgressBar()
        progress.setObjectName("pv_progress")
        progress.setRange(0, 100)
        progress.setValue(60)
        progress.setFixedHeight(6)
        progress.setTextVisible(False)
        right_col.addWidget(progress)
        self._preview_refs["progress"] = progress

        # Status badges row
        status_row = QHBoxLayout()
        status_row.setSpacing(6)
        for stype, stext in [("info", "INFO"), ("success", "ONLINE"), ("warning", "COOLDOWN"), ("error", "ERROR")]:
            badge = QLabel(stext)
            badge.setObjectName(f"pv_badge_{stype}")
            badge.setFont(font_mono(7, QFont.Weight.Bold))
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFixedHeight(16)
            status_row.addWidget(badge)
            self._preview_refs[f"badge_{stype}"] = badge
        right_col.addLayout(status_row)

        # Text hierarchy
        text_frame = QFrame()
        text_frame.setObjectName("pv_text_frame")
        text_lo = QVBoxLayout(text_frame)
        text_lo.setContentsMargins(6, 4, 6, 4)
        text_lo.setSpacing(2)

        hl = QLabel("Headline text (Sora)")
        hl.setObjectName("pv_headline")
        hl.setFont(font_mono(10, QFont.Weight.Bold))
        text_lo.addWidget(hl)
        self._preview_refs["headline"] = hl

        body = QLabel("Body text for reading content (Inter)")
        body.setObjectName("pv_body")
        body.setFont(font_inter(9))
        text_lo.addWidget(body)
        self._preview_refs["body"] = body

        dim = QLabel("Dim metadata and placeholders")
        dim.setObjectName("pv_dim")
        dim.setFont(font_inter(8))
        text_lo.addWidget(dim)
        self._preview_refs["dim"] = dim

        right_col.addWidget(text_frame)
        right_col.addStretch()

        content.addLayout(right_col, 1)

        outer_lo.addLayout(content)
        parent.addWidget(outer_frame)

        # Apply initial preview styles
        self._refresh_preview()

    def _refresh_preview(self):
        """Update all preview elements with current palette values."""
        r = self._preview_refs

        # Glass card
        card = r.get("card")
        if card:
            card.update()

        # Card text
        for key, color in [("card_title", P.ON_SURFACE), ("card_handle", P.PRIMARY),
                           ("card_bio", P.TEXT_DIM)]:
            lbl = r.get(key)
            if lbl:
                lbl.setStyleSheet(f"color: {color}; background: transparent; border: none;")

        # Card divider
        div = r.get("card_divider")
        if div:
            div.setStyleSheet(f"background: {P.OUTLINE_VARIANT};")

        # Data fields
        for prefix in ["field_ORG", "field_RANK"]:
            frame = r.get(prefix)
            if frame:
                frame.setStyleSheet(f"""
                    QFrame {{ background-color: {P.rgba(P.SURFACE_CONTAINER_LOWEST, 0.5)};
                             border-radius: 3px; }}
                """)
            lbl = r.get(f"{prefix}_lbl")
            if lbl:
                lbl.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent; border: none;")
            val = r.get(f"{prefix}_val")
            if val:
                val.setStyleSheet(f"color: {P.ON_SURFACE}; background: transparent; border: none;")

        # Nav items
        for i, active in enumerate([True, False, False]):
            item = r.get(f"nav_{i}")
            icon = r.get(f"nav_icon_{i}")
            if active:
                if item:
                    item.setStyleSheet(f"""
                        QFrame {{ background-color: {P.rgba(P.PRIMARY_CONTAINER, 0.14)};
                                 border-left: 2px solid {P.PRIMARY_CONTAINER};
                                 border-radius: 0; }}
                    """)
                if icon:
                    icon.setStyleSheet(f"color: {P.PRIMARY_CONTAINER}; background: transparent; border: none;")
            else:
                if item:
                    item.setStyleSheet(f"""
                        QFrame {{ background-color: transparent; border: none; border-radius: 0; }}
                    """)
                if icon:
                    icon.setStyleSheet(f"color: {P.ON_SURFACE_VARIANT}; background: transparent; border: none;")

        # Tabs
        for tab_text, active in [("DOSSIER", True), ("SEARCH", False), ("ARCHIVES", False)]:
            tab = r.get(f"tab_{tab_text}")
            if tab:
                if active:
                    tab.setStyleSheet(f"""
                        QLabel {{ color: {P.PRIMARY}; background: transparent; border: none;
                                  border-bottom: 2px solid {P.PRIMARY_CONTAINER}; padding-bottom: 2px; }}
                    """)
                else:
                    tab.setStyleSheet(f"""
                        QLabel {{ color: {P.TEXT_DIM}; background: transparent; border: none;
                                  border-bottom: 2px solid transparent; padding-bottom: 2px; }}
                    """)

        # Input field
        inp = r.get("input")
        if inp:
            inp.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {P.rgba(P.SPACE_VOID, 0.90)};
                    color: {P.ON_SURFACE};
                    border: 1px solid {P.OUTLINE_VARIANT};
                    border-radius: 4px;
                    padding: 4px 10px;
                    selection-background-color: {P.PRIMARY_CONTAINER};
                    selection-color: #FFFFFF;
                }}
                QLineEdit:focus {{
                    border-color: {P.PRIMARY_CONTAINER};
                    background-color: {P.rgba(P.SURFACE_DIM, 0.95)};
                }}
            """)

        # Buttons
        btn_specs = {
            "btn_primary": (P.PRIMARY_CONTAINER, "#FFFFFF", "none", P.PRIMARY_CONTAINER),
            "btn_ghost": ("transparent", P.PRIMARY_CONTAINER, f"1px solid {P.PRIMARY_CONTAINER}", P.PRIMARY_CONTAINER),
            "btn_danger": (P.ERROR_CONTAINER, P.ON_ERROR_CONTAINER, "none", P.HAZARD_RED),
            "btn_danger_ghost": ("transparent", P.HAZARD_RED, f"1px solid {P.HAZARD_RED}", P.HAZARD_RED),
        }
        for key, (bg, fg, border, _) in btn_specs.items():
            btn = r.get(key)
            if btn:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {bg};
                        color: {fg};
                        border: {border};
                        border-radius: 3px;
                        font-family: "JetBrains Mono", monospace;
                        font-size: 8px;
                        font-weight: 700;
                        letter-spacing: 0.08em;
                    }}
                """)

        # Icon button
        icon_btn = r.get("btn_icon")
        if icon_btn:
            icon_btn.setStyleSheet(f"""
                QPushButton {{ color: {P.TEXT_DIM}; background: transparent; border: none;
                               border-radius: 3px; font-size: 14px; }}
                QPushButton:hover {{ background: {P.rgba(P.PRIMARY_CONTAINER, 0.15)}; }}
            """)

        # Checkbox
        cb = r.get("checkbox")
        if cb:
            cb.setStyleSheet(f"""
                QCheckBox {{ color: {P.ON_SURFACE}; spacing: 4px; }}
                QCheckBox::indicator {{
                    width: 12px; height: 12px; border-radius: 2px;
                    border: 1px solid {P.OUTLINE_VARIANT};
                    background-color: {P.rgba(P.SPACE_VOID, 0.85)};
                }}
                QCheckBox::indicator:checked {{
                    background-color: {P.PRIMARY_CONTAINER};
                    border-color: {P.PRIMARY_CONTAINER};
                }}
            """)

        # Slider
        sl = r.get("slider")
        if sl:
            sl.setStyleSheet(f"""
                QSlider::groove:horizontal {{
                    background: {P.SURFACE_CONTAINER_HIGH}; height: 3px; border-radius: 1px;
                }}
                QSlider::handle:horizontal {{
                    background: {P.PRIMARY_CONTAINER}; width: 12px; height: 12px;
                    border-radius: 6px; margin: -5px 0;
                }}
                QSlider::sub-page:horizontal {{
                    background: {P.PRIMARY_CONTAINER}; border-radius: 1px;
                }}
            """)

        # Progress bar
        prog = r.get("progress")
        if prog:
            prog.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {P.SURFACE_CONTAINER_HIGH};
                    border-radius: 2px; border: none;
                }}
                QProgressBar::chunk {{
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 {P.SECONDARY_CONTAINER},
                        stop:1 {P.PRIMARY_CONTAINER}
                    );
                    border-radius: 2px;
                }}
            """)

        # Status badges
        badge_styles = {
            "info":    (P.TEXT_DIM, P.rgba(P.TEXT_DIM, 0.1), P.rgba(P.TEXT_DIM, 0.3)),
            "success": ("#00FF88", P.rgba("#00FF88", 0.1), P.rgba("#00FF88", 0.3)),
            "warning": ("#FFAA00", P.rgba("#FFAA00", 0.1), P.rgba("#FFAA00", 0.3)),
            "error":   (P.HAZARD_RED, P.rgba(P.HAZARD_RED, 0.1), P.rgba(P.HAZARD_RED, 0.3)),
        }
        for stype, (fg, bg, border) in badge_styles.items():
            badge = r.get(f"badge_{stype}")
            if badge:
                badge.setStyleSheet(f"""
                    QLabel {{
                        color: {fg}; background-color: {bg};
                        border: 1px solid {border}; border-radius: 3px;
                        padding: 0px 4px;
                    }}
                """)

        # Text hierarchy
        for key, color in [("headline", P.ON_SURFACE), ("body", P.ON_SURFACE), ("dim", P.TEXT_DIM)]:
            lbl = r.get(key)
            if lbl:
                lbl.setStyleSheet(f"color: {color}; background: transparent; border: none;")

    # ------------------------------------------------------------------
    # Scrollable Color List
    # ------------------------------------------------------------------
    def _build_scroll(self, parent: QVBoxLayout):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")
        scroll.viewport().setStyleSheet("background-color: transparent;")

        content = QWidget()
        content.setStyleSheet("background-color: transparent;")
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setContentsMargins(0, 0, 10, 0)
        self._content_layout.setSpacing(6)

        for group_key, keys in _GROUP_ORDER:
            self._build_group(group_key, keys)

        self._content_layout.addStretch()
        scroll.setWidget(content)
        parent.addWidget(scroll)

    def _build_group(self, group_key: str, keys: list[str]):
        """Build a single color group section."""
        label = QLabel(_GROUP_LABELS.get(group_key, group_key))
        label.setFont(label_caps())
        label.setStyleSheet(
            f"color: {P.PRIMARY}; letter-spacing: 0.12em; "
            f"background: transparent; border: none; padding-top: 4px;"
        )
        self._content_layout.addWidget(label)

        divider = QWidget()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: {P.rgba(P.OUTLINE_VARIANT, 0.5)};")
        self._content_layout.addWidget(divider)

        for key in keys:
            if key not in self._defaults:
                continue
            meta = _COLOR_META.get((key))
            name = meta[0] if meta else key
            desc = meta[1] if meta else ""
            self._build_color_row(key, name, desc)

    def _build_color_row(self, key: str, friendly_name: str, description: str):
        """Build a single color row: [swatch] [name + description] [reset] [picker]."""
        row = QWidget()
        row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        row.setStyleSheet("background-color: transparent;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(4, 3, 4, 3)
        row_layout.setSpacing(8)

        # Left: name + description
        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(1)

        name_lbl = QLabel(friendly_name)
        name_lbl.setFont(font_inter(10, QFont.Weight.DemiBold))
        name_lbl.setStyleSheet(f"color: {P.ON_SURFACE}; background: transparent; border: none;")

        desc_lbl = QLabel(description)
        desc_lbl.setFont(font_inter(8))
        desc_lbl.setStyleSheet(f"color: {P.TEXT_DIM}; background: transparent; border: none;")

        text_col.addWidget(name_lbl)
        if description:
            text_col.addWidget(desc_lbl)

        row_layout.addLayout(text_col, 1)

        # Reset button (small)
        reset = QPushButton("\u21ba")
        reset.setFixedSize(22, 22)
        reset.setToolTip("Reset to default")
        default_val = self._defaults[key]
        current_val = self._pending_overrides.get(key, default_val)
        is_modified = current_val != default_val
        self._style_reset_btn(reset, is_modified)
        reset.clicked.connect(lambda checked=False, k=key: self._reset_single(k))
        self._reset_btns[key] = reset
        row_layout.addWidget(reset)

        # Color picker
        btn = ColorPickerButton(current_val)
        btn.colorChanged.connect(lambda color, k=key: self._on_color_changed(k, color))
        self._pickers[key] = btn
        row_layout.addWidget(btn)

        self._content_layout.addWidget(row)

    def _style_reset_btn(self, btn: QPushButton, modified: bool):
        if modified:
            btn.setStyleSheet(f"""
                QPushButton {{
                    color: {P.PRIMARY_CONTAINER}; font-size: 14px; border: none;
                    background: {P.rgba(P.PRIMARY_CONTAINER, 0.10)}; border-radius: 3px;
                }}
                QPushButton:hover {{ background: {P.rgba(P.PRIMARY_CONTAINER, 0.25)}; }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    color: {P.TEXT_DIM}; font-size: 14px; border: none;
                    background: transparent; border-radius: 3px;
                }}
                QPushButton:hover {{ background: {P.rgba(P.ON_SURFACE, 0.08)}; }}
            """)

    # ------------------------------------------------------------------
    # Footer Buttons
    # ------------------------------------------------------------------
    def _build_buttons(self, parent: QVBoxLayout):
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        reset_btn = QPushButton("RESET ALL")
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
        parent.addLayout(btn_layout)

    # ------------------------------------------------------------------
    # Bracket corners
    # ------------------------------------------------------------------
    def paintEvent(self, event):
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

    # ------------------------------------------------------------------
    # Drag support
    # ------------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.pos().y() < 50:
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

    # ------------------------------------------------------------------
    # Color change handlers
    # ------------------------------------------------------------------
    def _on_color_changed(self, key: str, color: str):
        self._pending_overrides[key] = color
        self._apply_live_preview()

    def _reset_single(self, key: str):
        """Reset a single color to its default."""
        self._pending_overrides.pop(key, None)
        default_val = self._defaults[key]
        self._pickers[key].setColor(default_val)
        self._style_reset_btn(self._reset_btns[key], False)
        self._apply_live_preview()

    def _apply_live_preview(self):
        from src.core.events import EventBus
        P.apply_overrides(self._pending_overrides)
        EventBus.instance().settings_changed.emit(
            "theme_palette_overrides", self._pending_overrides
        )
        self._refresh_dialog_ui()

    def _refresh_dialog_ui(self):
        self._apply_container_style()
        self._refresh_preview()
        for key, btn in self._pickers.items():
            current_val = self._pending_overrides.get(
                key, self._defaults.get(key, P.PRIMARY_CONTAINER)
            )
            btn.setColor(current_val)
            is_modified = current_val != self._defaults.get(key, "")
            self._style_reset_btn(self._reset_btns[key], is_modified)

    # ------------------------------------------------------------------
    # Reset & Save
    # ------------------------------------------------------------------
    def _reset_defaults(self):
        self._pending_overrides.clear()
        self.sm.theme_palette_overrides = {}
        from src.core.events import EventBus
        P.apply_overrides({})
        EventBus.instance().settings_changed.emit("theme_palette_overrides", {})
        self._refresh_dialog_ui()

    def _save_changes(self):
        self.sm.theme_palette_overrides = self._pending_overrides
        from src.core.events import EventBus
        EventBus.instance().settings_changed.emit(
            "theme_palette_overrides", self._pending_overrides
        )

        dlg = ConfirmDialog(
            title="RESTART REQUIRED",
            message="Theme changes have been saved. Restart now to apply all changes?",
            confirm_text="RESTART NOW",
            cancel_text="LATER",
            danger=False,
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.sm.force_save()
            import os, sys
            os.execl(sys.executable, sys.executable, *sys.argv)
        else:
            self.accept()
