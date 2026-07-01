from __future__ import annotations

from datetime import datetime, timezone

from loguru import logger

from src.scrapers.base import BaseScraper, JobResult


class WorkdayScraper(BaseScraper):
    """Scraper for Workday job board API (public)."""

    SOURCE = "workday"

    COMPANY_URLS = {
        "microsoft": "https://gcsservices.wd5.myworkdayjobs.com/Microsoft_Careers",
        "amazon": "https://www.amazon.jobs/en/search.json",
    }

    async def scrape(self, **kwargs) -> list[JobResult]:
        results = []

        # Workday sites vary greatly; we'll use a simplified approach
        # for known public endpoints
        for company, base_url in self.COMPANY_URLS.items():
            try:
                jobs = await self._scrape_endpoint(company, base_url)
                results.extend(jobs)
            except Exception as e:
                logger.error(f"[{self.name}] Failed for {company}: {e}")

        logger.info(f"[{self.name}] Scraped {len(results)} jobs")
        return results

    async def _scrape_endpoint(self, company: str, url: str) -> list[JobResult]:
        results = []

        try:
            search_url = f"{url}?q=data+analyst&limit=50"
            response = await self.fetch(search_url)

            # Workday returns HTML or JSON depending on endpoint
            try:
                data = response.json()
                for item in data.get("jobPostings", data.get("jobs", [])):
                    job = self._parse_job(item, company)
                    if job:
                        results.append(job)
            except Exception:
                # HTML fallback
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, "html.parser")
                # Workday HTML parsing varies by company

        except Exception as e:
            logger.debug(f"[{self.name}] Endpoint {company} failed: {e}")

        return results

    def _parse_job(self, data: dict, company: str) -> Optional[JobResult]:
        try:
            title = data.get("title", "") or data.get("name", "")
            if not title:
                return None

            ext_id = data.get("externalPath", "") or str(data.get("bulletFields", [""])[0])

            location = data.get("locationsText", "") or data.get("location", "")

            posting_date = None
            posted = data.get("postedOn", "") or data.get("startDate", "")
            if posted:
                try:
                    posting_date = datetime.fromisoformat(posted.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass

            title_lower = title.lower()
            experience_level = "Entry-Level"
            if any(w in title_lower for w in ["senior", "sr", "lead"]):
                experience_level = "Senior"

            return JobResult(
                source=self.SOURCE,
                external_id=ext_id,
                title=title,
                company=company.title(),
                url=f"https://{company}.myworkdayjobs.com{data.get('externalPath', '')}",
                country=location,
                experience_level=experience_level,
                posting_date=posting_date,
                raw_data=data,
            )
        except Exception as e:
            logger.debug(f"[{self.name}] Failed to parse job: {e}")
            return None
