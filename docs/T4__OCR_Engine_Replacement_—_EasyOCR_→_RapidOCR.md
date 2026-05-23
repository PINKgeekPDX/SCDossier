# T4: OCR Engine Replacement — EasyOCR → RapidOCR

## Overview

Replace the heavyweight EasyOCR engine (re-instantiated per call, ~100MB model) with `rapidocr-onnxruntime` — lightweight, local, no large model download, lazy-initialized as a module-level singleton. The `OCRWorker` QThread pattern is preserved; only the engine underneath changes.

## Spec References

- spec:c441db88-8d38-408a-b39a-c0196029911d/42214321-7712-4003-8d87-011fe43f2d07 — Phase 4
- spec:c441db88-8d38-408a-b39a-c0196029911d/6aaf1867-554f-447d-af1e-6810954a0dd9 — OCRService section

## Depends On

- T1 (OCR flow must be wired correctly)

## Scope

### Files to Change

file:requirements.txt

- Replace `easyocr>=1.7.1` with `rapidocr-onnxruntime>=1.3.0`

file:src/app/constants.py

- Update `OCREngine` enum: replace `EASYOCR = "easyocr"` with `RAPIDOCR = "rapidocr"`

file:src/core/settings.py

- Update `DEFAULT_SETTINGS["ocr_engine"]` default value from `OCREngine.EASYOCR.value` to `OCREngine.RAPIDOCR.value`

file:src/services/ocr_service.py

- Add module-level `_rapid_ocr: RapidOCR | None = None` singleton variable
- `OCRWorker.run()`: initialize singleton on first call (lazy), reuse on subsequent calls
- Call `reader(str(self.image_path))` → receives `(boxes, txts, scores)` tuple
- Filter results by `confidence_threshold`, concatenate candidates
- Apply `re.sub(r'[^A-Za-z0-9_-]', '', best_text)` — same cleanup logic as current
- Remove all `import easyocr` references
- `OCRService` interface unchanged — `EventBus.capture_completed` and `EventBus.capture_failed` still emitted

file:src/ui/tabs/settings_tab.py

- Update `ocr_combo` items: `"RapidOCR"` / `"rapidocr"` replacing `"EasyOCR"` / `"easyocr"`
- Update `_load_values()` to match new engine value string

file:scripts/tools/ocr_test.py (new file)

- Simple script: load a test image, run RapidOCR, print extracted text and confidence scores
- Place in `scripts/tools/` per `agent.md` directory rules

### Out of Scope

- No Tesseract fallback path
- No GPU option (RapidOCR CPU-only is sufficient for short handle extraction)
- No changes to `RegionSelector` or capture flow

## Acceptance Criteria

pip install -r requirements.txt installs rapidocr-onnxruntime without errorsOCR capture flow completes end-to-end: region select → extract → capture_completed signal emitted with cleaned handle stringSecond OCR call reuses the singleton (no re-initialization delay)ocr_test.py runs and prints extracted text from a test imageSettings tab shows "RapidOCR" as the engine optionNo import easyocr anywhere in the codebaseConfidence threshold from settings is respected