from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtCore import QObject, pyqtSignal

from src.core.settings import SettingsManager
from src.core.paths import get_asset_path
from src.ui.theme import palette as P


class TrayIcon(QSystemTrayIcon):

    show_main_requested = pyqtSignal()
    quick_capture_requested = pyqtSignal()
    open_settings_requested = pyqtSignal()
    open_logs_requested = pyqtSignal()
    open_archive_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, icon: QIcon, parent: QObject | None = None) -> None:
        super().__init__(icon, parent)
        self._settings = SettingsManager.instance()
        self.setToolTip("SC Dossier - Right-click for options")

        self.menu = QMenu()
        self.menu.setStyleSheet(f"""
            QMenu {{
                background-color: {P.rgba(P.SURFACE_CONTAINER_LOW, 0.95)};
                border: 1px solid {P.PRIMARY_CONTAINER};
                border-radius: 4px;
                padding: 4px;
            }}
            QMenu::item {{
                color: {P.ON_SURFACE_VARIANT};
                padding: 6px 12px;
                border-radius: 2px;
                font-family: "Inter", "Segoe UI", Arial, sans-serif;
                font-size: 12px;
            }}
            QMenu::item:selected {{
                background-color: {P.rgba(P.PRIMARY_CONTAINER, 0.2)};
                color: {P.ON_PRIMARY};
            }}
            QMenu::separator {{
                height: 1px;
                background: {P.PRIMARY_CONTAINER};
                margin: 4px 8px;
            }}
        """)

        self.action_open_dossier = QAction("Show SC Dossier", self)
        self.action_open_dossier.setToolTip("Open the main SC Dossier application window")
        self.action_open_dossier.triggered.connect(self.show_main_requested.emit)
        self.menu.addAction(self.action_open_dossier)

        self.action_quick_capture = QAction("Quick Capture", self)
        self.action_quick_capture.setToolTip("Start an OCR screen capture session")
        self.action_quick_capture.triggered.connect(self.quick_capture_requested.emit)
        self.menu.addAction(self.action_quick_capture)

        self.menu.addSeparator()

        self.action_open_archive = QAction("Open Archive Folder", self)
        self.action_open_archive.setToolTip("Open the local folder where profiles are archived")
        self.action_open_archive.triggered.connect(self.open_archive_requested.emit)
        self.menu.addAction(self.action_open_archive)

        self.action_open_logs = QAction("Open Logs Folder", self)
        self.action_open_logs.setToolTip("Open the local folder containing application logs")
        self.action_open_logs.triggered.connect(self.open_logs_requested.emit)
        self.menu.addAction(self.action_open_logs)

        self.menu.addSeparator()

        self.action_settings = QAction("Settings", self)
        self.action_settings.setToolTip("Open application settings")
        self.action_settings.triggered.connect(self.open_settings_requested.emit)
        self.menu.addAction(self.action_settings)

        self.menu.addSeparator()

        self.action_quit = QAction("Quit", self)
        self.action_quit.setToolTip("Exit SC Dossier completely")
        self.action_quit.triggered.connect(self.quit_requested.emit)
        self.menu.addAction(self.action_quit)

        self.setContextMenu(self.menu)
        self.activated.connect(self._on_activated)

    def show_notification(self, title: str, message: str, icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information, duration: int = 5000) -> None:
        if self._settings.show_tray_notifications:
            self.showMessage(title, message, icon, duration)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_main_requested.emit()
