"""
src/core/settings.py
SettingsManager — load/save/watch settings.json with typed access.

- Loads settings.json on startup; creates with defaults if absent.
- Exposes typed getters/setters for all settings keys.
- Auto-saves on every value change (debounced via a short QTimer).
- QTimer requires PyQt6 to be initialized — SettingsManager must be
  instantiated after QApplication is created.
"""

import json
import logging
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QObject, QTimer

from src.app.constants import (
    APP_VERSION,
    DEFAULT_OCR_CONFIDENCE_THRESHOLD,
    DEFAULT_SCRAPER_DELAY_MS,
    DEFAULT_SYNC_INTERVAL_HOURS,
    DEFAULT_TEMP_CACHE_MAX_AGE_DAYS,
    DEFAULT_USER_AGENT,
    MAIN_WINDOW_DEFAULT_HEIGHT,
    MAIN_WINDOW_DEFAULT_WIDTH,
    OCREngine,
    ScreenEdge,
    TabId,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default Settings Schema
# ---------------------------------------------------------------------------
DEFAULT_SETTINGS: dict[str, Any] = {
    "toolbar": {
        "x": 0,
        "y": 100,
        "edge": ScreenEdge.LEFT.value,
    },
    "window": {
        "x": 100,
        "y": 100,
        "w": MAIN_WINDOW_DEFAULT_WIDTH,
        "h": MAIN_WINDOW_DEFAULT_HEIGHT,
    },
    "last_tab": TabId.SEARCH.value,
    "pin_state": False,
    "pin_on_startup": False,
    "minimize_to_tray_on_close": True,
    "show_tray_notifications": True,
    "auto_hide_toolbar_without_game": True,
    "ocr_engine": OCREngine.RAPIDOCR.value,
    "ocr_confidence_threshold": DEFAULT_OCR_CONFIDENCE_THRESHOLD,
    "ocr_thread_count": 2,
    "ocr_hotkey": "",
    "scraper_delay_ms": DEFAULT_SCRAPER_DELAY_MS,
    "scraper_timeout_sec": 30,
    "scraper_proxy": "",
    "user_agent": DEFAULT_USER_AGENT,
    "sync_interval_hours": DEFAULT_SYNC_INTERVAL_HOURS,
    "sync_on_load": True,
    "temp_cache_auto_clear": False,
    "temp_cache_max_age_days": DEFAULT_TEMP_CACHE_MAX_AGE_DAYS,
    "image_download_concurrency": 3,
    "toolbar_opacity": 1.0,
    "theme_accent_override": None,
    "theme_palette_overrides": {},
    "auto_check_updates": True,
    "auto_download_updates": False,
    "font_size_scaling": 100,
    "app_font_family": "Default",
    # Archive & Export Preferences
    "export_destination": "",
    "remember_export_folder": True,
    "archive_default_sort": "date_desc",
    # Diagnostics & Logs
    "log_level": "normal",
    "include_debug_in_diagnostics": False,
    "search_history_limit": 5,
    "search_history": [],
    "search_history_player": [],
    "search_history_org": [],
    # Reputation System
    "reputation_enabled": False,
    "reputation_auto_check": True,
    "reputation_prefetch_archived": False,
    "reputation_supabase_url": "",  # power-user override; uses constants default when empty
    "reputation_anon_key": "",      # power-user override; uses constants default when empty
    "reputation_history": {},
    "toolbar_interact_hotkey": "left alt",
    "toolbar_drag_hotkey": "left ctrl",
    "toolbar_idle_opacity": 0.4,
    "_version": APP_VERSION,
}


class SettingsManager(QObject):
    """
    Manages application settings with auto-save on change.

    Must be instantiated after QApplication is created (uses QTimer).
    """

    _instance: "SettingsManager | None" = None

    def __init__(self, settings_path: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._path = settings_path
        self._data: dict[str, Any] = {}
        self._dirty = False

        # Debounce timer — saves 500ms after last change
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(500)
        self._save_timer.timeout.connect(self._flush)

        self._load()

    @classmethod
    def instance(cls) -> "SettingsManager":
        if cls._instance is None:
            raise RuntimeError("SettingsManager not yet initialized. Call SettingsManager.initialize() first.")
        return cls._instance

    @classmethod
    def initialize(cls, settings_path: Path) -> "SettingsManager":
        """Create and return the singleton SettingsManager."""
        if cls._instance is None:
            cls._instance = cls(settings_path)
        return cls._instance

    # ------------------------------------------------------------------
    # Load / Save
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load settings.json; create with defaults if absent or invalid."""
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                # Merge with defaults so new keys are always present
                self._data = self._merge_defaults(DEFAULT_SETTINGS, loaded)
                log.debug("Settings loaded from %s", self._path)
                return
            except (json.JSONDecodeError, OSError) as e:
                log.warning("Failed to load settings (%s); using defaults.", e)
        self._data = json.loads(json.dumps(DEFAULT_SETTINGS))  # deep copy
        self._save_immediate()
        log.info("Created default settings at %s", self._path)

    @staticmethod
    def _merge_defaults(defaults: dict, loaded: dict) -> dict:
        """Recursively merge loaded values over defaults so missing keys use defaults."""
        result = dict(defaults)
        for key, default_val in defaults.items():
            if key in loaded:
                if isinstance(default_val, dict) and isinstance(loaded[key], dict):
                    result[key] = SettingsManager._merge_defaults(default_val, loaded[key])
                else:
                    result[key] = loaded[key]
        return result

    def _flush(self) -> None:
        """Write settings to disk if dirty."""
        if not self._dirty:
            return
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            tmp.replace(self._path)
            self._dirty = False
            log.debug("Settings saved to %s", self._path)
        except OSError as e:
            log.error("Failed to save settings: %s", e)

    def _save_immediate(self) -> None:
        """Save immediately without debounce."""
        self._dirty = True
        self._flush()

    def _mark_dirty(self) -> None:
        """Schedule a debounced save."""
        self._dirty = True
        self._save_timer.start()

    # ------------------------------------------------------------------
    # Generic get/set
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Get a top-level settings value."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a top-level settings value and schedule auto-save."""
        self._data[key] = value
        self._mark_dirty()
        try:
            from src.core.events import EventBus
            EventBus.instance().settings_changed.emit(key, value)
        except Exception:
            pass

    def get_nested(self, *keys: str, default: Any = None) -> Any:
        """Get a nested settings value. E.g. get_nested('toolbar', 'x')"""
        node = self._data
        for k in keys:
            if not isinstance(node, dict):
                return default
            node = node.get(k, default)
        return node

    def set_nested(self, *keys: str, value: Any) -> None:
        """Set a nested settings value. E.g. set_nested('toolbar', 'x', value=50)"""
        node = self._data
        for k in keys[:-1]:
            if k not in node or not isinstance(node[k], dict):
                node[k] = {}
            node = node[k]
        node[keys[-1]] = value
        self._mark_dirty()
        try:
            from src.core.events import EventBus
            EventBus.instance().settings_changed.emit(keys[0], self._data[keys[0]])
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Typed Accessors
    # ------------------------------------------------------------------

    # Toolbar
    @property
    def toolbar_x(self) -> int:
        return int(self.get_nested("toolbar", "x", default=0))

    @toolbar_x.setter
    def toolbar_x(self, v: int) -> None:
        self.set_nested("toolbar", "x", value=v)

    @property
    def toolbar_y(self) -> int:
        return int(self.get_nested("toolbar", "y", default=100))

    @toolbar_y.setter
    def toolbar_y(self, v: int) -> None:
        self.set_nested("toolbar", "y", value=v)

    @property
    def toolbar_edge(self) -> str:
        return str(self.get_nested("toolbar", "edge", default=ScreenEdge.LEFT.value))

    @toolbar_edge.setter
    def toolbar_edge(self, v: str) -> None:
        self.set_nested("toolbar", "edge", value=v)

    # Window
    @property
    def window_x(self) -> int:
        return int(self.get_nested("window", "x", default=100))

    @window_x.setter
    def window_x(self, v: int) -> None:
        self.set_nested("window", "x", value=v)

    @property
    def window_y(self) -> int:
        return int(self.get_nested("window", "y", default=100))

    @window_y.setter
    def window_y(self, v: int) -> None:
        self.set_nested("window", "y", value=v)

    @property
    def window_w(self) -> int:
        return int(self.get_nested("window", "w", default=MAIN_WINDOW_DEFAULT_WIDTH))

    @window_w.setter
    def window_w(self, v: int) -> None:
        self.set_nested("window", "w", value=v)

    @property
    def window_h(self) -> int:
        return int(self.get_nested("window", "h", default=MAIN_WINDOW_DEFAULT_HEIGHT))

    @window_h.setter
    def window_h(self, v: int) -> None:
        self.set_nested("window", "h", value=v)

    # State
    @property
    def last_tab(self) -> str:
        return str(self.get("last_tab", TabId.SEARCH.value))

    @last_tab.setter
    def last_tab(self, v: str) -> None:
        self.set("last_tab", v)

    @property
    def pin_state(self) -> bool:
        return bool(self.get("pin_state", False))

    @pin_state.setter
    def pin_state(self, v: bool) -> None:
        self.set("pin_state", v)

    # OCR
    @property
    def ocr_engine(self) -> str:
        return str(self.get("ocr_engine", OCREngine.RAPIDOCR.value))

    @ocr_engine.setter
    def ocr_engine(self, v: str) -> None:
        self.set("ocr_engine", v)

    @property
    def ocr_confidence_threshold(self) -> float:
        return float(self.get("ocr_confidence_threshold", DEFAULT_OCR_CONFIDENCE_THRESHOLD))

    @ocr_confidence_threshold.setter
    def ocr_confidence_threshold(self, v: float) -> None:
        self.set("ocr_confidence_threshold", max(0.0, min(1.0, v)))

    @property
    def ocr_hotkey(self) -> str:
        return str(self.get("ocr_hotkey", ""))

    @ocr_hotkey.setter
    def ocr_hotkey(self, v: str) -> None:
        self.set("ocr_hotkey", v)

    # Scraper
    @property
    def scraper_delay_ms(self) -> int:
        return int(self.get("scraper_delay_ms", DEFAULT_SCRAPER_DELAY_MS))

    @scraper_delay_ms.setter
    def scraper_delay_ms(self, v: int) -> None:
        self.set("scraper_delay_ms", max(0, v))

    @property
    def user_agent(self) -> str:
        return str(self.get("user_agent", DEFAULT_USER_AGENT))

    @user_agent.setter
    def user_agent(self, v: str) -> None:
        self.set("user_agent", v)

    # Sync
    @property
    def sync_interval_hours(self) -> int:
        return int(self.get("sync_interval_hours", DEFAULT_SYNC_INTERVAL_HOURS))

    @sync_interval_hours.setter
    def sync_interval_hours(self, v: int) -> None:
        self.set("sync_interval_hours", max(1, v))

    @property
    def sync_on_load(self) -> bool:
        return bool(self.get("sync_on_load", True))

    @sync_on_load.setter
    def sync_on_load(self, v: bool) -> None:
        self.set("sync_on_load", v)

    # Cache
    @property
    def temp_cache_auto_clear(self) -> bool:
        return bool(self.get("temp_cache_auto_clear", False))

    @temp_cache_auto_clear.setter
    def temp_cache_auto_clear(self, v: bool) -> None:
        self.set("temp_cache_auto_clear", v)

    @property
    def temp_cache_max_age_days(self) -> int:
        return int(self.get("temp_cache_max_age_days", DEFAULT_TEMP_CACHE_MAX_AGE_DAYS))

    @temp_cache_max_age_days.setter
    def temp_cache_max_age_days(self, v: int) -> None:
        self.set("temp_cache_max_age_days", max(1, v))

    # Appearance
    @property
    def toolbar_opacity(self) -> float:
        return float(self.get("toolbar_opacity", 1.0))

    @toolbar_opacity.setter
    def toolbar_opacity(self, v: float) -> None:
        self.set("toolbar_opacity", max(0.3, min(1.0, v)))

    @property
    def theme_accent_override(self) -> str | None:
        val = self.get("theme_accent_override", None)
        return str(val) if val else None

    @theme_accent_override.setter
    def theme_accent_override(self, v: str | None) -> None:
        self.set("theme_accent_override", v)

    @property
    def theme_palette_overrides(self) -> dict[str, str]:
        val = self.get("theme_palette_overrides", {})
        return dict(val) if isinstance(val, dict) else {}

    @theme_palette_overrides.setter
    def theme_palette_overrides(self, v: dict[str, str]) -> None:
        self.set("theme_palette_overrides", v)

    @property
    def font_size_scaling(self) -> int:
        return int(self.get("font_size_scaling", 100))

    @font_size_scaling.setter
    def font_size_scaling(self, v: int) -> None:
        self.set("font_size_scaling", max(80, min(150, v)))

    @property
    def app_font_family(self) -> str:
        return self.get("app_font_family", "Default")

    @app_font_family.setter
    def app_font_family(self, v: str) -> None:
        self.set("app_font_family", v)

    # General / behaviour
    @property
    def minimize_to_tray_on_close(self) -> bool:
        return bool(self.get("minimize_to_tray_on_close", True))

    @minimize_to_tray_on_close.setter
    def minimize_to_tray_on_close(self, v: bool) -> None:
        self.set("minimize_to_tray_on_close", v)

    @property
    def pin_on_startup(self) -> bool:
        return bool(self.get("pin_on_startup", False))

    @pin_on_startup.setter
    def pin_on_startup(self, v: bool) -> None:
        self.set("pin_on_startup", v)

    @property
    def show_tray_notifications(self) -> bool:
        return bool(self.get("show_tray_notifications", True))

    @show_tray_notifications.setter
    def show_tray_notifications(self, v: bool) -> None:
        self.set("show_tray_notifications", v)

    @property
    def auto_hide_toolbar_without_game(self) -> bool:
        return bool(self.get("auto_hide_toolbar_without_game", True))

    @auto_hide_toolbar_without_game.setter
    def auto_hide_toolbar_without_game(self, v: bool) -> None:
        self.set("auto_hide_toolbar_without_game", v)

    # Scraper extras
    @property
    def scraper_timeout_sec(self) -> int:
        return int(self.get("scraper_timeout_sec", 30))

    @scraper_timeout_sec.setter
    def scraper_timeout_sec(self, v: int) -> None:
        self.set("scraper_timeout_sec", max(5, min(120, v)))

    @property
    def scraper_proxy(self) -> str:
        return str(self.get("scraper_proxy", ""))

    @scraper_proxy.setter
    def scraper_proxy(self, v: str) -> None:
        self.set("scraper_proxy", v)

    # OCR extras
    @property
    def ocr_thread_count(self) -> int:
        return int(self.get("ocr_thread_count", 2))

    @ocr_thread_count.setter
    def ocr_thread_count(self, v: int) -> None:
        self.set("ocr_thread_count", max(1, min(8, v)))

    # Sync / cache extras
    @property
    def image_download_concurrency(self) -> int:
        return int(self.get("image_download_concurrency", 3))

    @image_download_concurrency.setter
    def image_download_concurrency(self, v: int) -> None:
        self.set("image_download_concurrency", max(1, min(10, v)))

    # Updater
    @property
    def auto_check_updates(self) -> bool:
        return bool(self.get("auto_check_updates", True))

    @auto_check_updates.setter
    def auto_check_updates(self, v: bool) -> None:
        self.set("auto_check_updates", v)

    @property
    def auto_download_updates(self) -> bool:
        return bool(self.get("auto_download_updates", False))

    @auto_download_updates.setter
    def auto_download_updates(self, v: bool) -> None:
        self.set("auto_download_updates", v)

    # Archive & Export Preferences
    @property
    def export_destination(self) -> str:
        return str(self.get("export_destination", ""))

    @export_destination.setter
    def export_destination(self, v: str) -> None:
        self.set("export_destination", v)

    @property
    def remember_export_folder(self) -> bool:
        return bool(self.get("remember_export_folder", True))

    @remember_export_folder.setter
    def remember_export_folder(self, v: bool) -> None:
        self.set("remember_export_folder", v)

    @property
    def archive_default_sort(self) -> str:
        return str(self.get("archive_default_sort", "date_desc"))

    @archive_default_sort.setter
    def archive_default_sort(self, v: str) -> None:
        self.set("archive_default_sort", v)

    # Diagnostics & Logs
    @property
    def log_level(self) -> str:
        return str(self.get("log_level", "normal"))

    @log_level.setter
    def log_level(self, v: str) -> None:
        self.set("log_level", v)

    @property
    def include_debug_in_diagnostics(self) -> bool:
        return bool(self.get("include_debug_in_diagnostics", False))

    @include_debug_in_diagnostics.setter
    def include_debug_in_diagnostics(self, v: bool) -> None:
        self.set("include_debug_in_diagnostics", v)

    @property
    def search_history_limit(self) -> int:
        return int(self.get("search_history_limit", 5))

    @search_history_limit.setter
    def search_history_limit(self, v: int) -> None:
        self.set("search_history_limit", max(0, min(15, v)))

    @property
    def search_history(self) -> list:
        return self.get("search_history", [])

    @search_history.setter
    def search_history(self, value: list) -> None:
        self.set("search_history", value)

    @property
    def search_history_player(self) -> list:
        return self.get("search_history_player", [])

    @search_history_player.setter
    def search_history_player(self, value: list) -> None:
        self.set("search_history_player", value)

    @property
    def search_history_org(self) -> list:
        return self.get("search_history_org", [])

    @search_history_org.setter
    def search_history_org(self, value: list) -> None:
        self.set("search_history_org", value)

    # ------------------------------------------------------------------
    # Reputation System
    # ------------------------------------------------------------------

    @property
    def reputation_enabled(self) -> bool:
        return bool(self.get("reputation_enabled", False))

    @reputation_enabled.setter
    def reputation_enabled(self, v: bool) -> None:
        self.set("reputation_enabled", v)

    @property
    def reputation_auto_check(self) -> bool:
        return bool(self.get("reputation_auto_check", True))

    @reputation_auto_check.setter
    def reputation_auto_check(self, v: bool) -> None:
        self.set("reputation_auto_check", v)

    @property
    def reputation_prefetch_archived(self) -> bool:
        return bool(self.get("reputation_prefetch_archived", False))

    @reputation_prefetch_archived.setter
    def reputation_prefetch_archived(self, v: bool) -> None:
        self.set("reputation_prefetch_archived", v)

    @property
    def reputation_supabase_url(self) -> str:
        return str(self.get("reputation_supabase_url", ""))

    @reputation_supabase_url.setter
    def reputation_supabase_url(self, v: str) -> None:
        self.set("reputation_supabase_url", v)

    @property
    def reputation_anon_key(self) -> str:
        return str(self.get("reputation_anon_key", ""))

    @reputation_anon_key.setter
    def reputation_anon_key(self, v: str) -> None:
        self.set("reputation_anon_key", v)

    @property
    def reputation_history(self) -> dict:
        return self.get("reputation_history", {})

    @reputation_history.setter
    def reputation_history(self, v: dict) -> None:
        self.set("reputation_history", v)

    @property
    def toolbar_interact_hotkey(self) -> str:
        return str(self.get("toolbar_interact_hotkey", "left alt"))

    @toolbar_interact_hotkey.setter
    def toolbar_interact_hotkey(self, v: str) -> None:
        self.set("toolbar_interact_hotkey", v)

    @property
    def toolbar_drag_hotkey(self) -> str:
        return str(self.get("toolbar_drag_hotkey", "left ctrl"))

    @toolbar_drag_hotkey.setter
    def toolbar_drag_hotkey(self, v: str) -> None:
        self.set("toolbar_drag_hotkey", v)

    @property
    def toolbar_idle_opacity(self) -> float:
        return float(self.get("toolbar_idle_opacity", 0.4))

    @toolbar_idle_opacity.setter
    def toolbar_idle_opacity(self, v: float) -> None:
        self.set("toolbar_idle_opacity", max(0.1, min(1.0, v)))

    def reset_to_defaults(self) -> None:
        """Reset all settings to factory defaults and save immediately."""
        self._data = json.loads(json.dumps(DEFAULT_SETTINGS))
        self._dirty = True
        self._flush()
        log.info("Settings reset to factory defaults.")
        try:
            from src.core.events import EventBus
            EventBus.instance().settings_changed.emit("_reset_all", None)
        except Exception:
            pass

    def force_save(self) -> None:
        """Force an immediate save regardless of dirty state."""
        self._dirty = True
        self._flush()
