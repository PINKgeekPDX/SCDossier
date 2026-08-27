"""
src/main.py
Application Entry Point.
"""

# Workaround removed to prevent "cannot load module more than once per process" in PyInstaller 3.12

import os
import sys
import logging
import subprocess
import time
import warnings

# Suppress RequestsDependencyWarning and ONNX Runtime Windows 11 warnings
try:
    from requests.exceptions import RequestsDependencyWarning
    warnings.filterwarnings("ignore", category=RequestsDependencyWarning)
except ImportError:
    pass
warnings.filterwarnings("ignore", category=UserWarning, module="onnxruntime.*")
warnings.filterwarnings("ignore", message=".*Windows.*version.*ONNX Runtime.*")
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QRect, QSharedMemory, Qt

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
from src.ui.splash.splash_screen import SplashScreen

log = logging.getLogger(__name__)


def _install_crash_handlers(log_path):
    """Install global exception and Qt message handlers to log crashes."""
    import traceback
    from PyQt6.QtCore import qInstallMessageHandler, QtMsgType

    def _excepthook(exc_type, exc_value, exc_tb):
        msg = "UNHANDLED EXCEPTION:\n" + "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        log.critical(msg)
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(msg)
        except Exception:
            pass

    def _qt_message_handler(mode, context, message):
        if mode == QtMsgType.QtFatalMsg or mode == QtMsgType.QtCriticalMsg:
            log.critical("Qt[%s] %s (file=%s line=%d)", mode.name, message, context.file, context.line)
        elif mode == QtMsgType.QtWarningMsg:
            log.warning("Qt[WARN] %s", message)

    sys.excepthook = _excepthook
    qInstallMessageHandler(_qt_message_handler)


def main():
    # 1. Setup Core Infrastructure
    from src.core.paths import PathManager
    pm = PathManager.instance()
    setup_logging(pm.logs_dir / "app.log")
    log.info("Starting SC Dossier...")
    _install_crash_handlers(str(pm.logs_dir / "app.log"))

    # Initialize Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName("SC Dossier")
    app.setOrganizationName("PINK")
    
    from PyQt6.QtGui import QIcon
    from src.core.paths import get_asset_path
    appicon_path = get_asset_path("assets/appicon.png")
    if os.path.exists(appicon_path):
        app.setWindowIcon(QIcon(appicon_path))

    # 1.5 Single Instance Lock
    app._single_instance_lock = QSharedMemory("SCDossierSingleInstanceLock")
    if app._single_instance_lock.attach():
        # Verify the other process is actually alive (not a stale lock from a crash)
        import ctypes
        app._single_instance_lock.lock()
        try:
            raw_pid = bytes(app._single_instance_lock.data()[:4])
            existing_pid = int.from_bytes(raw_pid, byteorder='little')
        except Exception:
            existing_pid = 0
        app._single_instance_lock.unlock()

        process_alive = False
        if existing_pid > 0:
            try:
                # OpenProcess with PROCESS_QUERY_LIMITED_INFORMATION (0x1000)
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.OpenProcess(0x1000, False, existing_pid)
                if handle:
                    kernel32.CloseHandle(handle)
                    process_alive = True
            except Exception:
                pass

        if process_alive:
            log.warning("SC Dossier is already running. Exiting this instance.")
            QMessageBox.information(None, "SC Dossier", "SC Dossier is already running in the background.\n\nCheck your system tray or click the overlay to open it.")
            sys.exit(0)
        else:
            log.warning("Stale single-instance lock found (PID %d dead). Reclaiming.", existing_pid)
            # Detach from stale shared memory so we can recreate it
            app._single_instance_lock.detach()
        
    if not app._single_instance_lock.isAttached():
        if not app._single_instance_lock.create(4):
            log.error(f"Failed to create single instance lock: {app._single_instance_lock.errorString()}")
            sys.exit(1)

    # Write current PID into shared memory for liveness checks by future instances
    import ctypes
    app._single_instance_lock.lock()
    try:
        pid_bytes = os.getpid().to_bytes(4, byteorder='little')
        buf = app._single_instance_lock.data()
        buf[:4] = pid_bytes
    except Exception:
        pass
    app._single_instance_lock.unlock()

    # Launch Splash Screen
    splash = SplashScreen()
    splash.fade_in()
    splash.update_progress("Initializing core systems...", 10)

    # Ensure Settings are loaded
    splash.update_progress("Loading user settings...", 30)
    sm = SettingsManager.initialize(pm.settings_file)

    # 2. Load SCPINK Design System
    splash.update_progress("Loading SCPINK Design System...", 50)
    register_fonts()
    
    from src.ui.theme import palette
    palette.apply_overrides(sm.theme_palette_overrides)
    
    app.setStyleSheet(build_stylesheet(
        font_scale=sm.font_size_scaling,
        app_font_family=sm.app_font_family
    ))


    # 3. Instantiate Architecture
    splash.update_progress("Instantiating core architecture...", 65)
    controller = AppController()
    main_window = MainWindow(controller)
    controller.set_main_window(main_window)
    toolbar = OverlayToolbar()
    toolbar.set_main_window_ref(main_window)

    # Create tray icon with app icon
    app_icon = QIcon(appicon_path) if os.path.exists(appicon_path) else QIcon()
    # Also set the app icon for taskbar purposes
    if os.path.exists(appicon_path):
        app_icon_ico = QIcon()
        ico_path = get_asset_path("assets/appicon.ico")
        if os.path.exists(ico_path):
            app_icon_ico = QIcon(ico_path)
            app.setWindowIcon(app_icon_ico)
        else:
            app.setWindowIcon(app_icon)
    tray_icon = TrayIcon(app_icon)

    active_selector = None

    # 4. Connect Toolbar Events
    splash.update_progress("Wiring up event bus...", 80)
    def _show_main_window():
        main_window.show()
        main_window.raise_()
        main_window.activateWindow()
        toolbar.hide()
        # Always navigate to search tab when showing window
        EventBus.instance().navigate_to_tab.emit("search")

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
            main_window.show()
            main_window.raise_()
            main_window.activateWindow()
            toolbar.hide()

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

    def _open_settings():
        _show_main_window()
        toolbar.hide()
        EventBus.instance().navigate_to_tab.emit("settings")

    def _open_logs():
        import os
        os.startfile(pm.logs_dir)

    def _open_archive():
        import os
        os.startfile(pm.archived_root)

    def _toggle_main_window():
        if main_window.isVisible():
            _hide_main_window()
        else:
            _show_main_window()

    # 6. Connect Tray Events
    tray_icon.show_main_requested.connect(_toggle_main_window)
    tray_icon.menu.aboutToShow.connect(
        lambda: tray_icon.action_open_dossier.setText("Hide SC Dossier" if main_window.isVisible() else "Show SC Dossier")
    )
    tray_icon.quick_capture_requested.connect(_start_capture)
    tray_icon.open_settings_requested.connect(_open_settings)
    tray_icon.open_logs_requested.connect(_open_logs)
    tray_icon.open_archive_requested.connect(_open_archive)
    def _quit_app():
        log.info("Quit requested — saving settings and exiting.")
        try:
            sm.force_save()
            EventBus.instance().app_exit.emit()
        except Exception:
            pass
        os._exit(0)
    tray_icon.quit_requested.connect(_quit_app)
    tray_icon.show()

    # 7. Restore Positions
    toolbar.restore_position(sm.toolbar_x, sm.toolbar_y, sm.toolbar_edge)

    # Apply toolbar opacity from settings (idle opacity for when SC is not running)
    toolbar.set_opacity(sm.toolbar_idle_opacity)

    # Restore main window geometry
    geom = QRect(sm.window_x, sm.window_y, sm.window_w, sm.window_h)
    if geom.isValid():
        main_window.setGeometry(geom)

    # Connect capture hotkey signal to start capture
    EventBus.instance().capture_hotkey_pressed.connect(_start_capture)

    # App exit handler to clean up hotkeys
    app.aboutToQuit.connect(lambda: EventBus.instance().app_exit.emit())

    # 9. Reputation System — initialized by AppController if enabled.
    # Show splash progress only; actual init is handled by the controller.
    splash.update_progress("Initializing Reputation System...", 90)

    # 10. Global settings_changed listener (hot-reload outside SettingsTab)
    def _on_settings_changed(key: str, value: object) -> None:
        if key in ("font_size_scaling", "theme_palette_overrides", "theme_palette_preview", "app_font_family"):
            if key == "theme_palette_overrides":
                palette.apply_overrides(sm.theme_palette_overrides)

            app.setStyleSheet(build_stylesheet(
                font_scale=sm.font_size_scaling,
                app_font_family=sm.app_font_family
            ))

            for widget in QApplication.topLevelWidgets():
                widget.update()

            EventBus.instance().theme_changed.emit()
        elif key == "auto_hide_toolbar_without_game":
            sc_running = False
            try:
                output = subprocess.check_output(
                    'tasklist /FI "IMAGENAME eq StarCitizen.exe" /NH',
                    shell=True,
                    creationflags=0x08000000
                ).decode()
                if "StarCitizen.exe" in output:
                    sc_running = True
            except Exception:
                pass
            if not sc_running and value is True:
                toolbar.hide()
                _show_main_window()
            elif value is False:
                toolbar.show()
        elif key == "log_level":
            level = logging.DEBUG if str(value) == "debug" else logging.INFO
            logging.getLogger().setLevel(level)

    EventBus.instance().settings_changed.connect(_on_settings_changed)

    splash.update_progress("Startup complete", 100)
    
    # 11. Finish up and fade out
    def _finalize_startup():
        splash.close()

        sc_running = False
        try:
            output = subprocess.check_output(
                'tasklist /FI "IMAGENAME eq StarCitizen.exe" /NH',
                shell=True,
                creationflags=0x08000000  # CREATE_NO_WINDOW
            ).decode()
            if "StarCitizen.exe" in output:
                sc_running = True
        except Exception:
            pass

        if sc_running:
            toolbar.show()
            main_window.hide()
        elif sm.auto_hide_toolbar_without_game:
            toolbar.hide()
            _show_main_window()
        else:
            toolbar.show()
            _show_main_window()

    splash.fade_out_finished.connect(_finalize_startup)
    splash.fade_out()

    log.info("SC Dossier fully initialized. Entering event loop.")
    start_time = time.time()
    exit_code = app.exec()
    end_time = time.time()
    log.info(f"App exited with code {exit_code} after {end_time-start_time:.1f} seconds")


if __name__ == "__main__":
    main()
