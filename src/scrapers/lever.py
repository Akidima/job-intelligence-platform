from __future__ import annotations

from datetime import datetime, timezone

from loguru import logger

from src.scrapers.base import BaseScraper, JobResult


class LeverScraper(BaseScraper):
    """Scraper for Lever job board API (public)."""

    SOURCE = "lever"

    # Verified working Lever company slugs (only ones known to work)
    COMPANY_SLUGS = [
        "netflix", "shopify", "github", "discord", "coinbase",
        "robinhood", "doordash", "instacart", "twilio", "pinterest",
    ]

    async def scrape(self, **kwargs) -> list[JobResult]:
        results = []
        slugs = kwargs.get("slugs", self.COMPANY_SLUGS)

        # Limit to first 6 companies
        for slug in slugs[:6]:
            try:
                jobs = await self._scrape_company(slug)
                results.extend(jobs)
            except Exception as e:
                logger.error(f"[{self.name}] Failed for {slug}: {e}")

        logger.info(f"[{self.name}] Scraped {len(results)} jobs")
        return results

    async def _scrape_company(self, slug: str) -> list[JobResult]:
        results = []
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"

        try:
            response = await self.fetch(url)
            data = response.json()

            if not isinstance(data, list):
                return results

            for item in data:
                job = self._parse_job(item, slug)
                if job:
                    results.append(job)

        except Exception as e:
            logger.debug(f"[{self.name}] Company {slug} failed: {e}")

        return results

    def _parse_job(self, data: dict, company: str) -> JobResult | None:
        try:
            title = data.get("text", "")
            if not title:
                return None

            categories = data.get("categories", {})
            team = categories.get("team", "")
            department = categories.get("department", "")
            location = categories.get("location", "")

            created = data.get("createdAt", 0)
            posting_date = None
            if created:
                posting_date = datetime.fromtimestamp(created / 1000, tz=timezone.utc)

            url = data.get("hostedUrl", "")
            apply_url = data.get("applyUrl", url)

            title_lower = title.lower()
            experience_level = "Entry-Level"
            if any(w in title_lower for w in ["senior", "sr", "lead", "principal"]):
                experience_level = "Senior"

            return JobResult(
                source=self.SOURCE,
                external_id=data.get("id", ""),
                title=title,
                company=company.title(),
                url=url,
                apply_url=apply_url or url,
                country=location,
                experience_level=experience_level,
                posting_date=posting_date,
                raw_data={"team": team, "department": department},
            )
        except Exception as e:
            logger.debug(f"[{self.name}] Failed to parse job: {e}")
            return None