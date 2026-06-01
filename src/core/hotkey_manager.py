"""
src/core/hotkey_manager.py
GlobalHotkeyManager — Integrates the `keyboard` module with PyQt EventBus to trigger actions system-wide.
"""
import logging
import keyboard
from PyQt6.QtCore import QObject, pyqtSlot

from src.core.settings import SettingsManager
from src.core.events import EventBus

log = logging.getLogger(__name__)


class GlobalHotkeyManager(QObject):
    """
    Manages global keyboard shortcuts using the `keyboard` package.
    Automatically re-binds when settings change.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.sm = SettingsManager.instance()
        self.bus = EventBus.instance()
        self._current_hook = None
        
        self.bus.settings_changed.connect(self._on_settings_changed)
        self.bus.app_exit.connect(self._cleanup)
        
        # Initial hook
        self._hook_hotkey(self.sm.ocr_hotkey)
        
    def _hook_hotkey(self, hotkey: str) -> None:
        # Unhook any existing hotkeys first
        if self._current_hook:
            try:
                keyboard.remove_hotkey(self._current_hook)
            except Exception:
                pass
            self._current_hook = None
        
        if not hotkey:
            log.debug("No global OCR hotkey configured.")
            return
            
        try:
            # We don't strictly suppress because suppressing hotkeys can cause
            # issues with certain combinations or anticheats, but it's optional.
            # Using suppress=True means the keystroke isn't sent to the active app.
            self._current_hook = keyboard.add_hotkey(hotkey, self._on_hotkey_triggered, suppress=True)
            log.info("Global hotkey hooked: %s", hotkey)
        except ValueError as e:
            log.error("Failed to hook hotkey '%s': %s", hotkey, e)
            
    def _on_hotkey_triggered(self) -> None:
        """
        Called by the keyboard listener thread when the hotkey is pressed.
        Emitting a pyqtSignal is thread-safe and will queue onto the main thread.
        """
        log.debug("Global hotkey triggered!")
        self.bus.capture_hotkey_pressed.emit()
        
    @pyqtSlot(str, object)
    def _on_settings_changed(self, key: str, value: object) -> None:
        if key == "ocr_hotkey":
            self._hook_hotkey(str(value))
            
    def _cleanup(self) -> None:
        if self._current_hook:
            try:
                keyboard.remove_hotkey(self._current_hook)
            except Exception:
                pass
            self._current_hook = None
