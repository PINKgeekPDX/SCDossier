# T6: Archive Export — Self-Contained ZIP with All Five File Types

## Overview

Complete the archive export so the ZIP is truly self-contained. The `_generate_html()` method currently uses relative image paths — update it to inline base64 images. Verify all five export file types are generated correctly.

## Spec References

- spec:c441db88-8d38-408a-b39a-c0196029911d/42214321-7712-4003-8d87-011fe43f2d07 — Phase 6
- spec:c441db88-8d38-408a-b39a-c0196029911d/6aaf1867-554f-447d-af1e-6810954a0dd9 — Archive Export section

## Depends On

- T3 (scraper must return real data so there are real images to embed)
- T5 (archive tab must be functional to trigger export)

## Scope

### Files to Change

file:src/services/archive_manager.py

`_generate_html(data)` — update image embedding:

- For `avatar_local`: read the file, base64-encode, embed as `data:image/png;base64,...` in `<img src="...">`
- For each badge `image_local`: same base64 embedding
- For each org `logo_local`: same base64 embedding
- Fall back to empty `src=""` if local file doesn't exist or can't be read
- All other HTML structure, Aegis styling, and layout remain identical to current implementation

Verify the other four generators are correct (they already exist):

- `_generate_txt(data)` — already implemented, verify output format
- `_generate_csv(data)` — already implemented, verify all fields present
- `export_profile()` — already adds all files to ZIP, verify ZIP structure

### Out of Scope

- No changes to archive list, filter, sort, or detail view (that's T5)
- No changes to `CacheManager` or `SyncService`
- No new export formats beyond the five specified

## Acceptance Criteria

Export ZIP contains exactly: profile.json, avatar.png (and all badge/org images), profile.txt, profile.csv, profile.htmlprofile.html opens in a browser with no external dependencies — all images display inline (base64 embedded)profile.html renders with correct Aegis styling (dark background, blue accents, correct typography)profile.txt contains all profile fields in readable formatprofile.csv contains all profile fields in spreadsheet-compatible formatZIP is placed in the user-selected directory (via QFileDialog)Export works even if some images are missing (graceful fallback, no crash)Status bar shows "EXPORT COMPLETE" on success, "EXPORT FAILED" on error