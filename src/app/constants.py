"""
src/app/constants.py
App-wide enums, string constants, RSI URL patterns, and path keys.
No PyQt6 imports — pure Python only.
"""

from enum import Enum, auto


# ---------------------------------------------------------------------------
# Application Metadata
# ---------------------------------------------------------------------------
APP_NAME = "SC Dossier"
APP_VERSION = "b0.4.2"
APP_AUTHOR = "PINK"
APP_VENDOR = "PINK"
ORG_FOLDER = "PINK"

# ---------------------------------------------------------------------------
# RSI URL Templates
# ---------------------------------------------------------------------------
RSI_BASE = "https://robertsspaceindustries.com"
RSI_CITIZEN_URL = RSI_BASE + "/en/citizens/{handle}"
RSI_CITIZEN_ORGS_URL = RSI_BASE + "/en/citizens/{handle}/organizations"
RSI_ORG_URL = RSI_BASE + "/en/orgs/{sid}"
RSI_ORG_LISTING_URL = RSI_BASE + "/en/community/orgs/listing"

# Default User-Agent for scraper requests
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# ---------------------------------------------------------------------------
# Tab Identifiers
# ---------------------------------------------------------------------------
class TabId(str, Enum):
    SEARCH = "search"
    DOSSIER = "dossier"
    ORGANIZATION = "organization"
    ARCHIVE = "archive"
    SETTINGS = "settings"


# ---------------------------------------------------------------------------
# Screen Edge Identifiers
# ---------------------------------------------------------------------------
class ScreenEdge(str, Enum):
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"


# ---------------------------------------------------------------------------
# OCR Engine Options
# ---------------------------------------------------------------------------
class OCREngine(str, Enum):
    RAPIDOCR = "rapidocr"


# ---------------------------------------------------------------------------
# Sort Options for Archive List
# ---------------------------------------------------------------------------
class ArchiveSortOrder(str, Enum):
    NAME_ASC = "name_asc"
    NAME_DESC = "name_desc"
    DATE_ARCHIVED = "date_archived"
    DATE_SYNCED = "date_synced"


# ---------------------------------------------------------------------------
# Status Levels for EventBus status_message signal
# ---------------------------------------------------------------------------
class StatusLevel(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Cache / Filesystem Constants
# ---------------------------------------------------------------------------
PROFILE_JSON_FILENAME = "profile.json"
AVATAR_FILENAME = "avatar.png"
OCR_CAPTURES_SUBDIR = "_captures"

# ---------------------------------------------------------------------------
# UI Layout Constants  — tightened for compact, dense layout
# ---------------------------------------------------------------------------
MAIN_WINDOW_MIN_WIDTH = 860
MAIN_WINDOW_MIN_HEIGHT = 560
MAIN_WINDOW_DEFAULT_WIDTH = 1024
MAIN_WINDOW_DEFAULT_HEIGHT = 680

SIDEBAR_WIDTH_COLLAPSED = 52      # was 64 — narrower icon rail
SIDEBAR_WIDTH_EXPANDED = 220      # was 240
TITLEBAR_HEIGHT = 36              # was 48 — slimmer chrome
STATUSBAR_HEIGHT = 20             # was 28 — ultra-thin strip
TOOLBAR_BUTTON_SIZE = 36          # was 44

# ---------------------------------------------------------------------------
# Scraper Defaults
# ---------------------------------------------------------------------------
DEFAULT_SCRAPER_DELAY_MS = 500
DEFAULT_SYNC_INTERVAL_HOURS = 24
DEFAULT_TEMP_CACHE_MAX_AGE_DAYS = 7
DEFAULT_OCR_CONFIDENCE_THRESHOLD = 0.5


# ---------------------------------------------------------------------------
# Supabase Configuration for Reputation System
# ---------------------------------------------------------------------------
# REP_SUPABASE_URL and REP_ANON_KEY must be populated after deploying the  
# SCDossierRepServer project. These are safe to embed in the client. 
# Alternatively, users can override them via settings file keys:
# reputation_supabase_url and reputation_anon_key. REP_APP_TOKEN is sent as 
# X-SCD-App-Token header on write requests; matches the APP_TOKEN Supabase 
# Edge Function secret.
# ---------------------------------------------------------------------------
REP_SUPABASE_URL = "https://epqkqmnxixybtwkczxfs.supabase.co"
REP_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVwcWtxbW54aXh5YnR3a2N6eGZzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk5MzM4OTMsImV4cCI6MjA5NTUwOTg5M30.PQFw8e3T6O-1ZXdZiJo64TcilYAngDzN_mRxdMHfjDg"
REP_APP_TOKEN = "6UILwmiuzMeXtpXRnoX2Yg"


# ---------------------------------------------------------------------------
# Reputation System — Rate Limiting
# ---------------------------------------------------------------------------
REPUTATION_MAX_TAGS = 5
REPUTATION_RATE_LIMIT_PER_MONTH = 2


# ---------------------------------------------------------------------------
# Reputation System — Tag Definitions
# All 15 static tags. Users select up to REPUTATION_MAX_TAGS per report.
# Shape: tag_id -> {"label": str, "category": str, "points": int}
# ---------------------------------------------------------------------------
REPUTATION_TAGS: dict = {
    # --- Dangerous ---
    "killed_me":        {"label": "They Killed Me",          "category": "dangerous",   "points": 1},
    "killed_us":        {"label": "They Killed Us All",       "category": "dangerous",   "points": 2},
    "ambushed":         {"label": "Set an Ambush / Trap",     "category": "dangerous",   "points": 1},
    "griefer":          {"label": "Griefed / Harassed Me",    "category": "dangerous",   "points": 1},
    # --- Shady ---
    "scammed":          {"label": "Scammed Me",               "category": "shady",       "points": 2},
    "lied":             {"label": "Lied / Deceived Me",       "category": "shady",       "points": 1},
    "manipulated":      {"label": "Manipulated / Lured Me",   "category": "shady",       "points": 1},
    # --- Pirate ---
    "pirate_act":       {"label": "Acted Like a Pirate",      "category": "pirate",      "points": 1},
    "pirate_confirmed": {"label": "Confirmed Pirate",          "category": "pirate",      "points": 2},
    # --- Elusive ---
    "elusive":          {"label": "Hard to Track / Elusive",  "category": "elusive",     "points": 1},
    "escaped":          {"label": "Escaped Every Time",        "category": "elusive",     "points": 1},
    # --- Trustworthy ---
    "trustworthy":      {"label": "Trustworthy / Reliable",   "category": "trustworthy", "points": 2},
    "helpful":          {"label": "Helped Me Out",             "category": "trustworthy", "points": 1},
    "fair_fight":       {"label": "Honorable Fighter",         "category": "trustworthy", "points": 1},
    "friendly":         {"label": "Friendly Encounter",        "category": "trustworthy", "points": 1},
}


# ---------------------------------------------------------------------------
# Reputation System — Category Definitions
# Each category has a display label, hex accent color, and score thresholds.
# Thresholds: list of (min_pct_inclusive, verdict_label) in ascending order.
# Score % is computed as: min(100, int(score / max(report_count * max_pts, max_pts * 50) * 100))
# Shape: category_id -> {"label": str, "color_hex": str, "thresholds": list}
# ---------------------------------------------------------------------------
REPUTATION_CATEGORIES: dict = {
    "dangerous": {
        "label": "⚔ DANGEROUS",
        "color_hex": "#FF3B3B",
        "thresholds": [
            (0,  "No Threat Reports"),
            (1,  "Minor Threat"),
            (41, "Moderately Dangerous"),
            (61, "Highly Dangerous"),
            (81, "⚠ EXTREMELY DANGEROUS"),
        ],
    },
    "trustworthy": {
        "label": "✓ TRUSTWORTHY",
        "color_hex": "#00AA66",
        "thresholds": [
            (0,  "No Trust Data"),
            (1,  "Somewhat Reliable"),
            (41, "Generally Trustworthy"),
            (61, "Highly Trusted"),
            (81, "✓ COMMUNITY TRUSTED"),
        ],
    },
    "pirate": {
        "label": "☠ PIRACY",
        "color_hex": "#FF8800",
        "thresholds": [
            (0,  "No Piracy Reports"),
            (1,  "Possibly a Pirate?"),
            (41, "Suspected Pirate — Be Careful"),
            (61, "Known Pirate — High Risk"),
            (81, "☠ NOTORIOUS PIRATE"),
        ],
    },
    "shady": {
        "label": "🎭 SHADY",
        "color_hex": "#CC44FF",
        "thresholds": [
            (0,  "No Shady Reports"),
            (1,  "Slightly Suspicious"),
            (41, "Shady as a Snake"),
            (61, "Highly Untrustworthy"),
            (81, "🚨 KNOWN SCAMMER / GRIEFER"),
        ],
    },
    "elusive": {
        "label": "👻 ELUSIVE",
        "color_hex": "#4488FF",
        "thresholds": [
            (0,  "Easy to Find"),
            (1,  "Somewhat Elusive"),
            (41, "Hard to Pin Down"),
            (61, "Ghost — Very Elusive"),
            (81, "👻 PHANTOM — IMPOSSIBLE TO CATCH"),
        ],
    },
}
