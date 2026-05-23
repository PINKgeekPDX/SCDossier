# T7: Settings & Session Persistence — Geometry, Tab, Tray

## Overview

Ensure all session state persists correctly across app restarts: window geometry, toolbar position, last-active tab, and tray icon behavior. Most of this is already implemented — this ticket verifies it all works end-to-end and fixes any gaps.

## Spec References

- spec:c441db88-8d38-408a-b39a-c0196029911d/42214321-7712-4003-8d87-011fe43f2d07 — Phase 7
- spec:c441db88-8d38-408a-b39a-c0196029911d/6aaf1867-554f-447d-af1e-6810954a0dd9 — Settings & MainWindow section

## Depends On

- T1 (settings save must be working)

## Scope

### Verify and Fix (files as needed)

file:src/main.py

- Verify geometry restore: `main_window.setGeometry(QRect(sm.window_x, sm.window_y, sm.window_w, sm.window_h))` — already present, verify it applies before `toolbar.show()`
- Verify toolbar position restore: `toolbar.restore_position(sm.toolbar_x, sm.toolbar_y, sm.toolbar_edge)` — already present
- Tray icon double-click: verify `tray_icon.show_main_requested` is connected to `_show_main_window` — already connected, verify behavior (show if hidden, bring to front if visible)

file:src/app/main_window.py

- Verify `closeEvent` saves geometry to `SettingsManager` and calls `sm.force_save()` — already implemented
- Verify last-tab restore in `__init__`: `sm.last_tab` → `self.sidebar.set_active_tab(last_tab)` — already implemented
- Verify last-tab save in `_on_tab_selected`: `SettingsManager.instance().last_tab = tab_id` — already implemented

file:src/ui/toolbar/overlay_toolbar.py

- Verify `_save_position()` is called after every snap — already implemented in `snap_to_nearest_edge()`
- Verify toolbar opacity is applied from settings on startup — add `toolbar.set_opacity(sm.toolbar_opacity)` call in `main.py` if missing

file:src/ui/tray/tray_icon.py

- Verify double-click activation: `QSystemTrayIcon.ActivationReason.DoubleClick` → emit `show_main_requested`
- Verify context menu has: Show Toolbar, Open Dossier, Quick Capture, Settings, Quit

### Out of Scope

- No new settings controls (those are in T5)
- No changes to `SettingsManager` internals (already correct)

## Acceptance Criteria

After closing and reopening the app, main window appears at the same position and size as when it was closedAfter closing and reopening, the last-active tab is restoredAfter dragging the toolbar to a new edge and restarting, toolbar appears at the saved edge positionToolbar opacity setting from SettingsTab is applied to the toolbar on startupDouble-clicking the tray icon shows the main window (or brings it to front if already visible)Tray context menu has all required items and they work correctlysettings.json is written to %USERPROFILE%\Documents\PINK\SCDossier\Config\ on Windows