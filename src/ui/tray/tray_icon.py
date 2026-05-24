"""
src/ui/tray/tray_icon.py
TrayIcon — System tray management for SC Dossier.
"""

from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QWidget, QApplication
from PyQt6.QtCore import QObject, pyqtSignal


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
        
        self.setToolTip("SC Dossier — Right-click for options")
        
        # Build Context Menu
        self.menu = QMenu()
        
        self.action_show_toolbar = QAction("Show Toolbar")
        self.action_show_toolbar.setToolTip("Display the overlay toolbar on screen")
        self.action_show_toolbar.triggered.connect(self.show_toolbar_requested.emit)
        
        self.action_open_dossier = QAction("Open Dossier")
        self.action_open_dossier.setToolTip("Open the main SC Dossier application window")
        self.action_open_dossier.triggered.connect(self.show_main_requested.emit)
        
        self.action_quick_capture = QAction("Quick Capture")
        self.action_quick_capture.setToolTip("Start an OCR screen capture session")
        self.action_quick_capture.triggered.connect(self.quick_capture_requested.emit)
        
        self.action_settings = QAction("Settings")
        self.action_settings.setToolTip("Open application settings")
        self.action_settings.triggered.connect(self.open_settings_requested.emit)
        
        self.action_quit = QAction("Quit")
        self.action_quit.setToolTip("Exit SC Dossier completely")
        self.action_quit.triggered.connect(self.quit_requested.emit)
        
        self.menu.addAction(self.action_show_toolbar)
        self.menu.addAction(self.action_open_dossier)
        self.menu.addAction(self.action_quick_capture)
        self.menu.addAction(self.action_settings)
        self.menu.addSeparator()
        self.menu.addAction(self.action_quit)
        
        self.setContextMenu(self.menu)
        
        # Handle double click
        self.activated.connect(self._on_activated)
        
    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_main_requested.emit()