# T4: Tab Content Polish — Search, Dossier, Org, Archive

## Purpose

Polish all four content-area tabs: remove stale text, apply consistent animated input styling, replace button labels with icon-only buttons, and enhance the Archive list with hover effects and compact controls.

## Scope

**In:**

**Search tab** (file:src/ui/tabs/search_tab.py):

- Remove any remaining "Aegis Liquid Interface RSI Network Access" text
- `USER.png` (48×48) + spacing + "CITIZEN DOSSIER" label (underlined, larger, glow effect)
- `StyledToggleButton` mode switcher (Player / Org) — active = filled blue gradient, inactive = ghost outline, hover = subtle glow
- `AnimatedSearchInput` — border paint animation on focus, color change on hover, cursor visible when typing
- Initiate button: icon-only `RIGHT.png` with consistent hover/press states
- Hint row: `info.png` (16×16) + "Enter player name or RSI dossier URL to find information"

**Dossier tab** (file:src/ui/tabs/dossier_tab.py):

- Apply `AnimatedSearchInput` focus/hover border effects to the action bar search input
- Search button: icon-only `icon_search.svg`
- Archive button: icon-only `icon_save.svg`; tooltip updates when enabled/disabled

**Org tab** (file:src/ui/tabs/org_tab.py):

- Apply `AnimatedSearchInput` focus/hover border effects to the action bar search input
- Search button: icon-only `icon_search.svg`

**Archive tab** (file:src/ui/tabs/archives_tab.py):

- `StyledFilterInput` — compact (h=32), hover/focus border animation
- `StyledComboBox` — compact (h=28), correct popup behavior
- `StyledArchiveList` — each row: avatar + moniker + handle + date; hover highlight
- Sync button: icon-only `Refresh.png`
- Export button: icon-only `icon_file.svg`
- Delete button: icon-only `No_Access.png` (from `Icons/` not `ships/default/`)

**Out:**

- Tooltip pass is T8
- Settings tab is T6
- Image preview is T5

## Acceptance Criteria

- No "Aegis Liquid Interface RSI Network Access" text visible anywhere in the Search tab
- All three tabs (Dossier, Org, Search) use visually consistent animated search inputs with focus border animation and hover color change
- All action buttons across all four tabs are icon-only with consistent hover/press states
- Archive list rows show avatar + moniker + handle + date with hover highlight
- Filter input and sort dropdown are compact and functional
- All icon paths resolve correctly in both dev and packaged runtime