"""
src/ui/toolbar/overlay_toolbar.py
OverlayToolbar — always-on-top, frameless, screen-edge-snapping HUD toolbar.

Design: Sci-fi chamfered-panel HUD with:
  - 8-sided chamfered body (angular, not rounded — real sci-fi shape language)
  - Animated energy spine along the screen-edge face
  - Periodic scan-sweep line (QPropertyAnimation)
  - Slow sine-wave border pulse
  - Hexagonal icon buttons with animated glow ring on hover
  - Tick-mark center separator
  - Corner bracket ornaments, edge-aware layout

Functionality (unchanged):
  - Drag to reposition; snaps to nearest screen edge on release
  - Saves/restores position via SettingsManager
  - Horizontal orientation for TOP/BOTTOM, vertical for LEFT/RIGHT
  - Configurable opacity via set_opacity()
"""

import logging
import math
import os

from PyQt6.QtCore import (
    Qt, QPoint, QPointF, QRectF, QRect, QTimer,
    QPropertyAnimation, QEasingCurve,
    pyqtSignal, pyqtProperty,
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush,
    QLinearGradient, QRadialGradient,
    QPainterPath,
)
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QApplication

from src.ui.theme import palette as P
from src.ui.theme.icon_utils import load_icon
from src.app.constants import ScreenEdge

log = logging.getLogger(__name__)

# ── Geometry ──────────────────────────────────────────────────────────────────
TOOLBAR_THICKNESS = 54    # short axis  (px)
TOOLBAR_LENGTH    = 110   # long axis   (px)
BTN_HEX_R        = 17    # hex circumradius — button outer ring
BTN_ICON_SIZE    = 18    # icon size inside hex
CHAMFER          = 9     # 45° corner-cut depth (px) — the sci-fi look
_PAD             = 6     # layout margin (px)
_SPACING         = 4     # spacing between buttons (px)

# ── Palette ───────────────────────────────────────────────────────────────────
_BG          = QColor(2,  11,  19, 238)    # near-void fill
_BORDER_DIM  = QColor(0, 160, 220,  45)    # idle border
_BORDER_HOT  = QColor(0, 200, 255, 110)    # pulse peak border
_SPINE_CORE  = QColor(0, 220, 255, 220)    # energy spine bright line
_SPINE_GLOW  = QColor(0, 180, 255,  55)    # energy spine soft halo
_SHEEN_START = QColor(0, 170, 255,  22)    # inner surface sheen (edge side)
_SEP         = QColor(0, 170, 255,  38)    # separator line
_TICK        = QColor(0, 210, 255,  80)    # tick-marks on separator
_SCAN_CORE   = QColor(190, 240, 255, 175)  # scan-sweep bright centre
_SCAN_HALO   = QColor( 80, 200, 255,  55)  # scan-sweep soft halo
_STRIPE      = QColor(0, 170, 255,   6)    # background scanline texture
_BRAK        = QColor(0, 220, 255, 150)    # corner bracket

_ICONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "assets", "icons",
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _chamfer_path(x: float, y: float, w: float, h: float, c: float) -> QPainterPath:
    """8-sided chamfered rectangle — 45° cuts at every corner."""
    path = QPainterPath()
    path.moveTo(x + c,     y)
    path.lineTo(x + w - c, y)
    path.lineTo(x + w,     y + c)
    path.lineTo(x + w,     y + h - c)
    path.lineTo(x + w - c, y + h)
    path.lineTo(x + c,     y + h)
    path.lineTo(x,         y + h - c)
    path.lineTo(x,         y + c)
    path.closeSubpath()
    return path


def _hex_path(cx: float, cy: float, r: float) -> QPainterPath:
    """Flat-top regular hexagon centred at (cx, cy), circumradius r."""
    path = QPainterPath()
    for i in range(6):
        angle = math.radians(60 * i - 30)       # flat-top orientation
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        path.moveTo(x, y) if i == 0 else path.lineTo(x, y)
    path.closeSubpath()
    return path


# ── Hex Button ────────────────────────────────────────────────────────────────

class ToolbarButton(QWidget):
    """
    Hexagonal sci-fi button.

    Fully custom-painted: hex clip path, animated glow ring, icon.
    Uses QPropertyAnimation on a pyqtProperty for the hover glow.
    """

    clicked = pyqtSignal()

    def __init__(
        self,
        icon_path: str,
        tooltip: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._icon_path = icon_path
        self._icon      = None
        self._pressed   = False
        self._glow      = 0.0

        # Button bounding box: hex fits in a square of side = 2*r + margin
        sz = BTN_HEX_R * 2 + 4
        self.setFixedSize(sz, sz)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        self._anim = QPropertyAnimation(self, b"_glow_prop", self)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._load_icon()

    # ── pyqtProperty (animatable) ─────────────────────────────────────────────
    def _get_glow(self) -> float:
        return self._glow

    def _set_glow(self, v: float) -> None:
        self._glow = float(v)
        self.update()

    _glow_prop = pyqtProperty(float, fget=_get_glow, fset=_set_glow)

    # ── Internal ──────────────────────────────────────────────────────────────
    def _load_icon(self) -> None:
        icon = load_icon(self._icon_path, BTN_ICON_SIZE)
        self._icon = icon if not icon.isNull() else None

    def _animate(self, target: float) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._glow)
        self._anim.setEndValue(target)
        self._anim.start()

    # ── Events ────────────────────────────────────────────────────────────────
    def enterEvent(self, e) -> None:
        self._animate(1.0)

    def leaveEvent(self, e) -> None:
        self._pressed = False
        self._animate(0.0)

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self.update()
            e.accept()

    def mouseReleaseEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton and self._pressed:
            self._pressed = False
            self.update()
            if self.rect().contains(e.position().toPoint()):
                self.clicked.emit()
            e.accept()

    # ── Paint ─────────────────────────────────────────────────────────────────
    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        g  = self._glow
        w  = float(self.width())
        h  = float(self.height())
        cx = w / 2
        cy = h / 2
        r  = float(BTN_HEX_R)

        hp = _hex_path(cx, cy, r)

        # ── 1. Base fill ──────────────────────────────────────────────────────
        if self._pressed:
            fill = QColor(0, 210, 255, 120)
        else:
            fill = QColor(3, 16, 28, int(195 + 45 * g))
        p.fillPath(hp, fill)

        # ── 2. Radial glow on hover ───────────────────────────────────────────
        if g > 0.01:
            rg = QRadialGradient(cx, cy, r)
            rg.setColorAt(0.0, QColor(0, 160, 255, int(80 * g)))
            rg.setColorAt(0.55, QColor(0, 110, 200, int(35 * g)))
            rg.setColorAt(1.0,  QColor(0,   0,   0,   0))
            p.fillPath(hp, QBrush(rg))

        # ── 3. Hex ring ───────────────────────────────────────────────────────
        if self._pressed:
            ring_c = QColor(0, 240, 255, 255)
            ring_w = 2.0
        elif g > 0.01:
            ring_c = QColor(0, int(175 + 65 * g), 255, int(95 + 155 * g))
            ring_w = 1.2 + 0.8 * g
        else:
            ring_c = QColor(0, 170, 255, 55)
            ring_w = 1.0

        p.setPen(QPen(ring_c, ring_w))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(hp)

        # ── 4. Outer ghost ring on hover ──────────────────────────────────────
        if g > 0.15:
            ghost = _hex_path(cx, cy, r + 2.5 * g)
            p.setPen(QPen(QColor(0, 190, 255, int(38 * g)), 1.2))
            p.drawPath(ghost)

        # ── 5. Icon ───────────────────────────────────────────────────────────
        off = int((self.width() - BTN_ICON_SIZE) / 2)
        if self._icon:
            self._icon.paint(p, off, off, BTN_ICON_SIZE, BTN_ICON_SIZE)
        else:
            p.setPen(QPen(QColor(0, 210, 255, 200)))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "◈")

        p.end()


# ── Overlay Toolbar ───────────────────────────────────────────────────────────

class OverlayToolbar(QWidget):
    """
    Always-on-top edge-snapping HUD toolbar — sci-fi chamfered panel.

    Signals:
        expand_requested():   Emitted when expand button is clicked.
        capture_requested():  Emitted when capture button is clicked.
    """

    expand_requested  = pyqtSignal()
    capture_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setMouseTracking(True)

        self._edge               = ScreenEdge.LEFT
        self._drag_active        = False
        self._drag_start_pos     = QPoint()
        self._drag_start_window  = QPoint()

        # ── Slow sine-wave border pulse ───────────────────────────────────────
        self._pulse_phase = 0.0
        self._pulse       = 50.0
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._tick_pulse)
        self._pulse_timer.start(33)   # ~30 fps

        # ── Periodic scan sweep ───────────────────────────────────────────────
        self._scan_pos     = -0.05
        self._scan_active  = False
        self._scan_anim    = QPropertyAnimation(self, b"_scan_prop", self)
        self._scan_anim.setDuration(850)
        self._scan_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._scan_anim.finished.connect(self._on_scan_done)

        self._scan_trigger = QTimer(self)
        self._scan_trigger.timeout.connect(self._start_scan)
        self._scan_trigger.start(5500)   # sweep every 5.5 s

        self._build_ui()
        self._set_orientation(self._edge)

    # ── pyqtProperty — scan sweep position (0 → 1) ───────────────────────────
    def _get_scan(self) -> float:
        return self._scan_pos

    def _set_scan(self, v: float) -> None:
        self._scan_pos = float(v)
        self.update()

    _scan_prop = pyqtProperty(float, fget=_get_scan, fset=_set_scan)

    # ── Animations ────────────────────────────────────────────────────────────
    def _tick_pulse(self) -> None:
        self._pulse_phase = (self._pulse_phase + 0.038) % (2 * math.pi)
        self._pulse = 38.0 + 34.0 * math.sin(self._pulse_phase)
        self.update()

    def _start_scan(self) -> None:
        self._scan_active = True
        self._scan_anim.stop()
        self._scan_anim.setStartValue(-0.04)
        self._scan_anim.setEndValue(1.04)
        self._scan_anim.start()

    def _on_scan_done(self) -> None:
        self._scan_active = False
        self.update()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        expand_icon  = os.path.join(_ICONS_DIR, "ships", "default", "MobiGlas.png")
        self._expand_btn = ToolbarButton(expand_icon, "Open SC Dossier", self)
        self._expand_btn.clicked.connect(self.expand_requested.emit)

        capture_icon = os.path.join(_ICONS_DIR, "ships", "default", "Target_Lock.png")
        self._capture_btn = ToolbarButton(capture_icon, "OCR Screen Capture", self)
        self._capture_btn.clicked.connect(self.capture_requested.emit)

    def _set_orientation(self, edge: ScreenEdge) -> None:
        """Arrange buttons horizontally or vertically based on snapped edge."""
        old = self.layout()
        if old is not None:
            while old.count():
                old.takeAt(0)
            old.deleteLater()

        if edge in (ScreenEdge.TOP, ScreenEdge.BOTTOM):
            layout = QHBoxLayout(self)
            self.setFixedSize(TOOLBAR_LENGTH, TOOLBAR_THICKNESS)
        else:
            layout = QVBoxLayout(self)
            self.setFixedSize(TOOLBAR_THICKNESS, TOOLBAR_LENGTH)

        layout.setContentsMargins(_PAD, _PAD, _PAD, _PAD)
        layout.setSpacing(_SPACING)
        layout.addWidget(self._expand_btn)
        layout.addWidget(self._capture_btn)

    # ── Position / snapping ───────────────────────────────────────────────────
    def restore_position(self, x: int, y: int, edge: str) -> None:
        """Restore toolbar to a previously saved screen position."""
        try:
            self._edge = ScreenEdge(edge)
        except ValueError:
            self._edge = ScreenEdge.LEFT
        self._set_orientation(self._edge)

        w = TOOLBAR_THICKNESS if edge in ("left", "right") else TOOLBAR_LENGTH
        h = TOOLBAR_LENGTH    if edge in ("left", "right") else TOOLBAR_THICKNESS
        target = QRect(x, y, w, h)
        on_screen = any(
            s.availableGeometry().intersects(target)
            for s in QApplication.screens()
        )

        if on_screen:
            self.move(x, y)
        else:
            log.warning(
                "Saved toolbar position (%d, %d) is off-screen; resetting to default.", x, y
            )
            self._edge = ScreenEdge.LEFT
            self._set_orientation(self._edge)
            primary = QApplication.primaryScreen()
            if primary:
                avail = primary.availableGeometry()
                self.move(avail.left(), avail.top() + (avail.height() - h) // 2)
            else:
                self.move(0, 100)
            self._save_position()

    def snap_to_nearest_edge(self) -> None:
        """Snap flush to nearest screen edge and persist position."""
        screen = QApplication.primaryScreen()
        if not screen:
            return
        avail = screen.availableGeometry()
        pos   = self.pos()
        cx    = pos.x() + self.width()  // 2
        cy    = pos.y() + self.height() // 2

        edge = min(
            (cx - avail.left(),    ScreenEdge.LEFT),
            (avail.right()  - cx,  ScreenEdge.RIGHT),
            (cy - avail.top(),     ScreenEdge.TOP),
            (avail.bottom() - cy,  ScreenEdge.BOTTOM),
            key=lambda t: t[0],
        )[1]

        if edge != self._edge:
            self._edge = edge
            self._set_orientation(edge)

        if edge == ScreenEdge.LEFT:
            nx = avail.left()
            ny = max(avail.top(), min(pos.y(), avail.bottom() - self.height()))
        elif edge == ScreenEdge.RIGHT:
            nx = avail.right() - self.width()
            ny = max(avail.top(), min(pos.y(), avail.bottom() - self.height()))
        elif edge == ScreenEdge.TOP:
            nx = max(avail.left(), min(pos.x(), avail.right() - self.width()))
            ny = avail.top()
        else:
            nx = max(avail.left(), min(pos.x(), avail.right() - self.width()))
            ny = avail.bottom() - self.height()

        self.move(nx, ny)
        self._save_position()

    def _save_position(self) -> None:
        try:
            from src.core.settings import SettingsManager
            sm = SettingsManager.instance()
            sm.toolbar_x    = self.x()
            sm.toolbar_y    = self.y()
            sm.toolbar_edge = self._edge.value
        except Exception as exc:
            log.debug("Could not save toolbar position: %s", exc)

    # ── Drag ──────────────────────────────────────────────────────────────────
    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_active   = True
            self._drag_start_pos    = e.globalPosition().toPoint()
            self._drag_start_window = self.pos()
            e.accept()

    def mouseMoveEvent(self, e) -> None:
        if self._drag_active:
            delta = e.globalPosition().toPoint() - self._drag_start_pos
            self.move(self._drag_start_window + delta)
            e.accept()

    def mouseReleaseEvent(self, e) -> None:
        if self._drag_active:
            self._drag_active = False
            self.snap_to_nearest_edge()
            e.accept()

    # ── Opacity ───────────────────────────────────────────────────────────────
    def set_opacity(self, opacity: float) -> None:
        self.setWindowOpacity(max(0.3, min(1.0, opacity)))

    # ── Paint — full sci-fi HUD render ────────────────────────────────────────
    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w     = float(self.width())
        h     = float(self.height())
        edge  = self._edge
        pulse = self._pulse          # 38 – 72 float, sine-wave

        # ── Body path (chamfered — the core sci-fi shape) ─────────────────────
        body = _chamfer_path(1.0, 1.0, w - 2.0, h - 2.0, float(CHAMFER))

        # ── Layer 1: ambient outer glow ───────────────────────────────────────
        ag = QRadialGradient(w / 2, h / 2, max(w, h) * 0.85)
        ag.setColorAt(0.0, QColor(0, 140, 255, 10))
        ag.setColorAt(1.0, QColor(0,   0,   0,  0))
        p.fillRect(QRectF(0, 0, w, h), QBrush(ag))

        # ── Layer 2: dark base fill ───────────────────────────────────────────
        p.fillPath(body, _BG)

        # ── Layer 3: edge-to-center sheen gradient ────────────────────────────
        if edge == ScreenEdge.LEFT:
            sheen = QLinearGradient(0, 0, w, 0)
        elif edge == ScreenEdge.RIGHT:
            sheen = QLinearGradient(w, 0, 0, 0)
        elif edge == ScreenEdge.TOP:
            sheen = QLinearGradient(0, 0, 0, h)
        else:
            sheen = QLinearGradient(0, h, 0, 0)

        sheen.setColorAt(0.00, _SHEEN_START)
        sheen.setColorAt(0.45, QColor(0, 100, 160, 7))
        sheen.setColorAt(1.00, QColor(0,   0,   0, 0))
        p.fillPath(body, QBrush(sheen))

        # ── Layer 4: scanline micro-texture ──────────────────────────────────
        p.save()
        p.setClipPath(body)
        y_t = 0.0
        while y_t < h:
            p.fillRect(QRectF(0, y_t, w, 1.0), _STRIPE)
            y_t += 3.0
        p.restore()

        # ── Layer 5: chamfered border (pulsing) ───────────────────────────────
        border_col = QColor(0, int(160 + 40 * (pulse / 72.0)), 230, int(pulse))
        p.setPen(QPen(border_col, 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(body)

        # ── Layer 6: energy spine (bright line on screen-edge face) ──────────
        spine_alpha = int(min(255, pulse * 2.8))
        spine_pen   = QPen(QColor(0, 220, 255, spine_alpha), 2,
                           Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap)
        halo_pen    = QPen(QColor(0, 180, 255, int(pulse * 0.7)), 6,
                           Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap)
        s = 2.5  # spine inset from edge

        if edge == ScreenEdge.LEFT:
            p1 = QPointF(s, CHAMFER + 2)
            p2 = QPointF(s, h - CHAMFER - 2)
        elif edge == ScreenEdge.RIGHT:
            p1 = QPointF(w - s, CHAMFER + 2)
            p2 = QPointF(w - s, h - CHAMFER - 2)
        elif edge == ScreenEdge.TOP:
            p1 = QPointF(CHAMFER + 2, s)
            p2 = QPointF(w - CHAMFER - 2, s)
        else:
            p1 = QPointF(CHAMFER + 2, h - s)
            p2 = QPointF(w - CHAMFER - 2, h - s)

        # Glow halo first, then bright core on top
        p.setPen(halo_pen)
        p.drawLine(p1, p2)
        p.setPen(spine_pen)
        p.drawLine(p1, p2)

        # ── Layer 7: center separator with tick marks ─────────────────────────
        p.setPen(QPen(_SEP, 1.0))
        if edge in (ScreenEdge.TOP, ScreenEdge.BOTTOM):
            mx = w / 2
            p.drawLine(QPointF(mx, _PAD + 4), QPointF(mx, h - _PAD - 4))
            # Tick cluster
            p.setPen(QPen(_TICK, 1.0))
            for offset in (-5.0, 0.0, 5.0):
                ty = h / 2 + offset
                p.drawLine(QPointF(mx - 2.5, ty), QPointF(mx + 2.5, ty))
        else:
            my = h / 2
            p.drawLine(QPointF(_PAD + 4, my), QPointF(w - _PAD - 4, my))
            p.setPen(QPen(_TICK, 1.0))
            for offset in (-5.0, 0.0, 5.0):
                tx = w / 2 + offset
                p.drawLine(QPointF(tx, my - 2.5), QPointF(tx, my + 2.5))

        # ── Layer 8: corner bracket ornaments ─────────────────────────────────
        self._draw_brackets(p, w, h, pulse)

        # ── Layer 9: scan sweep ───────────────────────────────────────────────
        if self._scan_active:
            self._draw_scan(p, w, h, edge, body)

        p.end()

    # ── Sub-renderers ─────────────────────────────────────────────────────────
    def _draw_brackets(
        self, p: QPainter, w: float, h: float, pulse: float
    ) -> None:
        """Small L-brackets aligned to chamfered corners — sci-fi ornaments."""
        c   = float(CHAMFER)
        arm = 6.0
        col = QColor(0, 225, 255, int(min(255, pulse + 95)))
        pen = QPen(col, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        # Top-left
        p.drawLine(QPointF(c,       1.5),      QPointF(c + arm,    1.5))
        p.drawLine(QPointF(1.5,     c),        QPointF(1.5,        c + arm))
        # Top-right
        p.drawLine(QPointF(w - c,   1.5),      QPointF(w - c - arm, 1.5))
        p.drawLine(QPointF(w - 1.5, c),        QPointF(w - 1.5,    c + arm))
        # Bottom-left
        p.drawLine(QPointF(c,       h - 1.5),  QPointF(c + arm,    h - 1.5))
        p.drawLine(QPointF(1.5,     h - c),    QPointF(1.5,        h - c - arm))
        # Bottom-right
        p.drawLine(QPointF(w - c,   h - 1.5),  QPointF(w - c - arm, h - 1.5))
        p.drawLine(QPointF(w - 1.5, h - c),    QPointF(w - 1.5,    h - c - arm))

    def _draw_scan(
        self,
        p: QPainter,
        w: float,
        h: float,
        edge: ScreenEdge,
        body: QPainterPath,
    ) -> None:
        """Animated scan-sweep line — clips to chamfered body."""
        t = self._scan_pos   # −0.04 → 1.04

        p.save()
        p.setClipPath(body)

        if edge in (ScreenEdge.TOP, ScreenEdge.BOTTOM):
            x = t * w
            p.setPen(QPen(_SCAN_HALO, 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            p.drawLine(QPointF(x, 1), QPointF(x, h - 1))
            p.setPen(QPen(_SCAN_CORE, 1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            p.drawLine(QPointF(x, 1), QPointF(x, h - 1))
        else:
            y = t * h
            p.setPen(QPen(_SCAN_HALO, 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            p.drawLine(QPointF(1, y), QPointF(w - 1, y))
            p.setPen(QPen(_SCAN_CORE, 1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            p.drawLine(QPointF(1, y), QPointF(w - 1, y))

        p.restore()
