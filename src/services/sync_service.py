"""
src/services/sync_service.py
SyncService — diffs live profile against archived profile and merges updates.
"""

import logging
from datetime import datetime, timezone, timedelta
from PyQt6.QtCore import QObject

from src.services.cache_manager import CacheManager
from src.core.events import EventBus

log = logging.getLogger(__name__)


class SyncService(QObject):
    """
    Compares a live scraped profile (Temp) against an existing Archive.
    If changes are detected, it updates the Archive json.
    """

    def __init__(self, cache_manager: CacheManager, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.cache = cache_manager

    def is_stale(self, profile_data: dict, max_age_hours: int = 24) -> bool:
        """
        Check if a profile's scraped_at is older than max_age_hours.
        Returns True if the profile should be re-scraped.
        """
        scraped_at_str = profile_data.get("scraped_at")
        if not scraped_at_str:
            return True
        try:
            scraped_at = datetime.fromisoformat(scraped_at_str.replace("Z", "+00:00"))
            age = datetime.now(timezone.utc) - scraped_at
            return age > timedelta(hours=max_age_hours)
        except (ValueError, TypeError):
            return True

    def sync_profile(self, handle: str, live_data: dict) -> bool:
        """
        Merge live_data into the archived profile for `handle`.
        Returns True if any fields were actually updated.
        """
        archived_data = self.cache.load_profile(handle, archived=True)
        if not archived_data:
            log.warning("Cannot sync: %s is not archived.", handle)
            return False

        updated = False
        
        # Fields to compare directly
        direct_fields = [
            "moniker", "enlisted", "location", "bio", "fluency"
        ]
        
        for field in direct_fields:
            live_val = live_data.get(field)
            arch_val = archived_data.get(field)
            if live_val != arch_val:
                archived_data[field] = live_val
                updated = True
                
        # Compare avatar URL (if URL changed, we'll need to re-download later, 
        # but for now we just update the JSON).
        if live_data.get("avatar_url") != archived_data.get("avatar_url"):
            archived_data["avatar_url"] = live_data.get("avatar_url")
            # Clear local path so the controller knows to re-download
            archived_data["avatar_local"] = ""
            updated = True

        # For Badges and Orgs, simple replacement is often easiest if the list length or contents differ.
        # Deep diffing lists of dicts is complex; doing a naive replace if not exactly equal.
        # But we must preserve the 'image_local' / 'logo_local' paths if the URL didn't change!
        
        updated |= self._sync_badges(archived_data, live_data)
        updated |= self._sync_orgs(archived_data, live_data)

        # Always update synced_at
        archived_data["synced_at"] = datetime.now(timezone.utc).isoformat()

        if updated:
            log.info("Profile %s synced successfully (changes found).", handle)
            self.cache.save_archived_profile(archived_data)
            EventBus.instance().archive_updated.emit()
            return True
        else:
            log.info("Profile %s synced (no changes).", handle)
            self.cache.save_archived_profile(archived_data)  # Just to update synced_at
            EventBus.instance().archive_updated.emit()
            return False

    def _sync_badges(self, arch_data: dict, live_data: dict) -> bool:
        """Merge badges, preserving local image paths if URLs match."""
        arch_badges = {b["name"]: b for b in arch_data.get("badges", [])}
        live_badges = live_data.get("badges", [])
        
        updated = False
        new_badges = []
        
        for lb in live_badges:
            name = lb["name"]
            if name in arch_badges:
                ab = arch_badges[name]
                if lb["image_url"] == ab["image_url"]:
                    lb["image_local"] = ab.get("image_local", "")
                else:
                    updated = True
            else:
                updated = True
            new_badges.append(lb)
            
        if len(new_badges) != len(arch_badges):
            updated = True
            
        if updated:
            arch_data["badges"] = new_badges
            
        return updated

    def _sync_orgs(self, arch_data: dict, live_data: dict) -> bool:
        """Merge orgs, preserving local logo paths if URLs match."""
        arch_orgs = {o["sid"]: o for o in arch_data.get("orgs", [])}
        live_orgs = live_data.get("orgs", [])
        
        updated = False
        new_orgs = []
        
        for lo in live_orgs:
            sid = lo["sid"]
            if sid in arch_orgs:
                ao = arch_orgs[sid]
                # Preserve local logo if URL hasn't changed
                if lo["logo_url"] == ao["logo_url"]:
                    lo["logo_local"] = ao.get("logo_local", "")
                else:
                    updated = True
                    
                # Did rank or main status change?
                if lo["rank"] != ao.get("rank") or lo["is_main"] != ao.get("is_main"):
                    updated = True
            else:
                updated = True
            new_orgs.append(lo)
            
        if len(new_orgs) != len(arch_orgs):
            updated = True
            
        if updated:
            arch_data["orgs"] = new_orgs
            
        return updated
