from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from src.scrapers.base import JobResult


class JobParser:
    """Parses and normalizes job data from raw scraper results."""

    TITLE_CLEANUP = [
        r"\s*[-–—]\s*(Remote|Hybrid|Onsite|Full.?time|Part.?time).*",
        r"\s*\(.*?\)\s*$",
    ]

    COUNTRY_MAP = {
        "usa": "United States", "u.s.": "United States",
        "us": "United States", "uk": "United Kingdom",
        "u.k.": "United Kingdom", "deutschland": "Germany",
        "nl": "Netherlands", "ie": "Ireland",
    }

    def parse(self, job: JobResult) -> dict:
        """Parse a JobResult into a clean dictionary for database storage."""
        try:
            title = self._clean_title(job.title)
            normalized_title = self._normalize_title(title)
            company = self._clean_company(job.company)
            country = self._normalize_country(job.country)
            experience_level = self._normalize_experience_level(job.experience_level)
            employment_type = self._normalize_employment_type(job.employment_type)

            return {
                "external_id": job.external_id,
                "source": job.source,
                "title": title,
                "normalized_title": normalized_title,
                "company": company,
                "url": job.url,
                "apply_url": job.apply_url or job.url,
                "description": job.description or "",
                "description_summary": self._summarize(job.description),
                "country": country,
                "city": job.city or "",
                "remote_type": job.remote_type,
                "salary_min": job.salary_min,
                "salary_max": job.salary_max,
                "salary_currency": job.salary_currency,
                "experience_level": experience_level,
                "employment_type": employment_type,
                "role_category": job.role_category,
                "visa_sponsorship": job.visa_sponsorship,
                "international_hiring": job.international_hiring,
                "relocation_support": job.relocation_support,
                "posting_date": job.posting_date,
                "closing_date": job.closing_date,
                "fingerprint": job.fingerprint,
                "raw_data": job.raw_data,
            }
        except Exception as e:
            logger.error(f"[Parser] Failed to parse job: {e}")
            return {}

    def _clean_title(self, title: str) -> str:
        cleaned = title.strip()
        for pattern in self.TITLE_CLEANUP:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip()

    def _normalize_title(self, title: str) -> str:
        title_lower = title.lower().strip()
        replacements = {
            "junior ": "", "jr. ": "", "jr ": "",
            "sr. ": "", "senior ": "", "sr ": "",
            "lead ": "", "principal ": "", "staff ": "",
        }
        for old, new in replacements.items():
            title_lower = title_lower.replace(old, new)
        return title_lower.strip()

    def _clean_company(self, company: str) -> str:
        company = company.strip()
        company = re.sub(r",?\s*Inc\.?$|,\s*LLC\.?$|,\s*Ltd\.?$", "", company)
        return company

    def _normalize_country(self, country: Optional[str]) -> str:
        if not country:
            return "Remote"
        country = country.strip()
        country_lower = country.lower()
        if country_lower in self.COUNTRY_MAP:
            return self.COUNTRY_MAP[country_lower]
        return country

    def _normalize_experience_level(self, level: Optional[str]) -> str:
        if not level:
            return "Entry-Level"
        level_lower = level.lower().strip()
        if any(w in level_lower for w in ["entry", "junior", "graduate", "intern"]):
            return "Entry-Level"
        if any(w in level_lower for w in ["mid", "intermediate"]):
            return "Mid-Level"
        if any(w in level_lower for w in ["senior", "sr", "lead"]):
            return "Senior"
        return "Entry-Level"

    def _normalize_employment_type(self, emp_type: str) -> str:
        emp_lower = emp_type.lower()
        if "full" in emp_lower:
            return "full_time"
        if "part" in emp_lower:
            return "part_time"
        if "contract" in emp_lower:
            return "contract"
        if "intern" in emp_lower:
            return "internship"
        if "graduate" in emp_lower:
            return "graduate"
        return "unknown"

    def _summarize(self, description: Optional[str], max_len: int = 500) -> str:
        if not description:
            return ""
        # Strip HTML
        clean = re.sub(r"<[^>]+>", " ", description)
        clean = re.sub(r"\s+", " ", clean).strip()
        if len(clean) <= max_len:
            return clean
        return clean[:max_len] + "..."
