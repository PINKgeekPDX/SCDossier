import logging
import time
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup
from PyQt6.QtCore import QThread, pyqtSignal

from src.app.constants import RSI_ORG_URL, RSI_ORG_LISTING_URL

log = logging.getLogger(__name__)


def _fetch_with_retry(url: str, headers: dict, max_attempts: int = 3,
                      timeout_sec: int = 10, proxy: str | None = None) -> requests.Response | None:
    delays = [1, 2, 4]
    proxies = {"http": proxy, "https": proxy} if proxy else None
    for attempt in range(max_attempts):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout_sec, proxies=proxies)
            if resp.status_code == 404:
                return resp
            if resp.status_code == 403:
                log.warning("Attempt %d: RSI blocked request (403) for %s", attempt + 1, url)
                if attempt < max_attempts - 1:
                    time.sleep(delays[min(attempt, len(delays) - 1)])
                    continue
                return resp
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            log.warning("Attempt %d failed for %s: %s", attempt + 1, url, e)
            if attempt < max_attempts - 1:
                delay = delays[min(attempt, len(delays) - 1)]
                log.info("Retrying in %ds...", delay)
                time.sleep(delay)
            else:
                log.error("All %d attempts failed for %s", max_attempts, url)
                raise
    return None


def _parse_visible_members(html: str) -> list[dict]:
    members = []
    soup = BeautifulSoup(html, "lxml")
    for card in soup.select("li.member-item"):
        handle = ""
        moniker = ""
        avatar_url = ""
        rank = ""
        roles = []

        nick_elem = card.select_one("span.nick")
        if nick_elem:
            handle = nick_elem.get_text(strip=True)
        else:
            a_elem = card.select_one("a.membercard")
            if a_elem and a_elem.has_attr("href"):
                href = a_elem["href"]
                if "/citizens/" in href:
                    handle = href.split("/citizens/")[-1].strip()

        name_elem = card.select_one("span.name")
        if name_elem:
            moniker = name_elem.get_text(strip=True)

        avatar_img = card.select_one("span.thumb img")
        if avatar_img and avatar_img.has_attr("src"):
            avatar_url = avatar_img["src"]
            if not avatar_url.startswith("http"):
                avatar_url = "https://robertsspaceindustries.com" + avatar_url

        rank_elem = card.select_one("span.rank")
        if rank_elem:
            rank = rank_elem.get_text(strip=True)

        role_elems = card.select("ul.rolelist li.role")
        for relem in role_elems:
            role_text = relem.get_text(strip=True)
            if role_text:
                roles.append(role_text)

        if handle:
            members.append({
                "handle": handle,
                "moniker": moniker or handle,
                "avatar_url": avatar_url,
                "avatar_local": "",
                "rank": rank,
                "role": ", ".join(roles),
            })
    return members


class OrgSearchWorker(QThread):

    candidates_found = pyqtSignal(list)
    finished_error = pyqtSignal(str)

    def __init__(self, query: str, user_agent: str,
                 timeout_sec: int = 10, proxy: str | None = None) -> None:
        super().__init__()
        self.query = query
        self.user_agent = user_agent
        self.timeout_sec = timeout_sec
        self.proxy = proxy

    def run(self) -> None:
        headers = {"User-Agent": self.user_agent}
        url = f"{RSI_ORG_LISTING_URL}?search={self.query}"

        try:
            resp = _fetch_with_retry(url, headers, timeout_sec=self.timeout_sec, proxy=self.proxy)

            if resp is None:
                self.finished_error.emit("Failed to fetch org listing after 3 attempts.")
                return

            if resp.status_code == 403:
                self.finished_error.emit("RSI WEBSITE BLOCKED REQUEST - TRY AGAIN LATER")
                return

            soup = BeautifulSoup(resp.text, "lxml")
            candidates = []

            org_cards = soup.select("div.listing-wrapper > ul.orgs-listing.search > div.org-cell > a.trans-03s.clearfix")
            for card in org_cards:
                sid_elem = card.select_one("span.symbol")
                name_elem = card.select_one("h3.name")
                img_elem = card.select_one("span.thumb img")

                if sid_elem and name_elem:
                    sid = sid_elem.text.strip()
                    name = name_elem.text.strip()

                    logo = ""
                    if img_elem and img_elem.has_attr("src"):
                        logo = img_elem["src"]
                        if not logo.startswith("http"):
                            logo = "https://robertsspaceindustries.com" + logo

                    candidates.append({
                        "sid": sid,
                        "name": name,
                        "logo_url": logo
                    })

            self.candidates_found.emit(candidates)

        except Exception as e:
            log.exception("Org search failed")
            self.finished_error.emit(f"Org search failed: {str(e)}")


class OrgScraperWorker(QThread):

    finished_success = pyqtSignal(dict)
    finished_error = pyqtSignal(str)
    progress = pyqtSignal(float)

    def __init__(self, sid: str, user_agent: str,
                 timeout_sec: int = 10, proxy: str | None = None) -> None:
        super().__init__()
        self.sid = sid.upper()
        self.user_agent = user_agent
        self.timeout_sec = timeout_sec
        self.proxy = proxy

    def run(self) -> None:
        headers = {"User-Agent": self.user_agent}
        data = {
            "sid": self.sid,
            "page_url": RSI_ORG_URL.format(sid=self.sid),
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "name": self.sid,
            "logo_url": "",
            "logo_local": "",
            "banner_url": None,
            "banner_local": None,
            "archetype": None,
            "language": None,
            "commitment": None,
            "recruiting": False,
            "roleplay": False,
            "member_count": 0,
            "description": None,
            "focus_primary": None,
            "focus_secondary": None,
            "focus_primary_url": "",
            "focus_secondary_url": "",
            "focus_primary_local": "",
            "focus_secondary_local": "",
            "badges": [],
            "tags": [],
            "history": None,
            "manifesto": None,
            "charter": None,
            "members": [],
        }

        try:
            self.progress.emit(0.3)
            resp = _fetch_with_retry(
                data["page_url"], headers,
                timeout_sec=self.timeout_sec, proxy=self.proxy
            )

            if resp is None:
                self.finished_error.emit(
                    f"Failed to fetch org '{self.sid}' after 3 attempts."
                )
                return

            if resp.status_code == 404:
                self.finished_error.emit(
                    f"Organization '{self.sid}' not found (404)."
                )
                return

            if resp.status_code == 403:
                self.finished_error.emit(
                    "RSI WEBSITE BLOCKED REQUEST - TRY AGAIN LATER"
                )
                return

            soup = BeautifulSoup(resp.text, "lxml")

            name_elem = soup.select_one("div.heading h1")
            data["name"] = (
                name_elem.text.split("/")[0].strip() if name_elem else self.sid
            )

            logo_elem = soup.select_one("div.logo img")
            if logo_elem and logo_elem.has_attr("src"):
                logo = logo_elem["src"]
                if not logo.startswith("http"):
                    logo = "https://robertsspaceindustries.com" + logo
                data["logo_url"] = logo

            banner_elem = soup.select_one("div.heading div.banner img")
            if banner_elem and banner_elem.has_attr("src"):
                banner = banner_elem["src"]
                if not banner.startswith("http"):
                    banner = "https://robertsspaceindustries.com" + banner
                data["banner_url"] = banner
            else:
                data["banner_url"] = None

            # Parse tags
            tags = []
            for li in soup.select("div.heading ul.tags li"):
                tag_text = li.get_text(strip=True)
                if tag_text:
                    tags.append(tag_text)
                    classes = li.get("class", [])
                    if "model" in classes:
                        data["archetype"] = tag_text
                    elif "commitment" in classes:
                        data["commitment"] = tag_text
                    elif "exclusive" in classes:
                        data["recruiting"] = (tag_text.lower() in ("yes", "true", "recruiting", "open", "exclusive"))
                    elif "roleplay" in classes:
                        data["roleplay"] = (tag_text.lower() in ("yes", "true", "roleplay", "enforced"))
                    elif "lang" in classes or "language" in classes:
                        data["language"] = tag_text
            data["tags"] = tags

            count_elem = soup.select_one("div.logo span.count")
            if count_elem:
                text = count_elem.text.strip()
                digits = "".join(c for c in text if c.isdigit())
                data["member_count"] = int(digits) if digits else 0

            self._parse_org_details(soup, data)

            # Scrape members with new working GET pagination
            page = 1
            while True:
                members_url = f"https://robertsspaceindustries.com/orgs/{self.sid}/members?page={page}"
                resp_members = _fetch_with_retry(
                    members_url, headers,
                    timeout_sec=self.timeout_sec, proxy=self.proxy
                )
                if not resp_members or resp_members.status_code != 200:
                    log.info("Finished fetching members at page %d", page)
                    break

                page_members = _parse_visible_members(resp_members.text)
                if not page_members:
                    log.info("No members found on page %d; finishing member scrape", page)
                    break

                data["members"].extend(page_members)
                page += 1
                time.sleep(0.3)

            log.info(
                "Fetched %d visible members for %s (total on site: %d)",
                len(data["members"]), self.sid, data["member_count"]
            )

            self.progress.emit(1.0)
            self.finished_success.emit(data)

        except requests.RequestException as e:
            log.error("Org Scraper HTTP Error: %s", e)
            self.finished_error.emit(f"Network error: {str(e)}")
        except Exception as e:
            log.exception("Org scraping failed")
            self.finished_error.emit(f"Org scraper error: {str(e)}")

    def _parse_org_details(self, soup, data: dict) -> None:
        try:
            # Description
            desc_elem = soup.select_one("div.content.block.description div.markitup-text")
            if not desc_elem:
                desc_elem = soup.select_one("div.content.block.description")
            if desc_elem:
                data["description"] = desc_elem.get_text(strip=True)

            # Focus
            focus_primary_elem = soup.select_one("div.heading ul.focus li.primary img")
            if focus_primary_elem:
                data["focus_primary"] = focus_primary_elem.get("alt", "").strip() or None
                src = focus_primary_elem.get("src", "")
                if src:
                    if not src.startswith("http"):
                        src = "https://robertsspaceindustries.com" + src
                    data["focus_primary_url"] = src

            focus_secondary_elem = soup.select_one("div.heading ul.focus li.secondary img")
            if focus_secondary_elem:
                data["focus_secondary"] = focus_secondary_elem.get("alt", "").strip() or None
                src = focus_secondary_elem.get("src", "")
                if src:
                    if not src.startswith("http"):
                        src = "https://robertsspaceindustries.com" + src
                    data["focus_secondary_url"] = src

            # Badges
            for b in soup.select("div.badges img"):
                if b.has_attr("src"):
                    src = b["src"]
                    if not src.startswith("http"):
                        src = "https://robertsspaceindustries.com" + src
                    alt = b.get("alt", "")
                    data["badges"].append(
                        {"name": alt, "image_url": src, "image_local": ""}
                    )

            # Tabs (History, Manifesto, Charter)
            history_elem = soup.select_one("div#tab-history div.markitup-text")
            if history_elem:
                data["history"] = history_elem.get_text(strip=True)

            manifesto_elem = soup.select_one("div#tab-manifesto div.markitup-text")
            if manifesto_elem:
                data["manifesto"] = manifesto_elem.get_text(strip=True)

            charter_elem = soup.select_one("div#tab-charter div.markitup-text")
            if charter_elem:
                data["charter"] = charter_elem.get_text(strip=True)

        except Exception as e:
            log.warning("Failed to parse org details: %s", e)
