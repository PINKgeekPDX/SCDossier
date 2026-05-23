"""
src/ui/widgets/confirm_dialog.py
ConfirmDialog — styled modal dialog for destructive action confirmation.

Features:
- GlassCard container aesthetic
- Custom title, message, confirm/cancel buttons
- Auto-centers on parent widget
- Returns bool result via exec()
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
)

from src.ui.theme import palette as P
from src.ui.theme.fonts import label_caps, font_inter


class ConfirmDialog(QDialog):
    """
    Styled confirmation dialog.

    Usage:
        dlg = ConfirmDialog(
            title="DELETE PROFILE",
            message="Permanently delete PINKgeekPDX and all associated files?",
            confirm_text="DELETE",
            danger=True,
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            do_delete()

    Args:
        title:        Dialog header text.
        message:      Body message text.
        confirm_text: Confirm button label (default "CONFIRM").
        cancel_text:  Cancel button label (default "CANCEL").
        danger:       If True, confirm button uses danger styling.
        parent:       Parent widget.
    """

    def __init__(
        self,
        title: str = "CONFIRM ACTION",
        message: str = "",
        confirm_text: str = "CONFIRM",
        cancel_text: str = "CANCEL",
        danger: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setMaximumWidth(520)

        self._build_ui(title, message, confirm_text, cancel_text, danger)

        # Center on parent
        if parent:
            parent_rect = parent.geometry()
            self.move(
                parent_rect.center().x() - self.width() // 2,
                parent_rect.center().y() - self.height() // 2,
            )

    def _build_ui(
        self,
        title: str,
        message: str,
        confirm_text: str,
        cancel_text: str,
        danger: bool,
    ) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Container widget with glass style
        container = QWidget(self)
        container.setObjectName("ConfirmContainer")
        container.setStyleSheet(f"""
            #ConfirmContainer {{
                background-color: rgba(10, 29, 41, 0.97);
                border: 1px solid rgba(0, 170, 255, 0.30);
                border-radius: 6px;
            }}
        """)
        outer.addWidget(container)

        inner = QVBoxLayout(container)
        inner.setContentsMargins(28, 24, 28, 24)
        inner.setSpacing(16)

        # Title
        title_lbl = QLabel(title.upper())
        title_lbl.setFont(label_caps())
        title_lbl.setStyleSheet(
            f"color: {P.HAZARD_RED if danger else P.PRIMARY}; background: transparent; letter-spacing: 0.15em;"
        )

        # Divider
        divider = QWidget()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: {P.OUTLINE_VARIANT};")

        # Message
        msg_lbl = QLabel(message)
        msg_lbl.setFont(font_inter(14))
        msg_lbl.setStyleSheet(f"color: {P.ON_SURFACE}; background: transparent;")
        msg_lbl.setWordWrap(True)
        msg_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch(1)

        # Only create cancel button if cancel_text is provided
        if cancel_text:
            cancel_btn = QPushButton(cancel_text)
            cancel_btn.setProperty("class", "ghost")
            cancel_btn.setMinimumWidth(100)
            cancel_btn.clicked.connect(self.reject)
            btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton(confirm_text)
        confirm_btn.setProperty("class", "danger" if danger else "primary")
        confirm_btn.setMinimumWidth(100)
        confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(confirm_btn)

        inner.addWidget(title_lbl)
        inner.addWidget(divider)
        inner.addWidget(msg_lbl)
        inner.addSpacing(8)
        inner.addLayout(btn_layout)

    def paintEvent(self, event) -> None:
        """Paint bracket corners on the dialog border."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        s = 10
        pen = QPen(QColor(P.BRACKET_COLOR), 2)
        painter.setPen(pen)
        x0, y0 = rect.left(), rect.top()
        x1, y1 = rect.right(), rect.bottom()
        for px, py, dx, dy in [(x0,y0,1,1),(x1,y0,-1,1),(x0,y1,1,-1),(x1,y1,-1,-1)]:
            painter.drawLine(px, py, px + dx*s, py)
            painter.drawLine(px, py, px, py + dy*s)
        painter.end()


def show_error_dialog(title: str, message: str, parent: QWidget | None = None) -> None:
    """Convenience function to show a non-interactive error message dialog."""
    dlg = ConfirmDialog(
        title=title,
        message=message,
        confirm_text="OK",
        cancel_text="",
        danger=True,
        parent=parent,
    )
    dlg.exec()


def show_confirm(
    title: str,
    message: str,
    parent: QWidget | None = None,
    danger: bool = False,
) -> bool:
    """Convenience: show a confirm dialog, return True if user confirmed."""
    dlg = ConfirmDialog(
        title=title,
        message=message,
        danger=danger,
        parent=parent,
    )
    return dlg.exec() == QDialog.DialogCode.Accepted
