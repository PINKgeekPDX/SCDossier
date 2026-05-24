# T8: Tooltip Completeness Audit — All Interactive Elements

## Purpose

Ensure every interactive element across the entire app has a rich, descriptive `setToolTip()` call. This is a final pass after all other tickets have landed.

## Scope

**In:**

- All `QPushButton` instances: title bar (pin, hide), nav sidebar (all 6), toolbar (2), all tab action buttons
- All `QCheckBox` instances: Settings tab (all sections)
- All `QSlider` instances: Settings tab (font scale, toolbar opacity, OCR confidence)
- All `QSpinBox` instances: Settings tab (request delay, timeout, sync interval, cache age, concurrency, thread count)
- All `QLineEdit` / `SearchInput` / `AnimatedSearchInput` instances: Search, Dossier, Org, Archive filter, Settings path fields
- All `QComboBox` instances: Settings (OCR engine, archive sort, log level), Archive sort
- System tray icon tooltip and tray menu actions
- Status bar dot indicator

**Out:**

- No functional or visual changes — tooltips only

## Tooltip Standard (from Core Flows)

- Sentence case
- Describes the action or value, not just the label
- Every interactive element must have one — no exceptions

## Acceptance Criteria

- Zero interactive elements across the entire app lack a tooltip
- This includes the system tray tooltip and tray menu actions where supported by the runtime surface
- All tooltip text matches or is consistent with the text specified in spec:f092360a-c39e-41e6-ab6b-19c17741aaa7/4bc76e92-227f-41fb-9aca-1911c2e8ea27 (Flow 2 through Flow 11)
- Tooltips appear on hover in both dev and packaged runtime