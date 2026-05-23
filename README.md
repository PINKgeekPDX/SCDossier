# SC Dossier

> A high-fidelity Star Citizen companion app — retrieve, inspect, archive, and export player and organization dossiers from the RSI website, without ever leaving your game session.

![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11%20%7C%20Linux-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Framework](https://img.shields.io/badge/UI-PyQt6-brightgreen)
![Status](https://img.shields.io/badge/status-In%20Development-yellow)

---

## Overview

**SC Dossier** is a standalone desktop tool for Star Citizen players. It runs quietly in your system tray as a compact edge-snapped overlay toolbar while you play. When you want to look up a player or org, one click expands into the full dossier interface.

### Key Features

- **Always-available overlay toolbar** — snaps to any screen edge, stays topmost, minimal footprint
- **OCR screen capture** — click the capture button, drag a box over any visible player name on screen, and instantly search their dossier
- **Player dossier lookup** — scrapes all real obtainable data from RSI: handle, moniker, enlist date, location, bio, fluency, avatar, badges, and all affiliated organizations
- **Organization lookup** — search orgs by name or SID; view full org details, archetype, focus, commitment, and member roster
- **Archive system** — save player profiles locally for persistent offline access
- **Auto-sync** — archived profiles can be checked against live RSI data and updated
- **Profile export** — export any archived profile to a ZIP (JSON, TXT, self-contained HTML card, all images)
- **System tray presence** — full context menu for quick access to all features

---

## Design Aesthetic

SC Dossier uses the **Aegis Liquid Interface** design system — a deep-space glassmorphism aesthetic with layered translucency, neon glow-states, tech-bracket corner ornaments, and Sora/Inter/JetBrains Mono typography. The visual language evokes a high-tech shipboard HUD rather than a standard desktop application.

---

## Requirements

- Python 3.11 or higher
- Windows 10/11 or Linux (Debian/Ubuntu/Mint/Arch)
- Internet connection for live RSI data retrieval

---

## Installation (From Source)

```bash
# Clone the repository
git clone https://github.com/your-repo/SCDossier.git
cd SCDossier

# Create virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python scripts/run_dev.py
```

---

## Installation (Pre-built Binary)

Download the latest release from the Releases page:

- **Windows**: `SCDossier-windows.zip` → extract and run `SCDossier.exe`
- **Linux (Debian/Ubuntu/Mint)**: `SCDossier.deb` → `sudo dpkg -i SCDossier.deb`
- **Linux (Arch)**: See `build/linux/arch/` for PKGBUILD

---

## Usage

### Overlay Toolbar

The toolbar appears snapped to the left edge of your screen by default. You can drag it to any edge position. Two buttons:

1. **Expand** `[≡]` — opens the main SC Dossier window
2. **Capture** `[⊕]` — enters OCR region-select mode for in-game player name lookup

### Main Window

Left navigation tabs:

| Tab | Purpose |
|---|---|
| **Search** | Choose player or org search, enter query |
| **Dossier** | Full player profile display |
| **Organization** | Standalone org lookup and display |
| **Archive** | Browse, sync, export, or delete archived profiles |
| **Settings** | Configure all app behavior and preferences |

### System Tray

Right-click the tray icon for quick access to: Show Toolbar, Open Dossier, Quick Capture, Settings, Quit.

---

## Data & Privacy

All data is retrieved directly from public RSI website pages. No credentials are required. All cached data is stored locally:

- **Windows**: `%USERPROFILE%\Documents\PINK\SCDossier\`
- **Linux**: `~/Documents/PINK/SCDossier/`

No data is sent to any third-party service. The OCR engine runs entirely locally.

---

## Project Structure

```
src/            Application source code
scripts/        Dev runner and utility tools
build/          Build scripts for each platform
built/          Compiled distribution outputs
docs/           Documentation and work tracking
logs/           Dev/tool script output logs
```

See `docs/documentation/` for full documentation.

---

## Contributing

See `agent.md` for agent-specific instructions and architecture context.

---

## License

MIT License — see `LICENSE` for details.
