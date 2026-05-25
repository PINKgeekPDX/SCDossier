# SC Dossier — Settings Reference

All settings are stored in `settings.json` at:

- **Windows**: `%USERPROFILE%\Documents\PINK\SCDossier\Config\settings.json`
- **Linux**: `~/Documents/PINK/SCDossier/Config/settings.json`

Settings auto-save on change. The file is created with defaults on first launch.

---

## Full Settings Schema

```json
{
  "toolbar": {
    "x": 0,
    "y": 100,
    "edge": "left"
  },
  "window": {
    "x": 100,
    "y": 100,
    "w": 1100,
    "h": 700
  },
  "last_tab": "search",
  "pin_state": false,
  "pin_on_startup": false,
  "minimize_to_tray_on_close": true,
  "show_tray_notifications": true,
  "ocr_engine": "rapidocr",
  "ocr_confidence_threshold": 0.5,
  "ocr_thread_count": 2,
  "scraper_delay_ms": 500,
  "scraper_timeout_sec": 30,
  "scraper_proxy": "",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
  "sync_interval_hours": 24,
  "sync_on_load": true,
  "temp_cache_auto_clear": false,
  "temp_cache_max_age_days": 7,
  "image_download_concurrency": 3,
  "toolbar_opacity": 1.0,
  "theme_accent_override": null,
  "auto_check_updates": true,
  "auto_download_updates": false,
  "font_size_scaling": 100,
  "export_destination": "",
  "remember_export_folder": true,
  "archive_default_sort": "date_desc",
  "log_level": "normal",
  "include_debug_in_diagnostics": false,
  "search_history_limit": 5,
  "search_history": [],
  "search_history_player": [],
  "search_history_org": [],
  "_version": "0.3.0"
}
```

---

## Settings Reference

### `toolbar`

| Key | Type | Default | Description |
|---|---|---|---|
| `x` | `int` | `0` | Toolbar X position on screen |
| `y` | `int` | `100` | Toolbar Y position on screen |
| `edge` | `str` | `"left"` | Snapped edge: `"left"`, `"right"`, `"top"`, `"bottom"` |

### `window`

| Key | Type | Default | Description |
|---|---|---|---|
| `x` | `int` | `100` | Main window X position |
| `y` | `int` | `100` | Main window Y position |
| `w` | `int` | `1100` | Main window width (min: 900) |
| `h` | `int` | `700` | Main window height (min: 600) |

### General State

| Key | Type | Default | Description |
|---|---|---|---|
| `last_tab` | `str` | `"search"` | Last active tab ID; restored on window show |
| `pin_state` | `bool` | `false` | Whether main window pin was active at last close |
| `pin_on_startup` | `bool` | `false` | Whether to automatically pin the window on startup |
| `minimize_to_tray_on_close` | `bool` | `true` | Minimizes app to system tray instead of closing |
| `show_tray_notifications` | `bool` | `true` | Toggles system tray pop-up notifications |

### OCR

| Key | Type | Default | Description |
|---|---|---|---|
| `ocr_engine` | `str` | `"rapidocr"` | OCR engine to use (RapidOCR is the default ML-based engine) |
| `ocr_confidence_threshold` | `float` | `0.5` | Minimum confidence score to accept OCR result (0.0–1.0) |
| `ocr_thread_count` | `int` | `2` | Number of threads to dedicate to OCR processing |

### Scraper

| Key | Type | Default | Description |
|---|---|---|---|
| `scraper_delay_ms` | `int` | `500` | Milliseconds to wait between RSI HTTP requests |
| `scraper_timeout_sec` | `int` | `30` | Timeout in seconds for HTTP requests |
| `scraper_proxy` | `str` | `""` | Optional HTTP proxy server |
| `user_agent` | `str` | browser UA | HTTP User-Agent string sent with scraper requests |

### Sync

| Key | Type | Default | Description |
|---|---|---|---|
| `sync_interval_hours` | `int` | `24` | How many hours before a profile is considered stale for sync |
| `sync_on_load` | `bool` | `true` | Whether to auto-check sync when loading an archived profile |

### Cache

| Key | Type | Default | Description |
|---|---|---|---|
| `temp_cache_auto_clear` | `bool` | `false` | Automatically clear temp cache entries older than max age |
| `temp_cache_max_age_days` | `int` | `7` | Age limit for temp cache entries (used if auto-clear is on) |
| `image_download_concurrency`| `int` | `3` | Maximum concurrent image downloads |

### Appearance

| Key | Type | Default | Description |
|---|---|---|---|
| `toolbar_opacity` | `float` | `1.0` | Overlay toolbar opacity (0.5–1.0) |
| `theme_accent_override` | `str \| null` | `null` | Optional hex color to override `#00AAFF` primary blue accent |
| `font_size_scaling` | `int` | `100` | UI font scaling percentage (80-150) |

### Auto-Updater

| Key | Type | Default | Description |
|---|---|---|---|
| `auto_check_updates` | `bool` | `true` | Automatically checks for new updates on launch |
| `auto_download_updates`| `bool` | `false` | Silently downloads updates in the background when available |

### Archive & Export

| Key | Type | Default | Description |
|---|---|---|---|
| `export_destination` | `str` | `""` | Path to the default directory for exporting ZIP files |
| `remember_export_folder`| `bool` | `true` | Whether to remember the last used export folder |
| `archive_default_sort` | `str` | `"date_desc"` | Default sorting method for the Archive list |

### Diagnostics

| Key | Type | Default | Description |
|---|---|---|---|
| `log_level` | `str` | `"normal"` | Logging verbosity (`normal` or `debug`) |
| `include_debug_in_diagnostics`| `bool` | `false` | Whether to package debug info in diagnostic reports |
| `search_history_limit` | `int` | `5` | Number of previous searches to retain |

---

## Notes

- Do not manually edit `settings.json` while the app is running — changes will be overwritten on next save.
- If `settings.json` becomes corrupted, delete it. SC Dossier will recreate it with all defaults on next launch.
- Toolbar position (`x`, `y`, `edge`) are updated automatically whenever you drag the toolbar to a new position.
- Window geometry (`x`, `y`, `w`, `h`) is updated whenever you move or resize the main window.
