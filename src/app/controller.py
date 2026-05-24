"""
src/app/controller.py
AppController — the central business logic coordinator.

Listens to EventBus signals, orchestrates Services (OCR, Scraper, Downloader),
and updates Cache/Archives accordingly.
"""

import logging
from PyQt6.QtCore import QObject, pyqtSlot

from src.core.events import EventBus
from src.services.cache_manager import CacheManager
from src.services.archive_manager import ArchiveManager
from src.services.sync_service import SyncService
from src.services.ocr_service import OCRService
from src.services.image_downloader import ImageDownloader
from src.services.scraper_player import PlayerScraperWorker
from src.services.scraper_org import OrgScraperWorker

log = logging.getLogger(__name__)


class AppController(QObject):
    """
    Coordinates application flow between UI events and background services.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        
        # Initialize Core Services
        self.cache_mgr = CacheManager()
        self.archive_mgr = ArchiveManager(self)
        self.sync_svc = SyncService(self.cache_mgr, self)
        self.ocr_svc = OCRService()
        self.img_dl = ImageDownloader()
        
        self._active_scraper: QObject | None = None
        
        self._connect_bus()

        # Check updates
        from src.core.settings import SettingsManager
        if getattr(SettingsManager.instance(), "auto_check_updates", True):
            from src.services.updater_service import UpdaterService
            self.updater = UpdaterService()
            self.updater.check_for_updates()

    def _connect_bus(self) -> None:
        bus = EventBus.instance()
        bus.search_player_requested.connect(self._on_search_player_requested)
        bus.search_org_requested.connect(self._on_search_org_requested)
        bus.capture_completed.connect(self._on_capture_completed)
        bus.capture_failed.connect(self._on_capture_failed)
        
        bus.request_archive.connect(self._on_request_archive)
        bus.request_sync.connect(self._on_request_sync)
        bus.request_load_archive.connect(self._on_request_load_archive)
        bus.request_delete_archive.connect(self._on_request_delete_archive)
        bus.request_export_archive.connect(self._on_request_export_archive)
        
        bus.request_org_scrape.connect(self._on_request_org_scrape)

    # -------------------------------------------------------------------------
    # Flow: Search -> Scrape -> Download Images -> UI Update
    # -------------------------------------------------------------------------

    @pyqtSlot(str)
    def _on_search_player_requested(self, handle: str) -> None:
        """Direct player search from UI (typed handle)."""
        handle = handle.strip()
        if not handle:
            return
        self._start_player_scrape(handle)

    @pyqtSlot(str)
    def _on_search_org_requested(self, query: str) -> None:
        """Org search by name or SID."""
        query = query.strip()
        if not query:
            return
        # If it looks like a SID (uppercase letters, no spaces), scrape directly
        if query.isupper() and " " not in query:
            self._on_request_org_scrape(query)
        else:
            # Name search: resolve to SID first via OrgSearchWorker
            from src.core.settings import SettingsManager
            sm = SettingsManager.instance()
            from src.services.scraper_org import OrgSearchWorker
            worker = OrgSearchWorker(query, sm.user_agent)
            worker.candidates_found.connect(self._on_org_candidates_found)
            worker.finished_error.connect(self._on_org_search_error)
            worker.start()

    @pyqtSlot(list)
    def _on_org_candidates_found(self, candidates: list) -> None:
        """When org name search returns candidates, emit for UI picker."""
        if len(candidates) == 1:
            # Auto-select single result
            self._on_request_org_scrape(candidates[0]["sid"])
        elif len(candidates) > 1:
            EventBus.instance().org_candidates_found.emit(candidates)
        else:
            EventBus.instance().status_message.emit("NO ORG FOUND FOR QUERY", "warning")

    @pyqtSlot(str)
    def _on_org_search_error(self, error_msg: str) -> None:
        EventBus.instance().status_message.emit(f"ORG SEARCH ERROR: {error_msg}", "error")

    # -------------------------------------------------------------------------
    # Flow: OCR -> Scrape -> Download Images -> UI Update
    # -------------------------------------------------------------------------

    @pyqtSlot(str)
    def _on_capture_completed(self, handle_or_path: str) -> None:
        """
        Triggered when OCR successfully reads a string OR user submits manual search.
        If it's an absolute path to an image, we send to OCR.
        If it's a raw string (handle), we start scraping.
        """
        import os
        if os.path.exists(handle_or_path) and os.path.isfile(handle_or_path):
            from pathlib import Path
            self.ocr_svc.process_image(Path(handle_or_path))
            return
            
        handle = handle_or_path.strip()
        if not handle:
            return

        # Start Scrape
        self._start_player_scrape(handle)

    @pyqtSlot(str)
    def _on_capture_failed(self, error_msg: str) -> None:
        EventBus.instance().status_message.emit(f"OCR ERROR: {error_msg}", "error")

    def _start_player_scrape(self, handle: str) -> None:
        """Initialize and run the player scraper."""
        if self._active_scraper and self._active_scraper.isRunning():
            log.warning("Scraper already running, ignoring request for %s", handle)
            return

        from src.core.settings import SettingsManager
        sm = SettingsManager.instance()
        
        EventBus.instance().status_message.emit(f"RETRIEVING DOSSIER: {handle}", "info")

        self._active_scraper = PlayerScraperWorker(handle, sm.user_agent, sm.scraper_delay_ms)
        self._active_scraper.finished_success.connect(self._on_scrape_success)
        self._active_scraper.finished_error.connect(self._on_scrape_error)
        self._active_scraper.start()

    @pyqtSlot(dict)
    def _on_scrape_success(self, data: dict) -> None:
        """When player data is scraped, we save to temp, then start image downloads."""
        handle = data.get("handle")
        
        # Determine if we should sync to archive instead of temp
        if self.cache_mgr.is_archived(handle):
            self.sync_svc.sync_profile(handle, data)
            # Re-load the merged data to show in UI and trigger downloads
            data = self.cache_mgr.load_profile(handle, archived=True)
            temp_dir = self.cache_mgr.paths.archived_dir(handle)
        else:
            self.cache_mgr.save_temp_profile(data)
            temp_dir = self.cache_mgr.paths.temp_cache_dir(handle)

        # Queue image downloads
        self._queue_downloads(data, temp_dir)

        EventBus.instance().status_message.emit("DATA RETRIEVED SUCCESSFULLY", "success")
        EventBus.instance().scrape_completed.emit(data)

    @pyqtSlot(str)
    def _on_scrape_error(self, error_msg: str) -> None:
        EventBus.instance().status_message.emit(f"SCRAPE ERROR: {error_msg}", "error")

    def _queue_downloads(self, data: dict, base_dir: "Path") -> None:
        """Queue avatar, badges, and org logos for download."""
        # Avatar
        avatar_url = data.get("avatar_url")
        if avatar_url and not data.get("avatar_local"):
            from pathlib import Path
            ext = avatar_url.split(".")[-1][:4] if "." in avatar_url else "png"
            dest = base_dir / f"avatar.{ext}"
            data["avatar_local"] = str(dest)
            self.img_dl.download(avatar_url, dest)

        # Badges
        for i, b in enumerate(data.get("badges", [])):
            b_url = b.get("image_url")
            if b_url and not b.get("image_local"):
                ext = b_url.split(".")[-1][:4] if "." in b_url else "png"
                dest = base_dir / f"badge_{i}.{ext}"
                b["image_local"] = str(dest)
                self.img_dl.download(b_url, dest)

        # Orgs
        for i, o in enumerate(data.get("orgs", [])):
            o_url = o.get("logo_url")
            if o_url and not o.get("logo_local"):
                ext = o_url.split(".")[-1][:4] if "." in o_url else "png"
                dest = base_dir / f"org_{i}.{ext}"
                o["logo_local"] = str(dest)
                self.img_dl.download(o_url, dest)
                
        # Re-save with local paths injected
        handle = data.get("handle")
        if self.cache_mgr.is_archived(handle):
            self.cache_mgr.save_archived_profile(data)
        else:
            self.cache_mgr.save_temp_profile(data)

    # -------------------------------------------------------------------------
    # Archive Actions
    # -------------------------------------------------------------------------

    @pyqtSlot(str)
    def _on_request_archive(self, handle: str) -> None:
        if self.cache_mgr.is_archived(handle):
            # Already archived — trigger a sync instead
            self._start_player_scrape(handle)
        elif self.cache_mgr.promote_to_archive(handle):
            EventBus.instance().status_message.emit("PROFILE ARCHIVED", "success")
            EventBus.instance().archive_updated.emit()
        else:
            EventBus.instance().status_message.emit("FAILED TO ARCHIVE", "error")

    @pyqtSlot(str)
    def _on_request_sync(self, handle: str) -> None:
        """Re-scrape an archived profile and sync changes."""
        if not self.cache_mgr.is_archived(handle):
            EventBus.instance().status_message.emit("PROFILE NOT ARCHIVED", "warning")
            return
        self._start_player_scrape(handle)

    @pyqtSlot(str)
    def _on_request_load_archive(self, handle: str) -> None:
        data = self.cache_mgr.load_profile(handle, archived=True)
        if data:
            EventBus.instance().scrape_completed.emit(data)
            # Instruct Main Window to switch to Dossier tab
            EventBus.instance().navigate_to_tab.emit("dossier")

    @pyqtSlot(str)
    def _on_request_delete_archive(self, handle: str) -> None:
        self.archive_mgr.delete_profile(handle)

    @pyqtSlot(str, str)
    def _on_request_export_archive(self, handle: str, out_dir: str) -> None:
        from pathlib import Path
        path = self.archive_mgr.export_profile(handle, Path(out_dir))
        if path:
            EventBus.instance().status_message.emit("EXPORT COMPLETE", "success")
        else:
            EventBus.instance().status_message.emit("EXPORT FAILED", "error")

    # -------------------------------------------------------------------------
    # Org Flow
    # -------------------------------------------------------------------------

    @pyqtSlot(str)
    def _on_request_org_scrape(self, sid: str) -> None:
        """Initialize and run the org scraper."""
        if self._active_scraper and self._active_scraper.isRunning():
            log.warning("Scraper already running, ignoring request for org %s", sid)
            return

        from src.core.settings import SettingsManager
        sm = SettingsManager.instance()
        
        EventBus.instance().status_message.emit(f"RETRIEVING ORG: {sid}", "info")

        self._active_scraper = OrgScraperWorker(sid, sm.user_agent)
        self._active_scraper.finished_success.connect(self._on_org_scrape_success)
        self._active_scraper.finished_error.connect(self._on_org_scrape_error)
        self._active_scraper.start()

    @pyqtSlot(dict)
    def _on_org_scrape_success(self, data: dict) -> None:
        EventBus.instance().status_message.emit("ORG DATA RETRIEVED", "success")
        # Reuse download queue for org logos/banners
        sid = data.get("sid")
        from src.core.paths import PathManager
        temp_dir = PathManager.instance().temp_root / "_orgs" / sid
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        self._queue_org_downloads(data, temp_dir)
        EventBus.instance().org_loaded.emit(data)

    @pyqtSlot(str)
    def _on_org_scrape_error(self, error_msg: str) -> None:
        EventBus.instance().status_message.emit(f"ORG SCRAPE ERROR: {error_msg}", "error")

    def _queue_org_downloads(self, data: dict, base_dir: "Path") -> None:
        # Logo
        url = data.get("logo_url")
        if url:
            ext = url.split(".")[-1][:4] if "." in url else "png"
            dest = base_dir / f"logo.{ext}"
            data["logo_local"] = str(dest)
            self.img_dl.download(url, dest)
            
        # Banner
        url = data.get("banner_url")
        if url:
            ext = url.split(".")[-1][:4] if "." in url else "png"
            dest = base_dir / f"banner.{ext}"
            data["banner_local"] = str(dest)
            self.img_dl.download(url, dest)
