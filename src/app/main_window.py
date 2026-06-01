import os

from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QApplication

from src.core.events import EventBus
from src.core.settings import SettingsManager
from src.ui.widgets.base_window import BaseWindow
from src.ui.widgets.title_bar import CustomTitleBar
from src.ui.widgets.status_bar import CustomStatusBar
from src.ui.widgets.nav_sidebar import NavSidebar

from src.ui.tabs.search_tab import SearchTab
from src.ui.tabs.dossier_tab import DossierTab
from src.ui.tabs.org_tab import OrgTab
from src.ui.tabs.archives_tab import ArchivesTab
from src.ui.tabs.settings_tab import SettingsTab

from src.app.controller import AppController


class MainWindow(BaseWindow):

    window_hidden = pyqtSignal()

    def __init__(self, controller: AppController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller

        from src.core.paths import get_asset_path
        _ico_path = get_asset_path("assets/appicon.ico")
        _png_path = get_asset_path("assets/appicon.png")
        if os.path.exists(_ico_path):
            self.setWindowIcon(QIcon(_ico_path))
        elif os.path.exists(_png_path):
            self.setWindowIcon(QIcon(_png_path))

        self.setWindowTitle("SC Dossier")
        self.resize(1024, 680)
        self.setMinimumSize(860, 560)
        self.setMaximumSize(1920, 1200)

        self._build_ui()
        self._connect_signals()

        sm = SettingsManager.instance()
        last_tab = sm.last_tab
        if last_tab and last_tab != "search":
            self.sidebar.set_active_tab(last_tab)
            self._on_tab_selected(last_tab)
        else:
            self.sidebar.set_active_tab("search")
            self._on_tab_selected("search")

        # Pin on startup if setting enabled
        if sm.pin_on_startup:
            self._toggle_always_on_top(True)

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self)
        self.set_drag_widget(self.title_bar)
        main_layout.addWidget(self.title_bar)

        middle_widget = QWidget()
        middle_layout = QHBoxLayout(middle_widget)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(0)

        self.sidebar = NavSidebar()

        self.stack = QStackedWidget()

        self.tab_search = SearchTab()
        self.tab_dossier = DossierTab()
        self.tab_org = OrgTab()
        self.tab_archives = ArchivesTab(self.controller.archive_mgr)
        self.tab_settings = SettingsTab()

        self.stack.addWidget(self.tab_search)
        self.stack.addWidget(self.tab_dossier)
        self.stack.addWidget(self.tab_org)
        self.stack.addWidget(self.tab_archives)
        self.stack.addWidget(self.tab_settings)

        middle_layout.addWidget(self.sidebar)
        middle_layout.addWidget(self.stack, 1)

        main_layout.addWidget(middle_widget, 1)

        self.status_bar = CustomStatusBar()
        main_layout.addWidget(self.status_bar)

    def _connect_signals(self) -> None:
        self.title_bar.hide_requested.connect(self._on_hide_requested)
        self.title_bar.pin_toggled.connect(self._toggle_always_on_top)
        self.title_bar.clear_results_requested.connect(self._on_clear_results)

        self.sidebar.tab_selected.connect(self._on_tab_selected)

        EventBus.instance().navigate_to_tab.connect(self.sidebar.set_active_tab)
        EventBus.instance().status_message.connect(self.status_bar.set_status)
        EventBus.instance().navigate_to_tab.connect(self._on_navigate_requested)

    def _on_hide_requested(self) -> None:
        self.window_hidden.emit()
        self.hide()

    def _on_tab_selected(self, tab_id: str) -> None:
        if tab_id == "search":
            self.stack.setCurrentWidget(self.tab_search)
        elif tab_id == "dossier":
            self.stack.setCurrentWidget(self.tab_dossier)
        elif tab_id == "organization":
            self.stack.setCurrentWidget(self.tab_org)
        elif tab_id == "archive":
            self.stack.setCurrentWidget(self.tab_archives)
        elif tab_id == "settings":
            self.stack.setCurrentWidget(self.tab_settings)

        SettingsManager.instance().last_tab = tab_id

    def _on_navigate_requested(self, tab_id: str) -> None:
        self.sidebar.set_active_tab(tab_id)
        self._on_tab_selected(tab_id)

    def _on_clear_results(self) -> None:
        if hasattr(self.tab_dossier, '_clear_results'):
            self.tab_dossier._clear_results()
        if hasattr(self.tab_org, '_clear_results'):
            self.tab_org._clear_results()
        if hasattr(self.tab_archives, '_clear_results'):
            self.tab_archives._clear_results()

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _toggle_always_on_top(self, pinned: bool) -> None:
        flags = self.windowFlags()
        if pinned:
            self.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()

    def closeEvent(self, event) -> None:
        sm = SettingsManager.instance()

        if sm.minimize_to_tray_on_close and not QApplication.closingDown():
            event.ignore()
            self.window_hidden.emit()
            self.hide()
            return

        # Full quit
        geom = self.geometry()
        sm.window_x = geom.x()
        sm.window_y = geom.y()
        sm.window_w = geom.width()
        sm.window_h = geom.height()
        sm.force_save()

        max_age = sm.temp_cache_max_age_days
        self.controller.cache_mgr.cleanup_temp(max_age)

        EventBus.instance().app_exit.emit()
        super().closeEvent(event)
