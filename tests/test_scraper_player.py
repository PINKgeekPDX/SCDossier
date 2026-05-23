"""
tests/test_scraper_player.py
Unit tests for PlayerScraperWorker scraper logic.
Tests the parsing and extraction logic without Qt dependencies.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup

from src.services.scraper_player import (
    _fetch_with_retry,
    _parse_org_entries,
    _parse_secondary_orgs,
)


class TestFetchWithRetry:
    """Tests for the _fetch_with_retry function."""

    def test_successful_fetch(self):
        """Test successful fetch returns response."""
        with patch('src.services.scraper_player.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = _fetch_with_retry("https://example.com", {})

            assert result.status_code == 200
            mock_get.assert_called_once()

    def test_retry_on_failure(self):
        """Test retry mechanism with exponential backoff."""
        with patch('src.services.scraper_player.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            with patch('src.services.scraper_player.time.sleep') as mock_sleep:
                result = _fetch_with_retry("https://example.com", {}, max_attempts=3)

                # Should have succeeded on first try
                assert result.status_code == 200
                mock_sleep.assert_not_called()

    def test_403_returns_response(self):
        """Test that 403 is returned for caller to handle."""
        with patch('src.services.scraper_player.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 403
            mock_get.return_value = mock_response

            result = _fetch_with_retry("https://example.com", {})

            assert result.status_code == 403

    def test_max_attempts_exceeded(self):
        """Test that RequestException raises after max attempts."""
        import requests
        with patch('src.services.scraper_player.requests.get') as mock_get:
            with patch('src.services.scraper_player.time.sleep'):
                mock_get.side_effect = requests.RequestException("Connection error")

                with pytest.raises(requests.RequestException):
                    _fetch_with_retry("https://example.com", {}, max_attempts=3)

                assert mock_get.call_count == 3


class TestParseOrgEntries:
    """Tests for _parse_org_entries parsing logic."""

    def test_parse_valid_org_entry(self):
        """Test parsing a valid org entry from HTML."""
        html = '''
        <div class="main-org right-col">
            <p class="entry"><a class="value">TESTORG</a></p>
            <p class="entry"><span class="label">SID</span><strong class="value">SID12345</strong></p>
            <p class="entry"><span class="label">Rank</span><strong class="value">MEMBER</strong></p>
            <div class="thumb"><img src="/logo.png"></div>
        </div>
        '''
        soup = BeautifulSoup(html, "lxml")
        org_list = []

        _parse_org_entries(soup, org_list, is_main=True)

        assert len(org_list) == 1
        assert org_list[0]["name"] == "TESTORG"
        assert org_list[0]["sid"] == "SID12345"
        assert org_list[0]["rank"] == "MEMBER"
        assert org_list[0]["is_main"] is True

    def test_parse_with_absolute_logo_url(self):
        """Test parsing org with absolute logo URL."""
        html = '''
        <div class="main-org right-col">
            <p class="entry"><a class="value">TESTORG2</a></p>
            <div class="thumb"><img src="https://robertsspaceindustries.com/logo.png"></div>
        </div>
        '''
        soup = BeautifulSoup(html, "lxml")
        org_list = []

        _parse_org_entries(soup, org_list)

        assert org_list[0]["logo_url"] == "https://robertsspaceindustries.com/logo.png"

    def test_parse_without_name_returns_empty(self):
        """Test that entries without name don't add to list."""
        html = '''
        <div class="main-org right-col">
            <p class="entry"><span class="label">SID</span><strong class="value">SID12345</strong></p>
        </div>
        '''
        soup = BeautifulSoup(html, "lxml")
        org_list = []

        _parse_org_entries(soup, org_list)

        assert len(org_list) == 0


class TestParseSecondaryOrgs:
    """Tests for _parse_secondary_orgs parsing logic."""

    def test_parse_secondary_orgs(self):
        """Test parsing secondary org affiliations."""
        html = '''
        <div class="orgs-content">
            <div class="org">
                <div class="info">
                    <p class="entry"><span class="value">SECONDORG</span></p>
                    <p class="entry"><span class="value">SID54321</span></p>
                    <p class="entry"><span class="value">OFFICER</span></p>
                </div>
                <div class="thumb"><img src="/logo2.png"></div>
            </div>
        </div>
        '''
        soup = BeautifulSoup(html, "lxml")
        org_list = []

        _parse_secondary_orgs(soup, org_list)

        assert len(org_list) == 1
        assert org_list[0]["name"] == "SECONDORG"
        assert org_list[0]["sid"] == "SID54321"
        assert org_list[0]["rank"] == "OFFICER"

    def test_skip_redacted_orgs(self):
        """Test that redacted orgs are skipped."""
        html = '''
        <div class="orgs-content">
            <div class="org">
                <div class="info">
                    <p class="entry"><span class="value">HIDDENORG</span></p>
                    <p class="entry"><span class="value">Redacted</span></p>
                </div>
            </div>
        </div>
        '''
        soup = BeautifulSoup(html, "lxml")
        org_list = []

        _parse_secondary_orgs(soup, org_list)

        assert len(org_list) == 0

    def test_deduplicate_orgs(self):
        """Test that orgs with same SID are deduplicated."""
        html = '''
        <div class="orgs-content">
            <div class="org">
                <div class="info">
                    <p class="entry"><span class="value">ORG1</span></p>
                    <p class="entry"><span class="value">TESTSID</span></p>
                </div>
            </div>
        </div>
        '''
        soup = BeautifulSoup(html, "lxml")
        org_list = [{"name": "ORG2", "sid": "TESTSID", "rank": ""}]

        _parse_secondary_orgs(soup, org_list)

        assert len(org_list) == 1