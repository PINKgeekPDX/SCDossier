"""
src/ui/theme/stylesheet.py
Global QSS stylesheet for SC Dossier — Aegis Liquid Interface.

Apply via: QApplication.instance().setStyleSheet(build_stylesheet())
"""

from src.ui.theme import palette as P


def build_stylesheet(accent_override: str | None = None) -> str:
    """
    Build and return the global QSS string.

    Args:
        accent_override: Optional hex color to replace the primary blue accent.
    """
    accent = accent_override or P.PRIMARY_CONTAINER  # #00AAFF

    return f"""
/* =========================================================
   SC Dossier — Aegis Liquid Interface QSS
   ========================================================= */

/* ---------------------------------------------------------
   Base Widget
   --------------------------------------------------------- */
QWidget {{
    background-color: {P.SPACE_VOID};
    color: {P.ON_SURFACE};
    font-family: "Inter", "Segoe UI", Arial, sans-serif;
    font-size: 14px;
    border: none;
    outline: none;
}}

QWidget:focus {{
    outline: none;
}}

/* ---------------------------------------------------------
   Main Window / Top-level
   --------------------------------------------------------- */
QMainWindow, QDialog {{
    background-color: {P.SPACE_VOID};
}}

/* ---------------------------------------------------------
   QPushButton — Primary (solid blue)
   --------------------------------------------------------- */
QPushButton[class="primary"] {{
    background-color: {accent};
    color: #FFFFFF;
    font-family: "JetBrains Mono", "Consolas", monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    border: none;
    border-radius: 4px;
    padding: 8px 20px;
    min-height: 36px;
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

/* ---------------------------------------------------------
   QPushButton — Ghost (bracketed border)
   --------------------------------------------------------- */
QPushButton[class="ghost"] {{
    background-color: transparent;
    color: {accent};
    font-family: "JetBrains Mono", "Consolas", monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.15em;
    border: 1px solid {accent};
    border-radius: 4px;
    padding: 7px 18px;
    min-height: 34px;
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

/* ---------------------------------------------------------
   QPushButton — Icon Only (toolbar / titlebar buttons)
   --------------------------------------------------------- */
QPushButton[class="icon"] {{
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 4px;
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

/* ---------------------------------------------------------
   QPushButton — Danger (destructive)
   --------------------------------------------------------- */
QPushButton[class="danger"] {{
    background-color: {P.ERROR_CONTAINER};
    color: {P.ON_ERROR_CONTAINER};
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.10em;
    border: none;
    border-radius: 4px;
    padding: 7px 18px;
    min-height: 34px;
}}

QPushButton[class="danger"]:hover {{
    background-color: {P.HAZARD_RED};
    color: #FFFFFF;
}}

/* ---------------------------------------------------------
   QLineEdit — Search / Input
   --------------------------------------------------------- */
QLineEdit {{
    background-color: rgba(5, 11, 15, 0.85);
    color: {P.ON_SURFACE};
    font-family: "Inter", "Segoe UI", Arial, sans-serif;
    font-size: 14px;
    border: 1px solid {P.OUTLINE_VARIANT};
    border-radius: 6px;
    padding: 8px 12px;
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

/* ---------------------------------------------------------
   QTextEdit / QPlainTextEdit
   --------------------------------------------------------- */
QTextEdit, QPlainTextEdit {{
    background-color: rgba(5, 11, 15, 0.85);
    color: {P.ON_SURFACE};
    font-family: "Inter", "Segoe UI", Arial, sans-serif;
    font-size: 14px;
    border: 1px solid {P.OUTLINE_VARIANT};
    border-radius: 6px;
    padding: 8px;
    selection-background-color: {accent};
}}

QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {accent};
}}

/* ---------------------------------------------------------
   QScrollBar — Vertical (6px, minimal)
   --------------------------------------------------------- */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: rgba(0, 170, 255, 0.20);
    border-radius: 4px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: rgba(0, 170, 255, 0.40);
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    border: none;
    background: none;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

/* ---------------------------------------------------------
   QScrollBar — Horizontal
   --------------------------------------------------------- */
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background: rgba(0, 170, 255, 0.20);
    border-radius: 4px;
    min-width: 24px;
}}

QScrollBar::handle:horizontal:hover {{
    background: rgba(0, 170, 255, 0.40);
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    border: none;
    background: none;
}}

/* ---------------------------------------------------------
   QListWidget
   --------------------------------------------------------- */
QListWidget {{
    background-color: transparent;
    border: none;
    padding: 4px;
    outline: none;
}}

QListWidget::item {{
    background-color: transparent;
    color: {P.ON_SURFACE};
    font-family: "Inter", "Segoe UI", Arial, sans-serif;
    font-size: 14px;
    padding: 10px 12px;
    border-radius: 4px;
    border: none;
}}

QListWidget::item:hover {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(79, 142, 255, 0.20),
        stop:1 rgba(79, 142, 255, 0.00)
    );
}}

QListWidget::item:selected {{
    background: rgba(0, 170, 255, 0.15);
    color: {P.PRIMARY};
    border-left: 2px solid {accent};
    padding-left: 10px;
}}

/* ---------------------------------------------------------
   QComboBox
   --------------------------------------------------------- */
QComboBox {{
    background-color: rgba(5, 11, 15, 0.85);
    color: {P.ON_SURFACE};
    font-family: "Inter", "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    border: 1px solid {P.OUTLINE_VARIANT};
    border-radius: 4px;
    padding: 6px 12px;
    min-height: 32px;
}}

QComboBox:hover {{
    border-color: {P.OUTLINE};
}}

QComboBox:focus {{
    border-color: {accent};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox::down-arrow {{
    width: 10px;
    height: 10px;
}}

QComboBox QAbstractItemView {{
    background-color: {P.SURFACE_CONTAINER};
    color: {P.ON_SURFACE};
    border: 1px solid {P.GLASS_BORDER};
    border-radius: 4px;
    selection-background-color: rgba(0, 170, 255, 0.20);
    selection-color: {P.PRIMARY};
    padding: 4px;
    outline: none;
}}

/* ---------------------------------------------------------
   QSlider
   --------------------------------------------------------- */
QSlider::groove:horizontal {{
    background: {P.SURFACE_CONTAINER_HIGH};
    height: 4px;
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background: {accent};
    width: 16px;
    height: 16px;
    border-radius: 8px;
    margin: -6px 0;
}}

QSlider::handle:horizontal:hover {{
    background: {P.PRIMARY};
}}

QSlider::sub-page:horizontal {{
    background: {accent};
    border-radius: 2px;
}}

/* ---------------------------------------------------------
   QCheckBox
   --------------------------------------------------------- */
QCheckBox {{
    color: {P.ON_SURFACE};
    font-family: "Inter", "Segoe UI", Arial, sans-serif;
    font-size: 14px;
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 3px;
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

/* ---------------------------------------------------------
   QLabel Variants (by objectName)
   --------------------------------------------------------- */
QLabel {{
    color: {P.ON_SURFACE};
    background: transparent;
}}

QLabel[class="label-caps"] {{
    font-family: "JetBrains Mono", "Consolas", monospace;
    font-size: 11px;
    font-weight: 700;
    color: {P.TEXT_DIM};
    letter-spacing: 0.15em;
}}

QLabel[class="data-point"] {{
    font-family: "JetBrains Mono", "Consolas", monospace;
    font-size: 13px;
    font-weight: 500;
    color: {P.ON_SURFACE};
}}

QLabel[class="headline"] {{
    font-family: "Sora", "Segoe UI", Arial, sans-serif;
    font-size: 24px;
    font-weight: 600;
    color: {P.ON_SURFACE};
}}

QLabel[class="status-ok"] {{
    color: #00FF88;
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    font-weight: 700;
}}

QLabel[class="status-error"] {{
    color: {P.HAZARD_RED};
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    font-weight: 700;
}}

/* ---------------------------------------------------------
   QSplitter
   --------------------------------------------------------- */
QSplitter::handle {{
    background-color: {P.OUTLINE_VARIANT};
    width: 1px;
    height: 1px;
}}

QSplitter::handle:hover {{
    background-color: {accent};
}}

/* ---------------------------------------------------------
   QToolTip
   --------------------------------------------------------- */
QToolTip {{
    background-color: {P.SURFACE_CONTAINER_HIGH};
    color: {P.ON_SURFACE};
    border: 1px solid rgba(0, 170, 255, 0.30);
    border-radius: 4px;
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    padding: 4px 8px;
}}

/* ---------------------------------------------------------
   QTabWidget / QTabBar (for any native tabs if used)
   --------------------------------------------------------- */
QTabBar::tab {{
    background-color: transparent;
    color: {P.TEXT_DIM};
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.10em;
    padding: 8px 16px;
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

/* ---------------------------------------------------------
   QFrame separators
   --------------------------------------------------------- */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: {P.OUTLINE_VARIANT};
    background-color: {P.OUTLINE_VARIANT};
    max-height: 1px;
    border: none;
}}

/* ---------------------------------------------------------
   QScrollArea
   --------------------------------------------------------- */
QScrollArea {{
    background: transparent;
    border: none;
}}

QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

/* ---------------------------------------------------------
   QProgressBar
   --------------------------------------------------------- */
QProgressBar {{
    background-color: {P.SURFACE_CONTAINER_HIGH};
    border-radius: 3px;
    height: 4px;
    text-align: center;
    color: transparent;
}}

QProgressBar::chunk {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {P.SECONDARY_CONTAINER},
        stop:1 {accent}
    );
    border-radius: 3px;
}}
"""
