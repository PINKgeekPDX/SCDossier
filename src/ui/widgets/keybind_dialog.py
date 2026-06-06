"""
src/ui/widgets/keybind_dialog.py
KeybindDetectDialog — A QDialog to capture a custom keybind combination.
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QObject

class KeyboardBridge(QObject):
    hotkey_detected = pyqtSignal(str)

class KeybindDetectDialog(QDialog):
    def __init__(self, parent=None, current_keybind=""):
        super().__init__(parent)
        self.setWindowTitle("Detect Hotkey")
        self.setFixedSize(300, 150)
        
        self.detected_keybind = ""
        self.is_listening = False
        self._hook_callback = None
        
        self.bridge = KeyboardBridge()
        self.bridge.hotkey_detected.connect(self._on_hotkey_detected)
        
        layout = QVBoxLayout(self)
        
        self.instruction_label = QLabel("Press your desired key combination...")
        self.instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instruction_label.setStyleSheet("color: #00AAFF; font-weight: bold;")
        layout.addWidget(self.instruction_label)
        
        self.keybind_label = QLabel(current_keybind if current_keybind else "Listening...")
        self.keybind_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.keybind_label.setStyleSheet("font-size: 16px; margin: 15px 0; border: 1px solid #444; padding: 5px;")
        layout.addWidget(self.keybind_label)
        
        btn_layout = QHBoxLayout()
        
        self.retry_btn = QPushButton("Retry")
        self.retry_btn.clicked.connect(self.retry_listening)
        
        self.set_btn = QPushButton("Set")
        self.set_btn.clicked.connect(self.accept)
        self.set_btn.setEnabled(False)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.retry_btn)
        btn_layout.addWidget(self.set_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self.retry_listening()

    def retry_listening(self):
        import keyboard
        self.detected_keybind = ""
        self.keybind_label.setText("Listening...")
        self.set_btn.setEnabled(False)
        
        self._pressed_keys = set()
        
        if self._hook_callback:
            try:
                keyboard.unhook(self._hook_callback)
            except Exception:
                pass
                
        self.is_listening = True
        self._hook_callback = keyboard.hook(self._on_keyboard_event)

    def _on_keyboard_event(self, event):
        if not self.is_listening:
            return
            
        import keyboard
        if event.event_type == keyboard.KEY_DOWN:
            if event.name not in self._pressed_keys:
                self._pressed_keys.add(event.name)
        elif event.event_type == keyboard.KEY_UP:
            if self._pressed_keys:
                # User released a key, so the combination is complete
                # Order modifiers first
                mods = {"ctrl", "left ctrl", "right ctrl", 
                        "alt", "left alt", "right alt", 
                        "shift", "left shift", "right shift", 
                        "windows", "left windows", "right windows"}
                
                parts = []
                # Add modifiers
                for k in self._pressed_keys:
                    if k in mods:
                        parts.append(k)
                # Add non-modifiers
                for k in self._pressed_keys:
                    if k not in mods:
                        parts.append(k)
                        
                hotkey_str = "+".join(parts)
                self.bridge.hotkey_detected.emit(hotkey_str)
                self._pressed_keys.clear()

    def _on_hotkey_detected(self, hotkey_str: str):
        if not self.is_listening:
            return
            
        self.is_listening = False
        if self._hook_callback:
            import keyboard
            try:
                keyboard.unhook(self._hook_callback)
            except Exception:
                pass
            self._hook_callback = None
            
        self.detected_keybind = hotkey_str
        self.keybind_label.setText(self.detected_keybind.upper())
        self.set_btn.setEnabled(True)

    def reject(self):
        if self._hook_callback:
            import keyboard
            try:
                keyboard.unhook(self._hook_callback)
            except Exception:
                pass
            self._hook_callback = None
        super().reject()

    def accept(self):
        if self._hook_callback:
            import keyboard
            try:
                keyboard.unhook(self._hook_callback)
            except Exception:
                pass
            self._hook_callback = None
        super().accept()

    def get_keybind(self) -> str:
        return self.detected_keybind
