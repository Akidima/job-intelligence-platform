from __future__ import annotations

from loguru import logger

from src.scrapers.base import BaseScraper, JobResult


class EUStartupJobsScraper(BaseScraper):
    """Scraper for EU Startup Jobs API."""

    BASE_URL = "https://api.eu-startup-jobs.com/v1/jobs"
    SOURCE = "eu_startup_jobs"

    async def scrape(self, **kwargs) -> list[JobResult]:
        results = []
        try:
            params = {
                "limit": 100,
                "sort": "created_at",
                "order": "desc",
            }
            url = f"{self.BASE_URL}"
            response = await self.fetch(url, params=params)
            data = response.json()

            for item in data.get("data", data if isinstance(data, list) else []):
                if not isinstance(item, dict):
                    continue
                job = self._parse_job(item)
                if job:
                    results.append(job)

            logger.info(f"[{self.name}] Scraped {len(results)} jobs")

        except Exception as e:
            logger.error(f"[{self.name}] Scrape failed: {e}")

        return results

    def _parse_job(self, data: dict) -> Optional[JobResult]:
        try:
            title = data.get("title", "")
            company_data = data.get("company", {})
            company = company_data.get("name", "") if isinstance(company_data, dict) else str(company_data)

            if not title:
                return None

            url = data.get("apply_url", "") or data.get("url", "")
            description = data.get("description", "")
            location = data.get("location", "")
            remote = data.get("remote", False)

            country = "Remote"
            if remote:
                remote_type = "remote"
            else:
                remote_type = "hybrid"
                country = location

            title_lower = title.lower()
            experience_level = "Entry-Level"
            if any(w in title_lower for w in ["senior", "sr", "lead"]):
                experience_level = "Senior"

            posting_date = None
            created = data.get("created_at", "") or data.get("published_at", "")
            if created:
                try:
                    from datetime import datetime, timezone
                    posting_date = datetime.fromisoformat(created.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass

            return JobResult(
                source=self.SOURCE,
                external_id=str(data.get("id", "")),
                title=title,
                company=company,
                url=url,
                apply_url=url,
                description=description,
                country=country,
                city=location.split(",")[0] if location else "",
                remote_type=remote_type,
                experience_level=experience_level,
                posting_date=posting_date,
                raw_data=data,
            )
        except Exception as e:
            logger.debug(f"[{self.name}] Failed to parse job: {e}")
            return None
