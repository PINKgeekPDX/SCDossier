"""
src/services/updater_service.py
UpdaterService — checks GitHub for new releases, downloads updates,
and handles self-replacement of the application executable.

Supports two release channels:
  - "live"  — stable releases (tags like v0.4.2)
  - "beta"  — pre-release builds (tags like b0.4.1)
"""

import logging
import json
import os
import ssl
import sys
import urllib.request
import tempfile
import zipfile
import shutil
import subprocess
from pathlib import Path
from dataclasses import dataclass

from PyQt6.QtCore import QThread, pyqtSignal, QObject

from src.app.constants import APP_VERSION

log = logging.getLogger(__name__)

GITHUB_REPO = "PINKgeekPDX/SCDossier"
GITHUB_API_RELEASES = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
GITHUB_API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


# ---------------------------------------------------------------------------
# Version helpers
# ---------------------------------------------------------------------------

def _strip_tag(tag: str) -> str:
    """Strip leading 'v' or 'b' from a tag for numeric comparison."""
    return tag.lstrip("vb")


def _parse_version_parts(version: str) -> list[int]:
    """Parse a version string like '0.4.1' or 'b0.4.1' into [0, 4, 1]."""
    clean = _strip_tag(version)
    try:
        return [int(x) for x in clean.split(".")]
    except (ValueError, AttributeError):
        return [0]


def _is_newer(current: str, latest: str) -> bool:
    """Return True if *latest* is a newer version than *current*."""
    curr = _parse_version_parts(current)
    lat = _parse_version_parts(latest)
    for c, l in zip(curr, lat):
        if l > c:
            return True
        elif c > l:
            return False
    return len(lat) > len(curr)


def _is_beta_tag(tag: str) -> bool:
    """Return True if the tag represents a beta release (e.g. 'b0.4.1')."""
    stripped = tag.lstrip("v")
    return stripped.startswith("b")


def _find_platform_asset(assets: list[dict]) -> str | None:
    """Find the browser_download_url for a platform-specific ZIP asset."""
    import platform as _plat
    sys_name = _plat.system().lower()
    if sys_name == "darwin":
        sys_name = "mac"
    for asset in assets:
        name = asset.get("name", "").lower()
        if name.endswith(".zip") and sys_name in name:
            return asset.get("browser_download_url")
    return None


def _make_ssl_context() -> ssl.SSLContext:
    """Create an SSL context that works on all platforms."""
    ctx = ssl.create_default_context()
    return ctx


def _github_request(url: str, timeout: int = 15) -> dict | list:
    """Make a GitHub API request with proper SSL and error handling."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"SCDossier/{APP_VERSION}",
            "Accept": "application/vnd.github.v3+json",
        }
    )
    ctx = _make_ssl_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return json.loads(resp.read().decode())


# ---------------------------------------------------------------------------
# Data class for release info
# ---------------------------------------------------------------------------

@dataclass
class ReleaseInfo:
    tag: str
    version: str          # cleaned numeric version (e.g. "0.4.1")
    is_beta: bool
    name: str
    body: str
    asset_url: str | None = None
    published_at: str = ""
    html_url: str = ""


# ---------------------------------------------------------------------------
# Background workers
# ---------------------------------------------------------------------------

class ReleaseListWorker(QThread):
    """Fetches ALL releases from GitHub and filters by channel."""
    releases_fetched = pyqtSignal(list)   # list[ReleaseInfo]
    error = pyqtSignal(str)

    def __init__(self, channel: str = "live", parent=None):
        super().__init__(parent)
        self._channel = channel

    def run(self) -> None:
        try:
            log.info("Fetching releases for channel: %s", self._channel)
            data = _github_request(GITHUB_API_RELEASES)
            log.info("GitHub returned %d releases", len(data))

            releases: list[ReleaseInfo] = []
            for r in data:
                tag = r.get("tag_name", "")
                if not tag:
                    continue
                is_beta = _is_beta_tag(tag)
                log.debug("  tag=%s is_beta=%s prerelease=%s", tag, is_beta, r.get("prerelease"))

                # Filter by channel
                if self._channel == "live" and is_beta:
                    continue
                if self._channel == "beta" and not is_beta:
                    continue

                asset_url = _find_platform_asset(r.get("assets", []))
                ri = ReleaseInfo(
                    tag=tag,
                    version=_strip_tag(tag),
                    is_beta=is_beta,
                    name=r.get("name", tag),
                    body=r.get("body", ""),
                    asset_url=asset_url,
                    published_at=r.get("published_at", ""),
                    html_url=r.get("html_url", ""),
                )
                releases.append(ri)

            log.info("Filtered to %d releases for channel '%s'", len(releases), self._channel)
            self.releases_fetched.emit(releases)

        except Exception as e:
            log.error("Release list fetch failed: %s", e, exc_info=True)
            self.error.emit(str(e))


class UpdaterWorker(QThread):
    """Checks GitHub for the latest release in a channel."""
    update_available = pyqtSignal(str, str, str)  # version, url, release_notes
    error = pyqtSignal(str)
    up_to_date = pyqtSignal()
    check_complete = pyqtSignal(bool)  # True if update available

    def __init__(self, channel: str = "live", silent: bool = False, parent=None):
        super().__init__(parent)
        self._channel = channel
        self._silent = silent
        self._asset_url = ""

    def run(self) -> None:
        try:
            if self._channel == "beta":
                self._check_beta()
            else:
                self._check_live()
        except Exception as e:
            log.debug("Update check failed: %s", e)
            if not self._silent:
                self.error.emit(str(e))
            self.check_complete.emit(False)

    def _check_live(self) -> None:
        """Live channel — use /releases/latest."""
        data = _github_request(GITHUB_API_LATEST, timeout=10)
        tag = data.get("tag_name", "")
        latest_version = _strip_tag(tag)
        if not latest_version:
            return

        log.info("Live check: current=%s latest=%s", APP_VERSION, latest_version)
        if _is_newer(APP_VERSION, latest_version):
            release_notes = data.get("body", "")
            download_url = data.get("html_url", "")
            self._asset_url = _find_platform_asset(data.get("assets", [])) or ""
            self.update_available.emit(latest_version, download_url, release_notes)
            self.check_complete.emit(True)
        else:
            if not self._silent:
                self.up_to_date.emit()
            self.check_complete.emit(False)

    def _check_beta(self) -> None:
        """Beta channel — fetch all releases and find latest beta."""
        data = _github_request(GITHUB_API_RELEASES, timeout=15)

        latest_beta = None
        for r in data:
            tag = r.get("tag_name", "")
            if _is_beta_tag(tag):
                latest_beta = r
                break  # GitHub API returns releases newest-first

        if not latest_beta:
            log.info("No beta releases found")
            if not self._silent:
                self.up_to_date.emit()
            self.check_complete.emit(False)
            return

        tag = latest_beta.get("tag_name", "")
        latest_version = _strip_tag(tag)
        if not latest_version:
            return

        log.info("Beta check: current=%s latest=%s", APP_VERSION, latest_version)
        if _is_newer(APP_VERSION, latest_version):
            release_notes = latest_beta.get("body", "")
            download_url = latest_beta.get("html_url", "")
            self._asset_url = _find_platform_asset(latest_beta.get("assets", [])) or ""
            self.update_available.emit(latest_version, download_url, release_notes)
            self.check_complete.emit(True)
        else:
            if not self._silent:
                self.up_to_date.emit()
            self.check_complete.emit(False)


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

            log.info("Downloading update from: %s", self._asset_url)
            req = urllib.request.Request(
                self._asset_url,
                headers={"User-Agent": f"SCDossier/{APP_VERSION}"}
            )
            ctx = _make_ssl_context()
            with urllib.request.urlopen(req, timeout=60, context=ctx) as response:
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

            log.info("Download complete: %s (%d bytes)", local_path, downloaded)
            self.download_complete.emit(str(local_path))

        except Exception as e:
            log.error("Download failed: %s", e, exc_info=True)
            self.download_failed.emit(str(e))


# ---------------------------------------------------------------------------
# Main service
# ---------------------------------------------------------------------------

class UpdaterService(QObject):
    """Service managing application update checks and installation."""

    update_status = pyqtSignal(str)  # status message
    update_checked = pyqtSignal(bool, str)  # update_available, version_or_msg
    download_progress = pyqtSignal(int)   # percentage 0-100
    update_ready_to_install = pyqtSignal(str)  # staged local path
    releases_loaded = pyqtSignal(list)   # list[ReleaseInfo]
    release_list_error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._downloader = None
        self._release_worker = None
        self._pending_version = ""
        self._pending_url = ""
        self._pending_notes = ""
        self._asset_url = ""
        self._staged_path = ""

    @property
    def current_version(self) -> str:
        return APP_VERSION

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_for_updates(self, channel: str = "live", silent: bool = False) -> None:
        """Check GitHub releases for a newer version in the given channel."""
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(2000)

        self.update_status.emit("CHECKING FOR UPDATES...")
        self._worker = UpdaterWorker(channel=channel, silent=silent)
        self._worker.update_available.connect(self._on_update_available)
        self._worker.up_to_date.connect(self._on_up_to_date)
        self._worker.error.connect(self._on_update_error)
        self._worker.check_complete.connect(self._on_check_complete)
        self._worker.start()

    def fetch_all_releases(self, channel: str = "live") -> None:
        """Fetch all releases for the given channel and emit releases_loaded."""
        # Kill old worker if still running
        if self._release_worker and self._release_worker.isRunning():
            self._release_worker.quit()
            self._release_worker.wait(2000)

        self._release_worker = ReleaseListWorker(channel=channel)
        self._release_worker.releases_fetched.connect(self._on_releases_fetched)
        self._release_worker.error.connect(self._on_release_list_error)
        self._release_worker.start()
        log.info("Started release list fetch for channel: %s", channel)

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
                actual_path = self._extract_installer_from_zip(downloaded_path)
                if not actual_path:
                    self.update_status.emit("INSTALL FAILED: No valid executable found in ZIP")
                    return

            if sys.platform == "win32":
                self._install_windows(actual_path)
            else:
                self._install_posix(actual_path)

        except Exception as e:
            log.error("Install failed: %s", e)
            self.update_status.emit(f"INSTALL FAILED: {e}")

    def _extract_installer_from_zip(self, zip_path: str) -> str:
        """Extract the installer binary from a ZIP archive; return its local path or ''."""
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
        """Windows: Launch the setup installer and exit the app so it can overwrite files."""
        current_exe = sys.executable
        if not current_exe.endswith(".exe"):
            self.update_status.emit("Cannot auto-update in development mode")
            return

        try:
            log.info("Launching installer: %s", download_path)
            subprocess.Popen([download_path])

            # Schedule app exit so the installer can overwrite files
            from src.core.events import EventBus
            EventBus.instance().app_exit.emit()
            self.update_status.emit("LAUNCHING INSTALLER — CLOSING APP...")
        except Exception as e:
            log.error("Failed to launch installer: %s", e)
            self.update_status.emit(f"INSTALL FAILED: {e}")

    def _install_posix(self, download_path: str) -> None:
        """POSIX: Handle update installation (rename, copy, restart)."""
        current_exe = sys.executable
        if not current_exe.endswith("SCDossier"):
            self.update_status.emit("Cannot auto-update in development mode")
            return

        import stat
        try:
            old_exe = current_exe + ".old"
            if os.path.exists(old_exe):
                os.remove(old_exe)
            os.rename(current_exe, old_exe)

            shutil.copy2(download_path, current_exe)
            os.chmod(current_exe, os.stat(current_exe).st_mode | stat.S_IEXEC)

            subprocess.Popen([current_exe])

            from src.core.events import EventBus
            EventBus.instance().app_exit.emit()
            self.update_status.emit("UPDATE INSTALLED — RESTARTING...")
        except Exception as e:
            log.error("POSIX install failed: %s", e)
            if not os.path.exists(current_exe) and os.path.exists(current_exe + ".old"):
                os.rename(current_exe + ".old", current_exe)
            raise

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------

    def _on_update_available(self, version: str, url: str, notes: str) -> None:
        self._pending_version = version
        self._pending_url = url
        self._pending_notes = notes
        self._asset_url = self._worker._asset_url if self._worker else ""
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
        self.update_status.emit("UPDATE CHECK FAILED")
        self.update_checked.emit(False, error_msg)
        log.error("Update check failed: %s", error_msg)

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

    def _on_releases_fetched(self, releases: list) -> None:
        log.info("Releases fetched: %d items", len(releases))
        self.releases_loaded.emit(releases)

    def _on_release_list_error(self, error_msg: str) -> None:
        log.error("Release list error: %s", error_msg)
        self.release_list_error.emit(error_msg)
