# T2: SVG Icon System — Create All Icons and Wire Into UI

## Overview

Create the 5 missing root-level SVG icons and wire all icons (including the existing `misc/` SVGs) into the toolbar, title bar, nav sidebar, and tray. Replace all Unicode character fallbacks with real SVG icons throughout the app.

## Spec References

- spec:c441db88-8d38-408a-b39a-c0196029911d/42214321-7712-4003-8d87-011fe43f2d07 — Phase 2
- spec:c441db88-8d38-408a-b39a-c0196029911d/6aaf1867-554f-447d-af1e-6810954a0dd9 — Assets section, NavSidebar section

## Depends On

- T1 (app must be runnable to verify icons render)

## Scope

### SVGs to Create (at `src/assets/icons/`)

| File | Description | Style |
| --- | --- | --- |
| `expand.svg` | Grid/expand HUD icon | Monochrome `#00AAFF`, 24×24 viewBox, aerospace aesthetic |
| `capture.svg` | Crosshair/reticle with corner brackets | Monochrome `#00AAFF`, 24×24 viewBox |
| `pin.svg` | Pin/thumbtack icon | Monochrome `#00AAFF`, 24×24 viewBox |
| `hide.svg` | Left-pointing chevron/collapse | Monochrome `#00AAFF`, 24×24 viewBox |
| `tray.svg` | SC Dossier app icon (stylized dossier/shield) | Monochrome `#00AAFF`, 64×64 viewBox |

### Code Changes

| File | Change |
| --- | --- |
| file:src/ui/widgets/nav_sidebar.py | Update `NAV_ITEMS` to include SVG paths; update `NavItem` to accept `icon_path` instead of `icon` char; update `paintEvent` to draw `QIcon(path).pixmap(22, 22)` via `painter.drawPixmap()` with Unicode fallback if file missing |
| file:src/ui/toolbar/overlay_toolbar.py | Already wired correctly — just needs the SVG files to exist at the referenced paths |
| file:src/ui/widgets/title_bar.py | Wire `pin.svg` and `hide.svg` into title bar buttons using `QIcon` |
| file:src/main.py | Wire `tray.svg` into `TrayIcon` (already partially done — verify path resolves) |

### SVG Paths for NavSidebar (already exist in `src/assets/icons/misc/`)

- Search tab → `misc/search.svg`
- Dossier tab → `misc/person.svg` (or closest equivalent)
- Organization tab → `misc/groups.svg` (or closest equivalent)
- Archive tab → `misc/archive.svg` (or closest equivalent)
- Settings tab → `misc/settings.svg`

<user_quoted_section>Note: Scan src/assets/icons/misc/ for the exact filenames before wiring — use the closest semantic match available.</user_quoted_section>

### Out of Scope

- SC brand icon decorations in tabs (that's T5)
- No changes to scraper or OCR

## Acceptance Criteria

Toolbar expand and capture buttons show SVG icons (not • text fallback)Title bar pin and hide buttons show SVG iconsNavSidebar shows SVG icons for all 5 tabs (no Unicode chars)Tray icon shows the app SVG iconAll icons are monochrome #00AAFF on transparent backgroundIf an SVG file is missing, the code falls back gracefully (no crash)Icons remain crisp at all window sizes (SVG scaling works correctly)