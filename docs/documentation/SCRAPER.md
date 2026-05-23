# SC Dossier — Scraper Field Reference

> Documents all fields actually obtainable from RSI website pages.  
> Do not add fields that do not exist on these pages.

---

## Player Dossier

**Source URL:** `https://robertsspaceindustries.com/en/citizens/{handle}`

| Field | Key | Type | Notes |
|---|---|---|---|
| Handle | `handle` | `str` | RSI login handle; extracted from page title or handle label |
| Moniker | `moniker` | `str` | Display name; extracted from page title (format: `Moniker \| Handle`) |
| Enlist Date | `enlisted` | `str` | "Enlisted" label section; ISO-ish date string |
| Location | `location` | `str \| None` | Optional; only present if player set it publicly |
| Bio | `bio` | `str \| None` | Optional; only present if player wrote one |
| Fluency | `fluency` | `list[str]` | List of language names from "Fluency" section |
| Avatar URL | `avatar_url` | `str` | Profile image URL from RSI CDN |
| Avatar Local | `avatar_local` | `str` | Local path after download |
| Badges | `badges` | `list[dict]` | See badge schema below |
| Page URL | `page_url` | `str` | The canonical RSI citizen page URL |
| Scraped At | `scraped_at` | `str` | ISO 8601 timestamp of when this data was retrieved |

### Badge Schema

| Field | Key | Type | Notes |
|---|---|---|---|
| Badge Name | `name` | `str` | Badge display name from RSI page |
| Image URL | `image_url` | `str` | Badge image URL from RSI CDN |
| Image Local | `image_local` | `str` | Local path after download |

---

## Player Organizations

**Source URL:** `https://robertsspaceindustries.com/en/citizens/{handle}/organizations`

Fetched as part of the player scrape. Each affiliated org entry contains:

| Field | Key | Type | Notes |
|---|---|---|---|
| Org Name | `name` | `str` | Organization display name |
| Org SID | `sid` | `str` | Organization SID (short ID) |
| Player Rank | `rank` | `str` | Player's rank/title within this org |
| Logo URL | `logo_url` | `str` | Org logo image URL |
| Logo Local | `logo_local` | `str` | Local path after download |
| Is Main Org | `is_main` | `bool` | Whether this is the player's main/primary org |
| Visibility | `visibility` | `str \| None` | Org visibility setting if exposed |
| Member Count | `member_count` | `int \| None` | If visible on page |

Additionally, for each org found, the full org page is scraped for extended details:

| Field | Key | Type | Notes |
|---|---|---|---|
| Description | `description` | `str \| None` | Org description/manifesto text |
| Archetype | `archetype` | `str \| None` | e.g., "Corporation", "PMC", etc. |
| Primary Focus | `focus_primary` | `str \| None` | e.g., "Exploration", "Combat" |
| Secondary Focus | `focus_secondary` | `str \| None` | Secondary focus tag if present |
| Language | `language` | `str \| None` | Primary org language |
| Commitment | `commitment` | `str \| None` | e.g., "Casual", "Regular" |
| Recruiting | `recruiting` | `bool` | Whether org is accepting members |
| Roleplay | `roleplay` | `bool` | Whether org has roleplay designation |

---

## Standalone Organization

**Source URL:** `https://robertsspaceindustries.com/en/orgs/{sid}`

| Field | Key | Type | Notes |
|---|---|---|---|
| Name | `name` | `str` | Org display name |
| SID | `sid` | `str` | Short identifier (from URL) |
| Logo URL | `logo_url` | `str` | Org logo image |
| Logo Local | `logo_local` | `str` | Local path after download |
| Banner URL | `banner_url` | `str \| None` | Org banner image if present |
| Banner Local | `banner_local` | `str \| None` | Local path after download |
| Description | `description` | `str \| None` | Full org description |
| Archetype | `archetype` | `str \| None` | Org archetype |
| Primary Focus | `focus_primary` | `str \| None` | Primary activity focus |
| Secondary Focus | `focus_secondary` | `str \| None` | Secondary activity focus |
| Language | `language` | `str \| None` | Primary language |
| Commitment | `commitment` | `str \| None` | Commitment level |
| Recruiting | `recruiting` | `bool` | Recruiting status |
| Roleplay | `roleplay` | `bool` | Roleplay designation |
| Member Count | `member_count` | `int` | Total member count from org page |
| Members Preview | `members_preview` | `list` | First page of member roster entries |
| Page URL | `page_url` | `str` | Canonical org page URL |
| Scraped At | `scraped_at` | `str` | ISO 8601 retrieval timestamp |

---

## Org Name → SID Resolution

**Source URL:** `https://robertsspaceindustries.com/en/community/orgs/listing?search={query}`

When a user searches by org name, the listing page is queried first. The scraper parses org cards to extract `(name, SID)` pairs.

Resolution logic:
- **Exactly 1 result** → use that SID directly
- **Multiple results** → present a picker dialog to the user
- **0 results** → show error dialog; suggest searching by SID directly

---

## Notes on Data Availability

- **Location and Bio** are user-configurable privacy fields — many players hide them. Always handle as optional.
- **Fluency** may be empty for many players.
- **Badges** section may be empty for new or private accounts.
- **Org details** depend on org visibility settings — some orgs are "Invite Only" and may hide member counts.
- **Banner images** for orgs may not exist for all orgs.
- Do not assume any optional field exists — check `None` before attempting to display.

---

## Test References

| Target | Handle/SID | URL |
|---|---|---|
| Player | `PINKgeekPDX` | `https://robertsspaceindustries.com/en/citizens/PINKgeekPDX` |
| Player Orgs | `PINKgeekPDX` | `https://robertsspaceindustries.com/en/citizens/PINKgeekPDX/organizations` |
| Org | `THEKVLT` | `https://robertsspaceindustries.com/en/orgs/THEKVLT` |
