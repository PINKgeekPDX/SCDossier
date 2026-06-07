"""
src/services/reputation_service.py
ReputationService — plain Python singleton wrapping the supabase-py client.

Follows the CacheManager singleton pattern (no QObject inheritance).
All network I/O happens inside QThread workers that call these methods.
This class is never called from the main thread directly.

Usage:
    # Initialization (main.py, once, after QApplication is created)
    ReputationService.initialize(url, anon_key)

    # Usage from workers
    svc = ReputationService.instance()
    data = svc.fetch_reputation("PINKgeekPDX")
"""

import hashlib
import logging
from typing import Any

try:
    from supabase import create_client, Client as SupabaseClient
    _SUPABASE_AVAILABLE = True
except ImportError:
    create_client = None  # type: ignore[assignment]
    SupabaseClient = None  # type: ignore[assignment]
    _SUPABASE_AVAILABLE = False

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Typed error for reputation service failures
# ---------------------------------------------------------------------------

class ReputationServiceError(Exception):
    """Raised when a ReputationService operation fails unrecoverably."""


# ---------------------------------------------------------------------------
# ReputationService — module-level singleton, plain Python class
# ---------------------------------------------------------------------------

class ReputationService:
    """
    Singleton that owns the supabase-py client and exposes synchronous
    methods called from QThread workers.

    Not a QObject — signals flow through the worker, not the service.
    """

    _instance: "ReputationService | None" = None
    _initialized: bool = False

    def __init__(self, url: str, anon_key: str) -> None:
        if not _SUPABASE_AVAILABLE or create_client is None:
            raise ReputationServiceError(
                "supabase-py is not installed. Run: pip install supabase>=2.4.0"
            )
        self._client = create_client(url, anon_key)
        self._known_handles: set[str] = set()
        self._local_player_handle: str = ""
        log.info("ReputationService initialized with Supabase URL: %s", url[:40])

    @property
    def local_player_handle(self) -> str:
        """Return the detected local player handle."""
        return self._local_player_handle

    @local_player_handle.setter
    def local_player_handle(self, val: str) -> None:
        """Set the local player handle."""
        self._local_player_handle = val

    def detect_local_player_handle(self) -> str:
        """
        Locate the Star Citizen installation and check the game.log.
        Extract the local player handle using regex matching.
        """
        import os
        import re

        default_path = r"C:\Program Files\Roberts Space Industries\StarCitizen"
        channels = ["LIVE", "PTU"]
        
        for channel in channels:
            log_path = os.path.join(default_path, channel, "Game.log")
            if os.path.exists(log_path):
                log.info("detect_local_player_handle: Found game log at %s", log_path)
                try:
                    # Read the log file
                    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    # Pattern 1: AccountLoginCharacterStatus_Character Character: ... - name NAME - state STATE_CURRENT
                    match = re.search(r"Character:.*?-\s*name\s+(\w+)\s+-\s*state\s+STATE_CURRENT", content)
                    if match:
                        handle = match.group(1)
                        self._local_player_handle = handle
                        log.info("detect_local_player_handle: Detected handle from Character Status: %s", handle)
                        return handle

                    # Pattern 2: Legacy login response user success: User Login Success - Handle[NAME]
                    match = re.search(r"User Login Success\s+-\s+Handle\[(\w+)\]", content)
                    if match:
                        handle = match.group(1)
                        self._local_player_handle = handle
                        log.info("detect_local_player_handle: Detected handle from Legacy Login: %s", handle)
                        return handle

                    # Pattern 3: Expect Incoming Connection ... nickname="NAME"
                    match = re.search(r"Expect Incoming Connection>.*?nickname=\"(\w+)\"", content)
                    if match:
                        handle = match.group(1)
                        self._local_player_handle = handle
                        log.info("detect_local_player_handle: Detected handle from Incoming Connection: %s", handle)
                        return handle

                except Exception as e:
                    log.warning("detect_local_player_handle: Failed to read %s: %s", log_path, e)
        
        log.warning("detect_local_player_handle: Could not detect username from Star Citizen log.")
        return ""

    # ------------------------------------------------------------------
    # Singleton lifecycle
    # ------------------------------------------------------------------

    @classmethod
    def initialize(cls, url: str, anon_key: str) -> "ReputationService":
        """
        Create and return the singleton ReputationService.
        Raises ReputationServiceError if url or anon_key are empty.
        """
        if not url or not anon_key:
            raise ReputationServiceError(
                "Cannot initialize ReputationService: url and anon_key must not be empty"
            )
        if cls._instance is None:
            cls._instance = cls(url, anon_key)
            cls._initialized = True
        return cls._instance

    @classmethod
    def instance(cls) -> "ReputationService":
        """Return the singleton. Raises RuntimeError if not initialized."""
        if cls._instance is None:
            raise RuntimeError(
                "ReputationService not initialized. Call ReputationService.initialize() first."
            )
        return cls._instance

    @classmethod
    def is_initialized(cls) -> bool:
        """Return True if the singleton has been created."""
        return cls._initialized and cls._instance is not None

    # ------------------------------------------------------------------
    # Public API (called from QThread workers)
    # ------------------------------------------------------------------

    def fetch_reputation(self, handle: str) -> dict | None:
        """
        Fetch all reputation_scores rows for a player.

        Returns a dict of the shape:
            {
                "dangerous":   {"score": int, "report_count": int},
                "trustworthy": {"score": int, "report_count": int},
                "pirate":      {"score": int, "report_count": int},
                "shady":       {"score": int, "report_count": int},
                "elusive":     {"score": int, "report_count": int},
            }
        Returns None if the player has no reputation data in the DB.
        Returns None on any network/DB error (does not raise).
        """
        try:
            handle_lower = handle.strip().lower()

            # Look up the player row first
            player_resp = (
                self._client
                .from_("players")
                .select("id")
                .eq("handle", handle_lower)
                .maybe_single()
                .execute()
            )

            if not player_resp.data:
                log.debug("No reputation data for handle: %s", handle)
                return None

            player_id = player_resp.data["id"]

            # Fetch all category scores
            scores_resp = (
                self._client
                .from_("reputation_scores")
                .select("category, score, report_count")
                .eq("player_id", player_id)
                .execute()
            )

            rows = scores_resp.data or []
            if not rows:
                return None

            # Build the result dict
            result: dict[str, Any] = {}
            for row in rows:
                cat = row.get("category")
                if cat:
                    result[cat] = {
                        "score": int(row.get("score", 0)),
                        "report_count": int(row.get("report_count", 0)),
                    }

            return result if result else None

        except Exception as e:
            log.warning("fetch_reputation(%s) failed: %s", handle, e)
            return None

    def submit_report(self, handle: str, tags: list[str], ip_hash: str) -> dict:
        """
        Submit an interaction report via the submit-report Edge Function.

        Returns the updated 5-category score dict on success.
        Raises ReputationServiceError on failure.
        """
        from src.app.constants import REP_APP_TOKEN
        import json

        try:
            response = self._client.functions.invoke(
                "submit-report",
                invoke_options={
                    "headers": {"X-SCD-App-Token": REP_APP_TOKEN},
                    "body": {
                        "handle": handle.strip().lower(),
                        "tags": tags,
                        "ip_hash": ip_hash,
                    },
                },
            )
            
            if isinstance(response, bytes):
                try:
                    response = json.loads(response.decode("utf-8"))
                except json.JSONDecodeError:
                    raise ReputationServiceError("Failed to parse JSON from edge function")

            if isinstance(response, dict) and "error" in response:
                raise ReputationServiceError(str(response["error"]))
            if not response:
                raise ReputationServiceError("Empty response from submit-report function")
            return response

        except ReputationServiceError:
            raise
        except Exception as e:
            log.error("submit_report(%s) failed: %s", handle, e)
            raise ReputationServiceError(str(e)) from e

    def check_rate_limit(self, handle: str, ip_hash: str) -> dict:
        """
        Check rate limit status for a given IP + player via the check-rate-limit Edge Function.

        Returns a dict:
            {
                "allowed": bool,
                "reports_used": int,
                "reports_remaining": int,
                "window_start": str | None,
                "cooldown_seconds": int,
                "monthly_limit": int,
                "monthly_remaining": int,
            }
        Returns None on failure.
        """
        from src.app.constants import REP_APP_TOKEN
        import json

        try:
            response = self._client.functions.invoke(
                "check-rate-limit",
                invoke_options={
                    "headers": {"X-SCD-App-Token": REP_APP_TOKEN},
                    "body": {
                        "handle": handle.strip().lower(),
                        "ip_hash": ip_hash,
                    },
                },
            )

            if isinstance(response, bytes):
                try:
                    response = json.loads(response.decode("utf-8"))
                except json.JSONDecodeError:
                    log.warning("check_rate_limit: failed to parse JSON response")
                    return None

            if isinstance(response, dict) and "error" in response:
                log.warning("check_rate_limit error: %s", response["error"])
                return None

            return response if isinstance(response, dict) else None

        except Exception as e:
            log.warning("check_rate_limit(%s) failed: %s", handle, e)
            return None

    def fetch_known_handles(self) -> list[str]:
        """
        Fetch all player handles that have reputation data.
        Used for startup pre-fetch / autocomplete.
        Raises RuntimeError on failure so callers can distinguish errors from empty DB.
        """
        try:
            resp = (
                self._client
                .from_("players")
                .select("handle")
                .execute()
            )
            handles = [row["handle"] for row in (resp.data or []) if row.get("handle")]
            self._known_handles = set(handles)
            log.debug("Fetched %d known reputation handles", len(handles))
            return handles

        except Exception as e:
            log.warning("fetch_known_handles() failed: %s", e)
            raise RuntimeError(f"Failed to fetch known handles: {e}") from e

    def ping(self) -> bool:
        """
        Ping the keep-alive Edge Function. Returns True on success.
        Used at startup to wake the Supabase free-tier project.
        """
        import json
        try:
            response = self._client.functions.invoke("keep-alive")
            if isinstance(response, bytes):
                try:
                    response = json.loads(response.decode("utf-8"))
                except json.JSONDecodeError:
                    pass
            # The keep-alive function returns {"status": "alive"} on success
            return isinstance(response, dict) and response.get("status") == "alive"
        except Exception as e:
            log.warning("ReputationService.ping() failed: %s", e)
            return False

    @staticmethod
    def _get_ip_hash() -> str | None:
        """
        Fetch the client's public IP from api.ipify.org and return its
        SHA-256 hash as a hex string. The raw IP is never stored or logged.

        Returns None on failure (no internet, service unavailable, etc.).
        """
        try:
            import urllib.request
            import json as _json

            with urllib.request.urlopen(
                "https://api.ipify.org?format=json", timeout=5
            ) as resp:
                data = _json.loads(resp.read().decode())
                raw_ip = data.get("ip", "")

            if not raw_ip:
                log.warning("_get_ip_hash: api.ipify.org returned empty IP")
                return None

            # Immediately hash — raw IP is discarded
            ip_hash = hashlib.sha256(raw_ip.encode()).hexdigest()
            return ip_hash

        except Exception as e:
            log.warning("_get_ip_hash() failed: %s", e)
            return None

    @staticmethod
    def _normalize_score(score: int, report_count: int, category: str) -> int:
        """
        Normalize score on a 0-100 scale.
        Score % is computed such that achieving 100% requires the equivalent of 50 max score reports.
        """
        if report_count <= 0 or score <= 0:
            return 0
            
        from src.app.constants import REPUTATION_TAGS
        max_score_per_report = sum(t["points"] for t in REPUTATION_TAGS.values() if t["category"] == category)
        if max_score_per_report == 0:
            return 0
            
        max_possible_points = max_score_per_report * 50
        denominator = max(report_count * max_score_per_report, max_possible_points)
        
        pct = int((score / denominator) * 100)
        return min(100, max(0, pct))
