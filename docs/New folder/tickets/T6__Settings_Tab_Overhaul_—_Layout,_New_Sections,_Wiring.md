# T6: Settings Tab Overhaul — Layout, New Sections, Wiring

## Purpose

Make the Settings tab more compact and readable, add the three new sections (Update Behavior, Archive & Export Preferences, Diagnostics & Logs), fix the `_init_updater()` initialization order bug, and ensure all controls correctly save/load/affect behavior.

## Scope

**In:**

- file:src/ui/tabs/settings_tab.py
- Fix init order: call `_load_values()` before `_init_updater()` in `__init__`
- Compact layout pass: reduce padding, use two-column grid where appropriate, ensure nothing is cut off or unreadable
- **Update Behavior section:** auto-check checkbox, auto-download checkbox, "Check for updates now" action button, "Install downloaded update" action button (enabled only when a staged update is ready), update status text, and download progress bar
- **Archive & Export Preferences section:** default export destination (path field + browse button), remember last export folder (checkbox), default archive sort (dropdown)
- **Diagnostics & Logs section:** open logs folder (action button), logging detail level (normal/debug dropdown), include debug details in diagnostics (checkbox), copy recent diagnostic summary (action button)
- All new controls must read from and write to `SettingsManager`
- About pane: app name + version, PyQt6 framework, developer PINKgeekPDX (clickable GitHub link), MIT License, CIG disclaimer

**Out:**

- Updater service internals (T7)
- Tooltip pass (T8)

## Acceptance Criteria

- All existing settings controls remain functional and correctly save/load after restart
- Three new sections are present and all controls save/load correctly
- Update controls include auto-check, auto-download, manual check-now, install-later, visible update status, and download progress UI
- "Install downloaded update" button is disabled until a staged update file exists on disk
- `_load_values()` is called before `_init_updater()` — no `AttributeError` on startup
- About pane shows version from `APP_VERSION` constant and a clickable GitHub link
- Layout is compact enough that all sections are accessible without excessive scrolling