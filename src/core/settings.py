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
    "ocr_engine": OCREngine.RAPIDOCR.value,
    "ocr_confidence_threshold": DEFAULT_OCR_CONFIDENCE_THRESHOLD,
    "scraper_delay_ms": DEFAULT_SCRAPER_DELAY_MS,
    "user_agent": DEFAULT_USER_AGENT,
    "sync_interval_hours": DEFAULT_SYNC_INTERVAL_HOURS,
    "sync_on_load": True,
    "temp_cache_auto_clear": False,
    "temp_cache_max_age_days": DEFAULT_TEMP_CACHE_MAX_AGE_DAYS,
    "toolbar_opacity": 1.0,
    "theme_accent_override": None,
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

    def force_save(self) -> None:
        """Force an immediate save regardless of dirty state."""
        self._dirty = True
        self._flush()
