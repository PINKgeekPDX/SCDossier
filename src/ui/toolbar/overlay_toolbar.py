import logging
import math
import os
import sys

from PyQt6.QtCore import (
    Qt, QPoint, QPointF, QRectF, QRect, QTimer,
    QPropertyAnimation, QEasingCurve,
    pyqtSignal, pyqtProperty, pyqtSlot
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


def _bg():          return P.qcolor(P.SPACE_VOID, 238)
def _border_dim():  c = P.qcolor(P.PRIMARY_CONTAINER); c.setAlpha(45); return c
def _border_hot():  c = P.qcolor(P.PRIMARY_CONTAINER); c.setAlpha(110); return c
def _spine_core():  c = P.qcolor(P.PRIMARY_CONTAINER); c.setAlpha(220); return c
def _spine_glow():  c = P.qcolor(P.PRIMARY_CONTAINER); c.setAlpha(55); return c
def _sheen_start(): return P.qcolor(P.PRIMARY_CONTAINER, 22)
def _sep():         return P.qcolor(P.PRIMARY_CONTAINER, 38)
def _tick():        c = P.qcolor(P.PRIMARY_CONTAINER); c.setAlpha(80); return c
def _stripe():      return P.qcolor(P.PRIMARY_CONTAINER, 6)
def _brak():        c = P.qcolor(P.PRIMARY_CONTAINER); c.setAlpha(150); return c

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
        parent = self.parent()
        if parent and not getattr(parent, "_interact_held", False):
            return
        self._animate(1.0)

    def leaveEvent(self, e) -> None:
        self._pressed = False
        self._animate(0.0)

    def mousePressEvent(self, e) -> None:
        parent = self.parent()
        if parent:
            if getattr(parent, "_drag_held", False):
                e.ignore()
                return
            if not getattr(parent, "_interact_held", False):
                e.ignore()
                return

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
            fill = P.qcolor(P.PRIMARY_CONTAINER, 120)
        else:
            fill = P.qcolor(P.SPACE_VOID, int(195 + 45 * g))
        p.fillPath(hp, fill)

        if g > 0.01:
            rg = QRadialGradient(cx, cy, r)
            rg.setColorAt(0.0, P.qcolor(P.PRIMARY, int(80 * g)))
            rg.setColorAt(0.55, P.qcolor(P.PRIMARY_CONTAINER, int(35 * g)))
            rg.setColorAt(1.0, P.qcolor(P.PRIMARY_CONTAINER, 0))
            p.fillPath(hp, QBrush(rg))

        if self._pressed:
            ring_c = P.qcolor(P.PRIMARY_CONTAINER, 255)
            ring_w = 2.0
        elif g > 0.01:
            ring_c = P.qcolor(P.PRIMARY_CONTAINER, int(95 + 155 * g))
            ring_w = 1.2 + 0.8 * g
        else:
            ring_c = P.qcolor(P.PRIMARY_CONTAINER, 55)
            ring_w = 1.0

        p.setPen(QPen(ring_c, ring_w))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(hp)

        if g > 0.15:
            ghost = _hex_path(cx, cy, r + 2.5 * g)
            p.setPen(QPen(P.qcolor(P.PRIMARY_CONTAINER, int(38 * g)), 1.2))
            p.drawPath(ghost)

        off = int((self.width() - BTN_ICON_SIZE) / 2)
        if self._icon:
            self._icon.paint(p, off, off, BTN_ICON_SIZE, BTN_ICON_SIZE)
        else:
            p.setPen(QPen(P.qcolor(P.PRIMARY_CONTAINER, 200)))
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
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setMouseTracking(True)
        
        from src.core.settings import SettingsManager
        sm = SettingsManager.instance()
        self.set_opacity(sm.toolbar_idle_opacity)

        self._interact_held = False
        self._drag_held = False
        self._toolbar_activated = False  # True when toolbar is the active window
        self._game_hwnd = None  # Store the game window handle to restore later

        self._fade_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_anim.setDuration(200)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

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
        
        from src.core.events import EventBus
        bus = EventBus.instance()
        bus.toolbar_interact_pressed.connect(self._on_interact_pressed)
        bus.toolbar_interact_released.connect(self._on_interact_released)
        bus.toolbar_drag_pressed.connect(self._on_drag_pressed)
        bus.toolbar_drag_released.connect(self._on_drag_released)
        bus.settings_changed.connect(self._on_settings_changed)

    def _activate_toolbar(self) -> None:
        """Activate the toolbar window so mouse clicks register immediately."""
        if self._toolbar_activated:
            return
        if sys.platform != "win32":
            self.activateWindow()
            self._toolbar_activated = True
            return
        
        import ctypes
        user32 = ctypes.windll.user32
        
        # Store the current foreground window (the game) before activating toolbar
        self._game_hwnd = user32.GetForegroundWindow()
        
        # Activate the toolbar window
        hwnd = int(self.winId())
        # Use SetForegroundWindow — works reliably when the calling process is the foreground process
        # or when the process was recently activated
        user32.SetForegroundWindow(hwnd)
        self._toolbar_activated = True

    def _deactivate_toolbar(self) -> None:
        """Restore the game window as the active window."""
        if not self._toolbar_activated:
            return
        if sys.platform != "win32":
            self._toolbar_activated = False
            return
        
        import ctypes
        user32 = ctypes.windll.user32
        
        # Restore the game window if we have its handle
        if self._game_hwnd and self._game_hwnd != int(self.winId()):
            try:
                user32.SetForegroundWindow(self._game_hwnd)
            except Exception:
                pass
        
        self._game_hwnd = None
        self._toolbar_activated = False

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._update_interaction_state()

    def _update_interaction_state(self) -> None:
        from src.core.settings import SettingsManager
        sm = SettingsManager.instance()
        active = self._interact_held or self._drag_held
        
        flags = getattr(self, "_current_window_flags", self.windowFlags())
        was_transparent = bool(flags & Qt.WindowType.WindowTransparentForInput)
        should_be_transparent = not active
        
        if was_transparent != should_be_transparent:
            import sys
            if sys.platform == "win32":
                import ctypes
                hwnd = int(self.winId())
                GWL_EXSTYLE = -20
                WS_EX_TRANSPARENT = 0x00000020
                
                ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                if should_be_transparent:
                    ex_style |= WS_EX_TRANSPARENT
                else:
                    ex_style &= ~WS_EX_TRANSPARENT
                ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
                
                # Flush the style change so Windows recalculates hit-testing
                SWP_NOMOVE = 0x0002
                SWP_NOSIZE = 0x0001
                SWP_NOZORDER = 0x0004
                SWP_FRAMECHANGED = 0x0020
                ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED)
                
                # Update Qt's internal state without triggering window recreation if possible, 
                # but it's actually safer to just update the windows ex_style directly and leave Qt out of it.
                # However, to keep our 'was_transparent' logic working:
                if should_be_transparent:
                    self._current_window_flags = flags | Qt.WindowType.WindowTransparentForInput
                else:
                    self._current_window_flags = flags & ~Qt.WindowType.WindowTransparentForInput
            else:
                if should_be_transparent:
                    flags |= Qt.WindowType.WindowTransparentForInput
                else:
                    flags &= ~Qt.WindowType.WindowTransparentForInput
                    
                self.setWindowFlags(flags)
                if self.isVisible():
                    self.show()
                
        self._fade_anim.stop()
        if self._interact_held:
            self._fade_anim.setStartValue(self.windowOpacity())
            self._fade_anim.setEndValue(1.0)
            self._fade_anim.start()
        elif self._drag_held:
            self.set_opacity(sm.toolbar_idle_opacity)
        else:
            self._fade_anim.setStartValue(self.windowOpacity())
            self._fade_anim.setEndValue(sm.toolbar_idle_opacity)
            self._fade_anim.start()
            
        self.update()

    @pyqtSlot()
    def _on_interact_pressed(self) -> None:
        self._interact_held = True
        self._update_interaction_state()
        # Immediately activate toolbar so mouse becomes visible (game releases cursor)
        self._activate_toolbar()
        
        from PyQt6.QtGui import QCursor
        pos = QCursor.pos()
        local_pos = self.mapFromGlobal(pos)
        child = self.childAt(local_pos)
        if isinstance(child, ToolbarButton):
            child._animate(1.0)

    @pyqtSlot()
    def _on_interact_released(self) -> None:
        self._interact_held = False
        # Only deactivate if drag is not also held
        if not self._drag_held:
            self._deactivate_toolbar()
        self._update_interaction_state()
        
        for btn in (self._expand_btn, self._capture_btn):
            btn._animate(0.0)
            btn._pressed = False

    @pyqtSlot()
    def _on_drag_pressed(self) -> None:
        self._drag_held = True
        self._update_interaction_state()
        # Activate toolbar so mouse becomes visible for dragging
        self._activate_toolbar()

    @pyqtSlot()
    def _on_drag_released(self) -> None:
        self._drag_held = False
        # Only deactivate if interact is not also held
        if not self._interact_held:
            self._deactivate_toolbar()
        if self._drag_active:
            self._drag_active = False
            self.releaseMouse()
            self.snap_to_nearest_edge()
        self._update_interaction_state()

    @pyqtSlot(str, object)
    def _on_settings_changed(self, key: str, value: object) -> None:
        if key == "toolbar_idle_opacity":
            self._update_interaction_state()

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
                    
        if is_running:
            import sys
            if sys.platform == "win32":
                import ctypes
                hwnd = int(self.winId())
                HWND_TOPMOST = -1
                SWP_NOMOVE = 0x0002
                SWP_NOSIZE = 0x0001
                SWP_NOACTIVATE = 0x0010
                ctypes.windll.user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)

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
        self._expand_btn.clicked.connect(self._on_button_clicked)

        capture_icon = get_asset_path("assets/icons/Icons/TARGET_LOCK.png")
        self._capture_btn = ToolbarButton(capture_icon, "OCR Screen Capture", self)
        self._capture_btn.clicked.connect(self.capture_requested.emit)
        self._capture_btn.clicked.connect(self._on_button_clicked)

    @pyqtSlot()
    def _on_button_clicked(self) -> None:
        """Called after a toolbar button is clicked — clear activation state without restoring game.
        
        The button actions (expand → show main window, capture → show region selector)
        will handle window activation themselves. We just clear the stored game handle
        so the subsequent key-release doesn't restore the game over the new window.
        """
        self._game_hwnd = None
        self._toolbar_activated = False

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

    def mouseMoveEvent(self, e) -> None:
        if self._drag_active:
            if not (e.buttons() & Qt.MouseButton.LeftButton):
                self._drag_active = False
                self.releaseMouse()
                self.snap_to_nearest_edge()
                return
            delta = e.globalPosition().toPoint() - self._drag_start_pos
            self.move(self._drag_start_window + delta)
            e.accept()
            return

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton and self._drag_held:
            self._drag_active   = True
            self._drag_start_pos    = e.globalPosition().toPoint()
            self._drag_start_window = self.pos()
            self.grabMouse()
            e.accept()

    def leaveEvent(self, e) -> None:
        super().leaveEvent(e)

    def mouseReleaseEvent(self, e) -> None:
        if self._drag_active:
            self._drag_active = False
            self.releaseMouse()
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
        ag.setColorAt(0.0, P.qcolor(P.PRIMARY_CONTAINER, 10))
        ag.setColorAt(1.0, P.qcolor(P.PRIMARY_CONTAINER, 0))
        p.fillRect(QRectF(0, 0, w, h), QBrush(ag))

        p.fillPath(body, _bg())

        if edge == ScreenEdge.LEFT:
            sheen = QLinearGradient(0, 0, w, 0)
        elif edge == ScreenEdge.RIGHT:
            sheen = QLinearGradient(w, 0, 0, 0)
        elif edge == ScreenEdge.TOP:
            sheen = QLinearGradient(0, 0, 0, h)
        else:
            sheen = QLinearGradient(0, h, 0, 0)

        sheen.setColorAt(0.00, _sheen_start())
        sheen.setColorAt(0.45, P.qcolor(P.PRIMARY, 7))
        sheen.setColorAt(1.00, P.qcolor(P.PRIMARY, 0))
        p.fillPath(body, QBrush(sheen))

        p.save()
        p.setClipPath(body)
        y_t = 0.0
        while y_t < h:
            p.fillRect(QRectF(0, y_t, w, 1.0), _stripe())
            y_t += 3.0
        p.restore()

        border_col = P.qcolor(P.PRIMARY_CONTAINER, int(pulse))
        if self._drag_held:
            border_col = QColor(255, 255, 0, 255)
            
        p.setPen(QPen(border_col, 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(body)

        spine_alpha = int(min(255, pulse * 2.8))
        spine_pen   = QPen(P.qcolor(P.PRIMARY_CONTAINER, spine_alpha), 2,
                           Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap)
        halo_pen    = QPen(P.qcolor(P.PRIMARY_CONTAINER, int(pulse * 0.7)), 6,
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

        p.setPen(QPen(_sep(), 1.0))
        if edge in (ScreenEdge.TOP, ScreenEdge.BOTTOM):
            mx = w / 2
            p.drawLine(QPointF(mx, _PAD + 4), QPointF(mx, h - _PAD - 4))
            p.setPen(QPen(_tick(), 1.0))
            for offset in (-5.0, 0.0, 5.0):
                ty = h / 2 + offset
                p.drawLine(QPointF(mx - 2.5, ty), QPointF(mx + 2.5, ty))
        else:
            my = h / 2
            p.drawLine(QPointF(_PAD + 4, my), QPointF(w - _PAD - 4, my))
            p.setPen(QPen(_tick(), 1.0))
            for offset in (-5.0, 0.0, 5.0):
                tx = w / 2 + offset
                p.drawLine(QPointF(tx, my - 2.5), QPointF(tx, my + 2.5))

        self._draw_brackets(p, w, h, pulse)
        p.end()

    def _draw_brackets(self, p: QPainter, w: float, h: float, pulse: float) -> None:
        c   = float(CHAMFER)
        arm = 6.0
        col = P.qcolor(P.PRIMARY_CONTAINER, int(min(255, pulse + 95)))
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
