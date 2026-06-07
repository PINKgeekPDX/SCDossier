"""
src/core/hotkey_manager.py
GlobalHotkeyManager — Uses Win32 RegisterHotKey for system-wide hotkey detection
that works even when fullscreen games (e.g. Star Citizen) capture exclusive input.

Architecture:
  _HotkeyThread — dedicated QThread that creates a Win32 message-only window
  (HWND_MESSAGE) and runs a GetMessage loop.  RegisterHotKey is called against
  this HWND so WM_HOTKEY arrives on the thread's own message queue, dispatched
  by the message loop.  No Qt nativeEvent involved — zero sip.voidptr risk.

  CRITICAL: RegisterHotKey with a non-NULL HWND must be called from the thread
  that OWNS that window (MSDN: "fails if you try to associate a hot key with a
  window created by another thread").  Therefore GlobalHotkeyManager (main thread)
  sends custom window messages (WM_APP + N) to the thread's HWND, and the thread's
  WndProc performs the actual RegisterHotKey/UnregisterHotKey calls.

  IMPORTANT — GetMessageW MUST use hWnd=NULL (0):
  WM_HOTKEY is posted to the THREAD's message queue, not to the window's queue.
  GetMessageW(hwnd, ...) with a non-NULL hwnd only processes messages in the
  window's private queue and silently discards thread-queue messages like WM_HOTKEY.
  Using NULL retrieves messages from both queues. WM_HOTKEY is then handled
  directly in the message loop before DispatchMessageW (which won't route
  thread messages to any WndProc).

  For state-based (hold) hotkeys, release is detected via lightweight
  GetAsyncKeyState polling on a QTimer — only while the key is actually held.
"""
import logging
import ctypes
import ctypes.wintypes as wintypes
import threading

from PyQt6.QtCore import QObject, QTimer, Qt, QThread, pyqtSignal, pyqtSlot

from src.core.settings import SettingsManager
from src.core.events import EventBus

log = logging.getLogger(__name__)

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
WM_APP = 0x8000
WM_REGISTER_HOTKEY = WM_APP + 1
WM_UNREGISTER_HOTKEY = WM_APP + 2


class _WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", ctypes.c_uint),
        ("lpfnWndProc", ctypes.c_void_p),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", ctypes.c_void_p),
        ("hIcon", ctypes.c_void_p),
        ("hCursor", ctypes.c_void_p),
        ("hbrBackground", ctypes.c_void_p),
        ("lpszMenuName", ctypes.c_wchar_p),
        ("lpszClassName", ctypes.c_wchar_p),
    ]

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

HOTKEY_ID_OCR = 1
HOTKEY_ID_INTERACT = 2
HOTKEY_ID_DRAG = 3

_ID_TO_NAME: dict[int, str] = {
    HOTKEY_ID_OCR: "ocr",
    HOTKEY_ID_INTERACT: "interact",
    HOTKEY_ID_DRAG: "drag",
}

_NAME_TO_ID: dict[str, int] = {v: k for k, v in _ID_TO_NAME.items()}

_VK_MAP: dict[str, int] = {
    'ctrl': 0x11, 'left ctrl': 0xA2, 'right ctrl': 0xA3,
    'alt': 0x12, 'left alt': 0xA4, 'right alt': 0xA5,
    'shift': 0x10, 'left shift': 0xA0, 'right shift': 0xA1,
    'windows': 0x5B, 'left windows': 0x5B, 'right windows': 0x5C,
    'esc': 0x1B, 'tab': 0x09, 'enter': 0x0D, 'space': 0x20,
    'backspace': 0x08, 'delete': 0x2E, 'insert': 0x2D,
    'home': 0x24, 'end': 0x23, 'page up': 0x21, 'page down': 0x22,
    'up': 0x26, 'down': 0x28, 'left': 0x25, 'right': 0x27,
    'caps lock': 0x14, 'num lock': 0x90, 'scroll lock': 0x91,
    # NumPad keys
    'num 0': 0x60, 'num 1': 0x61, 'num 2': 0x62, 'num 3': 0x63,
    'num 4': 0x64, 'num 5': 0x65, 'num 6': 0x66, 'num 7': 0x67,
    'num 8': 0x68, 'num 9': 0x69,
    # Punctuation
    'semicolon': 0xBA, 'equals': 0xBB, 'comma': 0xBC,
    'minus': 0xBD, 'period': 0xBE, 'slash': 0xBF,
    'backtick': 0xC0, 'open bracket': 0xDB,
    'backslash': 0xDC, 'close bracket': 0xDD, 'quote': 0xDE,
}

# VKs that are pure modifier keys — used to detect modifier-only hotkey strings
_MODIFIER_VKS: frozenset[int] = frozenset({
    0x10, 0xA0, 0xA1,        # Shift, LShift, RShift
    0x11, 0xA2, 0xA3,        # Ctrl, LCtrl, RCtrl
    0x12, 0xA4, 0xA5,        # Alt, LAlt, RAlt
    0x5B, 0x5C,              # LWin, RWin
})


def parse_hotkey_to_vk(hotkey_str: str) -> list[int]:
    if not hotkey_str:
        return []
    key_str = hotkey_str.strip().lower()
    parts = key_str.split('+')
    vks: list[int] = []
    for part in parts:
        p = part.strip()
        if p in _VK_MAP:
            vks.append(_VK_MAP[p])
        elif len(p) == 1:
            if 'a' <= p <= 'z':
                vks.append(ord(p.upper()))
            elif '0' <= p <= '9':
                vks.append(ord(p))
        elif len(p) in (2, 3) and p.startswith('f') and p[1:].isdigit():
            fn = int(p[1:])
            if 1 <= fn <= 24:
                vks.append(0x70 + fn - 1)
    return vks


def _split_modifiers_and_key(vks: list[int]) -> tuple[int, int]:
    """
    Split a list of VK codes into (modifier_flags, main_vk) for RegisterHotKey.

    Special case: if ALL keys are modifier keys (e.g. "left alt" alone), we treat
    the last VK as the main key with no modifier flags.  RegisterHotKey on
    Windows 10/11 accepts modifier VKs (VK_LMENU, VK_LCONTROL, etc.) as the
    main key when paired with MOD_NOREPEAT and no other modifier flag, allowing
    single-modifier-key hotkeys to work system-wide.
    """
    mod = 0
    main_key = 0

    for vk in vks:
        if vk in (0x11, 0xA2, 0xA3):
            mod |= MOD_CONTROL
        elif vk in (0x12, 0xA4, 0xA5):
            mod |= MOD_ALT
        elif vk in (0x10, 0xA0, 0xA1):
            mod |= MOD_SHIFT
        elif vk in (0x5B, 0x5C):
            mod |= MOD_WIN
        else:
            main_key = vk

    # If no non-modifier key found (modifier-only hotkey string like "left alt"),
    # use the last VK as the trigger key and clear accumulated modifier flags.
    # This lets RegisterHotKey register e.g. VK_LMENU as the main key directly.
    if main_key == 0 and vks:
        mod = 0
        main_key = vks[-1]

    return mod, main_key


class _HotkeyThread(QThread):
    """
    Creates a Win32 message-only window (HWND_MESSAGE) and runs a GetMessage
    loop.  When the OS delivers WM_HOTKEY (to the thread queue), the loop
    directly emits ``hotkey_fired(hk_id)`` via a queued signal connection to
    the main thread.

    ``register_hotkey()`` and ``unregister_hotkey()`` are thread-safe methods
    that use SendMessageW/PostMessageW to invoke the actual Win32 API calls
    on the thread that owns the HWND (as required by RegisterHotKey).

    KEY FIX: GetMessageW is called with hWnd=0 (NULL) so it receives messages
    from the *thread* message queue (where WM_HOTKEY is delivered), not just
    the window's private queue.  WM_HOTKEY is handled inline in the loop rather
    than via DispatchMessageW, because DispatchMessageW does not route thread
    messages to any WndProc.
    """

    hotkey_fired = pyqtSignal(int)

    _CLASS_NAME = "SCDossier_HotkeySink"

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._running = True
        self._hwnd: int = 0
        self._ready = threading.Event()
        self._user32 = ctypes.windll.user32
        self._kernel32 = ctypes.windll.kernel32

        # ---- declare argtypes/restype for all Win32 functions used ----
        # Without these, ctypes defaults to int (32-bit), which overflows
        # when 64-bit values are passed on x64.

        self._user32.DefWindowProcW.argtypes = [
            wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM,
        ]
        self._user32.DefWindowProcW.restype = ctypes.c_longlong  # LRESULT

        self._user32.GetMessageW.argtypes = [
            ctypes.c_void_p, wintypes.HWND, ctypes.c_uint, ctypes.c_uint,
        ]
        self._user32.GetMessageW.restype = ctypes.c_long  # BOOL

        self._user32.TranslateMessage.argtypes = [ctypes.c_void_p]
        self._user32.TranslateMessage.restype = ctypes.c_long  # BOOL

        self._user32.DispatchMessageW.argtypes = [ctypes.c_void_p]
        self._user32.DispatchMessageW.restype = ctypes.c_longlong  # LRESULT

        self._user32.PostMessageW.argtypes = [
            wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM,
        ]
        self._user32.PostMessageW.restype = ctypes.c_long  # BOOL

        self._user32.SendMessageW.argtypes = [
            wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM,
        ]
        self._user32.SendMessageW.restype = ctypes.c_longlong  # LRESULT

        self._user32.DestroyWindow.argtypes = [wintypes.HWND]
        self._user32.DestroyWindow.restype = ctypes.c_long  # BOOL

        self._user32.RegisterClassW.argtypes = [ctypes.c_void_p]
        self._user32.RegisterClassW.restype = ctypes.c_ushort  # ATOM

        self._user32.UnregisterClassW.argtypes = [
            ctypes.c_wchar_p, ctypes.c_void_p,
        ]
        self._user32.UnregisterClassW.restype = ctypes.c_long  # BOOL

        self._user32.CreateWindowExW.argtypes = [
            ctypes.c_uint,        # dwExStyle
            ctypes.c_wchar_p,     # lpClassName
            ctypes.c_wchar_p,     # lpWindowName
            ctypes.c_uint,        # dwStyle
            ctypes.c_int,         # x
            ctypes.c_int,         # y
            ctypes.c_int,         # nWidth
            ctypes.c_int,         # nHeight
            wintypes.HWND,        # hWndParent
            wintypes.HMENU,       # hMenu
            ctypes.c_void_p,      # hInstance
            ctypes.c_void_p,      # lpParam
        ]
        self._user32.CreateWindowExW.restype = wintypes.HWND

        # RegisterHotKey/UnregisterHotKey — called from within the WndProc
        # (on the thread that owns the window), so these argtypes serve the
        # thread's own direct calls.
        self._user32.RegisterHotKey.argtypes = [
            wintypes.HWND, ctypes.c_int, ctypes.c_uint, ctypes.c_uint,
        ]
        self._user32.RegisterHotKey.restype = ctypes.c_long  # BOOL

        self._user32.UnregisterHotKey.argtypes = [
            wintypes.HWND, ctypes.c_int,
        ]
        self._user32.UnregisterHotKey.restype = ctypes.c_long  # BOOL

        self._kernel32.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
        self._kernel32.GetModuleHandleW.restype = ctypes.c_void_p  # HMODULE

        self._kernel32.GetLastError.argtypes = []
        self._kernel32.GetLastError.restype = ctypes.c_ulong

        # WNDPROC callback type
        WNDPROC = ctypes.WINFUNCTYPE(
            ctypes.c_longlong,
            wintypes.HWND,
            ctypes.c_uint,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        self._wndproc = WNDPROC(self._wnd_proc)

    # -- WndProc -------------------------------------------------------------

    def _wnd_proc(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        """
        Handles WM_REGISTER_HOTKEY and WM_UNREGISTER_HOTKEY custom messages
        posted from the main thread.

        NOTE: WM_HOTKEY itself is NOT handled here — it arrives on the thread
        queue, not the window queue, so DispatchMessageW never routes it to
        WndProc.  It is handled directly in the run() message loop.
        """
        if msg == WM_REGISTER_HOTKEY:
            hk_id = wparam
            mod = lparam & 0xFFFF
            vk = (lparam >> 16) & 0xFFFF
            ok = self._user32.RegisterHotKey(hwnd, hk_id, mod | MOD_NOREPEAT, vk)
            if not ok:
                err = self._kernel32.GetLastError()
                log.warning(
                    "RegisterHotKey FAIL in WndProc  id=%d  mod=0x%x  vk=%#x  err=%d",
                    hk_id, mod, vk, err,
                )
            return 1 if ok else 0

        if msg == WM_UNREGISTER_HOTKEY:
            self._user32.UnregisterHotKey(hwnd, wparam)
            return 0

        return self._user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    # -- public API (thread-safe) --------------------------------------------

    def register_hotkey(self, hk_id: int, mod: int, vk: int) -> bool:
        """
        Thread-safe.  Sends a synchronous message to the hotkey thread's
        window so that RegisterHotKey is called from the thread that owns
        the HWND (required by Win32).
        """
        if not self._hwnd:
            return False
        # Pack modifiers and vk into LPARAM as two 16-bit halves
        lparam = (mod & 0xFFFF) | ((vk & 0xFFFF) << 16)
        result = self._user32.SendMessageW(
            self._hwnd, WM_REGISTER_HOTKEY, hk_id, lparam,
        )
        return bool(result)

    def unregister_hotkey(self, hk_id: int) -> None:
        """Thread-safe.  Posts an async message to unregister a hotkey."""
        if self._hwnd:
            self._user32.PostMessageW(
                self._hwnd, WM_UNREGISTER_HOTKEY, hk_id, 0,
            )

    # -- thread lifecycle ----------------------------------------------------

    def wait_ready(self, timeout: float = 5.0) -> bool:
        return self._ready.wait(timeout)

    def run(self):
        hInstance = self._kernel32.GetModuleHandleW(None)

        wc = _WNDCLASSW()
        wc.lpfnWndProc = ctypes.cast(self._wndproc, ctypes.c_void_p)
        wc.lpszClassName = self._CLASS_NAME
        wc.hInstance = hInstance
        atom = self._user32.RegisterClassW(ctypes.byref(wc))
        if not atom:
            log.error("RegisterClassW failed: %d", self._kernel32.GetLastError())
            self._ready.set()
            return

        HWND_MESSAGE = wintypes.HWND(-3)
        self._hwnd = self._user32.CreateWindowExW(
            0, self._CLASS_NAME, "", 0,
            0, 0, 0, 0,
            HWND_MESSAGE, 0, hInstance, None,
        )
        if not self._hwnd:
            log.error("CreateWindowExW failed: %d", self._kernel32.GetLastError())
            self._user32.UnregisterClassW(self._CLASS_NAME, hInstance)
            self._ready.set()
            return

        log.info("Hotkey sink HWND created: %#x", self._hwnd)
        self._ready.set()

        msg = wintypes.MSG()
        while self._running:
            # CRITICAL FIX: hWnd=0 (NULL) so GetMessageW reads from the full
            # thread message queue.  WM_HOTKEY is delivered to the thread queue,
            # NOT the window's queue.  A non-NULL hWnd filter silently discards
            # WM_HOTKEY messages, causing hotkeys to never fire.
            bRet = self._user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
            if bRet > 0:
                if msg.message == WM_HOTKEY:
                    # WM_HOTKEY is a thread message — DispatchMessageW will not
                    # route it to any WndProc.  Handle it directly here.
                    # wParam holds the hotkey ID registered via RegisterHotKey.
                    hk_id = msg.wParam
                    log.debug("WM_HOTKEY received in thread loop  id=%d", hk_id)
                    self.hotkey_fired.emit(hk_id)
                else:
                    self._user32.TranslateMessage(ctypes.byref(msg))
                    self._user32.DispatchMessageW(ctypes.byref(msg))
            elif bRet == 0:
                # WM_QUIT received
                break
            else:
                err = self._kernel32.GetLastError()
                log.error("GetMessageW failed: %d", err)
                break

        if self._hwnd:
            self._user32.DestroyWindow(self._hwnd)
            self._hwnd = 0
        self._user32.UnregisterClassW(self._CLASS_NAME, hInstance)

    def stop(self):
        self._running = False
        if self._hwnd:
            self._user32.PostMessageW(self._hwnd, WM_QUIT, 0, 0)
        self.wait(3000)


class GlobalHotkeyManager(QObject):
    """
    Manages global keyboard shortcuts via Win32 API.

    - Event hotkeys (OCR): fires once on key combination press, using RegisterHotKey.
    - State hotkeys (interact / drag): hold-to-activate, state detected via
      GetAsyncKeyState polling on a high-precision QTimer (25ms interval).

    Works even when a fullscreen exclusive game (e.g. Star Citizen) is the
    active foreground window, provided the application runs at the same privilege level.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.sm = SettingsManager.instance()
        self.bus = EventBus.instance()
        self._user32 = ctypes.windll.user32

        self._hotkey_thread = _HotkeyThread()
        self._hotkey_thread.hotkey_fired.connect(self._on_hotkey_fired)
        self._hotkey_thread.start()
        if not self._hotkey_thread.wait_ready():
            log.error("Hotkey sink thread failed to initialise — event-based hotkeys disabled")

        self._is_event: dict[str, bool] = {}
        self._held: dict[str, bool] = {}
        self._hotkey_strs: dict[str, str] = {}

        # Constantly running poll timer for state-based hotkeys
        self._poll_timer = QTimer(self)
        self._poll_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._poll_timer.timeout.connect(self._on_poll_tick)
        self._poll_timer.start(25)  # 25ms interval (40Hz)

        self._bind("ocr", self.sm.ocr_hotkey, is_event=True)
        self._bind("interact", self.sm.toolbar_interact_hotkey, is_event=False)
        self._bind("drag", self.sm.toolbar_drag_hotkey, is_event=False)

        self.bus.settings_changed.connect(self._on_settings_changed)
        self.bus.app_exit.connect(self._cleanup)

    # -- polling tick ----------------------------------------------------------

    def _on_poll_tick(self) -> None:
        for name, is_event in list(self._is_event.items()):
            if is_event:
                continue
            hotkey_str = self._hotkey_strs.get(name, "")
            if not hotkey_str:
                continue
            vks = parse_hotkey_to_vk(hotkey_str)
            if not vks:
                continue

            # Check if all keys in the combination are pressed
            still_pressed = True
            for vk in vks:
                # GetAsyncKeyState returns MSB set if key is currently down
                if not (self._user32.GetAsyncKeyState(vk) & 0x8000):
                    still_pressed = False
                    break

            was_held = self._held.get(name, False)
            if still_pressed and not was_held:
                self._held[name] = True
                log.debug("State hotkey '%s' pressed: %s", name, hotkey_str)
                self._emit_press(name)
            elif not still_pressed and was_held:
                self._held[name] = False
                log.debug("State hotkey '%s' released: %s", name, hotkey_str)
                self._emit_release(name)

    # -- registration helpers --------------------------------------------------

    def _register_win32(self, name: str, hotkey_str: str) -> bool:
        vks = parse_hotkey_to_vk(hotkey_str)
        if not vks:
            log.debug("No VKs parsed for hotkey '%s': '%s' — skipping", name, hotkey_str)
            return False
        mod, main_key = _split_modifiers_and_key(vks)
        if not main_key:
            log.warning(
                "Could not determine main VK for hotkey '%s': '%s' — skipping",
                name, hotkey_str,
            )
            return False
        hk_id = _NAME_TO_ID[name]
        ok = self._hotkey_thread.register_hotkey(hk_id, mod, main_key)
        if ok:
            log.info(
                "RegisterHotKey OK  '%s': '%s'  mod=0x%x  vk=%#x",
                name, hotkey_str, mod, main_key,
            )
        else:
            log.warning(
                "RegisterHotKey FAIL '%s': '%s'  mod=0x%x  vk=%#x  "
                "(another app may own this combo, or it is an invalid combination)",
                name, hotkey_str, mod, main_key,
            )
        return ok

    def _unregister_win32(self, name: str) -> None:
        hk_id = _NAME_TO_ID.get(name)
        if hk_id is not None:
            self._hotkey_thread.unregister_hotkey(hk_id)

    def _bind(self, name: str, hotkey_str: str, *, is_event: bool) -> None:
        self._is_event[name] = is_event
        self._held[name] = False

        if is_event:
            self._unregister_win32(name)
            if hotkey_str:
                ok = self._register_win32(name, hotkey_str)
                if ok:
                    self._hotkey_strs[name] = hotkey_str
                else:
                    self._hotkey_strs.pop(name, None)
            else:
                self._hotkey_strs.pop(name, None)
                log.debug("Hotkey '%s' has no binding configured — not registered", name)
        else:
            # State-based hotkeys are handled by _on_poll_tick, not RegisterHotKey
            if hotkey_str:
                self._hotkey_strs[name] = hotkey_str
                log.info("State hotkey '%s' bound to '%s' via polling", name, hotkey_str)
            else:
                self._hotkey_strs.pop(name, None)
                log.debug("State hotkey '%s' has no binding configured", name)

    # -- hotkey fired handler (event-based hotkeys only) ------------------------

    def _on_hotkey_fired(self, hk_id: int) -> None:
        name = _ID_TO_NAME.get(hk_id)
        if name is None:
            log.debug("Unknown hotkey id=%d received — ignoring", hk_id)
            return
        log.debug("WM_HOTKEY id=%d  name=%s", hk_id, name)

        if self._is_event.get(name, False):
            if name == "ocr":
                self.bus.capture_hotkey_pressed.emit()

    # -- state-based press / release emitters ----------------------------------

    def _emit_press(self, name: str) -> None:
        if name == "interact":
            self.bus.toolbar_interact_pressed.emit()
        elif name == "drag":
            self.bus.toolbar_drag_pressed.emit()

    def _emit_release(self, name: str) -> None:
        if name == "interact":
            self.bus.toolbar_interact_released.emit()
        elif name == "drag":
            self.bus.toolbar_drag_released.emit()

    # -- settings / cleanup ----------------------------------------------------

    @pyqtSlot(str, object)
    def _on_settings_changed(self, key: str, value: object) -> None:
        if key == "ocr_hotkey":
            self._bind("ocr", str(value) if value else "", is_event=True)
        elif key == "toolbar_interact_hotkey":
            self._bind("interact", str(value) if value else "", is_event=False)
        elif key == "toolbar_drag_hotkey":
            self._bind("drag", str(value) if value else "", is_event=False)

    def _cleanup(self) -> None:
        # Stop polling
        self._poll_timer.stop()
        
        # Unregister all active RegisterHotKey bindings
        for name, is_event in list(self._is_event.items()):
            if is_event:
                self._unregister_win32(name)
                
        self._hotkey_thread.stop()
