I have created the following plan after thorough exploration and analysis of the codebase. Follow the below plan verbatim. Trust the files and references. Do not re-verify what's written in the plan. Explore only when absolutely necessary. First implement all the proposed file changes and then I'll review all the changes together at the end.

## Codebase Observations

After a thorough audit, the codebase is already **significantly implemented** — most of the requested changes are already in place. The key areas that are already done: title bar gradient + animated title + icon + pin/hide buttons with correct icons, nav sidebar with correct icons + GitHub bottom button, search/dossier/org/archive tabs with icon-only buttons and styled inputs, settings tab with full settings scope + updater service, image preview at 95% screen size, tray icon using app icon, and taskbar icon set in `main.py`. What remains are targeted gaps and refinements.

## Approach

Rather than rebuilding from scratch, the plan targets the specific remaining gaps: the `ImagePreviewDialog` size needs to be pushed larger, the `main_window.py` needs an explicit `setWindowIcon` call on the window itself (not just the app), the `SettingsTab` about section needs developer details and license text expanded, and the `UpdaterService` needs the `_asset_url` properly surfaced to `SettingsTab._on_download_update`. All other items are confirmed already implemented.

---

## Implementation Steps

### 1. Fix Taskbar Window Icon — `file:src/app/main_window.py`

The `QApplication.setWindowIcon()` is set in `main.py` but the `MainWindow` instance itself does not call `self.setWindowIcon(...)`. Since it uses `BaseWindow` (frameless), the OS taskbar entry may still show a generic icon.

- In `MainWindow.__init__`, after `super().__init__(parent)`, resolve the `appicon.ico` path (same pattern used in `main.py`) and call `self.setWindowIcon(QIcon(ico_path))` on the window instance directly.
- Also call `self.setWindowTitle("SC Dossier")` (already present) — ensure it stays.

---

### 2. Expand Image Preview Size — `file:src/ui/widgets/image_preview.py`

The current cap is `0.95` of screen dimensions. Increase the preview to fill more of the screen:

- Change the `max_w` multiplier from `0.95` to `0.98` and `max_h` from `0.95` to `0.98`.
- This ensures the popout is as large as practically possible while still fitting on screen.

---

### 3. Expand Settings Tab — About Section — `file:src/ui/tabs/settings_tab.py`

The `_build_ui` method's `about_card` section currently shows minimal info. Expand it:

- **App info rows**: Already has `APPLICATION`, `DEVELOPER`, `FRAMEWORK`, `LICENSE`. Change `DEVELOPER` value from `f"{APP_AUTHOR}geekPDX"` to `"PINKgeekPDX"` (the correct GitHub handle). Add a `GITHUB` row linking to `https://github.com/pinkgeekpdx` using a `QLabel` with `setOpenExternalLinks(True)` and `setTextFormat(Qt.TextFormat.RichText)`.
- **Developer section**: Below the update management block, add a `QLabel` with a short developer bio paragraph — name, GitHub profile link, and a note that this is a community/fan project.
- **License section**: Expand the existing disclaimer `disc_lbl` to be a two-part block:
  - First label: `"LICENSE: MIT License — Open Source. See LICENSE file for full terms."` styled in `P.TEXT_DIM`.
  - Second label: The existing CIG disclaimer text, kept as-is.
- **`_about_row` helper**: Already exists and works — use it for the new rows.

---

### 4. Fix Updater `_asset_url` Surfacing — `file:src/ui/tabs/settings_tab.py` + `file:src/services/updater_service.py`

In `SettingsTab._on_download_update`, the code checks `self._updater._asset_url` directly. The `UpdaterService` stores `_asset_url` as an instance attribute set in `_on_update_available`. This is already correct. However, `_init_updater` is called before `_load_values`, so `auto_check_cb` may not be checked yet when `_init_updater` runs.

- In `_init_updater`, move the auto-check call to after `_load_values` completes, or guard it by reading `self.sm` directly: `if getattr(self.sm, 'auto_check_updates', True):` — this is already done correctly. No change needed here.

---

### 5. Verify & Patch `SettingsManager` Missing Typed Accessors — `file:src/core/settings.py`

The `settings_tab.py` uses `getattr(self.sm, 'scraper_timeout_sec', 30)`, `getattr(self.sm, 'scraper_proxy', "")`, `getattr(self.sm, 'ocr_thread_count', 2)`, `getattr(self.sm, 'font_size_scaling', 100)`, `getattr(self.sm, 'image_download_concurrency', 3)`, `getattr(self.sm, 'minimize_to_tray_on_close', True)`, `getattr(self.sm, 'pin_on_startup', False)`, `getattr(self.sm, 'show_tray_notifications', True)`, `getattr(self.sm, 'auto_check_updates', True)`, `getattr(self.sm, 'auto_download_updates', False)` — all using `getattr` fallbacks because typed properties are missing.

Add the following typed `@property` / `@setter` pairs to `SettingsManager`:

| Property | Type | Default |
|---|---|---|
| `scraper_timeout_sec` | `int` | `30` |
| `scraper_proxy` | `str` | `""` |
| `ocr_thread_count` | `int` | `2` |
| `font_size_scaling` | `int` | `100` |
| `image_download_concurrency` | `int` | `3` |
| `minimize_to_tray_on_close` | `bool` | `True` |
| `pin_on_startup` | `bool` | `False` |
| `show_tray_notifications` | `bool` | `True` |
| `auto_check_updates` | `bool` | `True` |
| `auto_download_updates` | `bool` | `False` |

Each follows the same pattern as existing properties (call `self.get(key, default)` in getter, `self.set(key, v)` in setter). This makes the `getattr` fallbacks in `settings_tab.py` unnecessary but harmless — they will now resolve to real properties.

---

### 6. Confirm All Icon Paths Are Correct — No Code Change Needed

A cross-check of all icon paths used in the codebase against the asset paths you specified:

| Location | Icon Used | Path in Code |
|---|---|---|
| Title bar app icon | `appicon.png` | ✅ `_APP_ICON` in `title_bar.py` |
| Title bar hide btn | `Return.png` | ✅ `_HIDE_ICON` in `title_bar.py` |
| Title bar pin (locked) | `Lock.png` | ✅ `_PIN_LOCKED_ICON` |
| Title bar pin (unlocked) | `Unlock.png` | ✅ `_PIN_UNLOCKED_ICON` |
| Toolbar expand btn | `MobiGlas.png` | ✅ `overlay_toolbar.py` |
| Toolbar capture btn | `Target_Lock.png` | ✅ `overlay_toolbar.py` |
| Nav: Search | `icon_search.svg` | ✅ `nav_sidebar.py` |
| Nav: Dossier | `FOIP.png` | ✅ `nav_sidebar.py` |
| Nav: Org | `SHLD.png` | ✅ `nav_sidebar.py` |
| Nav: Archive | `JOURNAL.png` | ✅ `nav_sidebar.py` |
| Nav: Settings | `icon_settings.svg` | ✅ `nav_sidebar.py` |
| Nav: GitHub btn | `!.png` | ✅ `nav_sidebar.py` |
| Search tab: initiate | `RIGHT.png` | ✅ `search_tab.py` |
| Search tab: info icon | `info.png` | ✅ `search_tab.py` |
| Search tab: user icon | `USER.png` | ✅ `search_tab.py` |
| Dossier: search btn | `icon_search.svg` | ✅ `dossier_tab.py` |
| Dossier: archive btn | `icon_save.svg` | ✅ `dossier_tab.py` |
| Org: search btn | `icon_search.svg` | ✅ `org_tab.py` |
| Archive: sync btn | `Refresh.png` | ✅ `archives_tab.py` |
| Archive: export btn | `icon_file.svg` | ✅ `archives_tab.py` |
| Archive: delete btn | `No_Access.png` | ✅ `archives_tab.py` |
| Tray icon | `appicon.png` | ✅ `main.py` |

All icon wiring is already correct. No changes needed.

---

### Summary of Files to Modify

```
src/app/main_window.py          — Add setWindowIcon() on the window instance
src/ui/widgets/image_preview.py — Increase preview size multiplier to 0.98
src/ui/tabs/settings_tab.py     — Expand about section (developer + license blocks)
src/core/settings.py            — Add 10 missing typed property accessors
```

All other requested changes (title bar gradient, animated title, icon buttons, nav icons, tab content styling, search/dossier/org/archive tab icon-only buttons, styled inputs, updater service, tray icon, status bar cleanup) are **already fully implemented** in the current codebase.