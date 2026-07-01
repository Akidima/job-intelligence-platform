from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from src.scrapers.base import BaseScraper, JobResult


class AshbyScraper(BaseScraper):
    """Scraper for Ashby job board API (public)."""

    SOURCE = "ashby"

    # Verified working Ashby company slugs
    COMPANY_SLUGS = [
        "ramp", "mercury", "linear", "notion", "vercel",
        "planetscale", "cursor", "retool", "scale", "brex",
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
        url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"

        try:
            response = await self.fetch(url)
            data = response.json()

            postings = data.get("jobPostings", [])
            for item in postings:
                job = self._parse_job(item, slug)
                if job:
                    results.append(job)

        except Exception as e:
            logger.debug(f"[{self.name}] Company {slug} failed: {e}")

        return results

    def _parse_job(self, data: dict, company: str) -> JobResult | None:
        try:
            title = data.get("title", "")
            if not title:
                return None

            location = data.get("locationName", "")
            employment = data.get("employmentType", "")
            department = data.get("departmentName", "")
            team = data.get("teamName", "")

            url = data.get("url", "")
            if not url:
                url = f"https://jobs.ashbyhq.com/{company}/{data.get('id', '')}"

            posting_date = None
            created = data.get("createdAt")
            if created:
                try:
                    posting_date = datetime.fromisoformat(created.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass

            title_lower = title.lower()
            experience_level = "Entry-Level"
            if any(w in title_lower for w in ["senior", "sr", "lead"]):
                experience_level = "Senior"

            return JobResult(
                source=self.SOURCE,
                external_id=data.get("id", ""),
                title=title,
                company=company.title(),
                url=url,
                apply_url=url,
                country=location,
                experience_level=experience_level,
                employment_type=employment.lower() if employment else "unknown",
                posting_date=posting_date,
                raw_data={"department": department, "team": team},
            )
        except Exception as e:
            logger.debug(f"[{self.name}] Failed to parse job: {e}")
            return None