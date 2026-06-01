"""
src/ui/widgets/keybind_dialog.py
KeybindDetectDialog — A QDialog to capture a custom keybind combination.
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent

class KeybindDetectDialog(QDialog):
    def __init__(self, parent=None, current_keybind=""):
        super().__init__(parent)
        self.setWindowTitle("Detect Hotkey")
        self.setFixedSize(300, 150)
        
        self.detected_keybind = ""
        self.is_listening = True
        
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

    def retry_listening(self):
        self.is_listening = True
        self.detected_keybind = ""
        self.keybind_label.setText("Listening...")
        self.set_btn.setEnabled(False)

    def keyPressEvent(self, event: QKeyEvent):
        if not self.is_listening:
            super().keyPressEvent(event)
            return

        key = event.key()
        modifiers = event.modifiers()
        
        # Ignore modifier-only key presses
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return
            
        parts = []
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            parts.append("ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            parts.append("alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            parts.append("shift")
            
        # Get the main key text
        # If it's a normal key, we can use QKeySequence to get its string representation
        # Or just parse the key text
        key_str = ""
        
        # Handle special keys manually to match `keyboard` module format
        special_keys = {
            Qt.Key.Key_Escape: "esc",
            Qt.Key.Key_Tab: "tab",
            Qt.Key.Key_Space: "space",
            Qt.Key.Key_Enter: "enter",
            Qt.Key.Key_Return: "enter",
            Qt.Key.Key_Backspace: "backspace",
            Qt.Key.Key_Delete: "delete",
            Qt.Key.Key_Insert: "insert",
            Qt.Key.Key_Home: "home",
            Qt.Key.Key_End: "end",
            Qt.Key.Key_PageUp: "page up",
            Qt.Key.Key_PageDown: "page down",
            Qt.Key.Key_F1: "f1", Qt.Key.Key_F2: "f2", Qt.Key.Key_F3: "f3",
            Qt.Key.Key_F4: "f4", Qt.Key.Key_F5: "f5", Qt.Key.Key_F6: "f6",
            Qt.Key.Key_F7: "f7", Qt.Key.Key_F8: "f8", Qt.Key.Key_F9: "f9",
            Qt.Key.Key_F10: "f10", Qt.Key.Key_F11: "f11", Qt.Key.Key_F12: "f12",
        }
        
        if key in special_keys:
            key_str = special_keys[key]
        else:
            try:
                k_val = key.value if hasattr(key, 'value') else int(key)
                if Qt.Key.Key_A.value <= k_val <= Qt.Key.Key_Z.value:
                    key_str = chr(k_val).lower()
                elif Qt.Key.Key_0.value <= k_val <= Qt.Key.Key_9.value:
                    key_str = chr(k_val)
                else:
                    from PyQt6.QtGui import QKeySequence
                    key_str = QKeySequence(k_val).toString().lower()
            except Exception:
                if event.text():
                    key_str = event.text().lower()
                    
        if not key_str:
            return  # Could not map key
            
        parts.append(key_str)
        
        self.detected_keybind = "+".join(parts)
        self.keybind_label.setText(self.detected_keybind.upper())
        self.is_listening = False
        self.set_btn.setEnabled(True)
        
        event.accept()

    def get_keybind(self) -> str:
        return self.detected_keybind
