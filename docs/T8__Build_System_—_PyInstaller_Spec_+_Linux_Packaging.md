# T8: Build System — PyInstaller Spec + Linux Packaging

## Overview

Create the complete build system: PyInstaller spec for Windows (onedir, all assets bundled), Debian packaging script, Arch PKGBUILD, and an OCR validation tool. After this ticket, the app can be distributed as a standalone executable.

## Spec References

- spec:c441db88-8d38-408a-b39a-c0196029911d/42214321-7712-4003-8d87-011fe43f2d07 — Phase 8
- spec:c441db88-8d38-408a-b39a-c0196029911d/6aaf1867-554f-447d-af1e-6810954a0dd9 — Build System section

## Depends On

- T4 (OCR engine must be finalized before build spec can reference correct dependencies)
- T7 (all features must be complete before packaging)

## Scope

### Files to Create

**`SCDossier.spec`** (project root — only `README.md`, `agent.md`, `requirements.txt`, `SCDossier.spec` are allowed at root per `agent.md`)

- PyInstaller `onedir` mode
- `datas`: bundle `src/assets/fonts/` and `src/assets/icons/` with correct destination paths
- `hiddenimports`: `['rapidocr_onnxruntime', 'lxml', 'bs4', 'PIL']`
- `icon`: `src/assets/icons/tray.ico` (Windows) — create `.ico` from `tray.svg` if needed
- Entry point: `src/main.py`
- Output: `built/dist/windows/SCDossier/`

**`build/linux/debian/build_deb.sh`**

- Runs PyInstaller, wraps output in Debian package structure
- Output: `built/dist/linux/debian/SCDossier.deb`

**`build/linux/arch/PKGBUILD`**

- Arch Linux package definition
- Output: `built/dist/linux/arch/SCDossier-*.pkg.tar.zst`

**`scripts/tools/ocr_test.py`** (if not already created in T4)

- Validates RapidOCR on a test image, prints results

### Verify `build.py` (already exists at root)

- Confirm it correctly invokes PyInstaller with the spec file
- Add platform detection if needed (Windows vs Linux build targets)

### Asset Path Resolution

- All `os.path.dirname(__file__)` references in source code must work correctly under PyInstaller's `sys._MEIPASS` — verify `_ICONS_DIR` in `overlay_toolbar.py` and font paths in `fonts.py` resolve correctly in bundled mode

### Out of Scope

- No macOS build target
- No code signing or notarization
- No auto-update mechanism
- No installer wizard (just the raw executable/package)

## Acceptance Criteria

python build.py (or pyinstaller SCDossier.spec) produces a working SCDossier/ directory under built/dist/windows/The built executable launches, shows the toolbar, and completes a full player search end-to-endAll fonts load correctly in the built executable (Sora, Inter, JetBrains Mono)All SVG icons display correctly in the built executablebuild_deb.sh produces a .deb file that installs and runs on Debian/UbuntuPKGBUILD is valid Arch Linux package definitionNo FileNotFoundError for assets in the bundled executable