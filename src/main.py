"""
src/main.py
Application Entry Point.
"""

import sys
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QRect

from src.core.logger import setup_logging
from src.core.events import EventBus
from src.core.settings import SettingsManager
from src.ui.theme.fonts import register_fonts
from src.ui.theme.stylesheet import build_stylesheet

from src.app.controller import AppController
from src.app.main_window import MainWindow

from src.ui.toolbar.overlay_toolbar import OverlayToolbar
from src.ui.capture.region_selector import RegionSelector
from src.ui.tray.tray_icon import TrayIcon
from src.ui.theme.palette import PRIMARY_CONTAINER

log = logging.getLogger(__name__)


def main():
    # 1. Setup Core Infrastructure
    from src.core.paths import PathManager
    pm = PathManager.instance()
    setup_logging(pm.logs_dir / "app.log")
    log.info("Starting SC Dossier...")

    # Initialize Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName("SC Dossier")
    app.setOrganizationName("PINK")

    # 2. Load Aegis Design System
    register_fonts()
    app.setStyleSheet(build_stylesheet())

    # Ensure Settings are loaded
    sm = SettingsManager.initialize(pm.settings_file)

    # 3. Instantiate Architecture
    controller = AppController()
    main_window = MainWindow(controller)
    toolbar = OverlayToolbar()

    # Create tray icon
    from PyQt6.QtGui import QIcon
    import os
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "icons", "tray.svg")
    tray_icon = TrayIcon(QIcon(icon_path) if os.path.exists(icon_path) else QIcon())

    active_selector = None

    # 4. Connect Toolbar Events
    def _show_main_window():
        main_window.show()
        main_window.raise_()
        main_window.activateWindow()
        toolbar.hide()

    def _hide_main_window():
        main_window.hide()
        toolbar.show()

    def _start_capture():
        nonlocal active_selector
        if active_selector:
            active_selector.close()

        toolbar.hide()
        active_selector = RegionSelector()

        def _on_captured(path):
            EventBus.instance().capture_completed.emit(str(path))
            _show_main_window()

        def _on_cancelled():
            toolbar.show()

        active_selector.capture_completed.connect(_on_captured)
        active_selector.capture_cancelled.connect(_on_cancelled)
        active_selector.show()

    toolbar.expand_requested.connect(_show_main_window)
    toolbar.capture_requested.connect(_start_capture)

    # 5. Connect MainWindow Events
    main_window.title_bar.hide_requested.connect(_hide_main_window)
    main_window.window_hidden.connect(toolbar.show)

    # 6. Connect Tray Events
    tray_icon.show_main_requested.connect(_show_main_window)
    tray_icon.quit_requested.connect(app.quit)
    tray_icon.show()

    # 7. Restore Positions
    toolbar.restore_position(sm.toolbar_x, sm.toolbar_y, sm.toolbar_edge)

    # Apply toolbar opacity from settings
    toolbar.set_opacity(sm.toolbar_opacity)

    # Restore main window geometry
    geom = QRect(sm.window_x, sm.window_y, sm.window_w, sm.window_h)
    if geom.isValid():
        main_window.setGeometry(geom)

    # 8. Launch UI — toolbar only by default
    toolbar.show()

    log.info("SC Dossier fully initialized. Entering event loop.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
