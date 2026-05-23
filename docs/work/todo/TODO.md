# SC Dossier — Phased Task Checklist

> This is the living task tracker for the full SC Dossier build.  
> Law document: `docs/work/todo/read-3rd-finalized-dev-tasks-stepbystep-allphases-must-follow.md`

---

## Phase 1 — Project Bootstrap & Core Infrastructure

- [x] `requirements.txt` — all dependencies pinned
- [x] `src/core/paths.py` — `PathManager` singleton (OS-aware runtime paths)
- [x] `src/core/settings.py` — `SettingsManager` (load/save/auto-save settings.json)
- [x] `src/core/logger.py` — `RotatingFileHandler` → `Logs/app.log`
- [x] `src/core/events.py` — `EventBus` QObject signal hub
- [x] `src/app/constants.py` — App-wide enums, URL constants, string keys
- [x] `src/app/__init__.py`
- [x] `src/core/__init__.py`

---

## Phase 2 — Theme & Base UI Widgets

- [x] `src/ui/theme/palette.py` — all color constants from DESIGN.md
- [x] `src/ui/theme/fonts.py` — font registration (Sora, Inter, JetBrains Mono)
- [x] `src/ui/theme/stylesheet.py` — global QSS string builder
- [x] `src/ui/theme/__init__.py`
- [x] `src/ui/widgets/base_window.py` — `BaseWindow` (frameless, draggable, resizable)
- [x] `src/ui/widgets/glass_card.py` — `GlassCard` (panel with bracket corners)
- [x] `src/ui/widgets/title_bar.py` — `CustomTitleBar` (drag region, pin, hide buttons)
- [x] `src/ui/widgets/status_bar.py` — `CustomStatusBar` (status, ping, uptime)
- [x] `src/ui/widgets/nav_sidebar.py` — `NavSidebar` (64px icon rail, expandable)
- [x] `src/ui/widgets/tech_label.py` — `TechLabel` (label-caps styled QLabel)
- [x] `src/ui/widgets/data_field.py` — `DataField` (label + JetBrains Mono value pair)
- [x] `src/ui/widgets/avatar_widget.py` — `AvatarWidget` (image + bracket overlay)
- [x] `src/ui/widgets/badge_chip.py` — `BadgeChip` (badge image + name pill)
- [x] `src/ui/widgets/search_input.py` — `SearchInput` (glow focus input)
- [x] `src/ui/widgets/progress_overlay.py` — `ProgressOverlay` (scanning animation)
- [x] `src/ui/widgets/confirm_dialog.py` — `ConfirmDialog` (styled modal)
- [x] `src/ui/widgets/__init__.py`
- [x] `src/ui/__init__.py`

---

## Phase 3 — Overlay Toolbar

- [x] `src/ui/toolbar/overlay_toolbar.py` — `OverlayToolbar` (snap logic, persistence, 2 buttons)
- [x] `src/ui/toolbar/__init__.py`
- [x] SVG icons: `src/assets/icons/expand.svg`, `capture.svg`, `pin.svg`, `hide.svg`, `tray.svg`

---

## Phase 4 — Screen Capture & OCR

- [x] `src/ui/capture/region_selector.py` — `RegionSelector` (fullscreen overlay + QRubberBand)
- [x] `src/ui/capture/__init__.py`
- [x] `src/services/ocr_service.py` — `OCRService` (EasyOCR wrapper, post-processing)

---

## Phase 5 — Scraping Services

- [x] `src/services/scraper_player.py` — `PlayerScraper` (RSI citizen + org pages)
- [x] `src/services/scraper_org.py` — `OrgScraper` (name→SID + org page)
- [x] `src/services/image_downloader.py` — `ImageDownloader` (QThreadPool concurrent)
- [x] `src/services/__init__.py`

---

## Phase 6 — Cache & Archive Management

- [x] `src/services/cache_manager.py` — `CacheManager` (temp/archived profile I/O)
- [x] `src/services/archive_manager.py` — `ArchiveManager` (CRUD + ZIP export)
- [x] `src/services/sync_service.py` — `SyncService` (diff + selective update)

---

## Phase 7 — Main Window & Tabs

- [x] `src/ui/main_window/main_window.py` — `MainWindow` (BaseWindow + sidebar + stack)
- [x] `src/ui/main_window/__init__.py`
- [x] `src/ui/main_window/tabs/search_tab.py` — `SearchTab`
- [x] `src/ui/main_window/tabs/dossier_tab.py` — `DossierTab`
- [x] `src/ui/main_window/tabs/org_tab.py` — `OrgTab`
- [x] `src/ui/main_window/tabs/archive_tab.py` — `ArchiveTab`
- [x] `src/ui/main_window/tabs/settings_tab.py` — `SettingsTab`
- [x] `src/ui/main_window/tabs/__init__.py`

---

## Phase 8 — Tray Icon

- [x] `src/ui/tray/tray_icon.py` — `TrayIcon` (QSystemTrayIcon + context menu)
- [x] `src/ui/tray/__init__.py`

---

## Phase 9 — AppController & Entry Point

- [x] `src/app/controller.py` — `AppController` (all signal wiring)
- [x] `src/main.py` — entry point

---

## Phase 10 — End-to-End Flow Wiring

- [ ] Player search → archive check → scrape/load → display pipeline tested
- [ ] Org search → name→SID → scrape → display pipeline tested
- [ ] OCR capture → handle extraction → search trigger tested
- [ ] Archive → sync → export pipeline tested
- [ ] Toolbar → main window → toolbar show/hide toggle tested

---

## Phase 11 — Build Configuration

- [ ] `build/windows/build_windows.spec` — PyInstaller spec (onedir, assets included)
- [ ] `build/linux/debian/build_deb.sh` — Debian/Ubuntu/Mint packaging script
- [ ] `build/linux/arch/build_arch.sh` — Arch PKGBUILD script
- [ ] `build/linux/mint_ubuntu/build_deb_ubuntu.sh` — Ubuntu variant
- [ ] `scripts/run_dev.py` — dev runner
- [ ] `scripts/tools/scraper_test.py` — scraper validation tool
- [ ] `scripts/tools/ocr_test.py` — OCR accuracy test tool

---

## Phase 12 — Documentation

- [x] `README.md` (root)
- [x] `agent.md` (root)
- [x] `requirements.txt`
- [x] `docs/documentation/README.md` — user guide
- [x] `docs/documentation/SCRAPER.md` — scraper field reference
- [x] `docs/documentation/SETTINGS.md` — settings reference
- [x] `docs/work/todo/TODO.md` — this file
- [x] `docs/work/summaries/ARCHITECTURE.md` — architecture overview
- [x] `docs/work/reports/DESIGN_ANALYSIS.md` — design system analysis

---

## Upcoming / Backlog

- [ ] Font file acquisition — download Sora, Inter, JetBrains Mono TTFs into `src/assets/fonts/`
- [ ] Icon design — create high-quality SVG icons for expand, capture, pin, hide, tray, nav tabs
- [ ] Scraper validation — run `scripts/tools/scraper_test.py` against PINKgeekPDX and THEKVLT
- [ ] OCR calibration — run `scripts/tools/ocr_test.py` with Star Citizen UI font samples
- [ ] End-to-end smoke test — full search → display → archive → export flow
- [ ] Windows binary validation — test PyInstaller output on clean Windows 10 VM
- [ ] Linux deb validation — test on Debian/Ubuntu environment
