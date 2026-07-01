from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from loguru import logger

from src.scrapers.base import BaseScraper, JobResult


class RemoteOKScraper(BaseScraper):
    """Scraper for RemoteOK job board (public JSON API)."""

    BASE_URL = "https://remoteok.com/api"
    SOURCE = "remoteok"

    async def scrape(self, **kwargs) -> list[JobResult]:
        results = []
        try:
            response = await self.fetch(self.BASE_URL)
            data = response.json()

            if not isinstance(data, list):
                logger.warning(f"[{self.name}] Unexpected response format")
                return results

            for item in data:
                if not isinstance(item, dict) or "id" not in item:
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
            tags = data.get("tags", []) or []
            title = data.get("position", "")
            company = data.get("company", "")

            if not title or not company:
                return None

            date_str = data.get("date", "")
            posting_date = None
            if date_str:
                try:
                    posting_date = datetime.fromisoformat(
                        date_str.replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            remote_type = "remote"
            if not data.get("remote", True):
                remote_type = "onsite"

            salary_min = None
            salary_max = None
            salary = data.get("salary_min")
            if salary:
                salary_min = int(salary)
            salary = data.get("salary_max")
            if salary:
                salary_max = int(salary)

            apply_url = data.get("url", "")
            if not apply_url:
                apply_url = f"https://remoteok.com/remote-jobs/{data['id']}"

            return JobResult(
                source=self.SOURCE,
                external_id=str(data["id"]),
                title=title,
                company=company,
                url=f"https://remoteok.com/remote-jobs/{data['id']}",
                apply_url=apply_url,
                description=data.get("description", ""),
                country=self._extract_country(tags, data),
                city=data.get("location", ""),
                remote_type=remote_type,
                salary_min=salary_min,
                salary_max=salary_max,
                experience_level=self._infer_level(title, tags),
                posting_date=posting_date,
                raw_data=data,
            )
        except Exception as e:
            logger.debug(f"[{self.name}] Failed to parse job: {e}")
            return None

    def _extract_country(self, tags: list, data: dict) -> str:
        location = data.get("location", "").lower()
        if not location or "remote" in location:
            return "Remote"
        country_map = {
            "united states": "United States", "usa": "United States",
            "us": "United States", "uk": "United Kingdom",
            "united kingdom": "United Kingdom", "germany": "Germany",
            "netherlands": "Netherlands", "ireland": "Ireland",
            "france": "France", "spain": "Spain", "sweden": "Sweden",
            "norway": "Norway", "denmark": "Denmark", "finland": "Finland",
        }
        for key, val in country_map.items():
            if key in location:
                return val
        return "Remote"

    def _infer_level(self, title: str, tags: list) -> str:
        title_lower = title.lower()
        if any(w in title_lower for w in ["junior", "jr", "entry", "graduate", "intern"]):
            return "Entry-Level"
        if any(w in title_lower for w in ["senior", "sr", "lead", "principal"]):
            return "Senior"
        if any(w in title_lower for w in ["mid", "intermediate"]):
            return "Mid-Level"
        return "Entry-Level"
