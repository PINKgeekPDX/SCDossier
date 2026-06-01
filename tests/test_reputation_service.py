"""
tests/test_reputation_service.py
Unit tests for ReputationService data methods.

Tests: fetch_reputation, _normalize_score.
Supabase client is mocked throughout — no real network calls.
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
def mock_supabase_client():
    """Return a MagicMock that behaves like a supabase Client."""
    return MagicMock()


@pytest.fixture
def service(mock_supabase_client):
    """Return an initialized ReputationService with a mocked Supabase client."""
    import src.services.reputation_service as rep_module
    rep_module.create_client = lambda url, key: mock_supabase_client
    rep_module._SUPABASE_AVAILABLE = True
    from src.services.reputation_service import ReputationService
    svc = ReputationService.initialize("https://example.supabase.co", "anon-key-fake")
    yield svc, mock_supabase_client
    # Restore — leave create_client patched state; singleton reset handles the rest


# ---------------------------------------------------------------------------
# Tests: fetch_reputation
# ---------------------------------------------------------------------------

class TestFetchReputation:

    def test_fetch_returns_score_dict_when_rows_exist(self, service):
        """fetch_reputation returns a correctly shaped dict when DB has scores."""
        svc, client = service

        # Mock player lookup
        player_chain = MagicMock()
        player_chain.execute.return_value.data = {"id": "player-uuid-001"}
        (client.from_.return_value
               .select.return_value
               .eq.return_value
               .maybe_single.return_value) = player_chain

        # Mock scores lookup
        scores_chain = MagicMock()
        scores_chain.execute.return_value.data = [
            {"category": "dangerous",   "score": 7,  "report_count": 2},
            {"category": "trustworthy", "score": 5,  "report_count": 1},
            {"category": "pirate",      "score": 4,  "report_count": 1},
            {"category": "shady",       "score": 0,  "report_count": 0},
            {"category": "elusive",     "score": 3,  "report_count": 1},
        ]
        (client.from_.return_value
               .select.return_value
               .eq.return_value) = scores_chain

        # Re-mock in sequence: first call is player, second is scores
        from_calls = []

        def from_side_effect(table):
            mock = MagicMock()
            from_calls.append(table)
            if table == "players":
                mock.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
                    "id": "player-uuid-001"
                }
            elif table == "reputation_scores":
                mock.select.return_value.eq.return_value.execute.return_value.data = [
                    {"category": "dangerous",   "score": 7,  "report_count": 2},
                    {"category": "trustworthy", "score": 5,  "report_count": 1},
                    {"category": "pirate",      "score": 4,  "report_count": 1},
                    {"category": "shady",       "score": 0,  "report_count": 0},
                    {"category": "elusive",     "score": 3,  "report_count": 1},
                ]
            return mock

        client.from_.side_effect = from_side_effect

        result = svc.fetch_reputation("PINKgeekPDX")

        assert result is not None
        assert "dangerous" in result
        assert result["dangerous"]["score"] == 7
        assert result["dangerous"]["report_count"] == 2
        assert result["trustworthy"]["score"] == 5
        assert result["pirate"]["score"] == 4

    def test_fetch_returns_none_when_player_not_found(self, service):
        """fetch_reputation returns None when the player is not in the DB."""
        svc, client = service

        def from_side_effect(table):
            mock = MagicMock()
            if table == "players":
                mock.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = None
            return mock

        client.from_.side_effect = from_side_effect

        result = svc.fetch_reputation("unknown_player")

        assert result is None

    def test_fetch_returns_none_on_network_exception(self, service):
        """fetch_reputation returns None on network error — does NOT raise."""
        svc, client = service

        client.from_.side_effect = Exception("Connection refused")

        result = svc.fetch_reputation("any_player")

        # Must not raise — returns None
        assert result is None


# ---------------------------------------------------------------------------
# Tests: _normalize_score
# ---------------------------------------------------------------------------

class TestNormalizeScore:

    def test_normalize_mid_range(self):
        """_normalize_score computes correct percentage for mid-range values."""
        from src.services.reputation_service import ReputationService
        # score=18, report_count=5 → 18/(5*6)*100 = 60%
        result = ReputationService._normalize_score(18, 5)
        assert result == 60

    def test_normalize_clamps_at_100(self):
        """_normalize_score clamps at 100 — never exceeds 100%."""
        from src.services.reputation_service import ReputationService
        # Very high score should be capped
        result = ReputationService._normalize_score(1000, 1)
        assert result == 100

    def test_normalize_returns_zero_when_no_reports(self):
        """_normalize_score returns 0 when report_count is 0."""
        from src.services.reputation_service import ReputationService
        result = ReputationService._normalize_score(10, 0)
        assert result == 0

    def test_normalize_zero_score(self):
        """_normalize_score returns 0 when score is 0."""
        from src.services.reputation_service import ReputationService
        result = ReputationService._normalize_score(0, 5)
        assert result == 0

    def test_normalize_single_max_tag(self):
        """Score of 6 with 1 report (pirate_confirmed, max single tag) = 100%."""
        from src.services.reputation_service import ReputationService
        # 6 / (1 * 6) * 100 = 100
        result = ReputationService._normalize_score(6, 1)
        assert result == 100

    def test_normalize_typical_low_score(self):
        """Low-threat scenario: score=3, report_count=3 → 3/(3*6)*100 = 16%."""
        from src.services.reputation_service import ReputationService
        result = ReputationService._normalize_score(3, 3)
        assert result == 16


# ---------------------------------------------------------------------------
# Tests: initialization
# ---------------------------------------------------------------------------

class TestReputationServiceInit:

    def test_initialize_raises_on_empty_url(self):
        """initialize() raises ReputationServiceError when url is empty."""
        from src.services.reputation_service import ReputationService, ReputationServiceError
        with pytest.raises(ReputationServiceError):
            ReputationService.initialize("", "some-key")

    def test_initialize_raises_on_empty_key(self):
        """initialize() raises ReputationServiceError when anon_key is empty."""
        from src.services.reputation_service import ReputationService, ReputationServiceError
        with pytest.raises(ReputationServiceError):
            ReputationService.initialize("https://x.supabase.co", "")

    def test_instance_raises_before_initialization(self):
        """instance() raises RuntimeError before initialize() is called."""
        from src.services.reputation_service import ReputationService
        with pytest.raises(RuntimeError):
            ReputationService.instance()

    def test_is_initialized_false_before_init(self):
        """is_initialized() returns False before initialize() is called."""
        from src.services.reputation_service import ReputationService
        assert ReputationService.is_initialized() is False

    def test_is_initialized_true_after_init(self):
        """is_initialized() returns True after initialize() succeeds."""
        import src.services.reputation_service as rep_module
        rep_module.create_client = lambda url, key: MagicMock()
        rep_module._SUPABASE_AVAILABLE = True
        from src.services.reputation_service import ReputationService
        ReputationService.initialize("https://x.supabase.co", "fake-key")
        assert ReputationService.is_initialized() is True

    @patch("os.path.exists")
    @patch("builtins.open")
    def test_detect_local_player_handle_patterns(self, mock_open, mock_exists, service):
        """detect_local_player_handle successfully extracts from all 3 patterns."""
        svc, _ = service
        mock_exists.side_effect = lambda path: "Game.log" in path
        
        # Test Pattern A (Character status)
        log_a = (
            "Some log line\n"
            "<2026-05-31T09:13:18.406Z> [Notice] <AccountLoginCharacterStatus_Character> "
            "Character: createdAt 1778731949259 - updatedAt 1779669072087 - geid 204502564273 - "
            "accountId 927959 - name TestPlayerA - state STATE_CURRENT [Team_GameServices][Login]"
        )
        mock_open.return_value.__enter__.return_value.read.return_value = log_a
        assert svc.detect_local_player_handle() == "TestPlayerA"
        
        # Test Pattern B (Legacy Login)
        log_b = (
            "Some log line\n"
            "<2026-05-31T09:13:19.016Z> [Notice] <Legacy login response> [CIG-net] User Login Success - Handle[TestPlayerB] - Time[288202229] [Team_GameServices][Login]"
        )
        mock_open.return_value.__enter__.return_value.read.return_value = log_b
        assert svc.detect_local_player_handle() == "TestPlayerB"
        
        # Test Pattern C (Expect Incoming Connection)
        log_c = (
            "Some log line\n"
            "<2026-05-31T09:13:23.359Z> [Notice] <Expect Incoming Connection> session=ca5702b nickname=\"TestPlayerC\" playerGEID=204502564273 [Team_Network][Network][Gateway]"
        )
        mock_open.return_value.__enter__.return_value.read.return_value = log_c
        assert svc.detect_local_player_handle() == "TestPlayerC"

    @patch("os.path.exists")
    def test_detect_local_player_handle_no_log(self, mock_exists, service):
        """detect_local_player_handle returns empty string when no game log is found."""
        svc, _ = service
        mock_exists.return_value = False
        assert svc.detect_local_player_handle() == ""

