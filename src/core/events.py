"""
src/core/events.py
EventBus — centralized QObject-based signal hub for cross-component communication.

All components emit and connect to signals on this singleton rather than
calling UI or service methods directly. This keeps layers decoupled.

Usage:
    bus = EventBus.instance()
    bus.search_player_requested.connect(my_slot)
    bus.search_player_requested.emit("PINKgeekPDX")
"""

from PyQt6.QtCore import QObject, pyqtSignal


class EventBus(QObject):
    """
    Singleton signal hub for SC Dossier.

    All cross-component signals are declared here. The AppController
    wires the service handler slots to these signals at startup.
    """

    _instance: "EventBus | None" = None

    # ------------------------------------------------------------------
    # Search Signals
    # ------------------------------------------------------------------

    # User requested a player profile search (handle string)
    search_player_requested = pyqtSignal(str)

    # User requested an org search (name or SID query string)
    search_org_requested = pyqtSignal(str)

    # ------------------------------------------------------------------
    # Data Loaded Signals
    # ------------------------------------------------------------------

    # Player profile data is ready for display (PlayerProfile dict)
    profile_loaded = pyqtSignal(dict)
    
    # Scrape completed successfully (dict)
    scrape_completed = pyqtSignal(dict)

    # Org profile data is ready for display (OrgProfile dict)
    org_loaded = pyqtSignal(dict)

    # Multiple org candidates found (list of {name, sid} dicts)
    # UI should show a picker dialog and emit search_org_requested(sid)
    org_candidates_found = pyqtSignal(list)

    # ------------------------------------------------------------------
    # OCR / Capture Signals
    # ------------------------------------------------------------------

    # OCR extraction completed successfully (extracted handle string)
    capture_completed = pyqtSignal(str)

    # OCR extraction failed (error message string for display)
    capture_failed = pyqtSignal(str)

    # ------------------------------------------------------------------
    # Archive Signals
    # ------------------------------------------------------------------

    # Archive list has changed (profile added, deleted, or synced)
    archive_updated = pyqtSignal()
    
    # Archive action requests
    request_archive = pyqtSignal(str)
    request_sync = pyqtSignal(str)
    request_load_archive = pyqtSignal(str)
    request_delete_archive = pyqtSignal(str)
    request_export_archive = pyqtSignal(str, str)

    # A sync operation completed for a handle (handle, changed: bool)
    sync_completed = pyqtSignal(str, bool)

    # Organization action requests
    request_org_scrape = pyqtSignal(str)

    # ------------------------------------------------------------------
    # UI Navigation Signals
    # ------------------------------------------------------------------

    # Request main window to show and switch to a specific tab (TabId.value)
    navigate_to_tab = pyqtSignal(str)
    nav_requested = pyqtSignal(int)

    # Request the main window to become visible
    show_main_window = pyqtSignal()

    # Request main window to hide (return to toolbar)
    hide_main_window = pyqtSignal()

    # Request OCR capture mode to begin
    start_capture = pyqtSignal()

    # Emitted when the global hotkey is pressed
    capture_hotkey_pressed = pyqtSignal()

    # Emitted when the toolbar interact hotkey is pressed/released
    toolbar_interact_pressed = pyqtSignal()
    toolbar_interact_released = pyqtSignal()

    # Emitted when the toolbar drag hotkey is pressed/released
    toolbar_drag_pressed = pyqtSignal()
    toolbar_drag_released = pyqtSignal()

    # ------------------------------------------------------------------
    # Status / Feedback Signals
    # ------------------------------------------------------------------

    # General status message for the status bar (message, level: StatusLevel.value)
    status_message = pyqtSignal(str, str)

    # Scraping/loading progress (0.0–1.0, or -1.0 for indeterminate)
    progress_update = pyqtSignal(float)

    # ------------------------------------------------------------------
    # Settings Signals
    # ------------------------------------------------------------------

    # A settings key changed (key, new_value)
    settings_changed = pyqtSignal(str, object)

    # ------------------------------------------------------------------
    # Image Download Signals
    # ------------------------------------------------------------------

    # An image download completed (url, local_path)
    image_downloaded = pyqtSignal(str, str)

    # An image download failed (url, error_message)
    image_download_failed = pyqtSignal(str, str)

    # ------------------------------------------------------------------
    # Reputation System Signals
    # ------------------------------------------------------------------

    # Reputation data loaded for a player (handle, scores_dict)
    # scores_dict shape: {category: {"score": int, "report_count": int}}
    reputation_loaded = pyqtSignal(str, dict)

    # Reputation data load failed (handle, error_message)
    reputation_load_failed = pyqtSignal(str, str)

    # An interaction report was successfully submitted (handle)
    reputation_report_submitted = pyqtSignal(str)

    # An interaction report submission failed (handle, error_message)
    reputation_report_failed = pyqtSignal(str, str)

    # Reputation system connection status changed
    # Values: "online" | "offline" | "disabled"
    reputation_system_status = pyqtSignal(str)

    # User requested to submit a report (handle, list_of_tag_ids)
    # Emitted by ReputationTab after ReportDialog is accepted
    reputation_report_requested = pyqtSignal(str, list)
    
    # Request a standalone reputation fetch without a full player scrape
    request_reputation_fetch = pyqtSignal(str)

    # ------------------------------------------------------------------
    # Application Signals
    # ------------------------------------------------------------------
    app_exit = pyqtSignal()

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

    @classmethod
    def instance(cls) -> "EventBus":
        """Return the singleton EventBus instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def initialize(cls) -> "EventBus":
        """Create and return the singleton EventBus."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
