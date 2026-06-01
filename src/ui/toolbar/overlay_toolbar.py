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

TOOLBAR_THICKNESS = 54
TOOLBAR_LENGTH    = 110
BTN_HEX_R        = 17
BTN_ICON_SIZE    = 18
CHAMFER          = 9
_PAD             = 6
_SPACING         = 4

_BG          = QColor(2,  11,  19, 238)
_BORDER_DIM  = QColor(0, 160, 220,  45)
_BORDER_HOT  = QColor(0, 200, 255, 110)
_SPINE_CORE  = QColor(0, 220, 255, 220)
_SPINE_GLOW  = QColor(0, 180, 255,  55)
_SHEEN_START = QColor(0, 170, 255,  22)
_SEP         = QColor(0, 170, 255,  38)
_TICK        = QColor(0, 210, 255,  80)
_STRIPE      = QColor(0, 170, 255,   6)
_BRAK        = QColor(0, 220, 255, 150)

from src.core.paths import get_asset_path


def _chamfer_path(x: float, y: float, w: float, h: float, c: float) -> QPainterPath:
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
    path = QPainterPath()
    for i in range(6):
        angle = math.radians(60 * i - 30)
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        path.moveTo(x, y) if i == 0 else path.lineTo(x, y)
    path.closeSubpath()
    return path


class ToolbarButton(QWidget):

    clicked = pyqtSignal()

    def __init__(self, icon_path: str, tooltip: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._icon_path = icon_path
        self._icon      = None
        self._pressed   = False
        self._glow      = 0.0

        sz = BTN_HEX_R * 2 + 4
        self.setFixedSize(sz, sz)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        self._anim = QPropertyAnimation(self, b"_glow_prop", self)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._load_icon()

    def _get_glow(self) -> float:
        return self._glow

    def _set_glow(self, v: float) -> None:
        self._glow = float(v)
        self.update()

    _glow_prop = pyqtProperty(float, fget=_get_glow, fset=_set_glow)

    def _load_icon(self) -> None:
        icon = load_icon(self._icon_path, BTN_ICON_SIZE)
        self._icon = icon if not icon.isNull() else None

    def _animate(self, target: float) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._glow)
        self._anim.setEndValue(target)
        self._anim.start()

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

        if self._pressed:
            fill = QColor(0, 210, 255, 120)
        else:
            fill = QColor(3, 16, 28, int(195 + 45 * g))
        p.fillPath(hp, fill)

        if g > 0.01:
            rg = QRadialGradient(cx, cy, r)
            rg.setColorAt(0.0, QColor(0, 160, 255, int(80 * g)))
            rg.setColorAt(0.55, QColor(0, 110, 200, int(35 * g)))
            rg.setColorAt(1.0,  QColor(0,   0,   0,   0))
            p.fillPath(hp, QBrush(rg))

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

        if g > 0.15:
            ghost = _hex_path(cx, cy, r + 2.5 * g)
            p.setPen(QPen(QColor(0, 190, 255, int(38 * g)), 1.2))
            p.drawPath(ghost)

        off = int((self.width() - BTN_ICON_SIZE) / 2)
        if self._icon:
            self._icon.paint(p, off, off, BTN_ICON_SIZE, BTN_ICON_SIZE)
        else:
            p.setPen(QPen(QColor(0, 210, 255, 200)))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "\u25C8")

        p.end()


class OverlayToolbar(QWidget):

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

        self._pulse_phase = 0.0
        self._pulse       = 50.0
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._tick_pulse)
        self._pulse_timer.start(33)

        self._build_ui()
        self._set_orientation(self._edge)

        self._sc_running = False
        self._game_check_timer = QTimer(self)
        self._game_check_timer.timeout.connect(self._check_game_state)
        self._game_check_timer.start(3000)
        self._check_game_state()

    def _check_game_state(self) -> None:
        from src.core.settings import SettingsManager
        sm = SettingsManager.instance()
        if not sm.auto_hide_toolbar_without_game:
            return

        import subprocess
        is_running = False
        try:
            output = subprocess.check_output(
                'tasklist /FI "IMAGENAME eq StarCitizen.exe" /NH',
                shell=True,
                creationflags=0x08000000
            ).decode()
            if "StarCitizen.exe" in output:
                is_running = True
        except Exception as e:
            log.debug("Game state check failed: %s", e)

        if is_running != self._sc_running:
            self._sc_running = is_running
            from src.core.events import EventBus
            if not self._sc_running:
                if self.isVisible():
                    self.hide()
                if hasattr(self, '_main_window_ref') and self._main_window_ref:
                    mw = self._main_window_ref()
                    if mw and not mw.isVisible():
                        mw.show()
                        mw.raise_()
                        mw.activateWindow()
            else:
                if not self.isVisible():
                    self.show()

    def set_main_window_ref(self, main_window) -> None:
        import weakref
        self._main_window_ref = weakref.ref(main_window)

    def _tick_pulse(self) -> None:
        self._pulse_phase = (self._pulse_phase + 0.038) % (2 * math.pi)
        self._pulse = 38.0 + 34.0 * math.sin(self._pulse_phase)
        self.update()

    def _build_ui(self) -> None:
        expand_icon = get_asset_path("assets/icons/Icons/MOBIGLAS.png")
        self._expand_btn = ToolbarButton(expand_icon, "Open SC Dossier", self)
        self._expand_btn.clicked.connect(self.expand_requested.emit)

        capture_icon = get_asset_path("assets/icons/Icons/TARGET_LOCK.png")
        self._capture_btn = ToolbarButton(capture_icon, "OCR Screen Capture", self)
        self._capture_btn.clicked.connect(self.capture_requested.emit)

    def _set_orientation(self, edge: ScreenEdge) -> None:
        old = self.layout()
        if old is not None:
            while old.count():
                old.takeAt(0)
            QWidget().setLayout(old)

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

    def restore_position(self, x: int, y: int, edge: str) -> None:
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
            log.warning("Saved toolbar position (%d, %d) is off-screen; resetting to default.", x, y)
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

    def set_opacity(self, opacity: float) -> None:
        self.setWindowOpacity(max(0.3, min(1.0, opacity)))

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w     = float(self.width())
        h     = float(self.height())
        edge  = self._edge
        pulse = self._pulse

        body = _chamfer_path(1.0, 1.0, w - 2.0, h - 2.0, float(CHAMFER))

        ag = QRadialGradient(w / 2, h / 2, max(w, h) * 0.85)
        ag.setColorAt(0.0, QColor(0, 140, 255, 10))
        ag.setColorAt(1.0, QColor(0,   0,   0,  0))
        p.fillRect(QRectF(0, 0, w, h), QBrush(ag))

        p.fillPath(body, _BG)

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

        p.save()
        p.setClipPath(body)
        y_t = 0.0
        while y_t < h:
            p.fillRect(QRectF(0, y_t, w, 1.0), _STRIPE)
            y_t += 3.0
        p.restore()

        border_col = QColor(0, int(160 + 40 * (pulse / 72.0)), 230, int(pulse))
        p.setPen(QPen(border_col, 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(body)

        spine_alpha = int(min(255, pulse * 2.8))
        spine_pen   = QPen(QColor(0, 220, 255, spine_alpha), 2,
                           Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap)
        halo_pen    = QPen(QColor(0, 180, 255, int(pulse * 0.7)), 6,
                           Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap)
        s = 2.5

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

        p.setPen(halo_pen)
        p.drawLine(p1, p2)
        p.setPen(spine_pen)
        p.drawLine(p1, p2)

        p.setPen(QPen(_SEP, 1.0))
        if edge in (ScreenEdge.TOP, ScreenEdge.BOTTOM):
            mx = w / 2
            p.drawLine(QPointF(mx, _PAD + 4), QPointF(mx, h - _PAD - 4))
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

        self._draw_brackets(p, w, h, pulse)
        p.end()

    def _draw_brackets(self, p: QPainter, w: float, h: float, pulse: float) -> None:
        c   = float(CHAMFER)
        arm = 6.0
        col = QColor(0, 225, 255, int(min(255, pulse + 95)))
        pen = QPen(col, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        p.drawLine(QPointF(c,       1.5),      QPointF(c + arm,    1.5))
        p.drawLine(QPointF(1.5,     c),        QPointF(1.5,        c + arm))
        p.drawLine(QPointF(w - c,   1.5),      QPointF(w - c - arm, 1.5))
        p.drawLine(QPointF(w - 1.5, c),        QPointF(w - 1.5,    c + arm))
        p.drawLine(QPointF(c,       h - 1.5),  QPointF(c + arm,    h - 1.5))
        p.drawLine(QPointF(1.5,     h - c),    QPointF(1.5,        h - c - arm))
        p.drawLine(QPointF(w - c,   h - 1.5),  QPointF(w - c - arm, h - 1.5))
        p.drawLine(QPointF(w - 1.5, h - c),    QPointF(w - 1.5,    h - c - arm))
