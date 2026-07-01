from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from src.scrapers.base import BaseScraper, JobResult


class AdzunaScraper(BaseScraper):
    """Scraper for Adzuna job API (requires API key)."""

    BASE_URL = "https://api.adzuna.com/v1/api/jobs"
    SOURCE = "adzuna"

    COUNTRY_CODES = {
        "United States": "us", "United Kingdom": "gb", "Germany": "de",
        "Netherlands": "nl", "Ireland": "ie", "France": "fr",
        "Belgium": "be", "Sweden": "se", "Norway": "no", "Denmark": "dk",
        "Finland": "fi", "Switzerland": "ch", "Austria": "at",
        "Spain": "es", "Portugal": "pt", "Italy": "it", "Poland": "pl",
        "Czech Republic": "cz", "Luxembourg": "lu",
    }

    # Countries queried by default (Adzuna bills per call, so keep it focused).
    DEFAULT_COUNTRIES = ["gb", "us", "de", "nl", "ie"]

    async def scrape(
        self,
        country: Optional[str] = None,
        what: Optional[str] = None,
        page: int = 1,
        results_per_page: int = 50,
        **kwargs,
    ) -> list[JobResult]:
        results = []

        app_id = self.settings.adzuna_app_id
        app_key = self.settings.adzuna_app_key

        if not app_id or not app_key:
            logger.warning(f"[{self.name}] No API credentials configured, skipping")
            return results

        countries = [country] if country else self.DEFAULT_COUNTRIES
        queries = [what] if what else self.settings.active_queries()

        for cc in countries:
            for query in queries:
                results.extend(
                    await self._search(cc, query, page, results_per_page, app_id, app_key)
                )

        logger.info(f"[{self.name}] Scraped {len(results)} jobs")
        return results

    async def _search(
        self, country: str, what: str, page: int,
        results_per_page: int, app_id: str, app_key: str,
    ) -> list[JobResult]:
        results = []
        try:
            url = (
                f"{self.BASE_URL}/{country}/search/{page}"
                f"?app_id={app_id}&app_key={app_key}"
                f"&what={what.replace(' ', '%20')}&results_per_page={results_per_page}"
                f"&max_days_old={self.settings.max_job_age_days}"
                f"&sort_by=date"
            )
            response = await self.fetch(url)
            data = response.json()

            for item in data.get("results", []):
                job = self._parse_job(item, country)
                if job:
                    results.append(job)
        except Exception as e:
            logger.error(f"[{self.name}] Scrape failed for {country}/{what}: {e}")

        return results

    def _parse_job(self, data: dict, country_code: str) -> Optional[JobResult]:
        try:
            title = data.get("title", "")
            company = data.get("company", {}).get("display_name", "")

            if not title:
                return None

            location = data.get("location", {}).get("display_name", "")
            posting_str = data.get("created", "")
            posting_date = None
            if posting_str:
                try:
                    posting_date = datetime.fromisoformat(
                        posting_str.replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            salary_min = data.get("salary_min")
            salary_max = data.get("salary_max")

            description = data.get("description", "")
            title_lower = title.lower()
            experience_level = "Entry-Level"
            if any(w in title_lower for w in ["senior", "sr", "lead"]):
                experience_level = "Senior"

            return JobResult(
                source=self.SOURCE,
                external_id=str(data.get("id", "")),
                title=title,
                company=company,
                url=data.get("redirect_url", ""),
                apply_url=data.get("redirect_url", ""),
                description=description,
                country=self._get_country_name(country_code),
                city=location.split(",")[0] if location else "",
                salary_min=int(salary_min) if salary_min else None,
                salary_max=int(salary_max) if salary_max else None,
                salary_currency="GBP" if country_code == "gb" else "EUR",
                experience_level=experience_level,
                posting_date=posting_date,
                raw_data=data,
            )
        except Exception as e:
            logger.debug(f"[{self.name}] Failed to parse job: {e}")
            return None

    def _get_country_name(self, code: str) -> str:
        reverse = {v: k for k, v in self.COUNTRY_CODES.items()}
        return reverse.get(code, code)
