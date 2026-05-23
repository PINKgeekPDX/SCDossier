# SC Dossier — Architecture Overview

## Philosophy

SC Dossier uses a strict layered architecture. Each layer has explicit allowed dependencies; no layer may import from a higher layer.

```
core/       (no UI, no Qt widgets — pure Python only)
  ↑
services/   (may use QThread/QThreadPool; no widget imports)
  ↑
ui/         (consumes core/ and services/ via signals)
  ↑
app/        (orchestration only; wires all layers together)
```

---

## Component Map

```
AppController (app/controller.py)
│
├── PathManager (core/paths.py)
│   └── Resolves all OS-aware runtime paths
│
├── SettingsManager (core/settings.py)
│   └── Loads/saves settings.json; typed getters/setters; auto-save
│
├── Logger (core/logger.py)
│   └── RotatingFileHandler → Logs/app.log
│
├── EventBus (core/events.py)
│   └── QObject singleton with all pyqtSignals
│
├── PlayerScraper (services/scraper_player.py)
│   └── RSI citizen pages → PlayerProfile dict
│
├── OrgScraper (services/scraper_org.py)
│   └── RSI org pages + name→SID resolution
│
├── ImageDownloader (services/image_downloader.py)
│   └── QThreadPool concurrent image fetching
│
├── OCRService (services/ocr_service.py)
│   └── EasyOCR local text extraction
│
├── CacheManager (services/cache_manager.py)
│   └── Temp + Archived profile I/O
│
├── ArchiveManager (services/archive_manager.py)
│   └── Archive CRUD + ZIP export
│
├── SyncService (services/sync_service.py)
│   └── Diff live vs archived; selective field update
│
├── TrayIcon (ui/tray/tray_icon.py)
│   └── QSystemTrayIcon + context menu
│
├── OverlayToolbar (ui/toolbar/overlay_toolbar.py)
│   └── Frameless, topmost, edge-snapping, 2 buttons
│
├── RegionSelector (ui/capture/region_selector.py)
│   └── Fullscreen overlay + QRubberBand screen capture
│
└── MainWindow (ui/main_window/main_window.py)
    ├── CustomTitleBar (pin + hide buttons)
    ├── NavSidebar (left icon rail)
    ├── QStackedWidget
    │   ├── SearchTab
    │   ├── DossierTab
    │   ├── OrgTab
    │   ├── ArchiveTab
    │   └── SettingsTab
    └── CustomStatusBar
```

---

## Signal Flow

All cross-component communication uses the EventBus (`core/events.py`). The AppController wires service slots to UI signals and vice versa.

### Player Search Flow

```
SearchTab.search_player_clicked
  → EventBus.search_player_requested(handle)
  → AppController slot:
      CacheManager.is_archived(handle)?
        YES: ArchiveManager.load → SyncService.check → emit profile_loaded
        NO:  PlayerScraper.scrape → CacheManager.save_temp → emit profile_loaded
  → EventBus.profile_loaded(data)
  → MainWindow → DossierTab.populate(data)
```

### OCR Capture Flow

```
OverlayToolbar.capture_clicked
  → toolbar.hide()
  → RegionSelector.show()
  → User drags region
  → QScreen.grabWindow() → save PNG
  → OCRService.extract_text(path)
      success: EventBus.capture_completed(handle)
      failure: ConfirmDialog("OCR failed")
  → EventBus.capture_completed
  → EventBus.search_player_requested(handle)
  → [same as Player Search Flow above]
```

### Org Search Flow

```
SearchTab.search_org_clicked
  → OrgScraper.resolve_sid(query) → SID
  → OrgScraper.scrape_org(sid) → OrgProfile
  → EventBus.org_loaded(data)
  → MainWindow → OrgTab.populate(data)
```

---

## UI Widget Hierarchy

```
BaseWindow (QWidget, FramelessWindowHint, WA_TranslucentBackground)
  └── MainWindow
      ├── CustomTitleBar
      ├── NavSidebar
      ├── QStackedWidget → [SearchTab, DossierTab, OrgTab, ArchiveTab, SettingsTab]
      └── CustomStatusBar

BaseWindow (with WindowStaysOnTopHint | Tool)
  └── OverlayToolbar

QWidget (fullscreen, WA_TranslucentBackground)
  └── RegionSelector

GlassCard (QFrame with QPainter bracket-corners + rgba bg)
  └── Used as primary panel container in all tabs
```

---

## Theme System

```
ui/theme/palette.py    → Color constants (SPACE_VOID, PRIMARY, GLASS_BORDER, ...)
ui/theme/fonts.py      → Font registration (Sora, Inter, JetBrains Mono)
ui/theme/stylesheet.py → Global QSS string applied via QApplication.setStyleSheet()
```

All widget styling flows through QSS. Individual widgets must not hardcode color values.

---

## Data Storage Architecture

```
Cache/Temp/{handle}/
  profile.json         ← full scraped data dict
  avatar.png
  badge_{name}.png
  org_{sid}_logo.png
  _captures/           ← OCR temp captures

Cache/Archived/{handle}/
  profile.json         ← same structure + archived_at, synced_at
  avatar.png
  badge_{name}.png
  org_{sid}_logo.png
```

`profile.json` is the single source of truth for a profile's state. All images are referenced by local path within this JSON (`avatar_local`, `logo_local`, etc.).

---

## Threading Model

| Operation | Thread | Mechanism |
|---|---|---|
| Image downloads | Worker pool | `QThreadPool` + `QRunnable` |
| Scraping | Background | `QThread` subclass with signals |
| OCR initialization | Background | `QThread` at startup |
| OCR extraction | Background | `QThread` per capture |
| Archive/sync ops | Background | `QThread` with progress signals |
| UI updates | Main thread | Signal → slot across threads |

All background threads communicate results back to the UI exclusively via Qt signals. Never call UI methods directly from a non-main thread.

---

## Build Targets

| Platform | Tool | Output |
|---|---|---|
| Windows 10/11 | PyInstaller (onedir) | `built/dist/windows/SCDossier/` |
| Linux Debian/Ubuntu/Mint | PyInstaller + `dpkg-deb` | `built/dist/linux/debian/SCDossier.deb` |
| Linux Arch | PyInstaller + PKGBUILD | `built/dist/linux/arch/SCDossier-*.pkg.tar.zst` |
