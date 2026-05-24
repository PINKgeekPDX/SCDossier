"""
src/ui/tray/tray_icon.py
TrayIcon — System tray management for SC Dossier.
"""

from PyQt6.QtGui import QIcon, QAction, QFont
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QWidget, QApplication
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from src.core.settings import SettingsManager
from src.core.paths import get_asset_path


class TrayIcon(QSystemTrayIcon):
    """
    Application system tray icon.
    Provides background running and context menu for quit/restore.
    """

    show_main_requested = pyqtSignal()
    show_toolbar_requested = pyqtSignal()
    quick_capture_requested = pyqtSignal()
    open_settings_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, icon: QIcon, parent: QObject | None = None) -> None:
        super().__init__(icon, parent)
        
        self._settings = SettingsManager.instance()
        self.setToolTip("SC Dossier — Right-click for options")
        
        # Build Context Menu
        self.menu = QMenu()
        self.menu.setStyleSheet("""
            QMenu {
                background-color: rgba(10, 20, 30, 0.95);
                border: 1px solid #00AAFF;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                color: #E0E0E0;
                padding: 6px 12px;
                border-radius: 2px;
                font-family: "Inter", "Segoe UI", Arial, sans-serif;
                font-size: 12px;
            }
            QMenu::item:selected {
                background-color: rgba(0, 170, 255, 0.2);
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background: #00AAFF;
                margin: 4px 8px;
            }
        """)
        
        # Main action - Open Dossier (primary action)
        self.action_open_dossier = QAction("Open Dossier", self)
        self.action_open_dossier.setToolTip("Open the main SC Dossier application window")
        self.action_open_dossier.setIcon(QIcon(get_asset_path("assets/appicon.png")))
        self.action_open_dossier.triggered.connect(self.show_main_requested.emit)
        self.menu.addAction(self.action_open_dossier)
        
        # Toolbar toggle
        self.action_show_toolbar = QAction("Show Toolbar", self)
        self.action_show_toolbar.setToolTip("Display the overlay toolbar on screen")
        self.action_show_toolbar.triggered.connect(self.show_toolbar_requested.emit)
        self.menu.addAction(self.action_show_toolbar)
        
        # Quick capture
        self.action_quick_capture = QAction("Quick Capture", self)
        self.action_quick_capture.setToolTip("Start an OCR screen capture session")
        self.action_quick_capture.triggered.connect(self.quick_capture_requested.emit)
        self.menu.addAction(self.action_quick_capture)
        
        self.menu.addSeparator()
        
        # Settings
        self.action_settings = QAction("Settings", self)
        self.action_settings.setToolTip("Open application settings")
        self.action_settings.triggered.connect(self.open_settings_requested.emit)
        self.menu.addAction(self.action_settings)
        
        # Version info
        version_action = QAction(f"v{self._get_version()}", self)
        version_action.setEnabled(False)  # Non-clickable info item
        version_action.setFont(QFont("Inter", 9, QFont.Weight.Light))
        version_action.setToolTip("Current version")
        self.menu.addAction(version_action)
        
        self.menu.addSeparator()
        
        # Quit action
        self.action_quit = QAction("Quit", self)
        self.action_quit.setToolTip("Exit SC Dossier completely")
        self.action_quit.triggered.connect(self.quit_requested.emit)
        self.menu.addAction(self.action_quit)
         
        self.setContextMenu(self.menu)
         
        # Handle double click
        self.activated.connect(self._on_activated)
        
    def _get_version(self) -> str:
        """Get application version."""
        try:
            from src.app.constants import APP_VERSION
            return APP_VERSION
        except ImportError:
            return "unknown"
        
    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_main_requested.emit()