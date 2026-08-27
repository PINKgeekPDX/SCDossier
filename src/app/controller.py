"""
src/app/controller.py
AppController — Main application orchestrator.

Connects UI events to backend services and manages background workers.
"""

import os
import logging
from PyQt6.QtCore import QObject, pyqtSlot, QThread

from src.core.events import EventBus
from src.core.settings import SettingsManager
from src.core.hotkey_manager import GlobalHotkeyManager

log = logging.getLogger(__name__)

# Color constants for status messages
_ORANGE = "#D9A52C"
_RED = "#D9412C"


class AppController(QObject):
    """
    The AppController is the main orchestrator of the application.
    It should not contain any business logic itself, but rather delegate
    to the appropriate service or worker.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        log.info("AppController initializing...")

        # Services (plain Python, no QObject)
        from src.services.cache_manager import CacheManager
        from src.services.archive_manager import ArchiveManager
        from src.services.sync_service import SyncService
        self.cache_mgr = CacheManager()
        self.archive_mgr = ArchiveManager()
        self.sync_svc = SyncService(self.cache_mgr, self.archive_mgr)

        # Services (QObject-based)
        from src.services.ocr_service import OCRService
        from src.services.image_downloader import ImageDownloader
        from src.services.updater_service import UpdaterService
        self.img_downloader = ImageDownloader()
        self.updater = UpdaterService(self)
        self.ocr_svc = OCRService()

        # Must be created before startup worker
        self._connect_events()

        # Must be created before hotkey manager
        if SettingsManager.instance().reputation_enabled:
            self._start_reputation_service()

        # Must be created after services are ready
        self.hotkey_mgr = GlobalHotkeyManager()

        # MainWindow reference set after creation by main.py
        self._main_window = None

        # Run startup tasks (e.g., local handle detection) in the background
        self._start_startup_worker()

        if SettingsManager.instance().auto_check_updates:
            self.updater.check_for_updates()

    def _connect_events(self) -> None:
        bus = EventBus.instance()

        # Search
        bus.search_player_requested.connect(self._on_search_player_requested)
        bus.search_org_requested.connect(self._on_search_org_requested)
        bus.search_history_updated.connect(self._on_search_history_updated)

        # Org scrape (emitted by dossier_tab org cards and org_tab refresh)
        bus.request_org_scrape.connect(self._start_org_scrape)

        # Archive
        bus.request_archive.connect(self._on_archive_requested)
        bus.request_unarchive.connect(self._on_unarchive_requested)
        bus.request_delete_archive.connect(self._on_delete_archive_requested)
        bus.request_sync.connect(self._on_sync_requested)
        bus.request_load_archive.connect(self._on_load_archive_requested)
        bus.request_export_archive.connect(self._on_export_requested)

        # Reputation
        bus.request_reputation_fetch.connect(self._start_reputation_fetch)
        bus.reputation_report_requested.connect(self._on_reputation_report_requested)
        bus.settings_changed.connect(self._on_settings_changed)

        # Capture / OCR
        bus.capture_completed.connect(self._on_capture_completed)
        bus.capture_failed.connect(self._on_capture_failed)

        # Startup / System
        bus.app_exit.connect(self.cleanup)
        bus.local_handle_detected.connect(self.set_local_player_handle)

    def _start_startup_worker(self) -> None:
        from src.app.workers.startup_worker import StartupWorker
        self._startup_worker = StartupWorker()
        self._startup_worker_thread = QThread()
        self._startup_worker.moveToThread(self._startup_worker_thread)
        self._startup_worker.finished.connect(self._startup_worker_thread.quit)
        # Connect handle detection to the EventBus so other components can react
        self._startup_worker.handle_detected.connect(EventBus.instance().local_handle_detected)
        self._startup_worker_thread.started.connect(self._startup_worker.run)
        self._startup_worker_thread.start()

    def set_local_player_handle(self, handle: str) -> None:
        """Set the detected local player handle on the ReputationService singleton."""
        if SettingsManager.instance().reputation_enabled:
            from src.services.reputation_service import ReputationService
            if ReputationService.is_initialized():
                ReputationService.instance().local_player_handle = handle

    @pyqtSlot(str)
    def _on_capture_completed(self, handle_or_path: str) -> None:
        """
        Triggered when OCR successfully reads a string OR user submits manual search.
        If it's an absolute path to an image, we send to OCR.
        If it's a raw string (handle), we start scraping.
        """
        if os.path.exists(handle_or_path) and os.path.isfile(handle_or_path):
            from pathlib import Path
            self.ocr_svc.process_image(Path(handle_or_path))
            return
            
        handle = handle_or_path.strip()
        if not handle:
            return

        # Start Scrape
        self._start_player_scrape(handle)
        EventBus.instance().navigate_to_tab.emit("dossier")

    @pyqtSlot(str)
    def _on_capture_failed(self, error_msg: str) -> None:
        EventBus.instance().status_push.emit("OCR ERROR", error_msg, _RED, 30000)

    def _start_reputation_service(self) -> None:
        """Initialize the ReputationService singleton and start the startup worker."""
        from src.app.constants import REP_SUPABASE_URL, REP_ANON_KEY
        from src.services.reputation_service import ReputationService
        from src.services.reputation_worker import ReputationStartupWorker

        url = REP_SUPABASE_URL
        key = REP_ANON_KEY
        if not url or not key:
            log.warning("Reputation enabled but REP_SUPABASE_URL/REP_ANON_KEY not set.")
            EventBus.instance().reputation_system_status.emit("error")
            return

        try:
            ReputationService.initialize(url, key)
        except Exception as e:
            log.error("Failed to initialize ReputationService: %s", e)
            EventBus.instance().reputation_system_status.emit("error")
            return

        self._rep_startup_worker = ReputationStartupWorker(self)
        self._rep_startup_worker.finished_success.connect(lambda _: None)
        self._rep_startup_worker.finished_error.connect(lambda _: None)
        self._rep_startup_worker.finished.connect(self._rep_startup_worker.deleteLater)
        self._rep_startup_worker.start()

    @pyqtSlot(str)
    def _start_reputation_fetch(self, handle: str) -> None:
        """Fetch reputation data for a handle in the background."""
        from src.services.reputation_worker import ReputationFetchWorker
        handle = handle.strip()
        if not handle:
            log.warning("_start_reputation_fetch: Empty handle, skipping.")
            return
        if hasattr(self, "_active_rep_fetcher") and self._active_rep_fetcher:
            try:
                if self._active_rep_fetcher.isRunning():
                    # Queue the handle — will be picked up after the current fetch completes
                    log.debug("Reputation fetch busy, queueing %s (replacing any previous pending)", handle)
                    self._next_rep_handle = handle
                    return
            except RuntimeError:
                pass
        self._pending_rep_handle = handle
        self._next_rep_handle = None
        self._active_rep_fetcher = ReputationFetchWorker(handle)
        self._active_rep_fetcher.finished_success.connect(self._on_reputation_fetch_success)
        self._active_rep_fetcher.finished_error.connect(self._on_reputation_fetch_error)
        self._active_rep_fetcher.finished.connect(self._active_rep_fetcher.deleteLater)
        # Clear reference only after thread has fully finished (avoid QThread destroy-while-running)
        self._active_rep_fetcher.finished.connect(lambda: setattr(self, '_active_rep_fetcher', None) if getattr(self, '_active_rep_fetcher', None) and not getattr(self, '_active_rep_fetcher', None).isRunning() else None)
        self._active_rep_fetcher.start()

        # Also start a silent rate limit check in parallel
        from src.services.reputation_worker import ReputationCheckRateLimitWorker
        from src.services.reputation_service import ReputationService
        _reporter_handle = ""
        try:
            if ReputationService.is_initialized():
                _reporter_handle = ReputationService.instance().local_player_handle
        except Exception:
            pass
        if hasattr(self, "_active_rate_checker") and self._active_rate_checker:
            try:
                if self._active_rate_checker.isRunning():
                    log.debug("Rate checker busy, queueing %s", handle)
                    self._next_rate_handle = (handle, _reporter_handle)
                    return
            except RuntimeError:
                pass
        self._pending_rate_handle = handle
        self._next_rate_handle = None
        self._active_rate_checker = ReputationCheckRateLimitWorker(handle, reporter_handle=_reporter_handle)
        self._active_rate_checker.finished_success.connect(
            lambda data, h=handle: self._on_rate_limit_success(h, data)
        )
        self._active_rate_checker.finished_error.connect(
            lambda err, h=handle: self._on_rate_limit_error(h, err)
        )
        self._active_rate_checker.finished.connect(self._active_rate_checker.deleteLater)
        # Clear reference only after thread fully finished
        self._active_rate_checker.finished.connect(lambda: setattr(self, '_active_rate_checker', None) if getattr(self, '_active_rate_checker', None) and not getattr(self, '_active_rate_checker', None).isRunning() else None)
        self._active_rate_checker.start()

    def _on_reputation_fetch_success(self, data: dict) -> None:
        handle = getattr(self, "_pending_rep_handle", "")
        EventBus.instance().reputation_loaded.emit(handle, data)
        # Drain the queue: if a new handle was requested while we were busy, fetch it now
        next_handle = getattr(self, "_next_rep_handle", None)
        if next_handle:
            self._next_rep_handle = None
            # Defer to next event loop to ensure finished signal fully processed
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._start_reputation_fetch(next_handle))

    def _on_reputation_fetch_error(self, error: str) -> None:
        handle = getattr(self, "_pending_rep_handle", "")
        EventBus.instance().reputation_load_failed.emit(handle, error)
        # Drain the queue
        next_handle = getattr(self, "_next_rep_handle", None)
        if next_handle:
            self._next_rep_handle = None
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._start_reputation_fetch(next_handle))

    def _on_rate_limit_success(self, handle: str, data: dict) -> None:
        EventBus.instance().reputation_rate_limit_loaded.emit(handle, data)
        # Drain queued rate check (defer to next loop to let finished fully complete)
        nxt = getattr(self, "_next_rate_handle", None)
        if nxt:
            self._next_rate_handle = None
            h, rh = nxt if isinstance(nxt, tuple) else (nxt, "")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda hh=h, rrh=rh: self._start_rate_limit_check(hh, rrh))

    def _start_rate_limit_check(self, handle: str, reporter_handle: str) -> None:
        """Helper to start a rate limit check (used for queued drains)."""
        from src.services.reputation_worker import ReputationCheckRateLimitWorker
        self._pending_rate_handle = handle
        self._active_rate_checker = ReputationCheckRateLimitWorker(handle, reporter_handle=reporter_handle)
        self._active_rate_checker.finished_success.connect(lambda d, hh=handle: self._on_rate_limit_success(hh, d))
        self._active_rate_checker.finished_error.connect(lambda e, hh=handle: self._on_rate_limit_error(hh, e))
        self._active_rate_checker.finished.connect(self._active_rate_checker.deleteLater)
        self._active_rate_checker.finished.connect(lambda: setattr(self, '_active_rate_checker', None) if getattr(self, '_active_rate_checker', None) and not getattr(self, '_active_rate_checker', None).isRunning() else None)
        self._active_rate_checker.start()

    def _on_rate_limit_error(self, handle: str, error: str) -> None:
        log.debug("Rate limit check failed for %s: %s", handle, error)
        # Non-fatal: a failed rate-limit check just means we can't update the button state.
        # Silently re-enable the report button so the user isn't locked out.
        EventBus.instance().reputation_rate_limit_loaded.emit(handle, {"allowed": True, "cooldown_seconds": 0, "friendly_allowed": True, "friendly_cooldown_seconds": 0})
        nxt = getattr(self, "_next_rate_handle", None)
        if nxt:
            self._next_rate_handle = None
            h, rh = nxt if isinstance(nxt, tuple) else (nxt, "")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda hh=h, rrh=rh: self._start_rate_limit_check(hh, rrh))

    @pyqtSlot(str, list, str)
    def _on_reputation_report_requested(self, handle: str, tags: list, disposition: str) -> None:
        from src.services.reputation_worker import ReputationSubmitWorker
        if hasattr(self, "_active_rep_submitter") and self._active_rep_submitter:
            try:
                if self._active_rep_submitter.isRunning():
                    log.warning("Reputation submit already running, ignoring request for %s", handle)
                    return
            except RuntimeError:
                pass

        self._pending_rep_submit_handle = handle
        self._active_rep_submitter = ReputationSubmitWorker(handle, tags, disposition)
        self._active_rep_submitter.finished_success.connect(self._on_reputation_submit_success)
        self._active_rep_submitter.finished_error.connect(self._on_reputation_submit_error)
        self._active_rep_submitter.finished.connect(self._active_rep_submitter.deleteLater)
        self._active_rep_submitter.start()

    def _on_reputation_submit_success(self, data: dict) -> None:
        handle = getattr(self, "_pending_rep_submit_handle", "")
        # Remove notices from data before passing as scores
        notices = data.pop("_notices", []) if "_notices" in data else []
        
        EventBus.instance().reputation_report_submitted.emit(handle)
        
        if notices:
            msg = " / ".join(notices)
            EventBus.instance().status_push.emit("NOTICE", msg, "#FFB84D", 8000)
        else:
            EventBus.instance().status_push.emit("REPORT SUBMITTED", "Report submitted successfully.", "#5CFF99", 5000)
            
        # Emit the freshly returned scores directly to avoid read-replica lag
        EventBus.instance().reputation_loaded.emit(handle, data)
        
        # Trigger a silent rate limit check to update the button cooldowns
        from src.services.reputation_worker import ReputationCheckRateLimitWorker
        from src.services.reputation_service import ReputationService
        _reporter_handle = ""
        try:
            if ReputationService.is_initialized():
                _reporter_handle = ReputationService.instance().local_player_handle
        except Exception:
            pass
        should_start_checker = True
        if hasattr(self, "_active_rate_checker") and self._active_rate_checker:
            try:
                if self._active_rate_checker.isRunning():
                    should_start_checker = False  # Keep running, result will arrive shortly
            except RuntimeError:
                pass
        if should_start_checker:
            self._active_rate_checker = ReputationCheckRateLimitWorker(handle, reporter_handle=_reporter_handle)
            self._active_rate_checker.finished_success.connect(
                lambda data, h=handle: self._on_rate_limit_success(h, data)
            )
            self._active_rate_checker.finished_error.connect(
                lambda err, h=handle: self._on_rate_limit_error(h, err)
            )
            self._active_rate_checker.finished.connect(self._active_rate_checker.deleteLater)
            self._active_rate_checker.start()

    def _on_reputation_submit_error(self, error: str) -> None:
        handle = getattr(self, "_pending_rep_submit_handle", "")
        EventBus.instance().reputation_report_failed.emit(handle, error)
        EventBus.instance().status_push.emit("REPORT FAILED", error, _RED, 30000)

    @pyqtSlot(str, object)
    def _on_settings_changed(self, key: str, value: object) -> None:
        if key == "reputation_enabled" and value is True:
            if not SettingsManager.instance().reputation_enabled:
                return
            from src.services.reputation_service import ReputationService
            if not ReputationService.is_initialized():
                log.info("Reputation system enabled via settings — initializing service...")
                self._start_reputation_service()
            else:
                # Already initialized, just ensure status is online
                EventBus.instance().reputation_system_status.emit("online")

    @pyqtSlot(str)
    def _on_search_player_requested(self, handle: str) -> None:
        _BLUE = "#93CCFF"
        handle = handle.strip()
        if not handle:
            return
        EventBus.instance().status_push.emit("RETRIEVING DOSSIER", f"Fetching dossier for {handle}...", _BLUE, 30000)
        self._start_player_scrape(handle)
        self.archive_mgr.add_to_global_history(handle, "player")

    @pyqtSlot(str)
    def _on_search_org_requested(self, query: str) -> None:
        _BLUE = "#93CCFF"
        query = query.strip()
        if not query:
            return
        EventBus.instance().status_push.emit("SEARCHING ORG", f"Searching for organization {query}...", _BLUE, 30000)
        # If it looks like a SID, scrape directly. Otherwise, search.
        if query.isupper() and " " not in query:
            self._start_org_scrape(query)
        else:
            self._start_org_search(query)
        self.archive_mgr.add_to_global_history(query, "org")

    @pyqtSlot(str, str)
    def _on_search_history_updated(self, query: str, mode: str) -> None:
        self.archive_mgr.add_to_global_history(query, mode)

    @pyqtSlot(str)
    def _on_archive_requested(self, handle: str) -> None:
        _GREEN = "#00FF88"
        _AMBER = "#FFAA00"
        _RED = "#FF4444"
        if self.cache_mgr.is_archived(handle):
            # Already archived — refresh it
            self._start_player_scrape(handle)
        elif self.cache_mgr.promote_to_archive(handle):
            EventBus.instance().status_push.emit("PROFILE ARCHIVED", "", _GREEN, 30000)
            EventBus.instance().archive_updated.emit()
        else:
            EventBus.instance().status_push.emit("FAILED TO ARCHIVE", "", _RED, 30000)

    @pyqtSlot(str)
    def _on_unarchive_requested(self, handle: str) -> None:
        self.archive_mgr.delete_profile(handle)

    @pyqtSlot(str)
    def _on_delete_archive_requested(self, handle: str) -> None:
        """Delete an archive after confirmation — emits signal for UI to confirm first."""
        EventBus.instance().status_push.emit(
            "CONFIRM DELETE", f"Delete archived profile for {handle}?", "#FFAA00", 5000
        )
        # The actual deletion is handled by the UI confirmation dialog
        # which will call request_unarchive after user confirms
        self.archive_mgr.delete_profile(handle)

    @pyqtSlot(str)
    def _on_load_archive_requested(self, handle: str) -> None:
        """Load an archived profile and display it in the dossier tab."""
        data = self.cache_mgr.get_temp_profile(handle) or self.archive_mgr.get_profile(handle)
        if data:
            EventBus.instance().scrape_completed.emit(data)
            EventBus.instance().navigate_to_tab.emit("dossier")

    @pyqtSlot(str)
    def _on_sync_requested(self, handle: str) -> None:
        _AMBER = "#FFAA00"
        if not self.cache_mgr.is_archived(handle):
            EventBus.instance().status_push.emit("PROFILE NOT ARCHIVED", "", _AMBER, 30000)
            return
        self._start_player_scrape(handle, force=True)

    @pyqtSlot(str, str)
    def _on_export_requested(self, handle: str, out_dir: str) -> None:
        _GREEN = "#00FF88"
        _RED = "#FF4444"
        from pathlib import Path
        result = self.archive_mgr.export_profile(handle, Path(out_dir))
        if result:
            EventBus.instance().status_push.emit("EXPORT COMPLETE", "", _GREEN, 30000)
        else:
            EventBus.instance().status_push.emit("EXPORT FAILED", "", _RED, 30000)

    def _start_org_scrape(self, sid: str) -> None:
        if hasattr(self, "_active_org_scraper") and self._active_org_scraper:
            try:
                if self._active_org_scraper.isRunning():
                    log.debug("Org scraper busy, queueing %s", sid)
                    self._next_org_scrape_sid = sid
                    return
            except RuntimeError:
                # Underlying C++ object already deleted
                pass

        self._pending_org_scrape_sid = sid
        self._next_org_scrape_sid = None
        EventBus.instance().status_push.emit("RETRIEVING ORG", f"Fetching organization {sid}...", "#93CCFF", 30000)

        from src.services.scraper_org import OrgScraperWorker
        settings = SettingsManager.instance()
        self._active_org_scraper = OrgScraperWorker(
            sid,
            user_agent=settings.user_agent,
            timeout_sec=settings.scraper_timeout_sec,
            proxy=settings.scraper_proxy or None,
        )
        self._active_org_scraper.finished_success.connect(self._on_org_scrape_success)
        self._active_org_scraper.finished_error.connect(self._on_org_scrape_error)
        self._active_org_scraper.finished.connect(self._active_org_scraper.deleteLater)
        self._active_org_scraper.start()

    def _start_org_search(self, query: str) -> None:
        if hasattr(self, "_org_search_worker") and self._org_search_worker:
            try:
                if self._org_search_worker.isRunning():
                    log.warning("Org search already running, ignoring request.")
                    return
            except RuntimeError:
                pass

        from src.services.scraper_org import OrgSearchWorker
        settings = SettingsManager.instance()
        self._org_search_worker = OrgSearchWorker(
            query,
            user_agent=settings.user_agent,
            timeout_sec=settings.scraper_timeout_sec,
            proxy=settings.scraper_proxy or None,
        )
        self._org_search_worker.candidates_found.connect(self._on_org_candidates_found)
        self._org_search_worker.finished_error.connect(self._on_org_search_error)
        self._org_search_worker.finished.connect(self._org_search_worker.deleteLater)
        self._org_search_worker.start()

    def _start_player_scrape(self, handle: str, force: bool = False) -> None:
        if hasattr(self, "_active_scraper") and self._active_scraper:
            try:
                if self._active_scraper.isRunning():
                    log.debug("Scraper busy, queueing %s", handle)
                    self._next_scrape_handle = handle
                    return
            except RuntimeError:
                pass

        self._pending_scrape_handle = handle
        self._next_scrape_handle = None

        # Check cache first unless forcing a refresh
        if not force:
            cached_profile = self.cache_mgr.get_temp_profile(handle) or self.archive_mgr.get_profile(handle)
            if cached_profile:
                log.info("Loaded %s from cache.", handle)
                EventBus.instance().scrape_completed.emit(cached_profile)

                # If it's stale, trigger a background sync but don't block the UI
                if self.sync_svc.is_stale(cached_profile):
                    self._start_player_scrape(handle, force=True)
                return

        from src.services.scraper_player import PlayerScraperWorker
        settings = SettingsManager.instance()
        self._active_scraper = PlayerScraperWorker(
            handle,
            user_agent=settings.user_agent,
            delay_ms=settings.scraper_delay_ms,
            timeout_sec=settings.scraper_timeout_sec,
            proxy=settings.scraper_proxy or None,
        )
        self._active_scraper.finished_success.connect(self._on_scrape_success)
        self._active_scraper.finished_error.connect(self._on_scrape_error)
        self._active_scraper.finished.connect(self._active_scraper.deleteLater)
        self._active_scraper.start()

    @pyqtSlot(dict)
    def _on_scrape_success(self, data: dict) -> None:
        _GREEN = "#00FF88"
        handle = data["handle"]

        # Determine download directory: archived dir for archived profiles, temp for others
        if self.cache_mgr.is_archived(handle):
            from src.core.paths import PathManager
            base_dir = str(PathManager.instance().archived_dir(handle))
        else:
            self.cache_mgr.save_temp_profile(data)
            base_dir = self.cache_mgr.get_temp_path(handle)

        self._queue_downloads(data, base_dir)
        EventBus.instance().status_push.emit("DATA RETRIEVED SUCCESSFULLY", "", _GREEN, 30000)
        EventBus.instance().scrape_completed.emit(data)

        # Re-save the profile so local image paths are persisted to disk
        if self.cache_mgr.is_archived(handle):
            self.cache_mgr.save_archived_profile(data)
        else:
            self.cache_mgr.save_temp_profile(data)

        # If profile is in archive, sync it in the background
        if self.archive_mgr.is_archived(handle):
            self.sync_svc.sync_profile(handle, data)

        # If reputation system is enabled, auto-fetch reputation
        settings = SettingsManager.instance()
        if settings.reputation_enabled and settings.reputation_auto_check:
            self._start_reputation_fetch(handle)

        # Drain queued player scrape if any
        nxt = getattr(self, "_next_scrape_handle", None)
        if nxt:
            self._next_scrape_handle = None
            # Defer to next event loop to avoid re-entrancy
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._start_player_scrape(nxt))

    @pyqtSlot(str)
    def _on_org_search_error(self, error_msg: str) -> None:
        _RED = "#D9412C"
        EventBus.instance().status_push.emit("ORG SEARCH ERROR", error_msg, _RED, 30000)

    @pyqtSlot(str)
    def _on_scrape_error(self, error: str) -> None:
        handle = getattr(self, "_pending_scrape_handle", "")
        log.error("Scrape for %s failed: %s", handle, error)
        EventBus.instance().status_push.emit(error, "", _RED, 15000)
        EventBus.instance().scrape_failed.emit(handle, error)
        # Drain queued scrape if any
        nxt = getattr(self, "_next_scrape_handle", None)
        if nxt:
            self._next_scrape_handle = None
            self._start_player_scrape(nxt)

    @pyqtSlot(dict)
    def _on_org_scrape_success(self, data: dict) -> None:
        _GREEN = "#00FF88"
        self.cache_mgr.save_org_profile(data)
        base_dir = self.cache_mgr.get_org_path(data["sid"])
        self._queue_downloads(data, base_dir)
        for member in data.get("members", []):
            self._queue_downloads(member, base_dir, is_member=True)
        # Re-save so local image paths are persisted to disk
        self.cache_mgr.save_org_profile(data)
        EventBus.instance().status_push.emit("ORG DATA RETRIEVED", "", _GREEN, 30000)
        EventBus.instance().org_scrape_completed.emit(data)
        # Also emit org_loaded for backward compatibility with UI tabs
        EventBus.instance().org_loaded.emit(data)
        # Drain queued org scrape
        nxt = getattr(self, "_next_org_scrape_sid", None)
        if nxt:
            self._next_org_scrape_sid = None
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._start_org_scrape(nxt))

    @pyqtSlot(str)
    def _on_org_scrape_error(self, error: str) -> None:
        sid = getattr(self, "_pending_org_scrape_sid", "")
        log.error("Org scrape for %s failed: %s", sid, error)
        EventBus.instance().status_push.emit("ORG FAILED", error, _RED, 15000)
        EventBus.instance().org_scrape_failed.emit(sid, error)
        nxt = getattr(self, "_next_org_scrape_sid", None)
        if nxt:
            self._next_org_scrape_sid = None
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._start_org_scrape(nxt))

    @pyqtSlot(list)
    def _on_org_candidates_found(self, candidates: list) -> None:
        _AMBER = "#FFAA00"
        if len(candidates) == 1:
            # Auto-scrape the single match
            self._start_org_scrape(candidates[0]["sid"])
        elif len(candidates) > 1:
            # Emit on the bus so org_tab can show its disambiguation dialog
            EventBus.instance().org_candidates_found.emit(candidates)
        else:
            EventBus.instance().status_push.emit("NO ORG FOUND FOR QUERY", "", _AMBER, 30000)

    def _get_main_window(self):
        """Return the MainWindow reference, if set."""
        return getattr(self, "_main_window", None)

    def set_main_window(self, window) -> None:
        """Called by main.py after MainWindow is created."""
        self._main_window = window

    def _queue_downloads(self, data: dict, base_dir: str, is_member: bool = False) -> None:
        items_to_download = []

        # Player avatar or Org logo
        if not is_member:
            key = "avatar_url" if "avatar_url" in data else "logo_url"
            if url := data.get(key):
                local_path_key = "avatar_local" if key == "avatar_url" else "logo_local"
                filename = "avatar.png" if key == "avatar_url" else "logo.png"
                local_path = os.path.join(base_dir, filename)
                items_to_download.append((url, local_path))
                data[local_path_key] = local_path

        # Org-specific images: banner, focus_primary, focus_secondary
        if not is_member and not data.get("avatar_url"):
            # This is an org profile (no avatar_url means it's an org)
            for img_key, local_key, filename in [
                ("banner_url", "banner_local", "banner.png"),
                ("focus_primary_url", "focus_primary_local", "focus_primary.png"),
                ("focus_secondary_url", "focus_secondary_local", "focus_secondary.png"),
            ]:
                if url := data.get(img_key):
                    local_path = os.path.join(base_dir, filename)
                    items_to_download.append((url, local_path))
                    data[local_key] = local_path

        # Org members have their own avatar
        if is_member and (url := data.get("avatar_url")):
            handle = data.get("handle", "unknown")
            filename = f"member_{handle}.png"
            local_path = os.path.join(base_dir, filename)
            items_to_download.append((url, local_path))
            data["avatar_local"] = local_path

        # Badges
        for badge in data.get("badges", []):
            if url := badge.get("image_url"):
                filename = os.path.basename(url).split("?")[0]
                local_path = os.path.join(base_dir, filename)
                items_to_download.append((url, local_path))
                badge["image_local"] = local_path

        # Orgs section (for a player)
        for org in data.get("orgs", []):
            if url := org.get("logo_url"):
                filename = f"org_{org['sid']}.png"
                local_path = os.path.join(base_dir, filename)
                items_to_download.append((url, local_path))
                org["logo_local"] = local_path

        for url, path in items_to_download:
            self.img_downloader.queue_download(url, path)

    def cleanup(self) -> None:
        log.info("AppController cleaning up background threads...")

        def _stop_worker_thread(thread, name: str, wait_ms: int = 1000) -> None:
            if thread is None:
                return
            try:
                if not thread.isRunning():
                    return
            except RuntimeError:
                # C++ object already deleted via deleteLater
                return
            try:
                thread.requestInterruption()
                thread.quit()
                if not thread.wait(wait_ms):
                    log.warning("%s did not stop within %dms — terminating.", name, wait_ms)
                    thread.terminate()
                    thread.wait(1000)
            except RuntimeError:
                pass

        _stop_worker_thread(
            getattr(self, '_active_scraper', None),
            'PlayerScraperWorker',
        )
        _stop_worker_thread(
            getattr(self, '_org_search_worker', None),
            'OrgSearchWorker',
        )
        _stop_worker_thread(
            getattr(self, '_active_org_scraper', None),
            'OrgScraperWorker',
        )

        if hasattr(self, "updater") and self.updater:
            _stop_worker_thread(
                getattr(self.updater, '_worker', None),
                'ReleaseListWorker',
            )
            _stop_worker_thread(
                getattr(self.updater, '_downloader', None),
                'UpdateDownloader',
            )

        if hasattr(self, "ocr_svc") and self.ocr_svc:
            _stop_worker_thread(
                getattr(self.ocr_svc, '_worker', None),
                'OCRWorker',
            )

        _stop_worker_thread(
            getattr(self, '_active_rep_fetcher', None),
            'ReputationFetchWorker',
        )
        _stop_worker_thread(
            getattr(self, '_active_rep_submitter', None),
            'ReputationSubmitWorker',
        )
        _stop_worker_thread(
            getattr(self, '_active_rate_checker', None),
            'ReputationCheckRateLimitWorker',
        )

        _stop_worker_thread(
            getattr(self, '_rep_startup_worker', None),
            'ReputationStartupWorker',
        )
        _stop_worker_thread(
            getattr(self, '_rep_startup_thread', None),
            'ReputationStartupWorker thread',
        )
        _stop_worker_thread(
            getattr(self, '_startup_worker_thread', None),
            'StartupWorker thread',
        )

        # Wait for image downloader pool to finish (avoid QThreadStorage warnings)
        if hasattr(self, "img_downloader") and self.img_downloader:
            try:
                self.img_downloader.pool.waitForDone(3000)
            except Exception:
                pass

        log.info("AppController cleanup complete.")
