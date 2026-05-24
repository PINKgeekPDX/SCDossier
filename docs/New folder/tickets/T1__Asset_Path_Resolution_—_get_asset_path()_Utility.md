# T1: Asset Path Resolution — get_asset_path() Utility

## Purpose

All icon paths across the app currently use `os.path.dirname(__file__)` chains that work in development but break in the PyInstaller frozen `.exe` bundle where `__file__` resolves inside `sys._MEIPASS`. This ticket adds a single shared utility that resolves asset paths correctly in both contexts, and migrates all icon path constants to use it.

## Scope

**In:**

- Add `get_asset_path(relative: str) -> str` to file:src/core/paths.py
- Migrate all icon path resolution in: file:src/ui/widgets/title_bar.py, file:src/ui/widgets/nav_sidebar.py, file:src/ui/toolbar/overlay_toolbar.py, file:src/ui/tabs/search_tab.py, file:src/ui/tabs/dossier_tab.py, file:src/ui/tabs/org_tab.py, file:src/ui/tabs/archives_tab.py, file:src/main.py

**Out:**

- No visual changes — this is a pure path-resolution correctness fix

## Acceptance Criteria

- `get_asset_path("assets/appicon.png")` returns a valid, existing path in both `python src/main.py` (dev) and the packaged `SCDossier.exe`
- All icon-bearing widgets load their icons without `QPixmap` null warnings in either runtime context
- No `os.path.dirname(__file__)` icon path chains remain in any of the listed files

## Technical Notes

The utility should check `sys._MEIPASS` first (frozen context), then fall back to the source tree root. The relative path argument should be relative to the `src/` directory (e.g. `"assets/icons/Icons/FOIP.png"`).