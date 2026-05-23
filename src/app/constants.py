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
APP_VERSION = "0.1.0"
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
# UI Layout Constants
# ---------------------------------------------------------------------------
MAIN_WINDOW_MIN_WIDTH = 900
MAIN_WINDOW_MIN_HEIGHT = 600
MAIN_WINDOW_DEFAULT_WIDTH = 1100
MAIN_WINDOW_DEFAULT_HEIGHT = 700

SIDEBAR_WIDTH_COLLAPSED = 64
SIDEBAR_WIDTH_EXPANDED = 240
TITLEBAR_HEIGHT = 48
STATUSBAR_HEIGHT = 28
TOOLBAR_BUTTON_SIZE = 44

# ---------------------------------------------------------------------------
# Scraper Defaults
# ---------------------------------------------------------------------------
DEFAULT_SCRAPER_DELAY_MS = 500
DEFAULT_SYNC_INTERVAL_HOURS = 24
DEFAULT_TEMP_CACHE_MAX_AGE_DAYS = 7
DEFAULT_OCR_CONFIDENCE_THRESHOLD = 0.5
