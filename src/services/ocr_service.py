"""
src/services/ocr_service.py
OCRService — Background thread runner for RapidOCR text extraction.
Uses rapidocr-onnxruntime as a lightweight, lazy-loaded singleton engine.
"""

import logging
import re
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

from src.core.events import EventBus

log = logging.getLogger(__name__)

# Module-level singleton for RapidOCR instance — initialized once, reused across all calls
_rapid_ocr_instance = None


def _get_rapid_ocr():
    """Lazy-load the RapidOCR engine singleton."""
    global _rapid_ocr_instance
    if _rapid_ocr_instance is None:
        from rapidocr_onnxruntime import RapidOCR
        _rapid_ocr_instance = RapidOCR()
        log.info("RapidOCR engine initialized (singleton).")
    return _rapid_ocr_instance


class OCRWorker(QThread):
    """
    Background worker that runs RapidOCR on an image file.

    Uses a module-level singleton RapidOCR instance so the engine
    is only initialized once across all worker runs.
    """

    finished_success = pyqtSignal(str)
    finished_error = pyqtSignal(str)

    def __init__(self, image_path: Path, confidence_threshold: float = 0.5) -> None:
        super().__init__()
        self.image_path = image_path
        self.confidence_threshold = confidence_threshold

    def run(self) -> None:
        try:
            reader = _get_rapid_ocr()

            log.info("Running OCR on %s", self.image_path)
            # RapidOCR returns (boxes, txts, scores) tuple
            result = reader(str(self.image_path))

            if result is None:
                self.finished_error.emit("No text detected in the selected region.")
                return

            boxes, txts, scores = result

            if not txts or not scores:
                self.finished_error.emit("No text detected in the selected region.")
                return

            best_text = ""
            best_conf = 0.0

            for text, conf in zip(txts, scores):
                if conf > best_conf and conf >= self.confidence_threshold:
                    best_conf = conf
                    best_text = text

            if not best_text:
                self.finished_error.emit(f"Text detected, but confidence too low (< {self.confidence_threshold:.2f}).")
                return

            # Clean up the text: RSI handles are alphanumeric + underscores/dashes
            cleaned = re.sub(r'[^A-Za-z0-9_-]', '', best_text)
            if not cleaned:
                self.finished_error.emit(f"Extracted text '{best_text}' contained no valid handle characters.")
                return

            log.info("OCR successful. Extracted: '%s' (conf: %.2f)", cleaned, best_conf)
            self.finished_success.emit(cleaned)

        except ImportError:
            log.error("rapidocr_onnxruntime not installed.")
            self.finished_error.emit("RapidOCR library is not installed. Run: pip install rapidocr-onnxruntime")
        except Exception as e:
            log.exception("OCR processing failed")
            self.finished_error.emit(f"OCR Error: {str(e)}")


class OCRService:
    """
    Service wrapper for managing OCR threads.
    Listens to the region_selector's output and fires the EventBus when done.
    """

    def __init__(self) -> None:
        self._worker: OCRWorker | None = None

    def process_image(self, image_path: Path) -> None:
        """Start OCR on the given image path."""
        from src.core.settings import SettingsManager
        
        sm = SettingsManager.instance()
        threshold = sm.ocr_confidence_threshold

        # If a worker is currently running, we could interrupt or ignore. We'll just ignore for now.
        if self._worker and self._worker.isRunning():
            log.warning("OCR already running. Ignoring new request.")
            return

        self._worker = OCRWorker(image_path, threshold)
        self._worker.finished_success.connect(self._on_success)
        self._worker.finished_error.connect(self._on_error)
        
        bus = EventBus.instance()
        bus.status_message.emit("INITIALIZING OCR ENGINE...", "info")
        
        self._worker.start()

    def _on_success(self, handle: str) -> None:
        EventBus.instance().capture_completed.emit(handle)

    def _on_error(self, error_msg: str) -> None:
        EventBus.instance().capture_failed.emit(error_msg)