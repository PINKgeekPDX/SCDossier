# SC Dossier — User Guide

## What is SC Dossier?

SC Dossier is a Star Citizen companion desktop application that lets you look up player and organization information from the RSI website while you play the game — without alt-tabbing to a browser.

---

## Getting Started

Launch SC Dossier. It will appear as:
1. A small toolbar snapped to the left edge of your screen
2. A system tray icon in your taskbar/notification area

---

## The Overlay Toolbar

The toolbar is always visible while SC Dossier is running. It snaps to a screen edge and stays on top of all other windows, including your game.

**Positioning:** Click and drag the toolbar to any edge of any connected monitor. It will automatically snap flush to the nearest edge when you release. Your position is saved between sessions.

**Two buttons:**

| Button | Action |
|---|---|
| `≡` Expand | Opens the SC Dossier main window |
| `⊕` Capture | Enters OCR screen capture mode for in-game lookups |

---

## OCR Screen Capture

The capture feature lets you look up a player without typing their name.

1. Click the `⊕` button on the toolbar
2. Your screen dims and the cursor becomes a crosshair
3. Click and drag to draw a box around the player's name visible on your screen
4. Release — SC Dossier extracts the text and immediately searches for that player's dossier
5. Press `Escape` at any time to cancel

**Tips:**
- Works best when the player name is clearly readable and not overlapping other text
- If extraction fails, a dialog will explain the issue — you can then type the name manually

---

## Main Window

Click the expand button or the tray icon to open the main window.

### Title Bar Controls

| Control | Behavior |
|---|---|
| **Pin** `📌` | Forces window to stay on top; disables auto-hide while pinned |
| **Hide** `✕` | Collapses back to toolbar; app continues running in tray |

The main window has no normal close button. To fully exit, use the system tray menu → **Quit**.

---

## Search Tab

The default view on first open each session.

1. Choose **SEARCH PLAYER** or **SEARCH ORG**
2. Type the player handle or org name/SID
3. Click **INITIATE SEARCH**

**Search Player** — navigates to the Dossier tab and loads the player's profile  
**Search Org** — navigates to the Organization tab and loads the org's profile

If a player is already archived locally, their data is loaded from disk first. You'll be prompted if a sync check is needed.

---

## Dossier Tab

Displays full player profile information retrieved from RSI:

- **Identity Core**: Avatar image, handle, moniker, enlist date, location, bio, fluency
- **Accreditations & Clearances**: All badge images and names
- **Primary Affiliation**: Main org logo, name, SID, player rank
- **Affiliated Organizations**: All associated orgs (if more than one)

**Action buttons:**
- `ARCHIVE PROFILE` — saves this profile to your local archive
- `SYNC` — re-scrapes live RSI data and updates archived profile
- `EXPORT` — exports profile to a ZIP on your Desktop

---

## Organization Tab

Displays standalone org information from RSI:

- Org logo, name, SID, archetype
- Focus tags, language, commitment level
- Recruiting and roleplay status
- Member count
- Member roster preview

---

## Archive Tab

Browse all locally saved player profiles.

**List pane (left):**
- Filter by name using the search box
- Sort by name (A-Z / Z-A), date archived, or last synced
- Click `▶` to collapse the list and give the detail pane more space

**Per-profile actions:**
- `SYNC CHECK` — checks if the live RSI profile has changed; offers to update
- `DELETE` — permanently removes the archived profile and all its files
- `EXPORT ZIP` — creates a ZIP on your Desktop with all profile data and a stylized HTML card

---

## Settings Tab

All settings auto-save when changed.

| Section | Options |
|---|---|
| Appearance | Accent color override, font size scale |
| Scraper | Request delay, User-Agent string |
| OCR | Engine (EasyOCR / Tesseract), confidence threshold |
| Cache | Auto-clear temp cache, max age limit, open cache folder |
| Sync | Auto-sync toggle, sync interval, sync on archive load |
| Toolbar | Edge preference, toolbar opacity |
| Paths | Display-only view of all data directories |
| About | App version and links |

---

## System Tray Menu

Right-click the tray icon for:
- **Show Toolbar** — restores the overlay toolbar if hidden
- **Open Dossier** — shows main window on the Dossier tab
- **Quick Capture** — starts OCR capture mode directly
- **Settings** — shows main window on the Settings tab
- **Quit** — fully exits SC Dossier

---

## Data Location

All app data is stored in your Documents folder:

**Windows:** `%USERPROFILE%\Documents\PINK\SCDossier\`  
**Linux:** `~/Documents/PINK/SCDossier/`

Subfolders:
- `Config/` — settings.json
- `Logs/` — app.log
- `Cache/Temp/` — recently looked-up player data (not archived)
- `Cache/Archived/` — permanently saved player profiles
