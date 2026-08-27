"""
src/ui/dialogs/org_disambiguation_dialog.py
OrgDisambiguationDialog -- shown when an org search returns multiple candidates.

The user sees a compact list of matching org names/SIDs and picks one.
On accept, the selected SID is available via dialog.selected_sid.
"""

import logging
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QWidget, QFrame,
)

from src.ui.theme import palette as P
from src.ui.theme.fonts import label_caps, font_inter

log = logging.getLogger(__name__)


class OrgDisambiguationDialog(QDialog):
    """
    Modal dialog that presents a list of org candidates and lets the user
    select one to load its full profile.

    Usage:
        dialog = OrgDisambiguationDialog(candidates, parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            sid = dialog.selected_sid
    """

    def __init__(self, candidates: list, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select Organization")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setModal(True)
        self.setMinimumWidth(360)
        self.setMaximumWidth(480)

        self._candidates = candidates
        self.selected_sid: str = ""

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.setStyleSheet(
            "QDialog { background: " + P.SURFACE + "; "
            "border: 1px solid rgba(0,170,255,0.3); border-radius: 6px; }"
        )

        # Header
        header = QLabel("MULTIPLE ORGANIZATIONS FOUND")
        header.setFont(label_caps())
        header.setStyleSheet("color: " + P.PRIMARY + "; background: transparent; border: none;")
        layout.addWidget(header)

        # Subtitle
        sub = QLabel("Select the organization you meant:")
        sub.setFont(font_inter(11))
        sub.setStyleSheet("color: " + P.TEXT_DIM + "; background: transparent; border: none;")
        layout.addWidget(sub)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: rgba(0,170,255,0.15);")
        layout.addWidget(divider)

        # List widget
        self._list = QListWidget()
        self._list.setStyleSheet(
            "QListWidget { background: rgba(10,29,41,0.4); border: 1px solid rgba(0,170,255,0.15); "
            "border-radius: 4px; color: " + P.ON_SURFACE + "; font-family: 'JetBrains Mono', monospace; "
            "font-size: 12px; padding: 4px; outline: none; } "
            "QListWidget::item { padding: 8px 10px; border-radius: 3px; } "
            "QListWidget::item:selected { background: rgba(0,170,255,0.18); color: " + P.PRIMARY + "; } "
            "QListWidget::item:hover { background: rgba(0,170,255,0.08); }"
        )
        self._list.setMinimumHeight(160)
        self._list.setMaximumHeight(300)
        self._list.itemDoubleClicked.connect(self._on_double_click)

        for candidate in self._candidates:
            name = candidate.get("name", "Unknown")
            sid = candidate.get("sid", "")
            item = QListWidgetItem(f"{name}  [{sid}]")
            item.setData(Qt.ItemDataRole.UserRole, sid)
            self._list.addItem(item)

        if self._list.count() > 0:
            self._list.setCurrentRow(0)

        layout.addWidget(self._list)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        btn_cancel = QPushButton("CANCEL")
        btn_cancel.setFixedHeight(32)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(
            "QPushButton { background: transparent; color: " + P.TEXT_DIM + "; "
            "border: 1px solid " + P.OUTLINE_VARIANT + "; border-radius: 4px; "
            "font-size: 11px; font-weight: bold; padding: 4px 16px; } "
            "QPushButton:hover { color: " + P.ON_SURFACE + "; }"
        )
        btn_cancel.clicked.connect(self.reject)

        btn_select = QPushButton("SELECT")
        btn_select.setFixedHeight(32)
        btn_select.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_select.setDefault(True)
        btn_select.setStyleSheet(
            "QPushButton { background: rgba(0,170,255,0.14); color: " + P.PRIMARY + "; "
            "border: 1px solid " + P.PRIMARY + "; border-radius: 4px; "
            "font-size: 11px; font-weight: bold; padding: 4px 16px; } "
            "QPushButton:hover { background: rgba(0,170,255,0.26); } "
            "QPushButton:disabled { color: " + P.TEXT_DIM + "; border-color: " + P.OUTLINE_VARIANT + "; background: transparent; }"
        )
        btn_select.clicked.connect(self._on_select)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_select)
        layout.addLayout(btn_layout)

    def _on_select(self) -> None:
        item = self._list.currentItem()
        if item:
            self.selected_sid = item.data(Qt.ItemDataRole.UserRole) or ""
            self.accept()

    def _on_double_click(self, item) -> None:
        self.selected_sid = item.data(Qt.ItemDataRole.UserRole) or ""
        self.accept()
