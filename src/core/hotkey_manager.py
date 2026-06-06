"""
src/core/hotkey_manager.py
GlobalHotkeyManager — Integrates the `keyboard` module with PyQt EventBus to trigger actions system-wide.
"""
import logging
import ctypes
import time
from PyQt6.QtCore import QObject, QThread, pyqtSlot, pyqtSignal

from src.core.settings import SettingsManager
from src.core.events import EventBus

log = logging.getLogger(__name__)

def parse_hotkey_to_vk(hotkey_str: str) -> list[int]:
    if not hotkey_str: return []
    key_str = hotkey_str.strip().lower()
    mapping = {
        'ctrl': 0x11, 'left ctrl': 0xA2, 'right ctrl': 0xA3,
        'alt': 0x12, 'left alt': 0xA4, 'right alt': 0xA5,
        'shift': 0x10, 'left shift': 0xA0, 'right shift': 0xA1,
        'windows': 0x5B, 'left windows': 0x5B, 'right windows': 0x5C,
        'esc': 0x1B, 'tab': 0x09, 'enter': 0x0D, 'space': 0x20,
        'backspace': 0x08, 'delete': 0x2E, 'insert': 0x2D,
        'home': 0x24, 'end': 0x23, 'page up': 0x21, 'page down': 0x22,
        'up': 0x26, 'down': 0x28, 'left': 0x25, 'right': 0x27,
        'caps lock': 0x14, 'num lock': 0x90, 'scroll lock': 0x91,
    }
    
    parts = key_str.split('+')
    vks = []
    for part in parts:
        p = part.strip()
        if p in mapping:
            vks.append(mapping[p])
        elif len(p) == 1:
            if 'a' <= p <= 'z':
                vks.append(ord(p.upper()))
            elif '0' <= p <= '9':
                vks.append(ord(p))
            else:
                # Basic symbols aren't reliably mapped without VkKeyScan,
                # but standard keyboard module mostly uses names.
                pass
        elif len(p) in (2, 3) and p.startswith('f') and p[1:].isdigit():
            vks.append(0x70 + int(p[1:]) - 1)
    return vks

class HotkeyPollingThread(QThread):
    hotkey_triggered = pyqtSignal(str)
    hotkey_state_changed = pyqtSignal(str, bool)

    def __init__(self):
        super().__init__()
        self._running = True
        self.bindings = {}  # name -> list of VKs
        self.states = {}    # name -> bool
        self.is_event = {}  # name -> bool (event vs state change)
        import sys
        self.is_windows = (sys.platform == "win32")

    def run(self):
        if not self.is_windows:
            log.warning("Absolute global hotkeys (GetAsyncKeyState) only supported on Windows.")
            return

        user32 = ctypes.windll.user32
        while self._running:
            for name, vks in list(self.bindings.items()):
                if not vks:
                    continue
                # Check if ALL keys in combination are currently pressed (MSB set)
                all_pressed = True
                for vk in vks:
                    if not (user32.GetAsyncKeyState(vk) & 0x8000):
                        all_pressed = False
                        break
                
                prev = self.states.get(name, False)
                if all_pressed and not prev:
                    self.states[name] = True
                    if self.is_event.get(name, False):
                        self.hotkey_triggered.emit(name)
                    else:
                        self.hotkey_state_changed.emit(name, True)
                elif not all_pressed and prev:
                    self.states[name] = False
                    if not self.is_event.get(name, False):
                        self.hotkey_state_changed.emit(name, False)
            
            time.sleep(0.015) # ~66 Hz polling

    def stop(self):
        self._running = False
        self.wait()

class GlobalHotkeyManager(QObject):
    """
    Manages global keyboard shortcuts using GetAsyncKeyState polling.
    Automatically re-binds when settings change.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.sm = SettingsManager.instance()
        self.bus = EventBus.instance()
        
        self.poll_thread = HotkeyPollingThread()
        self.poll_thread.hotkey_triggered.connect(self._on_hotkey_triggered)
        self.poll_thread.hotkey_state_changed.connect(self._on_state_changed)
        
        self.bus.settings_changed.connect(self._on_settings_changed)
        self.bus.app_exit.connect(self._cleanup)
        
        self._update_binding("ocr", self.sm.ocr_hotkey, is_event=True)
        self._update_binding("interact", self.sm.toolbar_interact_hotkey, is_event=False)
        self._update_binding("drag", self.sm.toolbar_drag_hotkey, is_event=False)
        
        self.poll_thread.start()
        
    def _update_binding(self, name: str, hotkey: str, is_event: bool) -> None:
        vks = parse_hotkey_to_vk(hotkey)
        self.poll_thread.bindings[name] = vks
        self.poll_thread.is_event[name] = is_event
        self.poll_thread.states[name] = False
        log.info(f"Hotkey '{name}' hooked: {hotkey} (VKs: {vks})")
            
    def _on_hotkey_triggered(self, name: str) -> None:
        if name == "ocr":
            log.debug("Global OCR hotkey triggered via polling!")
            self.bus.capture_hotkey_pressed.emit()
            
    def _on_state_changed(self, name: str, is_pressed: bool) -> None:
        if name == "interact":
            if is_pressed:
                self.bus.toolbar_interact_pressed.emit()
            else:
                self.bus.toolbar_interact_released.emit()
        elif name == "drag":
            if is_pressed:
                self.bus.toolbar_drag_pressed.emit()
            else:
                self.bus.toolbar_drag_released.emit()
        
    @pyqtSlot(str, object)
    def _on_settings_changed(self, key: str, value: object) -> None:
        if key == "ocr_hotkey":
            self._update_binding("ocr", str(value), is_event=True)
        elif key == "toolbar_interact_hotkey":
            self._update_binding("interact", str(value), is_event=False)
        elif key == "toolbar_drag_hotkey":
            self._update_binding("drag", str(value), is_event=False)
            
    def _cleanup(self) -> None:
        if self.poll_thread.isRunning():
            self.poll_thread.stop()
