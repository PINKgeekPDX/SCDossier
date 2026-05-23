# SC Dossier — Implementation Plan (Post-Audit)

> Generated: 2026-05-15  
> Based on: CODEBASE_AUDIT.md  
> Goal: Fix ALL critical bugs, overhaul ALL UI/UX, complete ALL missing features

---

## Phase 1: Critical Bug Fixes (Must Fix First)

### 1.1 PathManager — Add `documents_root` Property
- File: `src/core/paths.py`
- Add `documents_root` property returning platform-appropriate documents directory

### 1.2 Fix `font_inter()` Bold Usage
- Files: `src/ui/tabs/dossier_tab.py`, `src/ui/tabs/archives_tab.py`
- Change `font_inter(16, bold=True)` → `font_inter(16, QFont.Weight.Bold)`

### 1.3 Remove Invalid QSS `line-height`
- Files: `src/ui/tabs/dossier_tab.py`, `src/ui/tabs/org_tab.py`
- Remove `line-height: 1.5;` from QSS strings

### 1.4 Fix MainWindow Startup Visibility
- File: `src/main.py`
- Remove `main_window.show()` — only show toolbar at startup

### 1.5 Fix Status Bar Object Name
- File: `src/ui/widgets/status_bar.py`
- Change `self._status_lbl.setObjectName("class")` → `self._status_lbl.setObjectName("StatusText")`

---

## Phase 2: Signal Flow Fixes

### 2.1 Connect `search_player_requested` to Controller
- File: `src/app/controller.py`
- Add `bus.search_player_requested.connect(self._on_search_player)` in `_connect_bus()`
- Create `_on_search_player(handle)` slot that calls `_start_player_scrape(handle)`

### 2.2 Connect `search_org_requested` to Controller
- File: `src/app/controller.py`
- Add `bus.search_org_requested.connect(self._on_search_org)` in `_connect_bus()`
- Create `_on_search_org(query)` slot that initiates org name→SID resolution

### 2.3 Fix SearchTab Signal Emission
- File: `src/ui/tabs/search_tab.py`
- Change `EventBus.capture_completed.emit(handle)` → `EventBus.search_player_requested.emit(handle)`
- Add player/org mode toggle buttons
- When org mode: emit `search_org_requested` instead

### 2.4 Fix DossierTab Signal Emission
- File: `src/ui/tabs/dossier_tab.py`
- Change `EventBus.capture_completed.emit(handle)` → `EventBus.search_player_requested.emit(handle)`

---

## Phase 3: Create Missing Assets

### 3.1 Create Font Directory Structure
- Create `src/assets/fonts/` directory
- Add placeholder font files or download free fonts:
  - Sora: https://fonts.google.com/specimen/Sora
  - Inter: https://fonts.google.com/specimen/Inter
  - JetBrains Mono: https://fonts.google.com/specimen/JetBrains+Mono

### 3.2 Create Icon Directory and SVG Files
- Create `src/assets/icons/` directory
- Create SVG icon files:
  - `expand.svg` — grid/expand icon
  - `capture.svg` — crosshair/capture icon
  - `pin.svg` — pin/thumbtack icon
  - `hide.svg` — collapse/hide icon
  - `tray.svg` — app tray icon
  - `tray.ico` — Windows tray icon (from SVG)

---

## Phase 4: UI/UX Massive Overhaul

### 4.1 DossierTab Overhaul
- Wrap content sections in GlassCard containers
- Fix FlowLayout to actually wrap badges (implement proper flow layout)
- Add image refresh after downloads complete (listen to `image_downloaded`)
- Add empty state when no profile loaded
- Fix org card height (remove fixed 80px, use dynamic sizing)
- Add archive/update button state management

### 4.2 OrgTab Overhaul
- Wrap content sections in GlassCard containers
- Add name→SID resolution flow (search by name, show candidates)
- Add candidate picker dialog
- Add empty state when no org loaded
- Add member roster preview section

### 4.3 ArchiveTab Complete Rewrite
- Implement two-pane layout (QSplitter)
- Left pane: list with filter input, sort dropdown, collapse button
- Right pane: dossier-style detail view (reuse DossierTab display logic)
- Add collapse/expand animation for left pane
- Fix ArchiveItemWidget to use GlassCard aesthetic
- Add proper sorting (name A-Z, Z-A, date archived, last synced)

### 4.4 SettingsTab Expansion
- Add all missing settings controls:
  - Sync interval (QSpinBox)
  - Sync on load (QCheckBox)
  - Temp cache auto-clear (QCheckBox)
  - Toolbar opacity (QSlider)
  - Theme accent override (QLineEdit + color picker)
  - User-agent (QLineEdit)
  - OCR engine selector (QComboBox)
  - Paths display (read-only labels)
  - About section (version, links)
- Group settings into GlassCard sections with headers
- Add section dividers and visual hierarchy

### 4.5 SearchTab Enhancement
- Add player/org mode toggle (two buttons at top)
- Visual indication of current mode
- Proper signal emission based on mode
- Add recent searches or quick-access suggestions

### 4.6 NavSidebar Polish
- Remove toggle button from NavItem list (make it a separate element)
- Improve active state visual (stronger glow, wider accent bar)
- Add subtle animation on tab switch
- Fix expand/collapse to not interfere with layout

### 4.7 TitleBar Integration
- Wire title bar to BaseWindow's `set_drag_widget()` method
- Ensure drag works properly across the entire title bar

### 4.8 StatusBar Fix
- Fix object name
- Add actual ping measurement (optional — can remain as display-only)

---

## Phase 5: Service Improvements

### 5.1 ArchiveManager Export Enhancement
- Generate standalone HTML card in ZIP (Aegis-themed)
- Generate TXT summary file
- Generate CSV export
- Include profile.json

### 5.2 OCRService Optimization
- Make EasyOCR Reader a singleton (cache across calls)
- Add GPU option from settings
- Add progress reporting

### 5.3 ImageDownloader Improvements
- Add retry logic (3 attempts)
- Add per-download timeout from settings

### 5.4 Scraper Resilience
- Add retry logic for failed requests
- Add request delay between pages
- Better error messages for 403/Cloudflare

---

## Phase 6: AppController & MainWindow Fixes

### 6.1 MainWindow
- Restore geometry from settings on startup
- Restore last-active tab from settings
- Save geometry on hide/close
- Fix closeEvent to properly quit application

### 6.2 AppController
- Wire all EventBus signals properly
- Handle image download completion and refresh UI
- Add org name→SID resolution flow

### 6.3 TrayIcon
- Wire to controller
- Add more menu actions (Quick Capture, Settings)
- Handle show/hide properly

---

## Phase 7: Configuration & Polish

### 7.1 Settings Persistence
- Save window geometry on close
- Save toolbar position on snap
- Save last-active tab
- Force save on app shutdown

### 7.2 requirements.txt
- Add `colorama` for dev mode logging

### 7.3 Final Polish
- Ensure all GlassCards render correctly
- Verify all animations work
- Test all signal flows end-to-end
- Verify no hardcoded hex values in widget code

---

## Verification Checklist

- [ ] App starts showing only toolbar (not main window)
- [ ] Toolbar expand button shows main window
- [ ] Main window hide button returns to toolbar
- [ ] Pin button works (stays on top, disables hide)
- [ ] Player search works (manual type + Enter)
- [ ] OCR capture works (region select → extract → search)
- [ ] Dossier tab displays all scraped data correctly
- [ ] Org search works (by name and SID)
- [ ] Archive tab shows two-pane layout with filter/sort
- [ ] Archive export generates complete ZIP
- [ ] Settings tab has all controls and auto-saves
- [ ] Tray icon works with context menu
- [ ] All fonts load correctly (no fallback)
- [ ] All icons display correctly (no text fallback)
- [ ] No crashes on any action
- [ ] No console errors during normal operation
