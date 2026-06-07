"""
src/ui/widgets/keybind_dialog.py
KeybindDetectDialog — Captures a custom keybind combination using Qt-native
key event handling. No third-party library required.

Uses QDialog.grabKeyboard() to capture all keyboard input while listening,
then maps Qt key codes to the same string format consumed by
GlobalHotkeyManager.parse_hotkey_to_vk() (e.g. "left alt", "ctrl+f12").
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QKeyEvent

from src.ui.theme import palette as P
from src.ui.theme.fonts import font_inter


# ---------------------------------------------------------------------------
# Qt Key → hotkey string name mapping
# Must match the keys recognised by parse_hotkey_to_vk() in hotkey_manager.py
# ---------------------------------------------------------------------------

_QT_KEY_TO_NAME: dict[int, str] = {
    # Modifier keys (treated as main keys when used alone)
    Qt.Key.Key_Control.value:   "left ctrl",
    Qt.Key.Key_Alt.value:       "left alt",
    Qt.Key.Key_Shift.value:     "left shift",
    Qt.Key.Key_Meta.value:      "left windows",

    # Function keys F1–F24
    **{(Qt.Key.Key_F1.value + i): f"f{i + 1}" for i in range(24)},

    # Navigation
    Qt.Key.Key_Escape.value:    "esc",
    Qt.Key.Key_Tab.value:       "tab",
    Qt.Key.Key_Return.value:    "enter",
    Qt.Key.Key_Enter.value:     "enter",
    Qt.Key.Key_Space.value:     "space",
    Qt.Key.Key_Backspace.value: "backspace",
    Qt.Key.Key_Delete.value:    "delete",
    Qt.Key.Key_Insert.value:    "insert",
    Qt.Key.Key_Home.value:      "home",
    Qt.Key.Key_End.value:       "end",
    Qt.Key.Key_PageUp.value:    "page up",
    Qt.Key.Key_PageDown.value:  "page down",
    Qt.Key.Key_Up.value:        "up",
    Qt.Key.Key_Down.value:      "down",
    Qt.Key.Key_Left.value:      "left",
    Qt.Key.Key_Right.value:     "right",

    # Lock keys
    Qt.Key.Key_CapsLock.value:  "caps lock",
    Qt.Key.Key_NumLock.value:   "num lock",
    Qt.Key.Key_ScrollLock.value:"scroll lock",

    # Numpad
    Qt.Key.Key_0.value:  "0",
    Qt.Key.Key_1.value:  "1",
    Qt.Key.Key_2.value:  "2",
    Qt.Key.Key_3.value:  "3",
    Qt.Key.Key_4.value:  "4",
    Qt.Key.Key_5.value:  "5",
    Qt.Key.Key_6.value:  "6",
    Qt.Key.Key_7.value:  "7",
    Qt.Key.Key_8.value:  "8",
    Qt.Key.Key_9.value:  "9",
}

# Qt modifier flags → display/storage name
_QT_MOD_TO_NAME: list[tuple[Qt.KeyboardModifier, str]] = [
    (Qt.KeyboardModifier.ControlModifier, "left ctrl"),
    (Qt.KeyboardModifier.AltModifier,     "left alt"),
    (Qt.KeyboardModifier.ShiftModifier,   "left shift"),
    (Qt.KeyboardModifier.MetaModifier,    "left windows"),
]

# Modifier key codes — keys that are modifiers themselves
_MODIFIER_KEYS: frozenset[int] = frozenset({
    Qt.Key.Key_Control.value,
    Qt.Key.Key_Alt.value,
    Qt.Key.Key_Shift.value,
    Qt.Key.Key_Meta.value,
    Qt.Key.Key_AltGr.value,
})


def _qt_event_to_hotkey_str(event: QKeyEvent) -> str:
    """
    Convert a Qt key event into a hotkey string compatible with
    parse_hotkey_to_vk(), e.g. "left ctrl", "left alt+f12", "ctrl+z".

    Modifier ordering: ctrl → alt → shift → windows → main_key.
    """
    mods = event.modifiers()
    key = event.key()

    parts: list[str] = []

    # Build modifier prefix
    for qt_mod, name in _QT_MOD_TO_NAME:
        if mods & qt_mod:
            # Skip the modifier itself being added as a prefix when it IS the main key
            # (e.g. pressing Alt alone should yield "left alt", not "left alt+left alt")
            if key in _MODIFIER_KEYS:
                continue
            parts.append(name)

    # Main key
    key_name = _QT_KEY_TO_NAME.get(key)
    if key_name is None:
        # Single printable character (a-z, 0-9, punctuation)
        text = event.text().lower().strip()
        if text and len(text) == 1 and text.isprintable():
            key_name = text

    # If it's a pure modifier key press (e.g. Left Alt alone), name it correctly
    if key in _MODIFIER_KEYS and key_name:
        parts = [key_name]  # Only the modifier itself, no prefix
    elif key_name:
        parts.append(key_name)

    return "+".join(parts)


class KeybindDetectDialog(QDialog):
    """
    Modal dialog that listens for a key combination and returns the hotkey
    string on accept.

    Uses Qt-native keyboard capture (grabKeyboard / keyPressEvent /
    keyReleaseEvent) — no third-party keyboard library required.
    """

    def __init__(self, parent=None, current_keybind: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Detect Hotkey")
        self.setFixedSize(340, 165)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        self.detected_keybind = ""
        self._is_listening = True
        self._pressed_names: list[str] = []

        # ---- layout ----
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 14, 16, 12)

        self.instruction_label = QLabel("Press your desired key or key combination...")
        self.instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instruction_label.setFont(font_inter(10))
        self.instruction_label.setStyleSheet(
            f"color: {P.PRIMARY}; font-weight: bold; background: transparent; border: none;"
        )
        self.instruction_label.setWordWrap(True)
        layout.addWidget(self.instruction_label)

        self.keybind_label = QLabel(
            current_keybind.upper() if current_keybind else "Listening..."
        )
        self.keybind_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.keybind_label.setFont(font_inter(14))
        self.keybind_label.setMinimumHeight(36)
        self.keybind_label.setStyleSheet(
            f"font-size: 14px; margin: 4px 0; "
            f"border: 1px solid {P.OUTLINE_VARIANT}; "
            f"border-radius: 4px; padding: 6px 10px; "
            f"background: rgba(5, 11, 15, 0.85); "
            f"color: {P.ON_SURFACE};"
        )
        layout.addWidget(self.keybind_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        _btn_style = f"""
            QPushButton {{
                background: rgba(0, 170, 255, 0.12);
                color: {P.ON_SURFACE};
                border: 1px solid {P.PRIMARY_CONTAINER};
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 10px;
                font-weight: 600;
                min-height: 26px;
            }}
            QPushButton:hover {{ background: rgba(0, 170, 255, 0.25); }}
            QPushButton:pressed {{ background: rgba(0, 170, 255, 0.35); }}
            QPushButton:disabled {{ color: {P.TEXT_DIM}; border-color: {P.OUTLINE_VARIANT}; background: transparent; }}
        """

        self.retry_btn = QPushButton("RETRY")
        self.retry_btn.setStyleSheet(_btn_style)
        self.retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.retry_btn.clicked.connect(self._retry_listening)

        self.set_btn = QPushButton("SET")
        self.set_btn.setStyleSheet(_btn_style)
        self.set_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_btn.clicked.connect(self.accept)
        self.set_btn.setEnabled(False)

        self.cancel_btn = QPushButton("CANCEL")
        self.cancel_btn.setStyleSheet(_btn_style)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.retry_btn)
        btn_layout.addWidget(self.set_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        # Grab keyboard so all key events come here while dialog is open
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.grabKeyboard()

    def hideEvent(self, event) -> None:
        try:
            self.releaseKeyboard()
        except Exception:
            pass
        super().hideEvent(event)

    def event(self, event) -> bool:
        if getattr(self, "_is_listening", False) and event.type() in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            if event.type() == QEvent.Type.KeyPress:
                self.keyPressEvent(event)
            else:
                self.keyReleaseEvent(event)
            return True
        return super().event(event)

    # -- key detection -------------------------------------------------------

    def _retry_listening(self) -> None:
        """Reset and start listening for a new combination."""
        self.detected_keybind = ""
        self._is_listening = True
        self._pressed_names.clear()
        self.keybind_label.setText("Listening...")
        self.set_btn.setEnabled(False)
        self.grabKeyboard()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if not self._is_listening:
            return
        hotkey = _qt_event_to_hotkey_str(event)
        if hotkey:
            # Show live feedback while keys are held
            self.keybind_label.setText(hotkey.upper())
            self._current_combo = hotkey
        event.accept()

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if not self._is_listening:
            return

        # Capture the combo that was displayed when the first key is released
        combo = getattr(self, "_current_combo", "")
        if combo:
            self.detected_keybind = combo
            self.keybind_label.setText(combo.upper())
            self._is_listening = False
            self._current_combo = ""
            self.releaseKeyboard()
            self.set_btn.setEnabled(True)
            self.retry_btn.setEnabled(True)

        event.accept()

    # -- dialog accept / reject ----------------------------------------------

    def reject(self) -> None:
        self.releaseKeyboard()
        super().reject()

    def accept(self) -> None:
        self.releaseKeyboard()
        super().accept()

    def get_keybind(self) -> str:
        """Return the detected keybind string, or empty string if none."""
        return self.detected_keybind
