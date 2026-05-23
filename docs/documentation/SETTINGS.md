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
  "ocr_engine": "easyocr",
  "ocr_confidence_threshold": 0.5,
  "scraper_delay_ms": 500,
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
  "sync_interval_hours": 24,
  "sync_on_load": true,
  "temp_cache_auto_clear": false,
  "temp_cache_max_age_days": 7,
  "toolbar_opacity": 1.0,
  "theme_accent_override": null
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
| `last_tab` | `str` | `"search"` | Last active tab ID; restored on window show (except first open of session) |
| `pin_state` | `bool` | `false` | Whether main window pin was active at last close |

### OCR

| Key | Type | Default | Description |
|---|---|---|---|
| `ocr_engine` | `str` | `"easyocr"` | OCR engine to use: `"easyocr"` or `"tesseract"` |
| `ocr_confidence_threshold` | `float` | `0.5` | Minimum confidence score to accept OCR result (0.0–1.0) |

### Scraper

| Key | Type | Default | Description |
|---|---|---|---|
| `scraper_delay_ms` | `int` | `500` | Milliseconds to wait between RSI HTTP requests |
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

### Appearance

| Key | Type | Default | Description |
|---|---|---|---|
| `toolbar_opacity` | `float` | `1.0` | Overlay toolbar opacity (0.5–1.0) |
| `theme_accent_override` | `str \| null` | `null` | Optional hex color to override `#00AAFF` primary blue accent |

---

## Notes

- Do not manually edit `settings.json` while the app is running — changes will be overwritten on next save.
- If `settings.json` becomes corrupted, delete it. SC Dossier will recreate it with all defaults on next launch.
- Toolbar position (`x`, `y`, `edge`) are updated automatically whenever you drag the toolbar to a new position.
- Window geometry (`x`, `y`, `w`, `h`) is updated whenever you move or resize the main window.
