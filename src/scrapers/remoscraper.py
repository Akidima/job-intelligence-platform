from __future__ import annotations

import re
from datetime import datetime, timezone

from loguru import logger

from src.scrapers.base import BaseScraper, JobResult


class RemotiveScraper(BaseScraper):
    """Scraper for Remotive job board (public API)."""

    BASE_URL = "https://remotive.com/api/remote-jobs"
    SOURCE = "remotive"

    CATEGORY_MAP = {
        "data": ["data-analyst", "data-engineer", "data-scientist",
                  "analytics", "business-analyst"],
        "software": ["software-dev", "devops", "engineering"],
    }

    # Remotive job categories that map onto our enabled role categories.
    DEFAULT_CATEGORIES = ["data", "customer-service", "sales", "business"]

    async def scrape(self, **kwargs) -> list[JobResult]:
        results = []
        categories = kwargs.get("categories", self.DEFAULT_CATEGORIES)
        if isinstance(categories, str):
            categories = [c.strip() for c in categories.split(",") if c.strip()]

        # Remotive's API filters by a single category per request.
        for category in categories:
            try:
                url = f"{self.BASE_URL}?category={category}&limit=100"
                response = await self.fetch(url)
                data = response.json()

                for item in data.get("jobs", []):
                    job = self._parse_job(item)
                    if job:
                        results.append(job)
            except Exception as e:
                logger.error(f"[{self.name}] Scrape failed for '{category}': {e}")

        logger.info(f"[{self.name}] Scraped {len(results)} jobs")
        return results

    def _parse_job(self, data: dict) -> Optional[JobResult]:
        try:
            title = data.get("title", "")
            company = data.get("company_name", "")

            if not title or not company:
                return None

            publication_date = data.get("publication_date", "")
            posting_date = None
            if publication_date:
                try:
                    posting_date = datetime.fromisoformat(
                        publication_date.replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            tags = data.get("tags", []) or []
            candidate_required_location = data.get("candidate_required_location", "")

            country = "Remote"
            if candidate_required_location and "worldwide" not in candidate_required_location.lower():
                country = candidate_required_location.strip()

            salary = data.get("salary", "")
            salary_min, salary_max, currency = self._parse_salary(salary)

            title_lower = title.lower()
            experience_level = "Entry-Level"
            if any(w in title_lower for w in ["senior", "sr", "lead", "principal"]):
                experience_level = "Senior"

            return JobResult(
                source=self.SOURCE,
                external_id=str(data.get("id", "")),
                title=title,
                company=company,
                url=data.get("url", ""),
                apply_url=data.get("url", ""),
                description=data.get("description", ""),
                country=country,
                remote_type="remote",
                salary_min=salary_min,
                salary_max=salary_max,
                salary_currency=currency,
                experience_level=experience_level,
                posting_date=posting_date,
                raw_data=data,
            )
        except Exception as e:
            logger.debug(f"[{self.name}] Failed to parse job: {e}")
            return None

    def _parse_salary(self, salary_str: str):
        if not salary_str:
            return None, None, None

        currency = "USD"
        if "$" in salary_str or "USD" in salary_str:
            currency = "USD"
        elif "€" in salary_str or "EUR" in salary_str:
            currency = "EUR"
        elif "£" in salary_str or "GBP" in salary_str:
            currency = "GBP"

        numbers = re.findall(r"[\d,]+", salary_str.replace(",", ""))
        nums = []
        for n in numbers:
            try:
                nums.append(int(n))
            except ValueError:
                continue

        if len(nums) >= 2:
            return nums[0], nums[1], currency
        elif len(nums) == 1:
            return nums[0], None, currency
        return None, None, None
