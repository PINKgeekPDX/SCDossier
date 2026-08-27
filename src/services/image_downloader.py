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
        self.setAutoDelete(False)
        self.url = url
        self.dest_path = dest_path
        self.user_agent = user_agent
        self.signals = DownloaderSignals()
        # Keep signals alive until worker is explicitly deleted
        self.signals.setParent(None)

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
        # Limit concurrent image downloads to avoid saturating the pool and UI thread
        if self.pool.maxThreadCount() > 6:
            self.pool.setMaxThreadCount(6)
        self._active_workers: set[ImageDownloaderWorker] = set()

    def download(self, url: str, dest_path: Path) -> None:
        """Queue an image for download."""
        if not url:
            return

        from src.core.settings import SettingsManager
        ua = SettingsManager.instance().user_agent

        worker = ImageDownloaderWorker(url, dest_path, ua)
        self._active_workers.add(worker)
        # Use queued connections to ensure signals are delivered on main thread
        worker.signals.finished_success.connect(self._on_success)
        worker.signals.finished_error.connect(self._on_error)
        # Clean up worker after signal delivered (singleShot to defer until event loop processes)
        def _cleanup(w=worker):
            self._active_workers.discard(w)
            w.signals.deleteLater()
            # Schedule QRunnable deletion on next event loop tick
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: None)  # ensure event loop processes
            # Explicitly delete the QRunnable after signals processed
            # Use a timer to defer deletion until queued signals are delivered
            QTimer.singleShot(100, lambda w=w: self._delete_worker(w))
        worker.signals.finished_success.connect(lambda *a, w=worker: _cleanup(w))
        worker.signals.finished_error.connect(lambda *a, w=worker: _cleanup(w))

        self.pool.start(worker)

    def _delete_worker(self, worker: ImageDownloaderWorker) -> None:
        """Safely delete a finished QRunnable worker."""
        try:
            # QRunnable will be garbage collected; no explicit delete needed for Python
            pass
        except Exception:
            pass


    def queue_download(self, url: str, dest_path: str) -> None:
        """Queue an image for download. Accepts str or Path for dest_path."""
        self.download(url, Path(dest_path) if isinstance(dest_path, str) else dest_path)
    def _on_success(self, url: str, local_path: str) -> None:
        EventBus.instance().image_downloaded.emit(url, local_path)

    def _on_error(self, url: str, error_msg: str) -> None:
        EventBus.instance().image_download_failed.emit(url, error_msg)

