from src.ui.theme import palette as P


def _scale(sizes: list[int], factor: int) -> list[int]:
    f = factor / 100.0
    return [max(1, int(s * f)) for s in sizes]


def build_stylesheet(accent_override: str | None = None, font_scale: int = 100, app_font_family: str | None = None) -> str:
    accent = accent_override or P.PRIMARY_CONTAINER

    fs = _scale([12, 10, 9, 11, 18, 8, 7], font_scale)
    fs_body, fs_caps, fs_caps_sm, fs_data, fs_head, fs_tiny, fs_micro = fs

    global_font_override = f"""
* {{
    font-family: "{app_font_family}" !important;
}}
QToolTip {{
    font-family: "Inter" !important;
}}
""" if app_font_family and app_font_family != "Default" else ""

    return f"""
QWidget {{
    background-color: {P.SPACE_VOID};
    color: {P.ON_SURFACE};
    font-family: "Inter", "Segoe UI", Arial, sans-serif;
    font-size: {fs_body}px;
    border: none;
    outline: none;
}}

QWidget:focus {{
    outline: none;
}}

QMainWindow, QDialog {{
    background-color: {P.SPACE_VOID};
}}

QPushButton[class="primary"] {{
    background-color: {accent};
    color: #FFFFFF;
    font-family: "JetBrains Mono", "Consolas", monospace;
    font-size: {fs_caps}px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    border: none;
    border-radius: 3px;
    padding: 5px 14px;
    min-height: 28px;
}}

QPushButton[class="primary"]:hover {{
    background-color: {P.PRIMARY};
    color: {P.ON_PRIMARY};
}}

QPushButton[class="primary"]:pressed {{
    background-color: {P.ON_PRIMARY_FIXED_VARIANT};
    color: #FFFFFF;
}}

QPushButton[class="primary"]:disabled {{
    background-color: {P.SURFACE_CONTAINER_HIGH};
    color: {P.TEXT_DIM};
}}

QPushButton[class="ghost"] {{
    background-color: transparent;
    color: {accent};
    font-family: "JetBrains Mono", "Consolas", monospace;
    font-size: {fs_caps}px;
    font-weight: 700;
    letter-spacing: 0.12em;
    border: 1px solid {accent};
    border-radius: 3px;
    padding: 4px 12px;
    min-height: 26px;
}}

QPushButton[class="ghost"]:hover {{
    background-color: rgba(0, 170, 255, 0.10);
    border-color: {P.PRIMARY};
    color: {P.PRIMARY};
}}

QPushButton[class="ghost"]:pressed {{
    background-color: rgba(0, 170, 255, 0.20);
}}

QPushButton[class="ghost"]:disabled {{
    border-color: {P.OUTLINE_VARIANT};
    color: {P.TEXT_DIM};
}}

QPushButton[class="icon"] {{
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 3px;
}}

QPushButton[class="icon"]:hover {{
    background-color: rgba(0, 170, 255, 0.15);
}}

QPushButton[class="icon"]:pressed {{
    background-color: rgba(0, 170, 255, 0.30);
}}

QPushButton[class="icon"][checked="true"] {{
    background-color: rgba(0, 170, 255, 0.20);
    border: 1px solid rgba(0, 170, 255, 0.40);
}}

QPushButton[class="danger"] {{
    background-color: {P.ERROR_CONTAINER};
    color: {P.ON_ERROR_CONTAINER};
    font-family: "JetBrains Mono", monospace;
    font-size: {fs_caps}px;
    font-weight: 700;
    letter-spacing: 0.08em;
    border: none;
    border-radius: 3px;
    padding: 4px 12px;
    min-height: 26px;
}}

QPushButton[class="danger"]:hover {{
    background-color: {P.HAZARD_RED};
    color: #FFFFFF;
}}

QPushButton[class="danger-ghost"] {{
    background-color: transparent;
    color: {P.HAZARD_RED};
    font-family: "JetBrains Mono", monospace;
    font-size: {fs_caps}px;
    font-weight: 700;
    letter-spacing: 0.12em;
    border: 1px solid {P.HAZARD_RED};
    border-radius: 3px;
    padding: 4px 12px;
    min-height: 26px;
}}

QPushButton[class="danger-ghost"]:hover {{
    background-color: rgba(255, 68, 68, 0.10);
    border-color: {P.ERROR_CONTAINER};
    color: {P.ERROR_CONTAINER};
}}

QPushButton[class="danger-ghost"]:pressed {{
    background-color: rgba(255, 68, 68, 0.20);
}}

QPushButton[class="danger-ghost"]:disabled {{
    border-color: {P.OUTLINE_VARIANT};
    color: {P.TEXT_DIM};
}}

QLineEdit {{
    background-color: rgba(5, 11, 15, 0.85);
    color: {P.ON_SURFACE};
    font-family: "Inter", "Segoe UI", Arial, sans-serif;
    font-size: {fs_body}px;
    border: 1px solid {P.OUTLINE_VARIANT};
    border-radius: 4px;
    padding: 5px 10px;
    selection-background-color: {accent};
    selection-color: #FFFFFF;
}}

QLineEdit:hover {{
    border-color: {P.OUTLINE};
}}

QLineEdit:focus {{
    border-color: {accent};
    background-color: rgba(0, 10, 20, 0.90);
}}

QLineEdit:disabled {{
    background-color: {P.SURFACE_CONTAINER};
    color: {P.TEXT_DIM};
    border-color: {P.OUTLINE_VARIANT};
}}

QLineEdit[readOnly="true"] {{
    background-color: {P.SURFACE_CONTAINER_LOW};
    border-color: {P.OUTLINE_VARIANT};
}}

QTextEdit, QPlainTextEdit {{
    background-color: rgba(5, 11, 15, 0.85);
    color: {P.ON_SURFACE};
    font-family: "Inter", "Segoe UI", Arial, sans-serif;
    font-size: {fs_body}px;
    border: 1px solid {P.OUTLINE_VARIANT};
    border-radius: 4px;
    padding: 6px;
    selection-background-color: {accent};
}}

QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {accent};
}}

QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: rgba(0, 170, 255, 0.18);
    border-radius: 3px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background: rgba(0, 170, 255, 0.38);
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    border: none;
    background: none;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background: rgba(0, 170, 255, 0.18);
    border-radius: 3px;
    min-width: 20px;
}}

QScrollBar::handle:horizontal:hover {{
    background: rgba(0, 170, 255, 0.38);
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    border: none;
    background: none;
}}

QListWidget {{
    background-color: transparent;
    border: none;
    padding: 2px;
    outline: none;
}}

QListWidget::item {{
    background-color: transparent;
    color: {P.ON_SURFACE};
    font-family: "Inter", "Segoe UI", Arial, sans-serif;
    font-size: {fs_body}px;
    padding: 7px 10px;
    border-radius: 3px;
    border: none;
}}

QListWidget::item:hover {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(79, 142, 255, 0.18),
        stop:1 rgba(79, 142, 255, 0.00)
    );
}}

QListWidget::item:selected {{
    background: rgba(0, 170, 255, 0.14);
    color: {P.PRIMARY};
    border-left: 2px solid {accent};
    padding-left: 8px;
}}

QComboBox {{
    background-color: rgba(5, 11, 15, 0.85);
    color: {P.ON_SURFACE};
    font-family: "Inter", "Segoe UI", Arial, sans-serif;
    font-size: {fs_caps_sm}px;
    border: 1px solid {P.OUTLINE_VARIANT};
    border-radius: 3px;
    padding: 4px 10px;
    min-height: 26px;
}}

QComboBox:hover {{
    border-color: {P.OUTLINE};
}}

QComboBox:focus {{
    border-color: {accent};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox::down-arrow {{
    width: 8px;
    height: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {P.SURFACE_CONTAINER};
    color: {P.ON_SURFACE};
    border: 1px solid {P.GLASS_BORDER};
    border-radius: 3px;
    selection-background-color: rgba(0, 170, 255, 0.20);
    selection-color: {P.PRIMARY};
    padding: 2px;
    outline: none;
}}

QSlider::groove:horizontal {{
    background: {P.SURFACE_CONTAINER_HIGH};
    height: 3px;
    border-radius: 1px;
}}

QSlider::handle:horizontal {{
    background: {accent};
    width: 13px;
    height: 13px;
    border-radius: 6px;
    margin: -5px 0;
}}

QSlider::handle:horizontal:hover {{
    background: {P.PRIMARY};
}}

QSlider::sub-page:horizontal {{
    background: {accent};
    border-radius: 1px;
}}

QCheckBox {{
    color: {P.ON_SURFACE};
    font-family: "Inter", "Segoe UI", Arial, sans-serif;
    font-size: {fs_body}px;
    spacing: 6px;
}}

QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border-radius: 2px;
    border: 1px solid {P.OUTLINE_VARIANT};
    background-color: rgba(5, 11, 15, 0.85);
}}

QCheckBox::indicator:checked {{
    background-color: {accent};
    border-color: {accent};
}}

QCheckBox::indicator:hover {{
    border-color: {P.OUTLINE};
}}

QLabel {{
    color: {P.ON_SURFACE};
    background: transparent;
}}

QLabel[class="label-caps"] {{
    font-family: "JetBrains Mono", "Consolas", monospace;
    font-size: {fs_caps_sm}px;
    font-weight: 700;
    color: {P.TEXT_DIM};
    letter-spacing: 0.12em;
}}

QLabel[class="data-point"] {{
    font-family: "JetBrains Mono", "Consolas", monospace;
    font-size: {fs_data}px;
    font-weight: 500;
    color: {P.ON_SURFACE};
}}

QLabel[class="headline"] {{
    font-family: "Sora", "Segoe UI", Arial, sans-serif;
    font-size: {fs_head}px;
    font-weight: 600;
    color: {P.ON_SURFACE};
}}

QLabel[class="status-ok"] {{
    color: #00FF88;
    font-family: "JetBrains Mono", monospace;
    font-size: {fs_caps_sm}px;
    font-weight: 700;
}}

QLabel[class="status-error"] {{
    color: {P.HAZARD_RED};
    font-family: "JetBrains Mono", monospace;
    font-size: {fs_caps_sm}px;
    font-weight: 700;
}}

QSplitter::handle {{
    background-color: {P.OUTLINE_VARIANT};
    width: 1px;
    height: 1px;
}}

QSplitter::handle:hover {{
    background-color: {accent};
}}

QToolTip {{
    background-color: {P.SURFACE_CONTAINER_HIGH};
    color: {P.ON_SURFACE};
    border: 1px solid rgba(0, 170, 255, 0.25);
    border-radius: 3px;
    font-family: "JetBrains Mono", monospace;
    font-size: {fs_caps_sm}px;
    padding: 3px 7px;
}}

QTabBar::tab {{
    background-color: transparent;
    color: {P.TEXT_DIM};
    font-family: "JetBrains Mono", monospace;
    font-size: {fs_caps_sm}px;
    font-weight: 700;
    letter-spacing: 0.10em;
    padding: 6px 12px;
    border: none;
    border-bottom: 2px solid transparent;
}}

QTabBar::tab:selected {{
    color: {P.PRIMARY};
    border-bottom: 2px solid {accent};
}}

QTabBar::tab:hover {{
    color: {P.ON_SURFACE};
    background-color: rgba(0, 170, 255, 0.08);
}}

QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: {P.OUTLINE_VARIANT};
    background-color: {P.OUTLINE_VARIANT};
    max-height: 1px;
    border: none;
}}

QScrollArea {{
    background: transparent;
    border: none;
}}

QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

QProgressBar {{
    background-color: {P.SURFACE_CONTAINER_HIGH};
    border-radius: 2px;
    height: 3px;
    text-align: center;
    color: transparent;
}}

QProgressBar::chunk {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {P.SECONDARY_CONTAINER},
        stop:1 {accent}
    );
    border-radius: 2px;
}}
""" + global_font_override
