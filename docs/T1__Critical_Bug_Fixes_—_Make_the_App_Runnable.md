# T1: Critical Bug Fixes — Make the App Runnable

## Overview

Fix every bug that prevents the app from functioning at all. These are surgical, precisely located fixes — no redesign, no new features. After this ticket, a player search must route correctly and scraped data must appear on screen.

## Spec References

- spec:c441db88-8d38-408a-b39a-c0196029911d/42214321-7712-4003-8d87-011fe43f2d07 — Phase 1
- spec:c441db88-8d38-408a-b39a-c0196029911d/6aaf1867-554f-447d-af1e-6810954a0dd9 — Component Architecture, Settings & MainWindow sections

## Scope

### Files to Change

| File | Fix |
| --- | --- |
| file:src/ui/tabs/dossier_tab.py | After `_build_detail()` call, add `self.content_layout.addWidget(self.detail_container)` — this is why scraped data never appears |
| file:src/ui/tabs/org_tab.py | Same fix — `self.content_layout.addWidget(self.detail_container)` after `_build_detail()` |
| file:src/ui/tabs/archives_tab.py | After `_build_detail_content()` call, add `self.detail_layout.addWidget(self.detail_content)` |
| file:src/app/main_window.py | In `_build_ui()`, after `self.title_bar = CustomTitleBar(self)`, call `self.set_drag_widget(self.title_bar)` — title bar drag is broken without this |
| file:src/ui/tabs/settings_tab.py | Line 261: fix OCR engine save — change `lambda: self.sm.ocr_engine == (...)` to `lambda: setattr(self.sm, 'ocr_engine', self.ocr_combo.currentData())` |
| file:src/ui/widgets/status_bar.py | Change `self._status_lbl.setObjectName("class")` → `self._status_lbl.setObjectName("StatusText")` |
| file:src/main.py | Confirm `main_window.show()` is NOT called at startup — only `toolbar.show()` should be called |

### Out of Scope

- No UI redesign
- No new features
- No scraper changes
- No icon changes

## Acceptance Criteria

App launches showing only the toolbar (main window hidden)Clicking toolbar expand button shows the main windowTyping a handle in SearchTab and pressing Enter emits search_player_requested (verify via log output)After a scrape completes, the DossierTab detail view becomes visible (not blank)After an org scrape completes, the OrgTab detail view becomes visibleSelecting an archived profile in ArchivesTab shows the detail pane on the rightTitle bar drag moves the main windowOCR engine setting saves correctly (verify settings.json after changing)No AttributeError or TypeError on startup or during normal navigation