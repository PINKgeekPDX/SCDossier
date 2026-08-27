"""
src/app/workers/startup_worker.py
StartupWorker - Background tasks on application launch.

Performs initial, non-blocking tasks like:
  - Pinging the Supabase server to wake it up.
  - Detecting the local player handle from game logs.
"""

import logging
from PyQt6.QtCore import QObject, pyqtSignal

log = logging.getLogger(__name__)


class StartupWorker(QObject):
    """Performs background startup tasks."""

    finished = pyqtSignal()
    error = pyqtSignal(str)
    handle_detected = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()

    def run(self) -> None:
        """Main worker entry point."""
        try:
            from src.services.reputation_service import ReputationService

            if not ReputationService.is_initialized():
                log.warning("ReputationService not ready for startup worker.")
                self.finished.emit()
                return

            svc = ReputationService.instance()

            # Task 1: Ping Supabase to wake it up
            log.info("StartupWorker: Pinging Supabase...")
            svc.ping()

            # Task 2: Detect local player handle
            log.info("StartupWorker: Detecting local player handle...")
            handle = svc.detect_local_player_handle()
            if handle:
                self.handle_detected.emit(handle)

            self.finished.emit()

        except Exception as e:
            log.error("Error in StartupWorker: %s", e, exc_info=True)
            self.error.emit(str(e))
