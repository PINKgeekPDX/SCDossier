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
    svc = ReputationService.initialize("https://example.com", "anon-key-fake")
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
            {"category": "competent",   "score": 6,  "report_count": 2},
            {"category": "toxic",       "score": 2,  "report_count": 1},
            {"category": "spawn_killed", "score": 2, "report_count": 1},
            {"category": "fake_auction", "score": 4, "report_count": 2},
            {"category": "escort",      "score": 2,  "report_count": 1},
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
                    {"category": "competent",   "score": 6,  "report_count": 2},
                    {"category": "toxic",       "score": 2,  "report_count": 1},
                    {"category": "spawn_killed", "score": 2, "report_count": 1},
                    {"category": "fake_auction", "score": 4, "report_count": 2},
                    {"category": "escort",      "score": 2,  "report_count": 1},
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
        """fetch_reputation returns {} (empty dict) when the player is not in the DB."""
        svc, client = service

        def from_side_effect(table):
            mock = MagicMock()
            if table == "players":
                mock.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = None
            return mock

        client.from_.side_effect = from_side_effect

        result = svc.fetch_reputation("unknown_player")

        assert result == {}

    def test_fetch_returns_none_on_network_exception(self, service):
        """fetch_reputation returns None on network error — does NOT raise."""
        svc, client = service

        client.from_.side_effect = Exception("Connection refused")

        result = svc.fetch_reputation("any_player")

        # Must not raise — returns empty dict on error
        assert result == {}


# ---------------------------------------------------------------------------
# Tests: _normalize_score
# ---------------------------------------------------------------------------

class TestNormalizeScore:
    """Tests for _normalize_score(score, report_count, category).

    Formula: denominator = max(report_count * max_pts, max_pts * 50)
             pct = int(score / denominator * 100)
             clamped to [0, 100]

    Category max_pts (sum of tag points per category):
        dangerous=11, shady=11, pirate=10, elusive=6, trustworthy=6, competent=6, positive=6, friendly=6, toxic=6
    """

    def test_normalize_mid_range(self):
        """_normalize_score computes correct percentage for mid-range values."""
        from src.services.reputation_service import ReputationService
        # dangerous: max_pts=11, denom=max(5*11, 11*50)=max(55,550)=550
        # pct = int(275/550*100) = 50
        result = ReputationService._normalize_score(275, 5, "dangerous")
        assert result == 50

    def test_normalize_clamps_at_100(self):
        """_normalize_score clamps at 100 — never exceeds 100%."""
        from src.services.reputation_service import ReputationService
        # dangerous: max_pts=11, denom=max(1*11, 550)=550
        # pct = int(550/550*100) = 100
        result = ReputationService._normalize_score(550, 1, "dangerous")
        assert result == 100

    def test_normalize_returns_zero_when_no_reports(self):
        """_normalize_score returns 0 when report_count is 0."""
        from src.services.reputation_service import ReputationService
        result = ReputationService._normalize_score(10, 0, "shady")
        assert result == 0

    def test_normalize_zero_score(self):
        """_normalize_score returns 0 when score is 0."""
        from src.services.reputation_service import ReputationService
        result = ReputationService._normalize_score(0, 5, "pirate")
        assert result == 0

    def test_normalize_ceiling_at_max_reports(self):
        """At 50 max-score reports, player reaches 100%."""
        from src.services.reputation_service import ReputationService
        # pirate: max_pts=10, denom=max(1*10, 10*50)=max(10,500)=500
        # pct = int(500/500*100) = 100
        result = ReputationService._normalize_score(500, 1, "pirate")
        assert result == 100

    def test_normalize_typical_low_score(self):
        """Low-threat scenario with many reports but low score."""
        from src.services.reputation_service import ReputationService
        # dangerous: max_pts=11, denom=max(10*11, 550)=max(110,550)=550
        # pct = int(11/550*100) = 2
        result = ReputationService._normalize_score(11, 10, "dangerous")
        assert result == 2


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
            ReputationService.initialize("https://example.com", "")

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
        ReputationService.initialize("https://example.com", "fake-key")
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

