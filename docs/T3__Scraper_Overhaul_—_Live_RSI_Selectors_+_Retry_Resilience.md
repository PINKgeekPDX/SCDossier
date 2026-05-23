# T3: Scraper Overhaul — Live RSI Selectors + Retry Resilience

## Overview

The scraper CSS selectors were written speculatively and are likely broken against the current RSI website HTML. This ticket fetches the live RSI pages, analyzes the actual HTML structure, rewrites all selectors, and adds retry/fallback resilience so partial data displays rather than crashing.

## Spec References

- spec:c441db88-8d38-408a-b39a-c0196029911d/42214321-7712-4003-8d87-011fe43f2d07 — Phase 3
- spec:c441db88-8d38-408a-b39a-c0196029911d/6aaf1867-554f-447d-af1e-6810954a0dd9 — Scrapers section

## Depends On

- T1 (signal wiring must be correct before scraper output can be verified end-to-end)

## Scope

### Test Targets (from `agent.md`)

- Player: `https://robertsspaceindustries.com/en/citizens/PINKgeekPDX`
- Player orgs: `https://robertsspaceindustries.com/en/citizens/PINKgeekPDX/organizations`
- Org: `https://robertsspaceindustries.com/en/orgs/THEKVLT`
- Org listing: `https://robertsspaceindustries.com/en/community/orgs/listing?search=THEKVLT`

### Files to Change

file:src/services/scraper_player.py

- Fetch live pages for `PINKgeekPDX`, inspect actual HTML structure
- Rewrite all CSS selectors to match confirmed live structure:
  - Identity block (handle, moniker)
  - Enlist date, location, fluency entries
  - Bio text
  - Avatar image
  - Badges/accreditations container and individual badge items
  - Orgs page: main org vs affiliations, name, SID, rank, logo
- Add `_fetch_with_retry(url, headers, max_attempts=3)` helper — exponential backoff: 1s, 2s, 4s
- On partial success (main profile scraped, orgs page fails): emit `finished_success` with whatever data was collected
- Handle 403/Cloudflare: emit `finished_error` with `"RSI WEBSITE BLOCKED REQUEST — TRY AGAIN LATER"`
- Handle `Redacted` org SID gracefully (skip, don't crash)

file:src/services/scraper_org.py

- Fetch live pages for `THEKVLT` and listing search, inspect actual HTML
- Rewrite all CSS selectors:
  - `OrgScraperWorker`: name, logo, banner, archetype, language, commitment, recruiting, roleplay, member count, description, focus primary/secondary
  - `OrgSearchWorker`: org grid/list items, SID, name, logo on listing page
- Same retry pattern as player scraper
- Handle empty search results gracefully (emit `candidates_found([])`)

file:scripts/tools/scraper_test.py (already exists)

- Verify it runs correctly against both test targets and prints structured output

### Out of Scope

- No changes to `AppController` signal routing
- No UI changes
- No OCR changes

## Acceptance Criteria

Searching PINKgeekPDX returns a populated PlayerProfile dict with: handle, moniker, enlisted, location, fluency, bio, avatar_url, badges list, orgs listSearching THEKVLT (org) returns a populated OrgProfile dict with: sid, name, logo_url, archetype, language, commitment, recruiting, roleplay, member_count, description, focus_primary, focus_secondaryOrg name search for "The Kvlt" returns at least one candidate with correct SIDNetwork failure on orgs page does not crash — player profile still emits with empty orgs list404 response emits finished_error with clear messagescraper_test.py runs without errors and prints structured output for both targetsNo unhandled exceptions during scraping