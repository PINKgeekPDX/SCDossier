"""
src/services/image_downloader.py
ImageDownloader — QThreadPool worker for concurrent image fetching.
"""

import logging
import requests
from pathlib import Path
from PyQt6.QtCore import QRunnable, QObject, pyqtSignal, QThreadPool

from src.core.events import EventBus

log = logging.getLogger(__name__)


class DownloaderSignals(QObject):
    """Signals for the ImageDownloaderWorker."""
    finished_success = pyqtSignal(str, str)  # url, local_path
    finished_error = pyqtSignal(str, str)    # url, error_msg


class ImageDownloaderWorker(QRunnable):
    """
    QRunnable task to download a single image and save it to disk.
    """

    def __init__(self, url: str, dest_path: Path, user_agent: str) -> None:
        super().__init__()
        self.url = url
        self.dest_path = dest_path
        self.user_agent = user_agent
        self.signals = DownloaderSignals()

    def run(self) -> None:
        if self.dest_path.exists():
            log.debug("Image already exists locally: %s", self.dest_path)
            self.signals.finished_success.emit(self.url, str(self.dest_path))
            return

        try:
            log.debug("Downloading image: %s", self.url)
            headers = {"User-Agent": self.user_agent}
            resp = requests.get(self.url, headers=headers, timeout=10)
            resp.raise_for_status()

            # Create parent dirs if needed
            self.dest_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.dest_path, "wb") as f:
                f.write(resp.content)

            log.debug("Saved image to: %s", self.dest_path)
            self.signals.finished_success.emit(self.url, str(self.dest_path))

        except Exception as e:
            log.error("Failed to download image %s: %s", self.url, e)
            self.signals.finished_error.emit(self.url, str(e))


class ImageDownloader:
    """
    Service for downloading images concurrently using Qt's thread pool.
    Results are emitted via EventBus.
    """

    def __init__(self) -> None:
        self.pool = QThreadPool.globalInstance()

    def download(self, url: str, dest_path: Path) -> None:
        """Queue an image for download."""
        if not url:
            return

        from src.core.settings import SettingsManager
        ua = SettingsManager.instance().user_agent

        worker = ImageDownloaderWorker(url, dest_path, ua)
        worker.signals.finished_success.connect(self._on_success)
        worker.signals.finished_error.connect(self._on_error)

        self.pool.start(worker)

    def _on_success(self, url: str, local_path: str) -> None:
        EventBus.instance().image_downloaded.emit(url, local_path)

    def _on_error(self, url: str, error_msg: str) -> None:
        EventBus.instance().image_download_failed.emit(url, error_msg)
