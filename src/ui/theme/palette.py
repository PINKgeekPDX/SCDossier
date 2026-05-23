"""
src/ui/theme/palette.py
Aegis Liquid Interface — all color constants from DESIGN.md.

Use only these constants in widget/stylesheet code. No hardcoded hex values elsewhere.
"""

# ---------------------------------------------------------------------------
# Base Surfaces
# ---------------------------------------------------------------------------
SPACE_VOID = "#050B0F"           # Absolute background — deepest layer
SURFACE = "#031521"              # Primary surface
SURFACE_DIM = "#031521"          # Dimmed surface
SURFACE_BRIGHT = "#2A3B48"       # Elevated surface
SURFACE_CONTAINER_LOWEST = "#00101B"
SURFACE_CONTAINER_LOW = "#0A1D29"
SURFACE_CONTAINER = "#0F212E"    # Standard glass card background
SURFACE_CONTAINER_HIGH = "#1A2C38"
SURFACE_CONTAINER_HIGHEST = "#253744"
BACKGROUND = "#031521"

# ---------------------------------------------------------------------------
# Text Colors
# ---------------------------------------------------------------------------
ON_SURFACE = "#D2E5F6"           # Primary readable text
ON_SURFACE_VARIANT = "#BEC7D3"   # Secondary text
TEXT_DIM = "#A8B3BD"             # Tertiary / metadata text
INVERSE_SURFACE = "#D2E5F6"
INVERSE_ON_SURFACE = "#21323F"

# ---------------------------------------------------------------------------
# Primary Blue (Interactive / Glow)
# ---------------------------------------------------------------------------
PRIMARY = "#93CCFF"              # Primary accent color / text highlight
ON_PRIMARY = "#003351"
PRIMARY_CONTAINER = "#00AAFF"    # Active blue — glow, borders, interactive states
ON_PRIMARY_CONTAINER = "#003C5D"
INVERSE_PRIMARY = "#006398"
PRIMARY_FIXED = "#CCE5FF"
PRIMARY_FIXED_DIM = "#93CCFF"
ON_PRIMARY_FIXED = "#001D31"
ON_PRIMARY_FIXED_VARIANT = "#004B73"

# ---------------------------------------------------------------------------
# Secondary Blue
# ---------------------------------------------------------------------------
SECONDARY = "#AEC6FF"
ON_SECONDARY = "#002E6A"
SECONDARY_CONTAINER = "#4F8EFF"
ON_SECONDARY_CONTAINER = "#00275E"
SECONDARY_FIXED = "#D8E2FF"
SECONDARY_FIXED_DIM = "#AEC6FF"
ON_SECONDARY_FIXED = "#001A42"
ON_SECONDARY_FIXED_VARIANT = "#004396"

# ---------------------------------------------------------------------------
# Tertiary
# ---------------------------------------------------------------------------
TERTIARY = "#98CBFF"
ON_TERTIARY = "#003354"
TERTIARY_CONTAINER = "#4EA8F2"
ON_TERTIARY_CONTAINER = "#003B60"
TERTIARY_FIXED = "#CEE5FF"
TERTIARY_FIXED_DIM = "#98CBFF"
ON_TERTIARY_FIXED = "#001D33"
ON_TERTIARY_FIXED_VARIANT = "#004A77"

# ---------------------------------------------------------------------------
# Error / Hazard
# ---------------------------------------------------------------------------
ERROR = "#FFB4AB"
ON_ERROR = "#690005"
ERROR_CONTAINER = "#93000A"
ON_ERROR_CONTAINER = "#FFDAD6"
HAZARD_RED = "#FF3B3B"           # Errors, warnings, destructive action highlights

# ---------------------------------------------------------------------------
# Outline / Dividers
# ---------------------------------------------------------------------------
OUTLINE = "#88929D"
OUTLINE_VARIANT = "#3E4851"
SURFACE_TINT = "#93CCFF"
SURFACE_VARIANT = "#253744"

# ---------------------------------------------------------------------------
# Glass Effect Colors (rgba strings for QSS / QPainter)
# ---------------------------------------------------------------------------
GLASS_BORDER = "rgba(0, 170, 255, 0.3)"         # Standard glass card border
GLASS_BORDER_SUBTLE = "rgba(0, 170, 255, 0.15)" # Subtle border (title bar, etc.)
GLASS_BG = "rgba(10, 29, 41, 0.4)"              # Glass card background
GLASS_BG_DARK = "rgba(2, 13, 20, 0.85)"         # Status bar, toolbar bg
GLOW_BLUE = "rgba(0, 170, 255, 0.2)"            # Hover glow / nav highlight
GLOW_BLUE_STRONG = "rgba(0, 170, 255, 0.4)"     # Focus glow / active state
SCANLINE_OVERLAY = "rgba(0, 170, 255, 0.06)"    # Subtle scanline texture

# ---------------------------------------------------------------------------
# Navigation Sidebar
# ---------------------------------------------------------------------------
NAV_ACTIVE_BG = "rgba(0, 170, 255, 0.1)"
NAV_ACTIVE_BORDER = "rgba(0, 170, 255, 0.2)"
NAV_HOVER_GRADIENT_START = "rgba(79, 142, 255, 0.2)"
NAV_HOVER_GRADIENT_END = "rgba(79, 142, 255, 0.0)"

# ---------------------------------------------------------------------------
# Scrollbar
# ---------------------------------------------------------------------------
SCROLLBAR_TRACK = "rgba(0, 0, 0, 0.0)"
SCROLLBAR_THUMB = "rgba(0, 170, 255, 0.2)"
SCROLLBAR_THUMB_HOVER = "rgba(0, 170, 255, 0.4)"

# ---------------------------------------------------------------------------
# Corner Bracket Ornament
# ---------------------------------------------------------------------------
BRACKET_COLOR = "#00AAFF"        # Tech-bracket corner color
BRACKET_SIZE = 8                 # px — L-shape bracket arm length
BRACKET_WIDTH = 2                # px — bracket line width

# ---------------------------------------------------------------------------
# Utility: hex to RGBA string
# ---------------------------------------------------------------------------
def rgba(hex_color: str, alpha: float) -> str:
    """Convert a 6-digit hex color + alpha float to rgba() string for QSS."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha:.2f})"
