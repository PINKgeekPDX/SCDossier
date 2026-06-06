import logging
from PyQt6.QtCore import QObject, pyqtSlot

from src.core.events import EventBus
from src.core.settings import SettingsManager
from src.services.cache_manager import CacheManager
from src.services.archive_manager import ArchiveManager
from src.services.sync_service import SyncService
from src.services.ocr_service import OCRService
from src.services.image_downloader import ImageDownloader
from src.services.scraper_player import PlayerScraperWorker
from src.services.scraper_org import OrgScraperWorker

log = logging.getLogger(__name__)


class AppController(QObject):

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

        self.cache_mgr = CacheManager()
        self.archive_mgr = ArchiveManager(self)
        self.sync_svc = SyncService(self.cache_mgr, self)
        self.ocr_svc = OCRService()
        self.img_dl = ImageDownloader()

        self._active_scraper: QObject | None = None
        self._org_search_worker = None

        self._connect_bus()

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
        bus.reputation_report_requested.connect(self._on_reputation_report_requested)
        bus.request_reputation_fetch.connect(self._start_reputation_fetch)
        bus.app_exit.connect(self.cleanup)

    @pyqtSlot(str)
    def _on_search_player_requested(self, handle: str) -> None:
        handle = handle.strip()
        if not handle:
            return
        self._start_player_scrape(handle)

    @pyqtSlot(str)
    def _on_search_org_requested(self, query: str) -> None:
        query = query.strip()
        if not query:
            return
        if query.isupper() and " " not in query:
            self._on_request_org_scrape(query)
        else:
            sm = SettingsManager.instance()
            from src.services.scraper_org import OrgSearchWorker
            self._org_search_worker = OrgSearchWorker(
                query, sm.user_agent,
                timeout_sec=sm.scraper_timeout_sec,
                proxy=sm.scraper_proxy or None
            )
            self._org_search_worker.candidates_found.connect(self._on_org_candidates_found)
            self._org_search_worker.finished_error.connect(self._on_org_search_error)
            self._org_search_worker.start()

    @pyqtSlot(list)
    def _on_org_candidates_found(self, candidates: list) -> None:
        if len(candidates) == 1:
            self._on_request_org_scrape(candidates[0]["sid"])
        elif len(candidates) > 1:
            EventBus.instance().org_candidates_found.emit(candidates)
        else:
            EventBus.instance().status_message.emit("NO ORG FOUND FOR QUERY", "warning")

    @pyqtSlot(str)
    def _on_org_search_error(self, error_msg: str) -> None:
        EventBus.instance().status_message.emit(f"ORG SEARCH ERROR: {error_msg}", "error")

    @pyqtSlot(str)
    def _on_capture_completed(self, handle_or_path: str) -> None:
        import os
        if os.path.exists(handle_or_path) and os.path.isfile(handle_or_path):
            from pathlib import Path
            self.ocr_svc.process_image(Path(handle_or_path))
            return

        handle = handle_or_path.strip()
        if not handle:
            return

        self._start_player_scrape(handle)
        EventBus.instance().navigate_to_tab.emit("dossier")

    @pyqtSlot(str)
    def _on_capture_failed(self, error_msg: str) -> None:
        EventBus.instance().status_message.emit(f"OCR ERROR: {error_msg}", "error")

    def _start_player_scrape(self, handle: str) -> None:
        if self._active_scraper and self._active_scraper.isRunning():
            log.warning("Scraper already running, ignoring request for %s", handle)
            return

        self._add_to_global_history(handle, "player")

        sm = SettingsManager.instance()

        EventBus.instance().status_message.emit(f"RETRIEVING DOSSIER: {handle}", "info")

        self._active_scraper = PlayerScraperWorker(
            handle, sm.user_agent, sm.scraper_delay_ms,
            timeout_sec=sm.scraper_timeout_sec,
            proxy=sm.scraper_proxy or None
        )
        self._active_scraper.finished_success.connect(self._on_scrape_success)
        self._active_scraper.finished_error.connect(self._on_scrape_error)
        self._active_scraper.start()

    @pyqtSlot(dict)
    def _on_scrape_success(self, data: dict) -> None:
        handle = data.get("handle")

        if self.cache_mgr.is_archived(handle):
            self.sync_svc.sync_profile(handle, data)
            # Determine storage dir but keep fresh scraped data for image queueing
            temp_dir = self.cache_mgr.paths.archived_dir(handle)
        else:
            self.cache_mgr.save_temp_profile(data)
            temp_dir = self.cache_mgr.paths.temp_cache_dir(handle)

        self._queue_downloads(data, temp_dir)

        EventBus.instance().status_message.emit("DATA RETRIEVED SUCCESSFULLY", "success")
        EventBus.instance().scrape_completed.emit(data)

        # Auto-check reputation if enabled
        sm = SettingsManager.instance()
        if sm.reputation_enabled and sm.reputation_auto_check and handle:
            from src.services.reputation_service import ReputationService
            if ReputationService.is_initialized():
                EventBus.instance().request_reputation_fetch.emit(handle)

    @pyqtSlot(str)
    def _on_scrape_error(self, error_msg: str) -> None:
        EventBus.instance().status_message.emit(f"SCRAPE ERROR: {error_msg}", "error")

    def _queue_downloads(self, data: dict, base_dir: "Path") -> None:
        avatar_url = data.get("avatar_url")
        if avatar_url and not data.get("avatar_local"):
            from pathlib import Path
            ext = avatar_url.split(".")[-1][:4] if "." in avatar_url else "png"
            dest = base_dir / f"avatar.{ext}"
            data["avatar_local"] = str(dest)
            self.img_dl.download(avatar_url, dest)

        for i, b in enumerate(data.get("badges", [])):
            b_url = b.get("image_url")
            if b_url and not b.get("image_local"):
                ext = b_url.split(".")[-1][:4] if "." in b_url else "png"
                dest = base_dir / f"badge_{i}.{ext}"
                b["image_local"] = str(dest)
                self.img_dl.download(b_url, dest)

        for i, o in enumerate(data.get("orgs", [])):
            o_url = o.get("logo_url")
            if o_url and not o.get("logo_local"):
                ext = o_url.split(".")[-1][:4] if "." in o_url else "png"
                dest = base_dir / f"org_{i}.{ext}"
                o["logo_local"] = str(dest)
                self.img_dl.download(o_url, dest)

        handle = data.get("handle")
        if self.cache_mgr.is_archived(handle):
            self.cache_mgr.save_archived_profile(data)
        else:
            self.cache_mgr.save_temp_profile(data)

    @pyqtSlot(str)
    def _on_request_archive(self, handle: str) -> None:
        if self.cache_mgr.is_archived(handle):
            self._start_player_scrape(handle)
        elif self.cache_mgr.promote_to_archive(handle):
            EventBus.instance().status_message.emit("PROFILE ARCHIVED", "success")
            EventBus.instance().archive_updated.emit()
        else:
            EventBus.instance().status_message.emit("FAILED TO ARCHIVE", "error")

    @pyqtSlot(str)
    def _on_request_sync(self, handle: str) -> None:
        if not self.cache_mgr.is_archived(handle):
            EventBus.instance().status_message.emit("PROFILE NOT ARCHIVED", "warning")
            return
        self._start_player_scrape(handle)

    @pyqtSlot(str)
    def _on_request_load_archive(self, handle: str) -> None:
        data = self.cache_mgr.load_profile(handle, archived=True)
        if data:
            EventBus.instance().scrape_completed.emit(data)
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

    @pyqtSlot(str)
    def _on_request_org_scrape(self, sid: str) -> None:
        if self._active_scraper and self._active_scraper.isRunning():
            log.warning("Scraper already running, ignoring request for org %s", sid)
            return

        self._add_to_global_history(sid, "org")

        sm = SettingsManager.instance()

        EventBus.instance().status_message.emit(f"RETRIEVING ORG: {sid}", "info")

        self._active_scraper = OrgScraperWorker(
            sid, sm.user_agent,
            timeout_sec=sm.scraper_timeout_sec,
            proxy=sm.scraper_proxy or None
        )
        self._active_scraper.finished_success.connect(self._on_org_scrape_success)
        self._active_scraper.finished_error.connect(self._on_org_scrape_error)
        self._active_scraper.start()

    @pyqtSlot(dict)
    def _on_org_scrape_success(self, data: dict) -> None:
        EventBus.instance().status_message.emit("ORG DATA RETRIEVED", "success")
        sid = data.get("sid", "UNKNOWN")
        from src.core.paths import PathManager
        import json as _json
        temp_dir = PathManager.instance().temp_root / "_orgs" / sid
        temp_dir.mkdir(parents=True, exist_ok=True)

        self._queue_org_downloads(data, temp_dir)

        org_json_path = temp_dir / "org.json"
        try:
            with open(org_json_path, "w", encoding="utf-8") as _f:
                _json.dump(data, _f, indent=2, ensure_ascii=False)
            log.info("Saved org cache: %s", org_json_path)
        except OSError as _e:
            log.warning("Could not save org JSON: %s", _e)

        EventBus.instance().org_loaded.emit(data)

    @pyqtSlot(str)
    def _on_org_scrape_error(self, error_msg: str) -> None:
        EventBus.instance().status_message.emit(f"ORG SCRAPE ERROR: {error_msg}", "error")

    def _queue_org_downloads(self, data: dict, base_dir: "Path") -> None:
        url = data.get("logo_url")
        if url:
            ext = url.split(".")[-1][:4] if "." in url else "png"
            dest = base_dir / f"logo.{ext}"
            data["logo_local"] = str(dest)
            self.img_dl.download(url, dest)

        url = data.get("banner_url")
        if url:
            ext = url.split(".")[-1][:4] if "." in url else "png"
            dest = base_dir / f"banner.{ext}"
            data["banner_local"] = str(dest)
            self.img_dl.download(url, dest)

        url = data.get("focus_primary_url")
        if url:
            ext = url.split(".")[-1][:4] if "." in url else "png"
            dest = base_dir / f"focus_primary.{ext}"
            data["focus_primary_local"] = str(dest)
            self.img_dl.download(url, dest)

        url = data.get("focus_secondary_url")
        if url:
            ext = url.split(".")[-1][:4] if "." in url else "png"
            dest = base_dir / f"focus_secondary.{ext}"
            data["focus_secondary_local"] = str(dest)
            self.img_dl.download(url, dest)

        for i, b in enumerate(data.get("badges", [])):
            url = b.get("image_url")
            if url and not b.get("image_local"):
                ext = url.split(".")[-1][:4] if "." in url else "png"
                dest = base_dir / f"badge_{i}.{ext}"
                b["image_local"] = str(dest)
                self.img_dl.download(url, dest)

        members_dir = base_dir / "members"
        members_dir.mkdir(parents=True, exist_ok=True)
        for member in data.get("members", []):
            url = member.get("avatar_url")
            if url and not member.get("avatar_local"):
                handle = member.get("handle", "unknown")
                ext = url.split(".")[-1][:4] if "." in url else "png"
                dest = members_dir / f"{handle}.{ext}"
                member["avatar_local"] = str(dest)
                self.img_dl.download(url, dest)

    @pyqtSlot(str)
    def _start_reputation_fetch(self, handle: str) -> None:
        if getattr(self, '_active_rep_fetcher', None) and self._active_rep_fetcher.isRunning():
            log.warning("Rep fetch already running, ignoring.")
            return

        from src.services.reputation_worker import ReputationFetchWorker
        self._active_rep_fetcher = ReputationFetchWorker(handle)

        def _on_success(data):
            EventBus.instance().reputation_loaded.emit(handle, data)

        def _on_error(err):
            EventBus.instance().reputation_load_failed.emit(handle, err)

        self._active_rep_fetcher.finished_success.connect(_on_success)
        self._active_rep_fetcher.finished_error.connect(_on_error)
        self._active_rep_fetcher.start()

    @pyqtSlot(str, list)
    def _on_reputation_report_requested(self, handle: str, tags: list[str]) -> None:
        if getattr(self, '_active_rep_submitter', None) and self._active_rep_submitter.isRunning():
            log.warning("Rep submit already running, ignoring.")
            return

        from src.services.reputation_worker import ReputationSubmitWorker
        self._active_rep_submitter = ReputationSubmitWorker(handle, tags)

        def _on_success(data):
            EventBus.instance().reputation_report_submitted.emit(handle)
            self._start_reputation_fetch(handle)

        def _on_error(err):
            EventBus.instance().reputation_report_failed.emit(handle, err)
            EventBus.instance().status_message.emit(f"REPORT SUBMISSION FAILED: {err}", "error")

        self._active_rep_submitter.finished_success.connect(_on_success)
        self._active_rep_submitter.finished_error.connect(_on_error)
        self._active_rep_submitter.start()

    @pyqtSlot()
    def cleanup(self) -> None:
        log.info("AppController cleaning up background threads...")

        if self._active_scraper and self._active_scraper.isRunning():
            self._active_scraper.quit()
            self._active_scraper.wait(1000)

        if self._org_search_worker and self._org_search_worker.isRunning():
            self._org_search_worker.quit()
            self._org_search_worker.wait(1000)

        if hasattr(self, "updater") and self.updater:
            if self.updater._worker and self.updater._worker.isRunning():
                self.updater._worker.quit()
                self.updater._worker.wait(1000)
            if self.updater._downloader and self.updater._downloader.isRunning():
                self.updater._downloader.quit()
                self.updater._downloader.wait(1000)

        if hasattr(self, "ocr_svc") and self.ocr_svc:
            if self.ocr_svc._worker and self.ocr_svc._worker.isRunning():
                self.ocr_svc._worker.quit()
                self.ocr_svc._worker.wait(1000)

        if getattr(self, '_active_rep_fetcher', None) and self._active_rep_fetcher.isRunning():
            self._active_rep_fetcher.quit()
            self._active_rep_fetcher.wait(1000)
        if getattr(self, '_active_rep_submitter', None) and self._active_rep_submitter.isRunning():
            self._active_rep_submitter.quit()
            self._active_rep_submitter.wait(1000)

    def _add_to_global_history(self, query: str, mode: str) -> None:
        settings = SettingsManager.instance()
        limit = settings.search_history_limit

        master = settings.search_history
        if query in master:
            master.remove(query)
        master.append(query)
        if limit >= 0 and len(master) > limit:
            master = master[-limit:]
        settings.search_history = master

        if mode == "player":
            player_hist = settings.search_history_player
            if query in player_hist:
                player_hist.remove(query)
            player_hist.append(query)
            if limit >= 0 and len(player_hist) > limit:
                player_hist = player_hist[-limit:]
            settings.search_history_player = player_hist
        else:
            org_hist = settings.search_history_org
            if query in org_hist:
                org_hist.remove(query)
            org_hist.append(query)
            if limit >= 0 and len(org_hist) > limit:
                org_hist = org_hist[-limit:]
            settings.search_history_org = org_hist
