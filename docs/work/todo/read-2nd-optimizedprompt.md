# SC Dossier — Optimized Master Development Prompt

@Multi-Model Planner @dignified-python

You are the lead planning, architecture, and implementation agent for a serious desktop software project.

Your task is to initiate, plan, structure, and begin building a production-minded standalone desktop application named **SC Dossier**. You must preserve the intent and critical detail of the full specification below while improving clarity, execution order, technical rigor, maintainability, and the chances of a high-quality end result.

Do not dilute, ignore, or replace requirements with generic assumptions. Treat the specification as a real product brief for long-term development. When details are ambiguous, resolve them conservatively and document the decision. When details are in tension, prioritize maintainability, realism, cross-platform stability, and strict alignment with the stated product goals.

## Core Objective

Build **SC Dossier**, a standalone **Python** desktop companion app for **Star Citizen** that supports **Windows 10/11** and **Linux only**. The app’s purpose is to retrieve, display, cache, archive, sync, and export dossier information for **players** and **organizations** from the RSI website, while providing a compact, always-available overlay experience suitable for use while a player is actively in-game.

The app must feel like a polished desktop tool, not a rough prototype.

## Primary Technical Direction

- Language: **Python**.
- UI framework: strongly prefer **PyQt6** unless a thoroughly justified technical evaluation proves another choice is superior. Tkinter or Pygame should not be chosen casually. If another framework is selected, explain exactly why it is better for this product.
- The UI must be rich, highly styled, visually cohesive, and capable of custom chrome, animation, advanced layouts, tray behavior, overlays, and persistent topmost edge-snapped interaction patterns.
- The implementation should use a layered architecture with clear separation between UI, application state, models, services, scraping, OCR, persistence, exporting, platform integration, and tests.

## Product Behavior Overview

SC Dossier has two major visible application states:

1. **Default overlay toolbar state**.
2. **Expanded main window state**.

The overlay toolbar is the app’s default presence while the user is playing Star Citizen. It is intentionally compact, low-profile, and always available.

The expanded main window is the richer working interface used to search, inspect, archive, sync, export, configure settings, and browse stored dossiers.

The app must also maintain a **system tray icon with context menu presence at all times while running**.

## Overlay Toolbar Requirements

The overlay toolbar is a non-negotiable core interaction model.

- It must be a **small overlay slip-toolbar** that attaches/snaps to a screen edge.
- It must remain **always snapped to a screen edge**.
- The user must be able to choose its exact position along that edge.
- The user must be able to pin it to the desired position.
- It must remain **topmost**.
- Its default role is to remain quietly available while the user is in-game.
- It must contain **exactly two buttons**.
- The two buttons must use high-quality SC-style icons.

### Toolbar Button 1 — Expand / Open Main Window

This button expands the toolbar outward from its snapped position into the main application window.

Behavior:
- Clicking it should show the main window.
- When the main window is shown, the toolbar should hide.
- When the main window is later hidden/collapsed, the toolbar becomes visible again.

### Toolbar Button 2 — Snapshot OCR Capture Mode

This button initiates a screen capture workflow for extracting a visible player name from the screen.

Behavior:
- Enter a focused snapshot mode.
- Allow the user to click and drag anywhere on screen to define a rectangular capture region.
- Capture the selected screen region.
- Store the capture temporarily.
- Run a local OCR or text extraction service on the captured image.
- Attempt to extract the player name text string.
- If extraction fails or no usable text is found, show a clear dialog explaining the issue.
- If extraction succeeds, use the extracted string as an alternative to manually typing a player name into search.

This feature is specifically intended so that while the user is in-game, they can capture a visible player name from the screen and immediately search for that player’s dossier.

## OCR Search Workflow

The OCR-driven flow should behave like this:

1. User clicks the snapshot button on the toolbar.
2. App enters region selection capture mode.
3. User click-drags to define the exact region of the visible player name.
4. App takes the screenshot of that region.
5. App stores the image temporarily.
6. App runs local OCR/text extraction.
7. If OCR fails, display a dialog and stop gracefully.
8. If OCR succeeds:
   - Hide toolbar.
   - Open/show main window.
   - Navigate to the relevant search flow.
   - Insert the extracted player name into search.
   - Before running live scraping, check whether the player is already archived locally.
   - If found in archive, load the archived information first, then check the live site to determine whether a sync/update is needed.
   - If not archived, retrieve live data into temp cache and populate the UI.

Manual typed player search should follow the same downstream logic, just without the screen capture and OCR steps.

## Main Window Requirements

The main window must use a **fully custom title bar** and **custom status bar**.

### Title Bar / Window Chrome Rules

- Do **not** use the typical OS window controls in the title bar.
- The window must be draggable via the custom title bar.
- The window must be resizable.
- It must have minimum and maximum size constraints.
- It must **not** be maximizable.
- It must **not** expose a normal exit/close control in the main custom title bar.
- Instead, it must provide:
  - **Pin button**.
  - **Hide button**.

### Pin Button Behavior

- Pin forces the main window to remain topmost.
- While pinned, the window must not be collapsible back to the toolbar.
- This must be enforced clearly and predictably.

### Hide Button Behavior

- Hide collapses and hides the main window.
- Once hidden, the toolbar becomes visible again.
- This returns the app to its default overlay state.

### Navigation / Layout

- The main window must use a **left-side navigation bar** that functions like tabs.
- It must retain the visual style and UX direction described in the provided UI example materials.
- It should maintain the most recently used tab/content state when the window is hidden and reopened during the same session, except on the first open of a session where Search is the default.

## Main Window Sections / Tabs

The main window must include the following major areas:

1. **Search**
2. **Dossier**
3. **Organization**
4. **Archive**
5. **Settings**

### Search

This is effectively the starting action area and should appear at the top of the nav.

Behavior:
- On first main-window open of an app session, **Search** should be the default visible tab.
- Search presents two choices:
  - **Search Player**
  - **Search Organization**

#### Search Player Flow
- Selecting Search Player should route the user into the **Dossier** workflow.
- Instead of showing normal dossier detail elements initially, the Dossier area should temporarily show the player search UI: search box, controls, and progress state.
- After the search is performed and data is retrieved, the search-state UI should be replaced by the actual dossier display UI.

#### Search Organization Flow
- Selecting Search Organization should route the user into the **Organization** workflow.
- Instead of showing normal organization detail elements initially, the Organization area should temporarily show the org search UI: search box, controls, and progress state.
- After the search is performed and data is retrieved, the search-state UI should be replaced by the actual organization display UI.

### Dossier

This tab must display only **realistic, real, obtainable, actually scraped data** for a player from RSI sources.

Requirements:
- Only show details that truly exist and can actually be retrieved.
- Include real downloaded images where available, such as avatar, badges, org logo, and other real dossier-visible assets.
- Also show associated org information gathered for that player.
- If more than one org is associated and retrievable, the UI must account for displaying those org details clearly.
- Do not invent fields or mock content beyond clearly labeled loading/empty/error states.

### Organization

This tab must display only **realistic, real, obtainable, actually scraped data** for organizations from RSI sources.

Requirements:
- It is specifically for standalone organization lookup and display.
- It must not present fake or assumed fields.
- It should use temp data for standalone org searches.

### Archive

This tab is for archived **player** profiles.

Requirements:
- Use a **two-pane layout**.
- Left pane: archive list.
- Right pane: dossier-style details for the selected archived player.
- Left pane should support being collapsed or shrunk so the right pane can use more space.
- Archive list should be clean, readable, intuitive, filterable, and sortable.
- Selecting an archived player in the list should populate the right pane with all stored details and media.

Per-profile archive actions must include:
- Sync check / update.
- Delete archived profile and all associated files.
- Extract/export archived profile into a zip placed on the desktop.

Export zip contents should include at minimum:
- Avatar.
- Other relevant stored media.
- A text file containing player information and associated org information.
- A standalone stylized HTML page using the media and JSON in the zip to display a clean profile card/view.
- Structured JSON.
- Other useful output formats where sensible, such as CSV or TXT.

### Settings

The app must include a **comprehensive settings tab**.

Requirements:
- Settings should be broad and practical.
- Changes should auto-save.
- Changes should apply immediately wherever reasonable.
- Settings must include persistent handling of UI state, geometry, toolbar placement, behavior preferences, logging, cache/archive behaviors, OCR behavior, export preferences, and any other meaningful app configuration.

## App Purpose and Domain Scope

The primary job of SC Dossier is to retrieve information about:
- **Players**.
- Their **associated org details**.
- **Organizations**.

The app must give users ways to:
- Search live data.
- View live data in-app.
- Cache data temporarily.
- Archive player profiles for later viewing.
- Auto-sync or sync-check archived profiles so changes on the live RSI site can update archived data.
- Export retrieved or archived information in practical formats such as JSON, TXT, HTML, CSV, or other formats only where they genuinely make sense.

## Scraping System Requirements

A highly capable internal scraping core is required.

You must build sophisticated services for:
- Player dossier scraping.
- Associated player-org scraping.
- Standalone organization scraping.
- Media gathering/downloading.
- Temp cache management.
- Archived profile materialization.

### Player Scraping

The player scraper must gather all realistically obtainable details from the RSI dossier pages, including but not limited to:
- Player text details.
- Badge images.
- Org-related images.
- Player avatar images.
- Achievement-like visible assets if actually present and obtainable.
- Any other real dossier-visible media or metadata that can actually be scraped reliably.

This data should be placed into a **temp cache organized by player name** for immediate UI population.

If the user chooses to archive a profile, the app must then transform that temp gathered information into a persistent archive directory organized by player name, including:
- A profile JSON containing the stored text details.
- Downloaded player-related media.
- Associated org media/details that belong with the player dossier archive.
- Any other retrieved assets needed to recreate the dossier UI from local data.

### Associated Org Scraping for Player Dossiers

When a player dossier is retrieved, the associated org details and images gathered as part of that player dossier are part of the player dossier flow.

These associated org details:
- Must be handled in temp cache.
- Must also be persisted with archived player profiles where relevant.
- Must be displayed inside the dossier presentation where appropriate.

### Standalone Organization Scraping

A separate scraping service must exist for standalone organization lookups.

Important distinction:
- Standalone org lookups are **not** the same thing as player dossier associated-org retrieval.
- Standalone org searches should use temp storage for the purpose of retrieval and UI display.
- Standalone org results should **not** be archived as standalone archive entries.

## RSI URLs to Target

The scraping and retrieval system must focus on these live RSI sources:

### Player dossier
`https://robertsspaceindustries.com/en/citizens/<playername>`

### Player associated orgs
`https://robertsspaceindustries.com/en/citizens/<playername>/organizations`

### Organization page
`https://robertsspaceindustries.com/en/orgs/<org-sid>`

### Organization listing / ledger reference
`https://robertsspaceindustries.com/en/community/orgs/listing`

## Required Live Analysis and Validation Targets

You must deeply inspect the actual site structure and data reality before making assumptions about what fields exist or how scraping should work.

Use these provided live references for deep analysis, validation, and testing:

### Player dossier reference
`https://robertsspaceindustries.com/en/citizens/PINKgeekPDX`

### Organization reference
`https://robertsspaceindustries.com/en/orgs/THEKVLT`

### Organization listing reference
`https://robertsspaceindustries.com/en/community/orgs/listing`

You must thoroughly examine the real obtainable site data so you truly understand:
- What is actually available.
- What is not actually available.
- What can be extracted reliably.
- What media assets can be downloaded.
- What selectors, structures, page patterns, and anti-fragile parsing approaches are appropriate.

Do not fake completeness. Verify what the site truly exposes.

## Organization Search UX Constraint

The org page expects an **org SID**, but users should not be forced to know the SID in order to search.

The organization search experience must be designed so users can search intuitively by:
- Org name.
- Org SID.

You must carefully analyze and propose the best strategy for this, which may involve using the org listing/ledger or another practical discovery/indexing approach to resolve an org name into a SID.

## UI Design / Theme Direction

The UI, theming, layout style, content presentation, effects, and animations must be heavily influenced by the provided example files.

Reference location:
`C:\Users\Administrator\Desktop\projects\SCDossier\ui-example-files`

This location includes an `image.png` for visual examination.

You must study these examples as influence material for:
- look/style/theme,
- content layout,
- effects,
- animations,
- title bar treatment,
- status bar treatment,
- side navigation behavior,
- dialogs,
- warning messages,
- buttons,
- widgets,
- overlay/toolbar treatment,
- overall UX consistency.

The example UI may use a different framework than the one selected for this project. That does **not** reduce its importance. Recreate its design language and intent in the chosen desktop framework in a production-minded way.

The design language must be used consistently across the entire application and all UI/UX surfaces.

## Project Workspace and Directory Rules

Project root:
`C:\Users\Administrator\Desktop\projects\SCDossier`

Source root:
`C:\Users\Administrator\Desktop\projects\SCDossier\src`

The codebase containing application code, UI, assets, and tests must be created under the source structure in a clean, common-sense, industry-standard, intuitively organized way.

### Documentation destinations
All finalized documentation, app instructions, readmes, wikis, and related docs:
`C:\Users\Administrator\Desktop\projects\SCDossier\docs\docuuumentation`

All work-related documentation:
`C:\Users\Administrator\Desktop\projects\SCDossier\docs\work`

Todo docs:
`C:\Users\Administrator\Desktop\projects\SCDossier\docs\work\todo`

Summaries:
`C:\Users\Administrator\Desktop\projects\SCDossier\docs\work\summaries`

Reports:
`C:\Users\Administrator\Desktop\projects\SCDossier\docs\work\reports`

### Build script destinations
Windows build scripts:
`C:\Users\Administrator\Desktop\projects\SCDossier\build\windows`

Linux build scripts:
`C:\Users\Administrator\Desktop\projects\SCDossier\build\linux\<distro>\`

### Built output destinations
Windows dist output:
`C:\Users\Administrator\Desktop\projects\SCDossier\built\dist\windows`

Linux dist output:
`C:\Users\Administrator\Desktop\projects\SCDossier\built\dist\linux\<distro>\`

### Script/tool placement rules
All specific-purpose, single-case-use, or special tools/pipelines must be generated **only** here:
`C:\Users\Administrator\Desktop\projects\SCDossier\scripts\tools\`

Do **not** generate those into the project root.

General runner/debug scripts for starting the app from source during development may be placed here:
`C:\Users\Administrator\Desktop\projects\SCDossier\scripts\`

### Dev/test logs location
All logs generated by dev tools, helper scripts, or tests must go here:
`C:\Users\Administrator\Desktop\projects\SCDossier\logs\`

### Root-level files allowed
Project files, spec files, repo `README.md`, and `AGENTS.md` may be generated at project root:
`C:\Users\Administrator\Desktop\projects\SCDossier\`

## Runtime Data Locations

All runtime data handling must be consistent throughout the app. Windows-style paths below define the intended pattern; Linux must use equivalent platform-appropriate paths.

### Main settings
`Users\<user>\Documents\PINK\SCDossier\Config\`

### App runtime logs / error logs
`Users\<user>\Documents\PINK\SCDossier\Logs\`

### Temp player profile cache
`Users\<user>\Documents\PINK\SCDossier\Cache\Temp\<playername>\<image-name>.png`

`Users\<user>\Documents\PINK\SCDossier\Cache\Temp\<playername>\<extracted-text-info>.json`

### Archived player profile cache
`Users\<user>\Documents\PINK\SCDossier\Cache\Archived\<playername>\<image-name>.png`

`Users\<user>\Documents\PINK\SCDossier\Cache\Archived\<playername>\<extracted-text-info>.json`

The application must be absolutely consistent in how it uses these locations.

Persist at minimum:
- Settings values.
- Main window size and position.
- Toolbar overlay position and snapped edge placement.
- Pinned state and relevant show/hide/expand/collapse states where appropriate.
- Temp cache metadata.
- Archive metadata.
- Last-used tab/content where appropriate.

## Documentation Rules

- All documentation files must use `.md`.
- Finalized docs, instructions, readmes, wikis, reports, roadmaps, and project documentation should be written in clear structured Markdown.
- Work tracking, todos, summaries, and reports should also use `.md`.

## Engineering Standards

### Architecture
Use a modular, maintainable architecture with strong boundaries between concerns such as:
- app/bootstrap,
- UI,
- core models,
- shared utilities,
- services,
- scraping,
- OCR,
- storage,
- exporting,
- platform integration,
- settings,
- logging,
- tests.

### Data Modeling
Create explicit typed models for the major concepts such as:
- player dossiers,
- organization details,
- associated org summaries,
- scraped media assets,
- OCR results,
- archive entries,
- sync status,
- search requests/results,
- settings,
- cache manifests.

### Scraper Quality
The scraper must be:
- precise,
- resilient,
- realistic,
- testable,
- maintainable,
- based on actual verified site structure,
- careful about downloaded assets,
- explicit about what belongs to temp cache versus archive.

### Error Handling
- Never fail silently.
- Separate developer logs from user-facing messages.
- Gracefully handle OCR failure, network failure, missing fields, HTML changes, partial data retrieval, asset download failures, archive corruption, export failures, and sync conflicts.

### Testing
Include a practical plan and implementation structure for testing:
- scraper parsing,
- media gathering,
- OCR pipeline behavior,
- archive storage/load consistency,
- sync logic,
- export packaging,
- UI smoke tests,
- path handling on Windows and Linux.

## Required Initial Work Sequence

You must begin the project in a disciplined order.

### Phase 1 — Understand and Restate
1. Restate the product clearly as an engineering brief.
2. Extract all functional requirements.
3. Extract all UX/UI requirements.
4. Extract all filesystem/path rules.
5. Extract all scraping/data constraints.
6. Extract all archive/export/sync rules.
7. Identify ambiguities or risk areas.

### Phase 2 — Technical Assessment
1. Recommend the UI/application framework stack, with justification.
2. Assess PyQt6 first and explain why it is or is not the correct choice.
3. Inspect the provided UI example files and summarize the design language to preserve.
4. Deeply inspect the RSI player, player-org, org, and org-listing pages to determine actual obtainable data and realistic scraper design constraints.

### Phase 3 — Architecture and Structure
1. Produce a full architecture plan.
2. Propose the source tree under `src`.
3. Define the major modules and services.
4. Define the data models.
5. Define temp-cache and archive flows.
6. Define the OCR flow.
7. Define the search flows.
8. Define the sync/update flow.
9. Define the export flow.
10. Define logging and settings persistence strategy.

### Phase 4 — Documentation and Planning Outputs
Generate early-project documents such as:
- root `README.md`,
- root `AGENTS.md`,
- project specification,
- architecture document,
- scraper analysis report,
- UI design interpretation document,
- implementation roadmap,
- todo/work tracking documents,
- technical reports or summaries where helpful.

Place each file in the correct required project location.

### Phase 5 — Controlled Scaffolding
Only after the plan is solid:
- create foundational project scaffolding,
- create directory structure,
- establish base app bootstrap,
- establish models and service interfaces,
- establish logging/settings foundations,
- establish UI shell,
- establish tray and overlay architecture,
- establish scraper and OCR service contracts,
- begin implementation incrementally.

Do not jump straight into monolithic coding.

## Important Behavioral Rules for the Agent

- Preserve the full intent of the specification.
- Do not remove important constraints just because they add complexity.
- Do not invent RSI fields that are not actually obtainable.
- Do not overbuild speculative features before confirming data reality.
- Keep player dossier flow and standalone organization flow clearly separated.
- Keep temp cache and archive responsibilities clearly separated.
- Prefer conventional naming and maintainable structure.
- Avoid dumping logic into oversized files.
- Prefer clean interfaces, typed models, reusable services, and testable modules.
- Use platform-appropriate path handling on Linux rather than blindly copying Windows paths.
- Be explicit about assumptions, tradeoffs, and design decisions.
- Produce concrete outputs, not vague commentary.

## Final Required Output Style

Start by producing, in order:
1. A concise but complete engineering brief.
2. A recommended stack and framework justification.
3. A realistic architecture proposal.
4. A proposed source-tree layout.
5. A scraper/data-acquisition analysis plan.
6. A phased implementation roadmap.
7. A risk/unknowns list with mitigations.
8. A documentation generation plan.

Then begin the project in a controlled, production-minded way.
