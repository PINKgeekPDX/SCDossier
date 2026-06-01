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

    def __init__(self, handle: str, tags: list, parent=None) -> None:
        super().__init__(parent)
        self._handle = handle
        self._tags = list(tags)

    def run(self) -> None:
        try:
            svc = ReputationService.instance()

            # Step 1: Get IP hash — required for rate limiting
            ip_hash = svc._get_ip_hash()
            if ip_hash is None:
                msg = "Could not determine IP for rate limiting. Check your internet connection."
                log.warning("ReputationSubmitWorker: %s", msg)
                self.finished_error.emit(msg)
                return

            # Step 2: Submit the report
            result = svc.submit_report(self._handle, self._tags, ip_hash)
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
# ReputationStartupWorker
# ---------------------------------------------------------------------------

class ReputationStartupWorker(QThread):
    """
    Startup worker that pings the keep-alive endpoint and pre-fetches
    the list of known player handles.

    Emits EventBus.reputation_system_status("online") or ("offline").
    Emits finished_success(list) with the list of known handles.
    Emits finished_error(str) on critical failure (non-fatal — status is offline).
    """

    finished_success = pyqtSignal(list)
    finished_error = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

    def run(self) -> None:
        bus = EventBus.instance()
        try:
            svc = ReputationService.instance()

            # Detect local player handle from game.log
            try:
                svc.detect_local_player_handle()
            except Exception as e:
                log.warning("ReputationStartupWorker: Failed to detect local player handle: %s", e)

            # Ping keep-alive to wake free-tier project
            online = svc.ping()

            if not online:
                log.warning("ReputationStartupWorker: ping returned offline")
                bus.reputation_system_status.emit("offline")
                self.finished_error.emit("Reputation database is offline or unreachable.")
                return

            # Pre-fetch known handles
            handles = svc.fetch_known_handles()

            bus.reputation_system_status.emit("online")
            self.finished_success.emit(handles)
            log.info(
                "ReputationStartupWorker: online. %d known handles pre-fetched.", len(handles)
            )

        except RuntimeError as e:
            # Service not initialized
            log.warning("ReputationStartupWorker: %s", e)
            bus.reputation_system_status.emit("offline")
            self.finished_error.emit(str(e))
        except Exception as e:
            log.error("ReputationStartupWorker.run() unexpected error: %s", e)
            bus.reputation_system_status.emit("offline")
            self.finished_error.emit(str(e))
