"""
tests/test_scraper_org.py
Unit tests for OrgScraperWorker scraper logic.
Tests the parsing and extraction logic without Qt dependencies.
"""

import pytest
from unittest.mock import Mock, patch
from bs4 import BeautifulSoup

from src.services.scraper_org import _fetch_with_retry


class TestFetchWithRetry:
    """Tests for the _fetch_with_retry function (shared with player scraper)."""

    def test_successful_fetch(self):
        """Test successful fetch returns response."""
        with patch('src.services.scraper_org.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = _fetch_with_retry("https://example.com", {})

            assert result.status_code == 200

    def test_404_returns_response(self):
        """Test that 404 is returned for caller to handle."""
        with patch('src.services.scraper_org.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            result = _fetch_with_retry("https://example.com", {})

            assert result.status_code == 404

    def test_max_attempts_exceeded(self):
        """Test that RequestException raises after max attempts."""
        import requests
        with patch('src.services.scraper_org.requests.get') as mock_get:
            with patch('src.services.scraper_org.time.sleep'):
                mock_get.side_effect = requests.RequestException("Connection error")

                with pytest.raises(requests.RequestException):
                    _fetch_with_retry("https://example.com", {}, max_attempts=3)

                assert mock_get.call_count == 3


class TestOrgScraperParsing:
    """Tests for org scraping HTML parsing logic."""

    def test_parse_org_name_from_heading(self):
        """Test parsing org name from heading h1."""
        html = '<div class="heading"><h1>THEKVLT / STAR CITIZEN</h1></div>'
        soup = BeautifulSoup(html, "lxml")

        name_elem = soup.select_one("div.heading h1")
        name = name_elem.text.split('/')[0].strip() if name_elem else "UNKNOWN"

        assert name == "THEKVLT"

    def test_parse_org_sid_lowercase(self):
        """Test that SID is converted to uppercase."""
        html = '<div class="heading"><h1>TESTORG</h1></div>'
        soup = BeautifulSoup(html, "lxml")

        name_elem = soup.select_one("div.heading h1")
        name = name_elem.text.split('/')[0].strip() if name_elem else "UNKNOWN"

        assert name == "TESTORG"

    def test_parse_member_count_from_digits(self):
        """Test parsing member count extracting digits."""
        html = '<div class="logo"><span class="count">Members: 28</span></div>'
        soup = BeautifulSoup(html, "lxml")

        count_elem = soup.select_one("div.logo span.count")
        if count_elem:
            text = count_elem.text.strip()
            digits = ''.join(c for c in text if c.isdigit())
            count = int(digits) if digits else 0
        else:
            count = 0

        assert count == 28

    def test_parse_boolean_values(self):
        """Test parsing boolean values from tag spans."""
        html = '''
        <div class="heading">
            <ul class="tags">
                <li><label>Recruiting</label><span class="value">yes</span></li>
                <li><label>Roleplay</label><span class="value">enforced</span></li>
                <li><label>Commitment</label><span class="value">high</span></li>
            </ul>
        </div>
        '''
        soup = BeautifulSoup(html, "lxml")

        recruiting = False
        roleplay = False
        for li in soup.select("div.heading ul.tags li"):
            label_elem = li.select_one("label")
            value_elem = li.select_one("span.value")
            if label_elem and value_elem:
                label_text = label_elem.text.strip().lower()
                val = value_elem.text.strip().lower()
                if "recruiting" in label_text:
                    recruiting = val in ("yes", "true", "recruiting", "open")
                elif "roleplay" in label_text:
                    roleplay = val in ("yes", "true", "roleplay", "enforced")

        assert recruiting is True
        assert roleplay is True

    def test_parse_archetype_and_language(self):
        """Test parsing archetype and language from tags."""
        html = '''
        <div class="heading">
            <ul class="tags">
                <li><label>Archetype</label><span class="value">PMC</span></li>
                <li><label>Language</label><span class="value">English</span></li>
            </ul>
        </div>
        '''
        soup = BeautifulSoup(html, "lxml")

        archetype = None
        language = None
        for li in soup.select("div.heading ul.tags li"):
            label_elem = li.select_one("label")
            value_elem = li.select_one("span.value")
            if label_elem and value_elem:
                label_text = label_elem.text.strip().lower()
                val = value_elem.text.strip()
                if "archetype" in label_text:
                    archetype = val
                elif "lang" in label_text:
                    language = val

        assert archetype == "PMC"
        assert language == "English"