"""
src/services/reputation_worker.py
QThread workers for async reputation DB operations.

All workers follow the exact pattern of PlayerScraperWorker:
  - Call .run() in the background thread
  - Emit finished_success or finished_error on the main thread
  - Never block the main thread

Workers:
    ReputationFetchWorker   — fetch reputation data for a handle
    ReputationSubmitWorker  — submit an interaction report
    ReputationStartupWorker — ping keep-alive + fetch known handles at startup
"""

import logging
import time
from PyQt6.QtCore import QThread, pyqtSignal

from src.services.reputation_service import ReputationService, ReputationServiceError
from src.core.events import EventBus

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ReputationFetchWorker
# ---------------------------------------------------------------------------

class ReputationFetchWorker(QThread):
    """
    Fetches reputation data for a player handle in a background thread.

    Emits:
        finished_success(dict) — reputation score dict, or {} if no data
        finished_error(str)    — error message on failure
    """

    finished_success = pyqtSignal(dict)
    finished_error = pyqtSignal(str)

    def __init__(self, handle: str, parent=None) -> None:
        super().__init__(parent)
        self._handle = handle

    def run(self) -> None:
        try:
            if self.isInterruptionRequested():
                return

            svc = ReputationService.instance()
            data = svc.fetch_reputation(self._handle)
            # None means "no data yet" — emit empty dict, not an error
            self.finished_success.emit(data if data is not None else {})
        except RuntimeError as e:
            # ReputationService not initialized
            log.warning("ReputationFetchWorker: %s", e)
            self.finished_error.emit(str(e))
        except Exception as e:
            log.error("ReputationFetchWorker.run() unexpected error: %s", e)
            self.finished_error.emit(str(e))


# ---------------------------------------------------------------------------
# ReputationSubmitWorker
# ---------------------------------------------------------------------------

class ReputationSubmitWorker(QThread):
    """
    Submits an interaction report in a background thread.

    Flow:
        1. Get IP hash (calls api.ipify.org)
        2. Submit report via Edge Function
        3. Emit result

    Emits:
        finished_success(dict) — updated 5-category score dict
        finished_error(str)    — error message on failure
    """

    finished_success = pyqtSignal(dict)
    finished_error = pyqtSignal(str)

    def __init__(self, handle: str, tags: list, disposition: str = "unknown", parent=None) -> None:
        super().__init__(parent)
        self._handle = handle
        self._tags = list(tags)
        self._disposition = disposition

    def run(self) -> None:
        try:
            svc = ReputationService.instance()

            # Step 1: Get IP hash — required for rate limiting
            if self.isInterruptionRequested():
                return

            ip_hash = svc._get_ip_hash()
            if ip_hash is None:
                msg = "Could not determine IP for rate limiting. Check your internet connection."
                log.warning("ReputationSubmitWorker: %s", msg)
                self.finished_error.emit(msg)
                return

            # Step 2: Gather reporter info for mutual report detection and org cooldowns
            if self.isInterruptionRequested():
                return

            reporter_handle = svc.local_player_handle
            if not reporter_handle:
                log.info("ReputationSubmitWorker: local player handle not cached. Attempting dynamic re-detection from logs...")
                reporter_handle = svc.detect_local_player_handle()

            if not reporter_handle:
                log.warning(
                    "ReputationSubmitWorker: reporter_handle not detected — "
                    "mutual report detection (method 3), org dodging cache (method 8), "
                    "org size normalization (method 9), and org mutual normalization (method 10) "
                    "will operate with reduced data for this report."
                )

            # Fetch reporter's orgs on the spot using the scraper
            orgs: list[str] = []
            if reporter_handle:
                from src.services.scraper_player import scrape_player_orgs_sync
                from src.core.settings import SettingsManager
                from src.app.constants import DEFAULT_USER_AGENT
                
                if SettingsManager._instance is not None:
                    sm = SettingsManager.instance()
                    ua = sm.user_agent or DEFAULT_USER_AGENT
                else:
                    ua = DEFAULT_USER_AGENT
                    log.debug("SettingsManager not initialized during worker run (normal in tests). Falling back to DEFAULT_USER_AGENT.")

                # Try scraping with retry logic
                max_attempts = 3
                scrape_success = False
                last_error = None
                
                for attempt in range(max_attempts):
                    try:
                        orgs = scrape_player_orgs_sync(reporter_handle, ua)
                        scrape_success = True
                        break
                    except Exception as e:
                        last_error = e
                        log.debug(
                            "scrape_player_orgs_sync attempt %d failed for reporter %s: %s",
                            attempt + 1, reporter_handle, e,
                            exc_info=True
                        )
                        if attempt < max_attempts - 1:
                            time.sleep(0.5)
                
                if not scrape_success:
                    log.error(
                        "All %d attempts to scrape reporter's orgs failed for %s. Last error: %s",
                        max_attempts, reporter_handle, last_error,
                        exc_info=True
                    )
                    msg = f"REP SYSTEM WARNING: FAILED TO SCRAPE ORGS FOR {reporter_handle} (NETWORK ERROR)"
                    EventBus.instance().status_push.emit(msg.upper(), "Unable to verify org membership for cooldown checks.", "#FFB84D", 8000)

            # Step 3: Submit the report
            if self.isInterruptionRequested():
                return

            result = svc.submit_report(
                self._handle,
                self._tags,
                ip_hash,
                disposition=self._disposition,
                reporter_handle=reporter_handle,
                orgs=orgs,
            )
            self.finished_success.emit(result if isinstance(result, dict) else {})

        except ReputationServiceError as e:
            log.warning("ReputationSubmitWorker: submit failed: %s", e)
            self.finished_error.emit(str(e))
        except RuntimeError as e:
            log.warning("ReputationSubmitWorker: service not initialized: %s", e)
            self.finished_error.emit(str(e))
        except Exception as e:
            log.error("ReputationSubmitWorker.run() unexpected error: %s", e)
            self.finished_error.emit(str(e))


# ---------------------------------------------------------------------------
# ReputationCheckRateLimitWorker
# ---------------------------------------------------------------------------

class ReputationCheckRateLimitWorker(QThread):
    """
    Checks rate limit status for a player via the check-rate-limit Edge Function.

    Passes reporter_handle so the server can consult the org_roster_cache for
    org-dodging detection (anti-abuse method 8) even when the reporter's current
    org list is temporarily empty.

    Emits:
        finished_success(dict) — rate limit status dict
        finished_error(str)    — error message on failure
    """

    finished_success = pyqtSignal(dict)
    finished_error = pyqtSignal(str)

    def __init__(self, handle: str, reporter_handle: str = "", parent=None) -> None:
        super().__init__(parent)
        self._handle = handle
        self._reporter_handle = reporter_handle

    def run(self) -> None:
        try:
            svc = ReputationService.instance()

            # Step 1: Get IP hash
            if self.isInterruptionRequested():
                return

            ip_hash = svc._get_ip_hash()
            if ip_hash is None:
                self.finished_error.emit("Could not determine IP for rate limit check.")
                return

            # Step 2: Gather reporter info for org dodging cache (anti-abuse method 8)
            if self.isInterruptionRequested():
                return

            reporter_handle = self._reporter_handle or svc.local_player_handle
            if not reporter_handle:
                log.info("ReputationCheckRateLimitWorker: local player handle not cached. Attempting dynamic re-detection from logs...")
                reporter_handle = svc.detect_local_player_handle()

            # Fetch reporter's orgs for org size normalization (methods 8/9)
            orgs: list[str] = []
            if reporter_handle:
                from src.services.scraper_player import scrape_player_orgs_sync
                from src.core.settings import SettingsManager
                from src.app.constants import DEFAULT_USER_AGENT
                
                if SettingsManager._instance is not None:
                    sm = SettingsManager.instance()
                    ua = sm.user_agent or DEFAULT_USER_AGENT
                else:
                    ua = DEFAULT_USER_AGENT
                    log.debug("SettingsManager not initialized during worker run (normal in tests). Falling back to DEFAULT_USER_AGENT.")

                # Try scraping with retry logic
                max_attempts = 3
                scrape_success = False
                last_error = None
                
                for attempt in range(max_attempts):
                    try:
                        orgs = scrape_player_orgs_sync(reporter_handle, ua)
                        scrape_success = True
                        break
                    except Exception as e:
                        last_error = e
                        log.debug(
                            "scrape_player_orgs_sync attempt %d failed for reporter %s: %s",
                            attempt + 1, reporter_handle, e,
                            exc_info=True
                        )
                        if attempt < max_attempts - 1:
                            time.sleep(0.5)
                
                if not scrape_success:
                    log.warning(
                        "Rate-limit check: failed to scrape orgs for %s after %d attempts: %s (proceeding with cached orgs)",
                        reporter_handle, max_attempts, last_error,
                    )
                    # Non-critical for read-path: proceed with empty orgs, server will use cached orgs

            # Step 3: Check rate limit — pass reporter_handle for org dodging cache lookup
            if self.isInterruptionRequested():
                return

            result = svc.check_rate_limit(
                self._handle, ip_hash, orgs, reporter_handle=reporter_handle
            )
            if result is None:
                self.finished_error.emit("Rate limit check returned no data.")
                return

            self.finished_success.emit(result)

        except RuntimeError as e:
            log.warning("ReputationCheckRateLimitWorker: %s", e)
            self.finished_error.emit(str(e))
        except Exception as e:
            log.error("ReputationCheckRateLimitWorker.run() unexpected error: %s", e)
            self.finished_error.emit(str(e))


# ---------------------------------------------------------------------------
# ReputationStartupWorker
# ---------------------------------------------------------------------------

class ReputationStartupWorker(QThread):
    """
    Startup worker that pings the keep-alive endpoint and pre-fetches
    the list of known player handles.

    Emits EventBus.reputation_system_status with:
        "online"  — ping OK and handles fetched
        "offline" — ping failed (network unreachable)
        "error"   — service not initialized or fetch_known_handles failed
    Emits finished_success(list) with the list of known handles.
    Emits finished_error(str) on failure (non-fatal — status reflects error state).
    """

    finished_success = pyqtSignal(list)
    finished_error = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

    def run(self) -> None:
        bus = EventBus.instance()
        try:
            if self.isInterruptionRequested():
                return

            svc = ReputationService.instance()

            # Detect local player handle from game.log
            try:
                svc.detect_local_player_handle()
            except Exception as e:
                log.warning("ReputationStartupWorker: Failed to detect local player handle: %s", e)

            # Ping keep-alive to wake free-tier project
            if self.isInterruptionRequested():
                return

            online = svc.ping()

            if not online:
                log.warning("ReputationStartupWorker: ping returned offline")
                bus.reputation_system_status.emit("offline")
                self.finished_error.emit("Reputation database is offline or unreachable.")
                return

            # Pre-fetch known handles
            if self.isInterruptionRequested():
                return

            handles = svc.fetch_known_handles()

            bus.reputation_system_status.emit("online")
            self.finished_success.emit(handles)
            log.info(
                "ReputationStartupWorker: online. %d known handles pre-fetched.", len(handles)
            )

        except RuntimeError as e:
            # Service not initialized or fetch_known_handles failed
            log.warning("ReputationStartupWorker: %s", e)
            bus.reputation_system_status.emit("error")
            self.finished_error.emit(str(e))
        except Exception as e:
            log.error("ReputationStartupWorker.run() unexpected error: %s", e)
            bus.reputation_system_status.emit("error")
            self.finished_error.emit(str(e))
