from __future__ import annotations

from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup
from loguru import logger

from src.scrapers.base import BaseScraper, JobResult


class LinkedInRSSScraper(BaseScraper):
    """Scraper for LinkedIn's public "guest" jobs API.

    Uses the unauthenticated ``seeMoreJobPostings`` endpoint that powers the
    logged-out jobs search. It returns an HTML fragment of job cards. The
    endpoint is aggressively rate-limited, so we keep the location/query grid
    small, page shallowly, and rely on the base scraper's Retry-After handling.
    """

    BASE_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    SOURCE = "linkedin"
    REFERER = "https://www.linkedin.com/jobs"

    # f_E experience-level filter: 1=internship, 2=entry, 3=associate.
    # f_TPR=r2592000 limits to roughly the last 30 days.
    EXPERIENCE_FILTER = "1,2,3"
    DATE_POSTED_FILTER = "r2592000"

    # Text locations (verified to work with the &location= param). Kept short to
    # stay within rate limits; remote-friendly markets first.
    LOCATIONS = [
        "United Kingdom", "United States", "Germany", "Netherlands",
        "Ireland", "European Union",
    ]

    MAX_RESULTS = 150
    PAGES_PER_QUERY = 2  # start=0 and start=25

    async def scrape(self, **kwargs) -> list[JobResult]:
        queries = kwargs.get("queries") or self.settings.active_queries()
        locations = kwargs.get("locations") or self.LOCATIONS

        results: list[JobResult] = []
        seen: set[str] = set()

        for location in locations:
            for query in queries:
                keyword = query.replace(" ", "+")
                for page in range(self.PAGES_PER_QUERY):
                    start = page * 25
                    try:
                        cards = await self._scrape_page(keyword, location, start)
                    except Exception as e:
                        logger.warning(
                            f"[{self.name}] {query} @ {location} (start={start}) failed: {e}"
                        )
                        break  # stop paging this query on error (likely rate-limited)

                    new = 0
                    for job in cards:
                        if job.fingerprint in seen:
                            continue
                        seen.add(job.fingerprint)
                        results.append(job)
                        new += 1

                    # No more results for this query
                    if new == 0:
                        break
                    if len(results) >= self.MAX_RESULTS:
                        logger.info(f"[{self.name}] Scraped {len(results)} jobs (cap reached)")
                        return results

        logger.info(f"[{self.name}] Scraped {len(results)} jobs")
        return results

    async def _scrape_page(
        self, keyword: str, location: str, start: int
    ) -> list[JobResult]:
        url = (
            f"{self.BASE_URL}?keywords={keyword}"
            f"&location={location.replace(' ', '%20')}"
            f"&f_E={self.EXPERIENCE_FILTER}&f_TPR={self.DATE_POSTED_FILTER}"
            f"&start={start}&sortBy=DD"
        )
        response = await self.fetch(url)
        soup = BeautifulSoup(response.text, "html.parser")

        results = []
        for card in soup.select("li"):
            job = self._parse_card(card, location)
            if job:
                results.append(job)
        return results

    def _parse_card(self, card, location_name: str) -> Optional[JobResult]:
        try:
            title_el = card.select_one("h3.base-search-card__title")
            company_el = card.select_one("h4.base-search-card__subtitle")
            link_el = card.select_one("a.base-card__full-link")
            date_el = card.select_one("time")
            location_el = card.select_one("span.job-search-card__location")

            if not title_el or not company_el or not link_el:
                return None

            title = title_el.get_text(strip=True)
            company = company_el.get_text(strip=True)
            url = (link_el.get("href", "") or "").strip().split("?")[0]
            if not title or not company or not url:
                return None

            posting_date = None
            if date_el and date_el.get("datetime"):
                try:
                    posting_date = datetime.fromisoformat(
                        date_el["datetime"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            city = location_el.get_text(strip=True) if location_el else ""

            title_lower = title.lower()
            experience_level = "Entry-Level"
            if any(w in title_lower for w in ["senior", "sr ", "lead", "principal", "staff"]):
                experience_level = "Senior"

            # External id is the trailing numeric job id in the URL
            external_id = url.rstrip("/").split("/")[-1].split("-")[-1]

            return JobResult(
                source=self.SOURCE,
                external_id=external_id or url,
                title=title,
                company=company,
                url=url,
                apply_url=url,
                country=location_name,
                city=city,
                experience_level=experience_level,
                posting_date=posting_date,
                raw_data={"location_query": location_name},
            )
        except Exception as e:
            logger.debug(f"[{self.name}] Failed to parse card: {e}")
            return None
