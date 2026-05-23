# SC Dossier — Comprehensive Codebase Audit Report

> Generated: 2026-05-15  
> Scope: Full end-to-end audit of all source code, UI, services, and configuration

---

## Executive Summary

The codebase has **~30 Python files** implementing a PyQt6 desktop app with layered architecture. The core infrastructure (paths, settings, events, logging) is **well-implemented**. The theme system (palette, fonts, stylesheet) is **comprehensive**. However, there are **critical bugs**, **broken signal flows**, **missing assets**, and **significant UI/UX deficiencies** that prevent the app from functioning correctly.

---

## Critical Bugs (App Will Crash or Misbehave)

### 1. Missing `PathManager.documents_root` Property
- **File:** `src/ui/tabs/archives_tab.py:105`
- **Issue:** `PathManager.instance().documents_root` is referenced but does not exist
- **Impact:** Export dialog will crash with AttributeError
- **Fix:** Add `documents_root` property to PathManager

### 2. `font_inter()` Called with Invalid `bold=True` Kwarg
- **Files:** `src/ui/tabs/dossier_tab.py:288`, `src/ui/tabs/archives_tab.py:62`
- **Issue:** `font_inter(16, bold=True)` — function signature is `font_inter(size, weight=QFont.Weight.Normal)`
- **Impact:** TypeError at runtime when these widgets are created
- **Fix:** Use `font_inter(16, QFont.Weight.Bold)`

### 3. `line-height` Invalid in QSS
- **Files:** `src/ui/tabs/dossier_tab.py:148,238,241`, `src/ui/tabs/org_tab.py:134,213,215`
- **Issue:** QSS does not support CSS `line-height` property
- **Impact:** Silently ignored — no visual effect
- **Fix:** Remove from QSS; use QFont metrics or QLabel minimumHeight

### 4. MainWindow Shown on Startup (Should Be Hidden)
- **File:** `src/main.py:81`
- **Issue:** `main_window.show()` called at startup — spec says toolbar should be default state
- **Impact:** App opens with full window visible instead of compact toolbar
- **Fix:** Remove `main_window.show()` from startup; only show toolbar

### 5. EventBus `search_player_requested` Signal Never Connected
- **File:** `src/app/controller.py`
- **Issue:** Controller connects `capture_completed` but never connects `search_player_requested`
- **Impact:** Direct player searches from UI don't route through the proper signal
- **Fix:** Connect `search_player_requested` to controller's search handler

---

## Signal Flow Problems

### Current (Broken) Flow:
```
SearchTab._on_search → EventBus.capture_completed.emit(handle)
DossierTab._on_search → EventBus.capture_completed.emit(handle)
```

### Expected Flow:
```
SearchTab._on_search → EventBus.search_player_requested.emit(handle)
Controller._connect_bus → search_player_requested → _start_player_scrape
```

The `capture_completed` signal is meant for OCR results, not manual searches. Using it for both creates confusion and breaks the intended architecture.

---

## Missing Assets

### Fonts Directory (`src/assets/fonts/`)
- **Status:** Does not exist
- **Required:** Sora (Regular, Medium, SemiBold, Bold), Inter (Regular, Medium, SemiBold, Bold), JetBrains Mono (Regular, Medium, Bold)
- **Impact:** All fonts fall back to system defaults — breaks the Aegis design system entirely

### Icons Directory (`src/assets/icons/`)
- **Status:** Does not exist
- **Required:** expand.svg, capture.svg, pin.svg, hide.svg, tray.svg (+ tray.ico for Windows)
- **Impact:** All buttons use text characters (⊞, ⊕, ◇, ⊟) as fallback — looks unpolished

---

## UI/UX Deficiencies (Massive Overhaul Needed)

### DossierTab
1. No GlassCard containers — uses plain QWidget backgrounds
2. Action bar uses hardcoded `P.SURFACE` instead of glass effect
3. Org cards don't use GlassCard properly (fixed height 80px clips content)
4. No image refresh after downloads complete
5. FlowLayout is just a QHBoxLayout — badges don't actually wrap
6. No empty state illustration when no profile loaded

### OrgTab
1. No GlassCard containers
2. No name→SID resolution — only accepts direct SID input
3. No candidate picker when multiple orgs match
4. No empty state when no org loaded

### ArchiveTab
1. **Missing two-pane layout** — only shows a list, no detail pane
2. **Missing collapsible list pane** — no collapse button or animation
3. **Missing filter input** — no search/filter for archive list
4. **Missing sort dropdown** — no sort by name/date
5. ArchiveItemWidget uses inline QSS instead of GlassCard aesthetic
6. Export generates ZIP but no HTML card, TXT, or CSV inside

### SettingsTab
1. **Missing settings controls:**
   - Sync interval
   - Sync on load toggle
   - Temp cache auto-clear toggle
   - Toolbar opacity slider
   - Theme accent override
   - User-agent input
   - OCR engine selector
   - Paths display
   - About section
2. Form layout uses plain QWidget background instead of GlassCard sections
3. No section headers or visual grouping

### SearchTab
1. No player/org mode toggle — only does player search
2. Emits wrong signal (`capture_completed` instead of `search_player_requested`)
3. No visual distinction between player and org search modes

### NavSidebar
1. Toggle button at bottom takes up a NavItem slot and interferes with stretch
2. No visual feedback on expand/collapse
3. Active state could be more prominent

### TitleBar
1. Not wired to BaseWindow's drag system via `set_drag_widget()`
2. Title bar drag works independently but doesn't integrate with BaseWindow

### StatusBar
1. `_status_lbl.setObjectName("class")` — incorrect object name
2. Ping display never updated (no actual ping measurement)

---

## Service Issues

### Scraper (Player)
1. CSS selectors may be outdated for current RSI website
2. No retry logic for failed requests
3. No handling for Cloudflare/bot protection
4. Bio extraction uses `.profile-content .bio` — may not match current HTML structure

### Scraper (Org)
1. Org listing search uses standard page URL, not API endpoint
2. No pagination handling for large result sets
3. Focus parsing (`.focus .item`) may not match current HTML

### ArchiveManager
1. Export ZIP missing HTML card generation (marked TODO)
2. No TXT summary generation
3. No CSV export option
4. No profile.json included in a readable format

### ImageDownloader
1. No retry logic
2. No progress reporting beyond success/failure
3. No timeout configuration per download

### OCRService
1. Instantiates EasyOCR Reader per call — very slow (should be singleton)
2. No GPU option (hardcoded `gpu=False`)
3. No progress reporting during OCR

---

## Architecture Issues

### MainWindow
1. `closeEvent` calls `QApplication.quit()` indirectly via `EventBus.app_exit` but nothing handles it
2. `_toggle_maximize` method exists but is never called (and spec says no maximize)
3. Geometry/position not restored from settings on startup
4. Last-active tab not restored from settings

### AppController
1. `_on_scrape_success` re-saves profile after queueing downloads but images may not be downloaded yet
2. No handling for `search_player_requested` signal
3. No handling for `search_org_requested` signal
4. OCR flow: `_on_capture_completed` checks if path is a file → sends to OCR, else treats as handle — works but is confusing

---

## Configuration Issues

### SettingsManager
1. No `force_save` called on app shutdown
2. Settings not persisted for window geometry
3. No validation of saved values on load

### requirements.txt
1. Missing `colorama` (optional but referenced in logger.py)

---

## Priority Fix Order

1. **Critical bugs** (crashes, wrong signals)
2. **Missing assets** (fonts, icons)
3. **Signal flow fixes** (proper search routing)
4. **UI/UX overhaul** (GlassCards, layouts, polish)
5. **Missing features** (two-pane archive, org name search, export formats)
6. **Service improvements** (retry logic, OCR singleton)
7. **Configuration** (settings persistence, geometry restore)
