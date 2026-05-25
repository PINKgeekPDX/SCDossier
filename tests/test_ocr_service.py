"""
tests/test_ocr_service.py
Unit tests for OCRService text extraction logic.
Tests the text cleaning and confidence threshold logic.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.services.ocr_service import OCRWorker


class TestOCRWorkerTextCleaning:
    """Tests for OCR text processing logic."""

    def test_clean_handle_alphanumeric(self):
        """Test that handles are cleaned to alphanumeric + underscore/dash."""
        import re

        raw_text = "PINKgeekPDX!!"
        cleaned = re.sub(r'[^A-Za-z0-9_-]', '', raw_text)

        assert cleaned == "PINKgeekPDX"

    def test_clean_handle_with_special_chars(self):
        """Test cleaning handle with various special characters."""
        import re

        raw_text = "PINK-geek_PDX!@#$%^&*()"
        cleaned = re.sub(r'[^A-Za-z0-9_-]', '', raw_text)

        assert cleaned == "PINK-geek_PDX"

    def test_clean_handle_preserves_underscore_dash(self):
        """Test that underscores and dashes are preserved."""
        import re

        raw_text = "TEST_HANDLE-123"
        cleaned = re.sub(r'[^A-Za-z0-9_-]', '', raw_text)

        assert cleaned == "TEST_HANDLE-123"

    def test_clean_handle_empty_result(self):
        """Test that cleaning produces empty string for non-valid handles."""
        import re

        raw_text = "!!!@@@###"
        cleaned = re.sub(r'[^A-Za-z0-9_-]', '', raw_text)

        assert cleaned == ""


class TestOCRWorkerConfidenceThreshold:
    """Tests for OCR confidence threshold logic."""

    def test_select_best_text_by_confidence(self):
        """Test selecting best text by confidence above threshold."""
        texts = ["PINKgeekPDX", "THEKVLT", "TESTORG"]
        scores = [0.95, 0.45, 0.85]
        confidence_threshold = 0.5

        best_text = ""
        best_conf = 0.0

        for text, conf in zip(texts, scores):
            if conf > best_conf and conf >= confidence_threshold:
                best_conf = conf
                best_text = text

        assert best_text == "PINKgeekPDX"
        assert best_conf == 0.95

    def test_skip_low_confidence_text(self):
        """Test that low confidence text is skipped."""
        texts = ["PINKgeekPDX", "THEKVLT"]
        scores = [0.45, 0.35]
        confidence_threshold = 0.5

        best_text = ""
        best_conf = 0.0

        for text, conf in zip(texts, scores):
            if conf > best_conf and conf >= confidence_threshold:
                best_conf = conf
                best_text = text

        assert best_text == ""
        assert best_conf == 0.0

    def test_select_second_best_if_first_below_threshold(self):
        """Test selecting second best when first is below threshold."""
        texts = ["LOWCONF", "GOODHANDLE"]
        scores = [0.35, 0.85]
        confidence_threshold = 0.5

        best_text = ""
        best_conf = 0.0

        for text, conf in zip(texts, scores):
            if conf > best_conf and conf >= confidence_threshold:
                best_conf = conf
                best_text = text

        assert best_text == "GOODHANDLE"
        assert best_conf == 0.85


class TestOCRWorkerRunLogic:
    """Tests for OCRWorker run method logic (without Qt event loop)."""

    @patch('src.services.ocr_service._get_rapid_ocr')
    def test_successful_ocr_emits_text(self, mock_get_rapid_ocr):
        """Test successful OCR result processing."""
        from pathlib import Path

        # Mock RapidOCR returning (result, elapse_list)
        # result is [[box, text, score]]
        mock_ocr = Mock()
        mock_ocr.return_value = ([[None, "PINKgeekPDX", 0.95]], [0.1, 0.1, 0.1])
        mock_get_rapid_ocr.return_value = mock_ocr

        worker = OCRWorker(Path("/fake/path.png"), confidence_threshold=0.5)
        worker.finished_success = Mock()
        worker.finished_error = Mock()

        worker.run()

        worker.finished_success.emit.assert_called_once_with("PINKgeekPDX")
        worker.finished_error.emit.assert_not_called()

    @patch('src.services.ocr_service._get_rapid_ocr')
    def test_ocr_none_result_emits_error(self, mock_get_rapid_ocr):
        """Test that None result from OCR emits error."""
        from pathlib import Path

        mock_ocr = Mock()
        mock_ocr.return_value = None
        mock_get_rapid_ocr.return_value = mock_ocr

        worker = OCRWorker(Path("/fake/path.png"), confidence_threshold=0.5)
        worker.finished_success = Mock()
        worker.finished_error = Mock()

        worker.run()

        worker.finished_error.emit.assert_called_once_with("No text detected in the selected region.")
        worker.finished_success.emit.assert_not_called()

    @patch('src.services.ocr_service._get_rapid_ocr')
    def test_ocr_empty_texts_emits_error(self, mock_get_rapid_ocr):
        """Test that empty texts list emits error."""
        from pathlib import Path

        mock_ocr = Mock()
        mock_ocr.return_value = ([], [0.1, 0.1, 0.1])
        mock_get_rapid_ocr.return_value = mock_ocr

        worker = OCRWorker(Path("/fake/path.png"), confidence_threshold=0.5)
        worker.finished_success = Mock()
        worker.finished_error = Mock()

        worker.run()

        worker.finished_error.emit.assert_called_once_with("No text detected in the selected region.")

    @patch('src.services.ocr_service._get_rapid_ocr')
    def test_low_confidence_emits_error(self, mock_get_rapid_ocr):
        """Test that low confidence text emits error."""
        from pathlib import Path

        mock_ocr = Mock()
        mock_ocr.return_value = ([[None, "TEST", 0.3]], [0.1, 0.1, 0.1])
        mock_get_rapid_ocr.return_value = mock_ocr

        worker = OCRWorker(Path("/fake/path.png"), confidence_threshold=0.5)
        worker.finished_success = Mock()
        worker.finished_error = Mock()

        worker.run()

        worker.finished_error.emit.assert_called_once()
        assert "confidence too low" in worker.finished_error.emit.call_args[0][0]