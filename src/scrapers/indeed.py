from __future__ import annotations

from datetime import datetime, timezone

from loguru import logger

from src.scrapers.base import BaseScraper, JobResult


class IndeedScraper(BaseScraper):
    """Light scraper for Indeed public job listings."""

    BASE_URL = "https://www.indeed.com"
    SOURCE = "indeed"

    async def scrape(self, **kwargs) -> list[JobResult]:
        results = []
        countries = [
            ("us", "United States"), ("uk", "United Kingdom"),
            ("de", "Germany"), ("nl", "Netherlands"),
            ("ie", "Ireland"), ("fr", "France"),
        ]

        queries = [
            "data analyst", "junior data analyst", "business analyst",
            "analytics engineer", "data engineer",
        ]

        for country_code, country_name in countries[:2]:
            for query in queries[:2]:
                try:
                    jobs = await self._search(query, country_code, country_name)
                    results.extend(jobs)
                    if len(results) >= 80:
                        break
                except Exception as e:
                    logger.error(f"[{self.name}] Failed for {query} in {country_code}: {e}")
            if len(results) >= 80:
                break

        logger.info(f"[{self.name}] Scraped {len(results)} jobs")
        return results

    async def _search(
        self, query: str, country_code: str, country_name: str, start: int = 0,
    ) -> list[JobResult]:
        results = []
        base = "https://uk.indeed.com" if country_code == "uk" else f"https://{country_code}.indeed.com"
        url = f"{base}/jobs?q={query.replace(' ', '+')}&sort=date&start={start}"

        try:
            response = await self.fetch(url)
            html = response.text

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select("div.job_seen_beacon, div.jobsearch-ResultsList div.result")

            for card in cards[:25]:
                job = self._parse_card(card, country_name, country_code)
                if job:
                    results.append(job)

        except Exception as e:
            logger.debug(f"[{self.name}] Search failed: {e}")

        return results

    def _parse_card(self, card, country: str, country_code: str) -> Optional[JobResult]:
        try:
            title_el = card.select_one("h2.jobTitle a, a.jcs-JobTitle")
            company_el = card.select_one("span[data-testid='company-name'], span.companyName")
            location_el = card.select_one("div[data-testid='text-location'], div.companyLocation")
            date_el = card.select_one("span.date")

            if not title_el:
                return None

            title = title_el.get_text(strip=True)
            company = company_el.get_text(strip=True) if company_el else "Unknown"
            job_id = title_el.get("data-jk", "") or title_el.get("id", "").replace("job_", "")
            link = title_el.get("href", "")
            if link and not link.startswith("http"):
                link = f"{self.BASE_URL}{link}"

            posting_date = None
            if date_el:
                date_text = date_el.get_text(strip=True).lower()
                posting_date = self._parse_relative_date(date_text)

            title_lower = title.lower()
            experience_level = "Entry-Level"
            if any(w in title_lower for w in ["senior", "sr", "lead"]):
                experience_level = "Senior"

            city = location_el.get_text(strip=True) if location_el else ""

            return JobResult(
                source=self.SOURCE,
                external_id=job_id or title[:100],
                title=title,
                company=company,
                url=link,
                apply_url=link,
                country=country,
                city=city.split(",")[0] if city else "",
                experience_level=experience_level,
                posting_date=posting_date,
                raw_data={"country_code": country_code},
            )
        except Exception as e:
            logger.debug(f"[{self.name}] Failed to parse card: {e}")
            return None

    def _parse_relative_date(self, text: str) -> Optional[datetime]:
        from datetime import timedelta
        import re
        now = datetime.now(timezone.utc)
        match = re.search(r"(\d+)", text)
        if not match:
            return None
        num = int(match.group(1))
        if "minute" in text:
            return now - timedelta(minutes=num)
        elif "hour" in text:
            return now - timedelta(hours=num)
        elif "day" in text:
            return now - timedelta(days=num)
        elif "week" in text:
            return now - timedelta(weeks=num)
        return now
