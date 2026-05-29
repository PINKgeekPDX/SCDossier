"""
tests/test_reputation_worker.py
Unit tests for ReputationFetchWorker and ReputationSubmitWorker.

Workers are tested by calling .run() directly (not .start()) to avoid
spinning up real QThreads in unit tests.
"""

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the ReputationService singleton between tests."""
    from src.services.reputation_service import ReputationService
    ReputationService._instance = None
    ReputationService._initialized = False
    yield
    ReputationService._instance = None
    ReputationService._initialized = False


@pytest.fixture
def mock_service():
    """Patch ReputationService.instance() to return a MagicMock service."""
    svc = MagicMock()
    with patch(
        "src.services.reputation_worker.ReputationService.instance",
        return_value=svc,
    ):
        yield svc


# ---------------------------------------------------------------------------
# Tests: ReputationFetchWorker
# ---------------------------------------------------------------------------

class TestReputationFetchWorker:

    def test_run_emits_finished_success_with_dict_on_success(self, mock_service):
        """run() emits finished_success with the score dict when fetch_reputation returns data."""
        from src.services.reputation_worker import ReputationFetchWorker

        score_data = {
            "dangerous": {"score": 7, "report_count": 2},
            "trustworthy": {"score": 5, "report_count": 1},
        }
        mock_service.fetch_reputation.return_value = score_data

        worker = ReputationFetchWorker("TestHandle")

        received = []
        worker.finished_success.connect(lambda d: received.append(d))

        worker.run()

        assert len(received) == 1
        assert received[0] == score_data

    def test_run_emits_finished_success_empty_dict_when_no_data(self, mock_service):
        """run() emits finished_success({}) when fetch_reputation returns None."""
        from src.services.reputation_worker import ReputationFetchWorker

        mock_service.fetch_reputation.return_value = None

        worker = ReputationFetchWorker("UnknownPlayer")

        success_received = []
        error_received = []
        worker.finished_success.connect(lambda d: success_received.append(d))
        worker.finished_error.connect(lambda e: error_received.append(e))

        worker.run()

        # No data → success with empty dict, NOT an error
        assert len(success_received) == 1
        assert success_received[0] == {}
        assert len(error_received) == 0

    def test_run_emits_finished_error_on_exception(self, mock_service):
        """run() emits finished_error when fetch_reputation raises unexpectedly."""
        from src.services.reputation_worker import ReputationFetchWorker

        mock_service.fetch_reputation.side_effect = Exception("Connection timed out")

        worker = ReputationFetchWorker("TestHandle")

        success_received = []
        error_received = []
        worker.finished_success.connect(lambda d: success_received.append(d))
        worker.finished_error.connect(lambda e: error_received.append(e))

        worker.run()

        assert len(error_received) == 1
        assert "Connection timed out" in error_received[0]
        assert len(success_received) == 0

    def test_run_emits_finished_error_when_service_not_initialized(self):
        """run() emits finished_error when ReputationService is not initialized."""
        from src.services.reputation_worker import ReputationFetchWorker
        from src.services.reputation_service import ReputationService

        # Ensure instance() raises RuntimeError (singleton not initialized)
        assert not ReputationService.is_initialized()

        worker = ReputationFetchWorker("AnyHandle")
        error_received = []
        worker.finished_error.connect(lambda e: error_received.append(e))

        worker.run()

        assert len(error_received) == 1


# ---------------------------------------------------------------------------
# Tests: ReputationSubmitWorker
# ---------------------------------------------------------------------------

class TestReputationSubmitWorker:

    def test_run_emits_finished_error_when_ip_hash_unavailable(self, mock_service):
        """run() emits finished_error when _get_ip_hash() returns None."""
        from src.services.reputation_worker import ReputationSubmitWorker

        mock_service._get_ip_hash.return_value = None

        worker = ReputationSubmitWorker("TestHandle", ["killed_me"])

        success_received = []
        error_received = []
        worker.finished_success.connect(lambda d: success_received.append(d))
        worker.finished_error.connect(lambda e: error_received.append(e))

        worker.run()

        # IP hash unavailable → error, no report submitted
        assert len(error_received) == 1
        assert "rate limiting" in error_received[0].lower() or "ip" in error_received[0].lower()
        assert len(success_received) == 0
        mock_service.submit_report.assert_not_called()

    def test_run_emits_finished_success_on_successful_submit(self, mock_service):
        """run() emits finished_success with the updated score dict on success."""
        from src.services.reputation_worker import ReputationSubmitWorker

        mock_service._get_ip_hash.return_value = "abc123deadbeef" * 4  # 64 chars
        result_dict = {
            "dangerous":   {"score": 4,  "report_count": 1},
            "trustworthy": {"score": 0,  "report_count": 0},
            "pirate":      {"score": 0,  "report_count": 0},
            "shady":       {"score": 0,  "report_count": 0},
            "elusive":     {"score": 0,  "report_count": 0},
        }
        mock_service.submit_report.return_value = result_dict

        worker = ReputationSubmitWorker("TestHandle", ["killed_me", "ambushed"])

        success_received = []
        error_received = []
        worker.finished_success.connect(lambda d: success_received.append(d))
        worker.finished_error.connect(lambda e: error_received.append(e))

        worker.run()

        assert len(success_received) == 1
        assert success_received[0] == result_dict
        assert len(error_received) == 0
        mock_service.submit_report.assert_called_once_with(
            "TestHandle",
            ["killed_me", "ambushed"],
            "abc123deadbeef" * 4,
        )

    def test_run_emits_finished_error_on_service_error(self, mock_service):
        """run() emits finished_error when submit_report raises ReputationServiceError."""
        from src.services.reputation_worker import ReputationSubmitWorker
        from src.services.reputation_service import ReputationServiceError

        mock_service._get_ip_hash.return_value = "a" * 64
        mock_service.submit_report.side_effect = ReputationServiceError("Rate limit exceeded")

        worker = ReputationSubmitWorker("TestHandle", ["killed_me"])

        error_received = []
        worker.finished_error.connect(lambda e: error_received.append(e))

        worker.run()

        assert len(error_received) == 1
        assert "Rate limit exceeded" in error_received[0]
