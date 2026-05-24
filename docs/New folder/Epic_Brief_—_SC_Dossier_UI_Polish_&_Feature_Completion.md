# Epic Brief — SC Dossier UI Polish & Feature Completion

## Summary

SC Dossier is a PyQt6 desktop application for Star Citizen players that scrapes RSI (Roberts Space Industries) citizen and organization profiles, archives them locally, and provides OCR-based screen capture for in-game use. The codebase has undergone a significant prior implementation pass that addressed many UI customization requests, but the running application does not yet fully reflect those changes — either due to incomplete wiring, packaging gaps, or items that were partially implemented but not finished. This Epic covers a comprehensive, end-to-end UI polish and feature-completion pass: ensuring every visual element, icon assignment, interaction effect, tooltip, and settings control is correctly implemented, wired, and functional in the actual running app.

## Context & Problem

**Who is affected:** The sole developer/user (PINKgeekPDX) who runs the app daily as a Star Citizen companion tool.

**Where in the product:** Every surface of the application — title bar, status bar, nav sidebar, overlay toolbar, system tray, and all five tab content areas (Search, Dossier, Org, Archive, Settings).

**Current pain points:**

- The source code reflects many intended changes, but the running app may still show stale behavior (generic tray icon, "System Nominal" text, broken nav button, etc.) — the gap between code and runtime is the primary problem.
- Several UI areas lack the visual polish, animation consistency, and interaction feedback expected of a sci-fi themed app (hover effects, focus animations, button states).
- The Settings tab, while structurally present, needs a broader scope of configurable values and a more compact, readable layout.
- The auto-updater service exists in code but needs to be fully wired into the Settings About pane with proper status indicators and controls.
- Rich tooltips are inconsistently applied across the UI — many interactive elements have none.
- The image preview popout needs to feel more expansive when opened.
- The bottom nav button currently crashes the app and must be replaced with a safe GitHub profile link.

## Scope

| Area | What Changes |
| --- | --- |
| Title bar | App icon (far left), animated "SCD: Star Citizen Dossier" label, blue→grey gradient, icon-only pin/hide buttons |
| Status bar | Remove any remaining ping/uptime/nominal labels; keep only dot + status text |
| Nav sidebar | Correct icon paths for all 5 tabs; GitHub button at bottom with `!.png` icon, no crash |
| Overlay toolbar | `MobiGlas.png` for show-main, `Target_Lock.png` for OCR capture |
| System tray | `appicon.png`/`appicon.ico` as tray icon |
| Taskbar | `appicon.ico` as window icon |
| Search tab | Remove stale header text; USER.png + styled "CITIZEN DOSSIER" title; animated input; RIGHT.png initiate button; info icon + hint text |
| Dossier tab | Consistent styled search input; icon-only search/archive buttons |
| Org tab | Consistent styled search input; icon-only search button |
| Archive tab | Styled filter/sort controls; icon-only sync/export/delete buttons; enhanced list with hover effects |
| Settings tab | Compact layout; keep current settings scope but polish readability; add auto-check/auto-download/manual-check/install-later update controls plus status/progress UI, archive/export preferences, and end-user diagnostics/logging controls |
| Updater service | GitHub release checking, background download, staged install-later behavior from Settings, self-replace `.exe`, restart |
| Image preview | Larger frameless overlay-style preview that pops out from the clicked image, uses a thin border, and dismisses on any click |
| Tooltips | Rich, descriptive tooltips on all interactive elements across the entire app |

## Success Criteria

- Both the development run and packaged `.exe` runtime show the correct app icon across taskbar, tray, title bar, and toolbar-related surfaces.
- Stale visual leftovers are removed wherever they appear at runtime, including generic icons, stray "System Nominal" text, broken bottom-nav behavior, and unwanted status labels.
- None of the listed UI interactions crash the app.
- All changed controls share consistent hover, focus, and press states and expose rich, descriptive tooltips.
- All settings introduced or changed in this Epic save, load, and affect runtime behavior after restart.

## Out of Scope

- New scraper features or RSI data fields
- OCR engine changes
- Backend/service logic beyond what's needed to wire existing UI controls
- Deployment or packaging pipeline changes beyond what is necessary for the existing packaged `.exe` runtime to correctly reflect already-in-scope UI behavior