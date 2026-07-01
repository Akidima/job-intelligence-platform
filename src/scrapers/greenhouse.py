from __future__ import annotations

from datetime import datetime, timezone

from loguru import logger

from src.scrapers.base import BaseScraper, JobResult


class GreenhouseScraper(BaseScraper):
    """Scraper for Greenhouse job board API (public)."""

    SOURCE = "greenhouse"

    # Verified working Greenhouse board slugs
    BOARD_SLUGS = [
        "airbnb", "stripe", "coinbase", "robinhood", "databricks",
        "datadog", "snowflake", "reddit", "discord", "figma",
    ]

    async def scrape(self, **kwargs) -> list[JobResult]:
        results = []
        slugs = kwargs.get("slugs", self.BOARD_SLUGS)

        # Limit to first 6 boards
        for slug in slugs[:6]:
            try:
                jobs = await self._scrape_board(slug)
                results.extend(jobs)
            except Exception as e:
                logger.error(f"[{self.name}] Failed for {slug}: {e}")

        logger.info(f"[{self.name}] Scraped {len(results)} jobs")
        return results

    async def _scrape_board(self, slug: str) -> list[JobResult]:
        results = []
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"

        try:
            response = await self.fetch(url)
            data = response.json()

            for item in data.get("jobs", []):
                job = self._parse_job(item, slug)
                if job:
                    results.append(job)

        except Exception as e:
            logger.debug(f"[{self.name}] Board {slug} failed: {e}")

        return results

    def _parse_job(self, data: dict, board: str) -> JobResult | None:
        try:
            title = data.get("title", "")
            if not title:
                return None

            location = data.get("location", {})
            location_name = location.get("name", "") if isinstance(location, dict) else ""

            internal_job_id = data.get("id", "")
            url = data.get("absolute_url", f"https://boards.greenhouse.io/{board}/jobs/{internal_job_id}")

            posting_date = None
            updated = data.get("updated_at", "") or data.get("created_at", "")
            if updated:
                try:
                    posting_date = datetime.fromisoformat(
                        updated.replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            title_lower = title.lower()
            experience_level = "Entry-Level"
            if any(w in title_lower for w in ["senior", "sr", "lead", "principal"]):
                experience_level = "Senior"

            return JobResult(
                source=self.SOURCE,
                external_id=f"{board}_{internal_job_id}",
                title=title,
                company=board.title(),
                url=url,
                apply_url=url,
                country=location_name,
                experience_level=experience_level,
                posting_date=posting_date,
                raw_data={"board": board},
            )
        except Exception as e:
            logger.debug(f"[{self.name}] Failed to parse job: {e}")
            return None