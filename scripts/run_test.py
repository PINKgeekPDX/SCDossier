#!/usr/bin/env python
"""Test runner for SC Dossier app - runs app for specified seconds then quits."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_app(duration_seconds: int = 5):
    """Run the app with auto-quit timer."""
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QIcon
    from PyQt6.QtCore import QTimer

    from src.core.paths import PathManager
    from src.core.logger import setup_logging
    from src.app.controller import AppController
    from src.app.main_window import MainWindow
    from src.ui.toolbar.overlay_toolbar import OverlayToolbar
    from src.ui.tray.tray_icon import TrayIcon
    from src.ui.theme.fonts import register_fonts
    from src.ui.theme.stylesheet import build_stylesheet
    from src.core.settings import SettingsManager

    pm = PathManager.instance()
    setup_logging(pm.logs_dir / "app.log")

    app = QApplication(sys.argv)
    app.setApplicationName("SC Dossier")

    register_fonts()
    app.setStyleSheet(build_stylesheet())
    sm = SettingsManager.initialize(pm.settings_file)
    controller = AppController()
    main_window = MainWindow(controller)
    toolbar = OverlayToolbar()

    asset_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "assets", "icons", "tray.svg")
    tray_icon = TrayIcon(QIcon(asset_path) if os.path.exists(asset_path) else QIcon())

    # Auto-quit
    QTimer.singleShot(duration_seconds * 1000, app.quit)

    print(f"App running for {duration_seconds} seconds...")
    return app.exec()

if __name__ == "__main__":
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    sys.exit(run_app(duration))