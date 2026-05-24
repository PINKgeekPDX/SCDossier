# T2: Chrome & Shell — Title Bar, Status Bar, Tray, Taskbar, Toolbar

## Purpose

Ensure every app-chrome surface shows the correct icon, correct gradient, correct button icons, and no stale text — in both dev run and packaged `.exe`. This is the most visible acceptance gate for the Epic.

## Scope

**In:**

- file:src/ui/widgets/title_bar.py — verify gradient (`#040C1A` → `#23282D`), animated label, `appicon.png` (24×24), `Lock.png`/`Unlock.png` pin toggle, `Return.png` hide button, hide button disabled+grayed when pinned
- file:src/ui/widgets/status_bar.py — confirm ping/uptime/nominal labels are absent at runtime; keep only dot + status text
- file:src/ui/tray/tray_icon.py — confirm `appicon.png` is the tray icon in both dev and packaged contexts, verify tray tooltip text, double-click behavior, and right-click menu actions
- file:src/app/main_window.py — confirm `appicon.ico` is set as the taskbar window icon
- file:src/ui/toolbar/overlay_toolbar.py — confirm `MobiGlas.png` and `Target_Lock.png` are loaded and visible, verify edge snapping and persisted position/edge behavior
- file:src/main.py — use `get_asset_path()` (from T1) for all icon resolution and preserve toolbar-first launch behavior with the main window hidden by default
- Verify startup orchestration: show the overlay toolbar on launch, keep the main window hidden, and perform the silent update check only when auto-check is enabled

**Out:**

- No layout or behavior changes beyond what is already specified in the Core Flows

## Acceptance Criteria

- Taskbar shows `appicon.ico` for the main window in both dev and packaged runtime
- System tray shows `appicon.png` in both dev and packaged runtime
- On launch, the overlay toolbar is shown by default and the main window remains hidden until explicitly opened
- Silent startup update checks occur only when auto-check is enabled
- Tray double-click shows the main window and hides the toolbar
- Tray tooltip reads "SC Dossier — Right-click for options"
- Tray right-click menu exposes: Show Toolbar | Open Dossier | Quick Capture | Settings | Quit
- Title bar shows: `appicon.png` far left → animated "SCD: Star Citizen Dossier" label → pin button → hide button
- Pin button shows `Unlock.png` when unpinned, `Lock.png` when pinned; clicking toggles `WindowStaysOnTopHint`
- Hide button is grayed and disabled while window is pinned; tooltip reads "Unpin the window first before hiding"
- Status bar shows only the dot + status text — no ping, uptime, or "System Nominal" text anywhere
- Toolbar shows `MobiGlas.png` and `Target_Lock.png` buttons, snaps to the nearest screen edge, restores its saved position/edge, and honors the configured opacity