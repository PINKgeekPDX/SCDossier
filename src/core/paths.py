"""
src/core/paths.py
PathManager — OS-aware singleton for all SC Dossier runtime data paths.

Windows base: %USERPROFILE%\\Documents\\PINK\\SCDossier\\
Linux base:   ~/Documents/PINK/SCDossier/   (or $XDG_DOCUMENTS_DIR/PINK/SCDossier/)

All directories are created on first access.
No PyQt6 imports — pure Python only.
"""

import os
import sys
import platform
from pathlib import Path


class PathManager:
    """
    Singleton that resolves all runtime data paths in an OS-aware manner.

    Usage:
        paths = PathManager.instance()
        config = paths.settings_file
        temp = paths.temp_cache_dir("SomePlayer")
    """

    _instance: "PathManager | None" = None

    def __init__(self) -> None:
        self._base = self._resolve_base()
        # Eagerly create top-level dirs
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.temp_root.mkdir(parents=True, exist_ok=True)
        self.archived_root.mkdir(parents=True, exist_ok=True)

    @classmethod
    def instance(cls) -> "PathManager":
        """Return the singleton PathManager instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Base Resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_base() -> Path:
        """Resolve the SC Dossier data root for the current OS."""
        if platform.system() == "Windows":
            # Use USERPROFILE\Documents on Windows
            user_profile = os.environ.get("USERPROFILE", Path.home())
            return Path(user_profile) / "Documents" / "PINK" / "SCDossier"
        else:
            # Linux / macOS — prefer XDG_DOCUMENTS_DIR, fall back to ~/Documents
            xdg = os.environ.get("XDG_DOCUMENTS_DIR", "")
            if xdg:
                return Path(xdg) / "PINK" / "SCDossier"
            return Path.home() / "Documents" / "PINK" / "SCDossier"

    # ------------------------------------------------------------------
    # Fixed Directories
    # ------------------------------------------------------------------

    @property
    def base(self) -> Path:
        """Root data directory: .../PINK/SCDossier/"""
        return self._base

    @property
    def config_dir(self) -> Path:
        """Config directory: .../PINK/SCDossier/Config/"""
        p = self._base / "Config"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def logs_dir(self) -> Path:
        """Logs directory: .../PINK/SCDossier/Logs/"""
        p = self._base / "Logs"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def temp_root(self) -> Path:
        """Temp cache root: .../PINK/SCDossier/Cache/Temp/"""
        p = self._base / "Cache" / "Temp"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def archived_root(self) -> Path:
        """Archived profiles root: .../PINK/SCDossier/Cache/Archived/"""
        p = self._base / "Cache" / "Archived"
        p.mkdir(parents=True, exist_ok=True)
        return p

    # ------------------------------------------------------------------
    # Dynamic Per-Profile Paths
    # ------------------------------------------------------------------

    def temp_cache_dir(self, player_name: str) -> Path:
        """
        Temp cache directory for a specific player handle.
        Created on first access.

        Example: .../Cache/Temp/PINKgeekPDX/
        """
        safe = self._safe_name(player_name)
        p = self.temp_root / safe
        p.mkdir(parents=True, exist_ok=True)
        return p

    def archived_dir(self, player_name: str) -> Path:
        """
        Archived profile directory for a specific player handle.
        Created on first access.

        Example: .../Cache/Archived/PINKgeekPDX/
        """
        safe = self._safe_name(player_name)
        p = self.archived_root / safe
        p.mkdir(parents=True, exist_ok=True)
        return p

    def ocr_captures_dir(self) -> Path:
        """
        Directory for OCR screen capture temp images.
        Stored under .../Cache/Temp/_captures/
        """
        p = self.temp_root / "_captures"
        p.mkdir(parents=True, exist_ok=True)
        return p

    # ------------------------------------------------------------------
    # Fixed File Paths
    # ------------------------------------------------------------------

    @property
    def documents_root(self) -> Path:
        """Platform-appropriate documents directory."""
        if platform.system() == "Windows":
            user_profile = os.environ.get("USERPROFILE", Path.home())
            return Path(user_profile) / "Documents"
        else:
            xdg = os.environ.get("XDG_DOCUMENTS_DIR", "")
            if xdg:
                return Path(xdg)
            return Path.home() / "Documents"

    @property
    def settings_file(self) -> Path:
        """settings.json path: .../Config/settings.json"""
        return self.config_dir / "settings.json"

    @property
    def app_log_file(self) -> Path:
        """App log file: .../Logs/app.log"""
        return self.logs_dir / "app.log"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_name(name: str) -> str:
        """
        Sanitize a player name for use as a directory name.
        RSI handles are [A-Za-z0-9_-] so this is a safety net only.
        """
        safe = "".join(c for c in name if c.isalnum() or c in ("-", "_"))
        return safe or "_unknown"

    def profile_json(self, player_name: str, archived: bool = False) -> Path:
        """Convenience: get the profile.json path for temp or archived."""
        base_dir = self.archived_dir(player_name) if archived else self.temp_cache_dir(player_name)
        return base_dir / "profile.json"

    def __repr__(self) -> str:
        return f"PathManager(base={self._base})"
