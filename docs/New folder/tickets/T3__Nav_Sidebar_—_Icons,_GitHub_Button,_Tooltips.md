# T3: Nav Sidebar — Icons, GitHub Button, Tooltips

## Purpose

Wire all five nav tab icons to their correct asset paths, fix the bottom GitHub button so it opens the browser without crashing, and add tooltips to every nav element.

## Scope

**In:**

- file:src/ui/widgets/nav_sidebar.py
- All five tab icon assignments (Search → `icon_search.svg`, Dossier → `FOIP.png`, Org → `SHLD.png`, Archive → `JOURNAL.png`, Settings → `icon_settings.svg`)
- GitHub button at bottom: icon = `!.png`, action = `webbrowser.open("https://github.com/pinkgeekpdx")`, no crash
- Tooltips on all six nav elements (see Core Flows Flow 3 for exact tooltip text)
- Active state: 3px left accent bar + background highlight
- Hover state: horizontal gradient highlight from left

**Out:**

- No changes to tab content areas (covered in T4)

## Acceptance Criteria

- All five tab icons display correctly in both dev and packaged runtime
- Clicking the GitHub button opens `https://github.com/pinkgeekpdx` in the default browser and does not crash or navigate within the app
- GitHub button icon is `!.png`
- All six nav elements have tooltips matching the text in spec:f092360a-c39e-41e6-ab6b-19c17741aaa7/4bc76e92-227f-41fb-9aca-1911c2e8ea27 Flow 3
- Active and hover states are visually distinct