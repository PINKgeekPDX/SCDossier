# T5: UI/UX Overhaul — All Tabs, NavSidebar, SC Brand Icons

## Overview

Complete the visual and functional overhaul of all five tabs and the nav sidebar. This is the largest ticket — it covers everything from GlassCard polish to SC brand icon decorations to the WrapLayout badge fix. After T1 the app works; after T5 it looks and feels like the Aegis Liquid Interface it's supposed to be.

## Spec References

- spec:c441db88-8d38-408a-b39a-c0196029911d/42214321-7712-4003-8d87-011fe43f2d07 — Phase 5
- spec:c441db88-8d38-408a-b39a-c0196029911d/6aaf1867-554f-447d-af1e-6810954a0dd9 — UI Widgets & Tabs section, wireframes

## Depends On

- T1, T2, T3 (bugs fixed, icons present, scraper returning real data)

## Scope

### file:src/ui/tabs/dossier_tab.py

- Extract `WrapLayout` to file:src/ui/widgets/wrap_layout.py (shared with ArchivesTab)
- Optimize `_on_image_downloaded`: only refresh avatar/badge images that match the downloaded URL rather than re-populating everything
- Add RSI brand icon decoration (`brand-icons/sc-icon-brand-rsi.svg` or closest match) as a subtle watermark in the identity card header
- Verify all GlassCard sections render correctly with real scraped data

### file:src/ui/tabs/org_tab.py

- Add manufacturer logo decoration: match `data["name"]` against known SC manufacturer names (RSI, Anvil, Drake, Origin, MISC, Mirai, Crusader, Aegis, Banu, Xi'an, Esperia, etc.) and display the corresponding SVG from `src/assets/icons/manufact-names/` in the identity card
- Verify candidate picker dialog works correctly for multi-result org name searches

### file:src/ui/tabs/archives_tab.py

- Replace `detail_badges_layout` (`QHBoxLayout`) with `WrapLayout` from the new shared widget — badges currently don't wrap
- Consolidate `_apply_filter` and `_apply_sort` into a single `_refresh_display()` method (current double-filter is redundant)
- Remove fixed `card.setFixedHeight(72)` from `_add_org_card()` — clips content

### file:src/ui/tabs/settings_tab.py

- Verify all 7 GlassCard sections render correctly (Scraper, OCR, Sync, Cache, Toolbar, Paths, About)
- Verify all controls auto-save via `SettingsManager` (all lambdas correct after T1 fix)

### file:src/ui/tabs/search_tab.py

- Verify player/org mode toggle visual state updates correctly (button style refresh via `unpolish`/`polish`)
- Verify `navigate_to_tab` emission routes to correct tab after search

### file:src/ui/widgets/nav_sidebar.py

- Increase active state visual weight: background alpha `26` → `40`, left accent bar `2px` → `3px`
- Ensure sidebar expand/collapse animation triggers `item.update()` on all items so labels appear/disappear correctly

### file:src/ui/widgets/wrap_layout.py (new shared widget)

- Extract `WrapLayout` from `dossier_tab.py` into its own file
- Import in both `dossier_tab.py` and `archives_tab.py`

### Out of Scope

- No new tabs or tab reordering
- No changes to `BaseWindow`, `GlassCard`, `AvatarWidget`, `DataField`, `BadgeChip` (these are already correct)
- No changes to scraper or OCR

## Acceptance Criteria

DossierTab: all GlassCard sections (Identity, Profile Data, Biography, Accreditations, Organizations) render with real scraped dataDossierTab: badges wrap correctly at narrow widths (WrapLayout working)DossierTab: avatar and badge images refresh after download without full re-populateDossierTab: RSI brand icon decoration visible in identity cardOrgTab: manufacturer logo decoration appears for known SC manufacturersOrgTab: candidate picker dialog appears and works for ambiguous org name searchesArchivesTab: badges in detail pane wrap correctlyArchivesTab: org cards in detail pane are not clipped (no fixed height)SettingsTab: all 7 sections visible and all controls save correctlySearchTab: mode toggle visually updates (active button style changes)NavSidebar: active item has stronger glow (3px accent bar, higher alpha background)No hardcoded hex color values in any widget code (all from palette.py)