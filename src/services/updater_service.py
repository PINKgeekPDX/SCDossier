"""
src/services/updater_service.py
UpdaterService — checks GitHub for new releases.
"""

import logging
import json
import urllib.request
from PyQt6.QtCore import QThread, pyqtSignal

from src.app.constants import APP_VERSION

log = logging.getLogger(__name__)

class UpdaterWorker(QThread):
    update_available = pyqtSignal(str, str, str) # version, url, release_notes
    error = pyqtSignal(str)
    up_to_date = pyqtSignal()

    def run(self) -> None:
        url = "https://api.github.com/repos/PINKgeekPDX/SCDossier/releases/latest"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": f"SCDossier/{APP_VERSION}"})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                
                latest_version = data.get("tag_name", "").lstrip("v")
                if not latest_version:
                    return
                
                if self._is_newer(APP_VERSION, latest_version):
                    release_notes = data.get("body", "")
                    download_url = data.get("html_url", "")
                    self.update_available.emit(latest_version, download_url, release_notes)
                else:
                    self.up_to_date.emit()
                    
        except Exception as e:
            log.debug(f"Update check failed: {e}")
            self.error.emit(str(e))

    def _is_newer(self, current: str, latest: str) -> bool:
        try:
            curr_parts = [int(x) for x in current.split(".")]
            latest_parts = [int(x) for x in latest.split(".")]
            for c, l in zip(curr_parts, latest_parts):
                if l > c:
                    return True
                elif c > l:
                    return False
            return len(latest_parts) > len(curr_parts)
        except Exception:
            return current != latest

class UpdaterService:
    def __init__(self):
        self._worker = None

    def check_for_updates(self):
        if self._worker and self._worker.isRunning():
            return
            
        self._worker = UpdaterWorker()
        self._worker.update_available.connect(self._on_update_available)
        self._worker.start()

    def _on_update_available(self, version: str, url: str, notes: str):
        from src.core.events import EventBus
        EventBus.instance().status_message.emit(f"UPDATE AVAILABLE: v{version}", "info")
