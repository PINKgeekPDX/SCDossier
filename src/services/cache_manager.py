"""
src/services/cache_manager.py
CacheManager — handles JSON I/O for temp and archived profiles.
"""

import json
import shutil
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

from src.core.paths import PathManager

log = logging.getLogger(__name__)

# Maximum number of temp-cached profiles to keep on disk
_MAX_TEMP_CACHE_PROFILES = 50


class CacheManager:
    """
    Manages reading and writing profile data to the filesystem.
    Handles both temporary (Cache/Temp) and archived (Cache/Archived) storage.
    """

    def __init__(self) -> None:
        self.paths = PathManager.instance()
        self._lock = threading.RLock()

    def is_archived(self, handle: str) -> bool:
        """Check if a player profile exists in the archived directory."""
        return self.paths.profile_json(handle, archived=True).exists()

    def is_temp(self, handle: str) -> bool:
        """Check if a player profile exists in the temp directory."""
        return self.paths.profile_json(handle, archived=False).exists()

    def load_profile(self, handle: str, archived: bool = False) -> dict | None:
        """Load profile JSON. Prefer archived if exists, otherwise temp."""
        # If archived is explicitly requested or exists
        if archived or self.is_archived(handle):
            path = self.paths.profile_json(handle, archived=True)
        else:
            path = self.paths.profile_json(handle, archived=False)

        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.error("Failed to load profile %s: %s", path, e)
            return None

    def save_temp_profile(self, data: dict) -> Path | None:
        """Save a newly scraped profile to the temp cache."""
        handle = data.get("handle")
        if not handle:
            return None

        with self._lock:
            # Clean up existing temp dir to avoid orphaned images
            temp_dir = self.paths.temp_cache_dir(handle)
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)

            json_path = temp_dir / "profile.json"
            try:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                self._evict_lru_temp(_MAX_TEMP_CACHE_PROFILES)
                return json_path
            except OSError as e:
                log.error("Failed to save temp profile for %s: %s", handle, e)
                return None

    def _evict_lru_temp(self, max_count: int) -> None:
        """Remove oldest temp profiles when count exceeds max_count (LRU by mtime)."""
        temp_root = self.paths.temp_root
        if not temp_root.exists():
            return
        dirs = [d for d in temp_root.iterdir()
                if d.is_dir() and d.name != "_captures"]
        if len(dirs) <= max_count:
            return
        dirs.sort(key=lambda d: d.stat().st_mtime)
        to_remove = dirs[:len(dirs) - max_count]
        for d in to_remove:
            try:
                shutil.rmtree(d)
                log.info("LRU evicted temp cache: %s", d.name)
            except Exception as e:
                log.warning("Failed to evict %s: %s", d, e)

    def save_archived_profile(self, data: dict) -> Path | None:
        """Save a profile to the archived directory, adding archive metadata."""
        handle = data.get("handle")
        if not handle:
            return None

        with self._lock:
            if "archived_at" not in data:
                data["archived_at"] = datetime.now(timezone.utc).isoformat()
            
            # When first archived, synced_at is the same as scraped_at
            if "synced_at" not in data:
                data["synced_at"] = data.get("scraped_at", data["archived_at"])

            arch_dir = self.paths.archived_dir(handle)
            arch_dir.mkdir(parents=True, exist_ok=True)
            
            json_path = arch_dir / "profile.json"
            try:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                return json_path
            except OSError as e:
                log.error("Failed to save archived profile for %s: %s", handle, e)
                return None

    def promote_to_archive(self, handle: str) -> bool:
        """
        Move a profile and all its downloaded images from Temp to Archived.
        """
        if self.is_archived(handle):
            # Already archived. We might just overwrite.
            pass

        temp_dir = self.paths.temp_cache_dir(handle)
        if not temp_dir.exists() or not self.is_temp(handle):
            log.error("Cannot promote %s: temp profile does not exist", handle)
            return False

        data = self.load_profile(handle, archived=False)
        if not data:
            return False

        arch_dir = self.paths.archived_dir(handle)
        arch_dir.mkdir(parents=True, exist_ok=True)

        # Copy all image files
        for item in temp_dir.iterdir():
            if item.is_file() and item.suffix.lower() in (".png", ".jpg", ".jpeg"):
                shutil.copy2(item, arch_dir / item.name)
                
        # Re-map local paths in JSON to point to archive folder
        self._remap_local_paths(data, arch_dir)
        
        # Save as archived
        success = bool(self.save_archived_profile(data))
        if success:
            # Cleanup temp
            shutil.rmtree(temp_dir)
        return success

    def _remap_local_paths(self, data: dict, new_dir: Path) -> None:
        """Update image local paths in a profile dict to point to the new directory."""
        if data.get("avatar_local"):
            data["avatar_local"] = str(new_dir / Path(data["avatar_local"]).name)
        
        if data.get("logo_local"):
            data["logo_local"] = str(new_dir / Path(data["logo_local"]).name)
        
        if data.get("banner_local"):
            data["banner_local"] = str(new_dir / Path(data["banner_local"]).name)
        
        if data.get("focus_primary_local"):
            data["focus_primary_local"] = str(new_dir / Path(data["focus_primary_local"]).name)
        
        if data.get("focus_secondary_local"):
            data["focus_secondary_local"] = str(new_dir / Path(data["focus_secondary_local"]).name)
            
        for badge in data.get("badges", []):
            if badge.get("image_local"):
                badge["image_local"] = str(new_dir / Path(badge["image_local"]).name)
                
        for org in data.get("orgs", []):
            if org.get("logo_local"):
                org["logo_local"] = str(new_dir / Path(org["logo_local"]).name)


    def get_temp_profile(self, handle: str) -> dict | None:
        """Load a profile from the temp cache. Alias for load_profile(archived=False)."""
        return self.load_profile(handle, archived=False)

    def get_temp_path(self, handle: str) -> str:
        """Return the string path to the temp cache directory for a handle."""
        return str(self.paths.temp_cache_dir(handle))

    def get_org_path(self, sid: str) -> str:
        """Return the string path to the temp cache directory for an org SID."""
        return str(self.paths.temp_cache_dir(f"org_{sid}"))

    def save_org_profile(self, data: dict) -> "Path | None":
        """Save a scraped org profile to the temp cache (keyed by SID)."""
        sid = data.get("sid")
        if not sid:
            return None

        with self._lock:
            temp_dir = self.paths.temp_cache_dir(f"org_{sid}")
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)

            json_path = temp_dir / "profile.json"
            try:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                return json_path
            except OSError as e:
                log.error("Failed to save org profile for %s: %s", sid, e)
                return None
    def cleanup_temp(self, max_age_days: int) -> None:
        """Delete temp caches older than max_age_days."""
        now = datetime.now(timezone.utc).timestamp()
        max_age_sec = max_age_days * 24 * 3600

        for d in self.paths.temp_root.iterdir():
            if d.is_dir() and d.name != "_captures":
                try:
                    mtime = d.stat().st_mtime
                    if now - mtime > max_age_sec:
                        shutil.rmtree(d)
                        log.info("Cleaned up old temp cache: %s", d.name)
                except Exception as e:
                    log.warning("Failed to cleanup %s: %s", d, e)

        # Cleanup captures
        cap_dir = self.paths.ocr_captures_dir()
        if cap_dir.exists():
            for f in cap_dir.iterdir():
                if f.is_file():
                    try:
                        mtime = f.stat().st_mtime
                        # Captures expire much faster (e.g. 1 hour)
                        if now - mtime > 3600:
                            f.unlink()
                    except Exception:
                        pass

