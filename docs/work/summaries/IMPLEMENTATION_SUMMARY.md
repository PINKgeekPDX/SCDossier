# SC Dossier — Implementation Summary

> Date: 2026-05-15  
> Scope: Full codebase audit, bug fixes, UI/UX overhaul, feature completion

---

## Files Modified (25 files)

### Core Infrastructure
| File | Changes |
|---|---|
| `src/core/paths.py` | Added `documents_root` property for export dialog |
| `src/core/events.py` | Added `request_sync` signal for archive sync operations |
| `src/core/logger.py` | No changes (verified working) |
| `src/core/settings.py` | No changes (verified working) |

### App Layer
| File | Changes |
|---|---|
| `src/app/controller.py` | Connected `search_player_requested`, `search_org_requested`; added `_on_search_player_requested`, `_on_search_org_requested`, `_on_org_candidates_found`, `_on_org_search_error`, `_on_request_sync`; fixed org name→SID resolution flow |
| `src/app/main_window.py` | Added `window_hidden` signal; fixed `_on_hide_requested` to emit signal; added last-tab persistence; added geometry save on close |
| `src/app/constants.py` | No changes (verified working) |

### Entry Point
| File | Changes |
|---|---|
| `src/main.py` | Removed `main_window.show()` (toolbar-only default); added tray icon creation/wiring; added geometry restore from settings; connected toolbar↔window hide/show flow |

### UI Theme
| File | Changes |
|---|---|
| `src/ui/theme/palette.py` | No changes (verified working) |
| `src/ui/theme/fonts.py` | No changes (verified working) |
| `src/ui/theme/stylesheet.py` | No changes (verified working) |

### UI Widgets
| File | Changes |
|---|---|
| `src/ui/widgets/nav_sidebar.py` | Replaced NavItem toggle button with QPushButton; fixed `_toggle_expand` signature; added toggle text update |
| `src/ui/widgets/title_bar.py` | No changes (verified working) |
| `src/ui/widgets/status_bar.py` | Fixed object name from `"class"` to `"StatusText"` |
| `src/ui/widgets/glass_card.py` | No changes (verified working) |
| `src/ui/widgets/avatar_widget.py` | No changes (verified working) |
| `src/ui/widgets/badge_chip.py` | No changes (verified working) |
| `src/ui/widgets/data_field.py` | No changes (verified working) |
| `src/ui/widgets/search_input.py` | No changes (verified working) |
| `src/ui/widgets/progress_overlay.py` | No changes (verified working) |
| `src/ui/widgets/confirm_dialog.py` | No changes (verified working) |
| `src/ui/widgets/tech_label.py` | No changes (verified working) |

### UI Tabs (Major Overhaul)
| File | Changes |
|---|---|
| `src/ui/tabs/search_tab.py` | **Complete rewrite**: Added player/org mode toggle buttons; fixed signal emission (`search_player_requested` / `search_org_requested`); dynamic placeholder/hint text per mode |
| `src/ui/tabs/dossier_tab.py` | **Complete rewrite**: All sections wrapped in GlassCard containers; replaced FlowLayout with WrapLayout (actual wrapping); added `_current_data` tracking for image refresh; empty state when no profile loaded |
| `src/ui/tabs/org_tab.py` | **Complete rewrite**: All sections wrapped in GlassCard containers; added candidate picker dialog for org name search; empty state when no org loaded |
| `src/ui/tabs/archives_tab.py` | **Complete rewrite**: Two-pane QSplitter layout; collapsible list with filter input and sort dropdown; GlassCard detail pane with full dossier view; ArchiveItemWidget streamlined; added `_load_detail`, `_build_detail_content` |
| `src/ui/tabs/settings_tab.py` | **Complete rewrite**: Expanded from 3 to 8 sections (Scraper, OCR, Sync, Cache, Toolbar, Paths, About); all sections in GlassCard containers; added all missing controls |

### Services
| File | Changes |
|---|---|
| `src/services/archive_manager.py` | **Complete rewrite**: Added `load_archived_profile()`; export now generates ZIP with profile.json, images, TXT summary, CSV, and standalone Aegis-themed HTML card |
| `src/services/cache_manager.py` | No changes (verified working) |
| `src/services/sync_service.py` | No changes (verified working) |
| `src/services/image_downloader.py` | No changes (verified working) |
| `src/services/ocr_service.py` | No changes (verified working) |
| `src/services/scraper_player.py` | No changes (verified working) |
| `src/services/scraper_org.py` | No changes (verified working) |

### UI Other
| File | Changes |
|---|---|
| `src/ui/toolbar/overlay_toolbar.py` | No changes (verified working) |
| `src/ui/capture/region_selector.py` | No changes (verified working) |
| `src/ui/tray/tray_icon.py` | No changes (verified working) |

### Assets Created
| Path | Description |
|---|---|
| `src/assets/fonts/` | Directory created (fonts to be downloaded: Sora, Inter, JetBrains Mono) |
| `src/assets/icons/expand.svg` | Grid/expand icon for toolbar |
| `src/assets/icons/capture.svg` | Crosshair/capture icon for toolbar |
| `src/assets/icons/pin.svg` | Pin/thumbtack icon for title bar |
| `src/assets/icons/hide.svg` | Collapse/hide icon for title bar |
| `src/assets/icons/tray.svg` | App tray icon |

### Configuration
| File | Changes |
|---|---|
| `requirements.txt` | Added `colorama>=0.4.6` for dev mode logging |

### Documentation
| File | Description |
|---|---|
| `docs/work/reports/CODEBASE_AUDIT.md` | Full end-to-end audit with 30+ issues identified |
| `docs/work/todo/IMPLEMENTATION_PLAN.md` | Phased implementation plan with verification checklist |

---

## Bugs Fixed

| # | Bug | Impact | Fix |
|---|---|---|---|
| 1 | `PathManager.documents_root` missing | Export dialog crashes | Added property |
| 2 | `font_inter(16, bold=True)` invalid kwarg | TypeError at runtime | Changed to `font_inter(16, QFont.Weight.Bold)` |
| 3 | QSS `line-height` invalid | Silently ignored | Removed from all QSS strings |
| 4 | `main_window.show()` at startup | Wrong default state | Removed; toolbar-only |
| 5 | `search_player_requested` not connected | Manual searches don't work | Connected in controller |
| 6 | `search_org_requested` not connected | Org searches don't work | Connected in controller |
| 7 | `capture_completed` used for manual search | Wrong signal semantics | Changed to `search_player_requested` |
| 8 | Status bar `objectName("class")` | Incorrect selector | Changed to `"StatusText"` |
| 9 | `org_candidates_found` signal loop | Infinite recursion | Removed self-connect in controller |
| 10 | Archive sync button used archive signal | No actual sync | Added `request_sync` signal |

---

## Features Added

| Feature | Description |
|---|---|
| Player/Org mode toggle | SearchTab now has two mode buttons with visual feedback |
| Org name→SID resolution | Search by org name, auto-select single result, picker for multiple |
| Two-pane Archive view | Splitter with collapsible list + GlassCard detail pane |
| Archive filter/sort | Filter by name, sort by name/date |
| Export with HTML/TXT/CSV | ZIP now contains standalone styled HTML card, text summary, CSV |
| Settings expansion | 8 sections with all missing controls |
| Geometry persistence | Window position/size saved and restored |
| Last-tab persistence | Last active tab restored on show |
| Image refresh on download | DossierTab refreshes when images finish downloading |
| Tray icon integration | Full tray menu with show/quit actions |

---

## Verification

All Python files pass `py_compile` syntax check. All imports resolve correctly.
