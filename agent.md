# AGENTS.md — SC Dossier

> Instructions for AI agents, automated pipelines, and coding assistants working on this project.

---

## Project Identity

- **App name**: SC Dossier
- **Language**: Python 3.11+
- **UI Framework**: PyQt6 (non-negotiable — do not substitute)
- **Target platforms**: Windows 10/11 and Linux only
- **Purpose**: Star Citizen companion app for RSI player/org dossier retrieval, display, archive, sync, and export

---

## Law Document

The finalized implementation plan is located at:

```
docs/work/todo/read-3rd-finalized-dev-tasks-stepbystep-allphases-must-follow.md
```

This is the authoritative task-by-task specification. When in doubt, this document is law. All phase ordering and module definitions come from it.

---

## Project Root

```
C:\Users\Administrator\Desktop\projects\SCDossier\
```

---

## Critical Directory Rules

| Content | Location |
|---|---|
| Application source code | `src/` |
| Dev runner scripts | `scripts/` |
| Single-use tools/pipelines | `scripts/tools/` ONLY — never project root |
| Build scripts | `build/{platform}/` |
| Built dist output | `built/dist/{platform}/` |
| Dev/test logs | `logs/` (project-level, not root) |
| Finalized docs | `docs/documentation/` |
| Work tracking docs | `docs/work/` |
| Root-level files | `README.md`, `agent.md`, `requirements.txt`, `SCDossier.spec` only |

**Never** generate scripts, tools, or log files into the project root.

---

## Runtime Data Paths

All runtime data uses the user's Documents folder, not the project directory.

**Windows:**
```
%USERPROFILE%\Documents\PINK\SCDossier\Config\settings.json
%USERPROFILE%\Documents\PINK\SCDossier\Logs\app.log
%USERPROFILE%\Documents\PINK\SCDossier\Cache\Temp\{handle}\
%USERPROFILE%\Documents\PINK\SCDossier\Cache\Archived\{handle}\
```

**Linux:**
```
~/Documents/PINK/SCDossier/Config/settings.json
~/Documents/PINK/SCDossier/Logs/app.log
~/Documents/PINK/SCDossier/Cache/Temp/{handle}/
~/Documents/PINK/SCDossier/Cache/Archived/{handle}/
```

`PathManager` in `src/core/paths.py` is the single source of truth for all runtime paths. Always use it — never hardcode paths.

---

## Architecture Rules

### Layer Boundaries

```
core/       →  NO PyQt6 imports (pure Python, platform-independent)
services/   →  May use QThread/QThreadPool but no UI widgets
ui/         →  May import from core/ and services/; no circular deps
app/        →  May import everything; final wiring point
```

### Event System

All cross-component communication uses signals defined in `src/core/events.py`. Do not call UI methods directly from services. Emit signals; let the controller wire them.

### Do Not Break Separation
- `core/` must have zero PyQt6 widget imports
- `services/` must never import from `ui/`
- Tab widgets must not directly call scraper methods — route through signals → controller → service

---

## Data Sources & Scraping Rules

- **Scraping**: Use **pure HTML scraping** (`requests` + `BeautifulSoup` + `lxml`) for RSI pages.
- **Backend API**: The Community Reputation System uses **Supabase** (Edge Functions and Database). Uses `supabase-py` client.
- Target URLs (never hardcode these — use constants from `src/app/constants.py`):
  - `https://robertsspaceindustries.com/en/citizens/{handle}`
  - `https://robertsspaceindustries.com/en/citizens/{handle}/organizations`
  - `https://robertsspaceindustries.com/en/orgs/{sid}`
  - `https://robertsspaceindustries.com/en/community/orgs/listing`
- Only extract fields that actually exist on the live RSI pages
- Never invent or mock data fields — use `None` for missing optional data
- Org SID resolution: use listing page with `?search=` param; present picker if ambiguous

---

## UI Design Rules

The design system is **Aegis Liquid Interface** (see `ui-example-files/DESIGN.md`).

- Always use `GlassCard` as the primary container panel
- Always use `DataField` for label+value pairs
- Always use `AvatarWidget` for image display with tech-bracket overlay
- Global QSS applied via `src/ui/theme/stylesheet.py` at startup
- Color constants from `src/ui/theme/palette.py` only — no hardcoded hex values in widget code
- Fonts registered via `src/ui/theme/fonts.py` — Sora, Inter, JetBrains Mono

---

## Testing Reference

Test RSI handles for scraper validation:
- **Player**: `PINKgeekPDX` — `https://robertsspaceindustries.com/en/citizens/PINKgeekPDX`
- **Organization**: `THEKVLT` — `https://robertsspaceindustries.com/en/orgs/THEKVLT`

---

## Documentation Rules

- All documentation files must use `.md` extension
- Finalized docs → `docs/documentation/`
- Work/todo/summaries/reports → `docs/work/`
- Do not generate docs into `src/` or project root (except README.md and agent.md)

---

## Dependency Rules

Locked dependency set (do not add without reason):
- `PyQt6`
- `requests`
- `beautifulsoup4`
- `lxml`
- `Pillow`
- `easyocr`
- `pyinstaller`
- `supabase`

Do not add `pystray` — tray is handled by `QSystemTrayIcon` natively.
Do not add `pytesseract` unless specifically implementing Tesseract fallback path.

---

## Code Style

- Python 3.11+ syntax; use type hints on all public methods
- PEP 8 compliance
- Docstrings on all classes and public methods
- No logic in `__init__.py` files (re-exports are fine)
- Prefer composition over inheritance except for PyQt6 widget subclassing
