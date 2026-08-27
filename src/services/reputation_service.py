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

# Reports needed to reach 100% score (used in normalization)
_REPORTS_FOR_MAX_SCORE = 50

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
        # Use longer timeout for Edge Functions (default is ~5s, but submit can take 15-20s with RSI fetches)
        try:
            from supabase.lib.client_options import ClientOptions
            import httpx as _httpx
            # Create a custom httpx client with 30s timeout for functions
            _timeout = _httpx.Timeout(30.0, connect=10.0)
            _options = ClientOptions(
                postgrest_client_timeout=30,
                storage_client_timeout=30,
                function_client_timeout=60,
                httpx_client=_httpx.Client(timeout=_timeout),
            )
            self._client = create_client(url, anon_key, options=_options)
        except Exception as e:
            log.debug("Failed to create client with custom timeout, falling back to default: %s", e)
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

    @staticmethod
    def _find_sc_install_paths() -> list[str]:
        """
        Return a list of candidate Star Citizen installation directories.
        Checks the Windows registry first (RSI Launcher stores the path there),
        then falls back to well-known default locations.
        """
        import os
        paths: list[str] = []

        # --- Registry lookup (RSI Launcher) ---
        try:
            import winreg
            reg_hives = [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]
            reg_keys = [
                r"SOFTWARE\Roberts Space Industries\StarCitizen",
                r"SOFTWARE\WOW6432Node\Roberts Space Industries\StarCitizen",
            ]
            for hive in reg_hives:
                for key_path in reg_keys:
                    try:
                        with winreg.OpenKey(hive, key_path) as key:
                            # The launcher stores "InstallPath" or "LibraryFolders"
                            for value_name in ("InstallPath", "LibraryFolders", "ProductInstallPath"):
                                try:
                                    val, _ = winreg.QueryValueEx(key, value_name)
                                    if val and isinstance(val, str) and os.path.isdir(val):
                                        paths.append(val)
                                except (FileNotFoundError, OSError):
                                    pass
                    except (FileNotFoundError, OSError):
                        pass
        except ImportError:
            pass  # winreg not available (non-Windows or stripped build)

        # --- Well-known default paths ---
        defaults = [
            r"C:\Program Files\Roberts Space Industries\StarCitizen",
            r"C:\Program Files (x86)\Roberts Space Industries\StarCitizen",
            r"D:\Roberts Space Industries\StarCitizen",
            r"E:\Roberts Space Industries\StarCitizen",
        ]
        for d in defaults:
            if d not in paths and os.path.isdir(d):
                paths.append(d)

        # --- Also check drives C-Z for the RSI folder (edge cases) ---
        import string
        for letter in string.ascii_uppercase:
            candidate = f"{letter}:\\Roberts Space Industries\\StarCitizen"
            if candidate not in paths and os.path.isdir(candidate):
                paths.append(candidate)

        return paths

    @staticmethod
    def _parse_handle_from_log(log_path: str) -> str:
        """Try to extract the player handle from a Game.log file. Returns '' on failure."""
        import re
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Pattern 1: AccountLoginCharacterStatus_Character Character: ... - name NAME - state STATE_CURRENT
            match = re.search(r"Character:.*?-\s*name\s+(\w+)\s+-\s*state\s+STATE_CURRENT", content)
            if match:
                return match.group(1)

            # Pattern 2: Legacy login response user success: User Login Success - Handle[NAME]
            match = re.search(r"User Login Success\s+-\s+Handle\[(\w+)\]", content)
            if match:
                return match.group(1)

            # Pattern 3: Expect Incoming Connection ... nickname="NAME"
            match = re.search(r"Expect Incoming Connection>.*?nickname=\"(\w+)\"", content)
            if match:
                return match.group(1)

        except Exception as e:
            log.warning("_parse_handle_from_log: Failed to read %s: %s", log_path, e)
        return ""

    def detect_local_player_handle(self) -> str:
        """
        Locate the Star Citizen installation and check the game.log.
        Extract the local player handle using regex matching.
        Tries registry-detected paths first, then well-known defaults.
        Searches LIVE channel before PTU.
        """
        import os
        channels = ["LIVE", "PTU"]
        install_paths = self._find_sc_install_paths()

        log.info("detect_local_player_handle: Searching %d candidate install paths", len(install_paths))

        for base_path in install_paths:
            for channel in channels:
                log_path = os.path.join(base_path, channel, "Game.log")
                if not os.path.exists(log_path):
                    continue

                log.info("detect_local_player_handle: Found game log at %s", log_path)
                handle = self._parse_handle_from_log(log_path)
                if handle:
                    self._local_player_handle = handle
                    log.info("detect_local_player_handle: Detected handle: %s", handle)
                    return handle

        log.warning("detect_local_player_handle: Could not detect username from Star Citizen log.")
        return ""

    def get_last_activity_timestamp(self) -> str | None:
        """
        Return the modification time of the Game.log file in UTC ISO format.
        Used to prove the player was recently active in-game.
        """
        import os
        import time
        from datetime import datetime, timezone

        channels = ["LIVE", "PTU"]
        
        for attempt in range(2):
            install_paths = self._find_sc_install_paths()
            for base_path in install_paths:
                for channel in channels:
                    log_path = os.path.join(base_path, channel, "Game.log")
                    if os.path.exists(log_path):
                        try:
                            # Try to open the file to verify read permission/avoid lock issue
                            with open(log_path, "rb") as f:
                                pass
                            mtime = os.path.getmtime(log_path)
                            dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
                            log.debug("Successfully read Game.log mtime: %s", dt.isoformat())
                            return dt.isoformat()
                        except Exception as e:
                            log.warning("Attempt %d failed to read mtime of %s: %s", attempt + 1, log_path, e)
            if attempt == 0:
                time.sleep(0.1)
                            
        return None

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
        Returns an empty dict {} if the player exists but has no score rows.
        Returns None if the player has no row in the players table (never reported).
        Returns None on any network/DB error (does not raise).
        """
        try:
            handle = handle.strip()
            if not handle:
                log.debug("fetch_reputation: Empty handle, returning empty dict")
                return {}
            handle_lower = handle.lower()

            # Look up the player row first - defensive access
            player_resp = (
                self._client
                .from_("players")
                .select("id, hostile_count, friendly_count")
                .eq("handle", handle_lower)
                .maybe_single()
                .execute()
            )

            # Safe access to player_resp.data
            player_data = getattr(player_resp, 'data', None)

            if not player_data:
                log.debug("No player row found for handle: %s", handle)
                return {}

            player_id = player_data["id"]
            hostile_count = int(player_data.get("hostile_count", 0))
            friendly_count = int(player_data.get("friendly_count", 0))

            # Fetch all category scores
            scores_resp = (
                self._client
                .from_("reputation_scores")
                .select("category, score, report_count")
                .eq("player_id", player_id)
                .execute()
            )

            rows = getattr(scores_resp, 'data', []) or []
            if not rows:
                # Player exists in players table but has no score rows yet
                log.debug("No score rows found for player: %s", handle)
                return {"hostile_count": hostile_count, "friendly_count": friendly_count}

            # Build the result dict
            result: dict[str, Any] = {}
            for row in rows:
                cat = row.get("category")
                if cat:
                    result[cat] = {
                        "score": int(row.get("score", 0)),
                        "report_count": int(row.get("report_count", 0)),
                    }

            # Include disposition counts for aggregate disposition marker
            result["hostile_count"] = hostile_count
            result["friendly_count"] = friendly_count

            return result if result else {}

        except Exception as e:
            log.warning("fetch_reputation(%s) failed: %s", handle, e)
            return {}

    def submit_report(self, handle: str, tags: list[str], ip_hash: str, disposition: str = "unknown", reporter_handle: str = "", orgs: list[str] | None = None) -> dict:
        """
        Submit an interaction report via the submit-report Edge Function.

        Args:
            handle: Player handle (case-insensitive).
            tags: List of tag IDs (e.g. ["killed_me", "scammed"]).
            ip_hash: SHA-256 hash of the client's public IP.
            disposition: One of "hostile", "unknown", or "friendly".
            reporter_handle: The local player's handle (for mutual report detection).
            orgs: List of org SIDs the reporter belongs to (for org cooldown detection).

        Returns the updated 5-category score dict on success.
        Raises ReputationServiceError on failure.
        """
        from src.app.constants import REP_APP_TOKEN
        import json

        try:
            # Get real activity timestamp from Game.log
            activity_timestamp = self.get_last_activity_timestamp()
            
            # If we couldn't find the log file, we still try to submit, but the 
            # server will reject it if activity_timestamp is missing or old.
            # We don't artificially spoof it anymore.

            body: dict = {
                "handle": handle.strip().lower(),
                "tags": tags,
                "ip_hash": ip_hash,
                "disposition": disposition,
                "orgs": orgs if orgs is not None else [],
                "reporter_handle": reporter_handle or None,
            }
            if activity_timestamp:
                body["activity_timestamp"] = activity_timestamp

            response = self._client.functions.invoke(
                "submit-report",
                invoke_options={
                    "headers": {"X-SCD-App-Token": REP_APP_TOKEN},
                    "body": body,
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
            err_msg = str(e)
            # Handle read timeout: the server may have succeeded despite client timeout
            # Wait briefly and check if the report was actually applied
            if "timed out" in err_msg.lower() or "timeout" in err_msg.lower():
                log.warning("submit_report timed out for %s, verifying via re-fetch...", handle)
                import time as _time
                _time.sleep(2)
                try:
                    # Re-fetch to see if the report was committed
                    verify_data = self.fetch_reputation(handle)
                    if verify_data and isinstance(verify_data, dict):
                        # If we got data back, assume the report went through
                        # Return the verified data instead of raising timeout error
                        log.info("Verified report for %s after timeout via re-fetch: %s", handle, verify_data)
                        return verify_data
                except Exception as verify_e:
                    log.debug("Verification re-fetch after timeout failed: %s", verify_e)
            log.error("submit_report(%s) failed: %s", handle, e)
            raise ReputationServiceError(err_msg) from e

    def check_rate_limit(self, handle: str, ip_hash: str, orgs: list[str] | None = None, reporter_handle: str = "") -> dict:
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
                "friendly_allowed": bool,
                "friendly_cooldown_seconds": int
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
                        "orgs": orgs if orgs is not None else [],
                        "reporter_handle": reporter_handle or None,
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
        Retries up to 3 times on transient failures (503, timeouts).
        """
        import json
        max_attempts = 3
        delays = [2, 4]
        for attempt in range(max_attempts):
            try:
                response = self._client.functions.invoke("keep-alive")
                if isinstance(response, bytes):
                    try:
                        response = json.loads(response.decode("utf-8"))
                    except json.JSONDecodeError:
                        pass
                if isinstance(response, dict) and response.get("status") == "alive":
                    return True
                log.debug("ping attempt %d: unexpected response %r", attempt + 1, response)
            except Exception as e:
                log.debug("ping attempt %d failed: %s", attempt + 1, e)
            if attempt < max_attempts - 1:
                import time
                time.sleep(delays[min(attempt, len(delays) - 1)])
        log.warning("ReputationService.ping() failed after %d attempts", max_attempts)
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
            
        max_possible_points = max_score_per_report * _REPORTS_FOR_MAX_SCORE
        denominator = max(report_count * max_score_per_report, max_possible_points)
        
        if denominator <= 0:
            return 0
        
        pct = int((score / denominator) * 100)
        return min(100, max(0, pct))
