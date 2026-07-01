from __future__ import annotations

from datetime import datetime, timezone

from loguru import logger

from src.scrapers.base import BaseScraper, JobResult


class SmartRecruitersScraper(BaseScraper):
    """Scraper for SmartRecruiters job board API (public)."""

    SOURCE = "smartrecruiters"

    # Verified working SmartRecruiters company slugs
    COMPANY_SLUGS = [
        "google", "microsoft", "uber", "booking-holding",
        "adobe", "vmware", "zoom", "dropbox", "atlassian", "salesforce",
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
        url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"

        try:
            response = await self.fetch(url)
            data = response.json()

            content = data.get("content", data) if isinstance(data, dict) else data
            if isinstance(content, list):
                for item in content:
                    job = self._parse_job(item, slug)
                    if job:
                        results.append(job)

        except Exception as e:
            logger.debug(f"[{self.name}] Company {slug} failed: {e}")

        return results

    def _parse_job(self, data: dict, company: str) -> JobResult | None:
        try:
            name = data.get("name", "")
            if not name:
                return None

            ref = data.get("ref", "")
            url = f"https://careers.smartrecruiters.com/{company}/{ref}"

            location = data.get("location", {})
            city = location.get("city", "") if isinstance(location, dict) else ""
            country = location.get("country", "") if isinstance(location, dict) else ""

            release_date = data.get("releasedDate", "")
            posting_date = None
            if release_date:
                try:
                    posting_date = datetime.fromisoformat(
                        release_date.replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            title_lower = name.lower()
            experience_level = "Entry-Level"
            if any(w in title_lower for w in ["senior", "sr", "lead"]):
                experience_level = "Senior"

            return JobResult(
                source=self.SOURCE,
                external_id=ref or data.get("id", ""),
                title=name,
                company=company.title(),
                url=url,
                apply_url=data.get("applyUrl", url),
                country=country,
                city=city,
                experience_level=experience_level,
                posting_date=posting_date,
                raw_data=data,
            )
        except Exception as e:
            logger.debug(f"[{self.name}] Failed to parse job: {e}")
            return None