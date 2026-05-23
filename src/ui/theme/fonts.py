"""
src/ui/theme/fonts.py
Font registration for SC Dossier — Sora, Inter, JetBrains Mono.

Fonts must be bundled in src/assets/fonts/ as .ttf files.
Call register_fonts() once after QApplication is created.
"""

import logging
from pathlib import Path

from PyQt6.QtGui import QFont, QFontDatabase

log = logging.getLogger(__name__)

# Font family name strings (as registered in Qt)
FONT_SORA = "Sora"
FONT_INTER = "Inter"
FONT_MONO = "JetBrains Mono"

# Fallback chains
FONT_SORA_FALLBACK = "Segoe UI, Arial, sans-serif"
FONT_INTER_FALLBACK = "Segoe UI, Arial, sans-serif"
FONT_MONO_FALLBACK = "Consolas, Courier New, monospace"

_FONTS_DIR = Path(__file__).parent.parent.parent / "assets" / "fonts"

_FONT_FILES = [
    # Sora
    "Sora-Regular.ttf",
    "Sora-Medium.ttf",
    "Sora-SemiBold.ttf",
    "Sora-Bold.ttf",
    # Inter
    "Inter-Regular.ttf",
    "Inter-Medium.ttf",
    "Inter-SemiBold.ttf",
    "Inter-Bold.ttf",
    # JetBrains Mono
    "JetBrainsMono-Regular.ttf",
    "JetBrainsMono-Medium.ttf",
    "JetBrainsMono-Bold.ttf",
]

_registered = False


def register_fonts() -> None:
    """
    Register all bundled font files with Qt's font database.
    Must be called after QApplication is created.
    Falls back gracefully if font files are missing.
    """
    global _registered
    if _registered:
        return
    _registered = True

    for filename in _FONT_FILES:
        font_path = _FONTS_DIR / filename
        if font_path.exists():
            fid = QFontDatabase.addApplicationFont(str(font_path))
            if fid == -1:
                log.warning("Failed to register font: %s", filename)
            else:
                log.debug("Registered font: %s (id=%d)", filename, fid)
        else:
            log.warning("Font file not found: %s — using system fallback", font_path)


# ---------------------------------------------------------------------------
# Font Constructor Helpers
# ---------------------------------------------------------------------------

def font_sora(size: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    """Return a Sora font of the given size and weight."""
    f = QFont(FONT_SORA)
    f.setPointSize(size)
    f.setWeight(weight)
    return f


def font_inter(size: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    """Return an Inter font of the given size and weight."""
    f = QFont(FONT_INTER)
    f.setPointSize(size)
    f.setWeight(weight)
    return f


def font_mono(size: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    """Return a JetBrains Mono font of the given size and weight."""
    f = QFont(FONT_MONO)
    f.setPointSize(size)
    f.setWeight(weight)
    return f


# ---------------------------------------------------------------------------
# Type Scale Presets
# ---------------------------------------------------------------------------

def headline_xl() -> QFont:
    """headline-xl: Sora 32pt Bold"""
    return font_sora(32, QFont.Weight.Bold)


def headline_lg() -> QFont:
    """headline-lg: Sora 24pt SemiBold"""
    return font_sora(24, QFont.Weight.DemiBold)


def headline_md() -> QFont:
    """headline-md: Sora 18pt SemiBold"""
    return font_sora(18, QFont.Weight.DemiBold)


def body_md() -> QFont:
    """body-md: Inter 14pt Regular"""
    return font_inter(14)


def data_point() -> QFont:
    """data-point: JetBrains Mono 13pt Medium"""
    return font_mono(13, QFont.Weight.Medium)


def label_caps() -> QFont:
    """label-caps: JetBrains Mono 11pt Bold"""
    return font_mono(11, QFont.Weight.Bold)
