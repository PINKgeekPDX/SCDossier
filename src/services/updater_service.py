"""
src/services/updater_service.py
UpdaterService — checks GitHub for new releases, downloads updates,
and handles self-replacement of the application executable.
"""

import logging
import json
import os
import sys
import urllib.request
import tempfile
import zipfile
import shutil
import subprocess
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal, QObject

from src.app.constants import APP_VERSION

log = logging.getLogger(__name__)

GITHUB_REPO = "PINKgeekPDX/SCDossier"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


class UpdaterWorker(QThread):
    update_available = pyqtSignal(str, str, str)  # version, url, release_notes
    error = pyqtSignal(str)
    up_to_date = pyqtSignal()
    check_complete = pyqtSignal(bool)  # True if update available

    def __init__(self, silent: bool = False, parent=None):
        super().__init__(parent)
        self._silent = silent
        self._download_url = ""
        self._asset_url = ""

    def run(self) -> None:
        try:
            req = urllib.request.Request(
                GITHUB_API,
                headers={"User-Agent": f"SCDossier/{APP_VERSION}"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())

                latest_version = data.get("tag_name", "").lstrip("v")
                if not latest_version:
                    return

                if self._is_newer(APP_VERSION, latest_version):
                    release_notes = data.get("body", "")
                    download_url = data.get("html_url", "")

                    # Find the right asset for this platform
                    import platform
                    sys_name = platform.system().lower()
                    if sys_name == "darwin":
                        sys_name = "mac"

                    assets = data.get("assets", [])
                    for asset in assets:
                        name = asset.get("name", "").lower()
                        # Match the zipped asset for the specific platform
                        if name.endswith(".zip") and sys_name in name:
                            self._asset_url = asset.get("browser_download_url", "")
                            break

                    self.update_available.emit(latest_version, download_url, release_notes)
                    self.check_complete.emit(True)
                else:
                    if not self._silent:
                        self.up_to_date.emit()
                    self.check_complete.emit(False)

        except Exception as e:
            log.debug(f"Update check failed: {e}")
            if not self._silent:
                self.error.emit(str(e))
            self.check_complete.emit(False)

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


class UpdateDownloader(QThread):
    """Downloads the update asset in the background."""
    download_progress = pyqtSignal(int)  # percentage
    download_complete = pyqtSignal(str)  # local path to downloaded file
    download_failed = pyqtSignal(str)    # error message

    def __init__(self, asset_url: str, parent=None):
        super().__init__(parent)
        self._asset_url = asset_url

    def run(self) -> None:
        try:
            temp_dir = Path(tempfile.gettempdir()) / "SCDossier_Update"
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Determine filename from URL
            filename = self._asset_url.split("/")[-1].split("?")[0]
            if not filename:
                filename = "SCDossier_Update.zip"
            local_path = temp_dir / filename

            req = urllib.request.Request(
                self._asset_url,
                headers={"User-Agent": f"SCDossier/{APP_VERSION}"}
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                total_size = int(response.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 8192

                with open(local_path, "wb") as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = int(downloaded * 100 / total_size)
                            self.download_progress.emit(progress)

            self.download_complete.emit(str(local_path))

        except Exception as e:
            log.error(f"Download failed: {e}")
            self.download_failed.emit(str(e))


class UpdaterService(QObject):
    """Service managing application update checks and installation."""

    update_status = pyqtSignal(str)  # status message
    update_checked = pyqtSignal(bool, str)  # update_available, version_or_msg
    download_progress = pyqtSignal(int)   # percentage 0-100
    update_ready_to_install = pyqtSignal(str)  # staged local path

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._downloader = None
        self._pending_version = ""
        self._pending_url = ""
        self._pending_notes = ""
        self._asset_url = ""
        self._staged_path = ""  # path of staged update file, set after download

    @property
    def current_version(self) -> str:
        return APP_VERSION

    def check_for_updates(self, silent: bool = False) -> None:
        """Check GitHub releases for a newer version."""
        if self._worker and self._worker.isRunning():
            return

        self.update_status.emit("CHECKING FOR UPDATES...")
        self._worker = UpdaterWorker(silent=silent)
        self._worker.update_available.connect(self._on_update_available)
        self._worker.up_to_date.connect(self._on_up_to_date)
        self._worker.error.connect(self._on_update_error)
        self._worker.check_complete.connect(self._on_check_complete)
        self._worker.start()

    def download_update(self, asset_url: str) -> None:
        """Download the update asset."""
        if self._downloader and self._downloader.isRunning():
            return

        self.update_status.emit("DOWNLOADING UPDATE...")
        self._downloader = UpdateDownloader(asset_url)
        self._downloader.download_progress.connect(self._on_download_progress)
        self._downloader.download_complete.connect(self._on_download_complete)
        self._downloader.download_failed.connect(self._on_download_failed)
        self._downloader.start()

    def install_update(self, downloaded_path: str) -> None:
        """Install the downloaded (or staged) update and restart the application."""
        try:
            self.update_status.emit("INSTALLING UPDATE...")

            # Extract binary from zip if needed
            actual_path = downloaded_path
            if downloaded_path.lower().endswith(".zip"):
                actual_path = self._extract_binary_from_zip(downloaded_path)
                if not actual_path:
                    self.update_status.emit("INSTALL FAILED: No valid executable found in ZIP")
                    return

            if sys.platform == "win32":
                self._install_windows(actual_path)
            else:
                self._install_posix(actual_path)

        except Exception as e:
            log.error(f"Install failed: {e}")
            self.update_status.emit(f"INSTALL FAILED: {e}")

    def _extract_binary_from_zip(self, zip_path: str) -> str:
        """Extract the target installer binary from a ZIP archive; return its local path or ''."""
        try:
            extract_dir = Path(zip_path).parent / "extracted"
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            target_ext = ".exe" if sys.platform == "win32" else ""
            
            with zipfile.ZipFile(zip_path, "r") as zf:
                for name in zf.namelist():
                    lower_name = name.lower()
                    if lower_name.endswith("setup.exe") or (target_ext and lower_name.endswith(target_ext)):
                        zf.extract(name, extract_dir)
                        exe_path = extract_dir / name
                        log.info("Extracted installer binary: %s", exe_path)
                        return str(exe_path)
            log.error("No valid binary found in ZIP: %s", zip_path)
            return ""
        except Exception as e:
            log.error("ZIP extraction failed: %s", e)
            return ""

    def _install_windows(self, download_path: str) -> None:
        """Windows: Launch the setup installer and restart the application."""
        current_exe = sys.executable
        if not current_exe.endswith(".exe"):
            # Running from python, not a bundled exe
            self.update_status.emit("Cannot auto-update in development mode")
            return

        # Launch the installer interactively
        try:
            log.info(f"Launching installer: {download_path}")
            subprocess.Popen([download_path])
            
            # Schedule app exit so the installer can overwrite files
            from src.core.events import EventBus
            EventBus.instance().app_exit.emit()
            self.update_status.emit("LAUNCHING INSTALLER — CLOSING APP...")
        except Exception as e:
            log.error(f"Failed to launch installer: {e}")
            self.update_status.emit(f"INSTALL FAILED: {e}")

    def _install_posix(self, download_path: str) -> None:
        """POSIX: Handle update installation (rename, copy, restart)."""
        current_exe = sys.executable
        if not current_exe.endswith("SCDossier"):
            self.update_status.emit("Cannot auto-update in development mode")
            return

        import stat
        try:
            # Overwriting a running binary yields 'Text file busy'.
            # Renaming the running binary is allowed.
            old_exe = current_exe + ".old"
            if os.path.exists(old_exe):
                os.remove(old_exe)
            os.rename(current_exe, old_exe)
            
            shutil.copy2(download_path, current_exe)
            os.chmod(current_exe, os.stat(current_exe).st_mode | stat.S_IEXEC)
            
            # Start the new version
            subprocess.Popen([current_exe])
            
            # Exit this one
            from src.core.events import EventBus
            EventBus.instance().app_exit.emit()
            self.update_status.emit("UPDATE INSTALLED — RESTARTING...")
        except Exception as e:
            # Fallback to rollback
            log.error(f"POSIX install failed: {e}")
            if not os.path.exists(current_exe) and os.path.exists(current_exe + ".old"):
                os.rename(current_exe + ".old", current_exe)
            raise

    def _on_update_available(self, version: str, url: str, notes: str) -> None:
        self._pending_version = version
        self._pending_url = url
        self._pending_notes = notes
        self._asset_url = self._worker._asset_url if hasattr(self._worker, '_asset_url') else ""
        self.update_status.emit(f"UPDATE AVAILABLE: v{version}")
        self.update_checked.emit(True, version)

        from src.core.events import EventBus
        EventBus.instance().status_message.emit(f"UPDATE AVAILABLE: v{version}", "info")

    def _on_up_to_date(self) -> None:
        self.update_status.emit(f"SC Dossier v{APP_VERSION} is up to date")
        self.update_checked.emit(False, APP_VERSION)

        from src.core.events import EventBus
        EventBus.instance().status_message.emit("APP IS UP TO DATE", "success")

    def _on_update_error(self, error_msg: str) -> None:
        self.update_status.emit(f"UPDATE CHECK FAILED")
        self.update_checked.emit(False, error_msg)
        log.error(f"Update check failed: {error_msg}")

    def _on_check_complete(self, available: bool) -> None:
        pass

    def _on_download_progress(self, percentage: int) -> None:
        self.update_status.emit(f"DOWNLOADING... {percentage}%")
        self.download_progress.emit(percentage)

    def _on_download_complete(self, local_path: str) -> None:
        """Stage the downloaded file and notify UI to enable install button."""
        self._staged_path = local_path
        self.update_status.emit("UPDATE READY TO INSTALL")
        self.update_ready_to_install.emit(local_path)
        log.info("Update staged at: %s", local_path)

    def _on_download_failed(self, error_msg: str) -> None:
        self.update_status.emit(f"DOWNLOAD FAILED: {error_msg}")