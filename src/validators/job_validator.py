from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from loguru import logger


class JobValidator:
    """Validates job listings for legitimacy and quality."""

    SCAM_INDICATORS = [
        "make money fast", "work from home guaranteed",
        "no experience needed", "earn $", "wire transfer",
        "send money", "pay upfront", "mlm", "pyramid",
        "crypto investment", "binary options",
    ]

    STAFFING_KEYWORDS = [
        "staffing", "staffing agency", "recruitment agency",
        "talent solutions", "human resources solutions",
        "consulting group", "workforce solutions",
    ]

    def __init__(self, max_age_days: int = 14):
        self.max_age_days = max_age_days

    def validate(self, job: dict) -> tuple[bool, float, list[str]]:
        """
        Validate a job listing.
        Returns (is_valid, confidence_score, rejection_reasons).
        """
        reasons = []
        score = 1.0

        # Check for scam indicators
        scam_score = self._check_scam(job)
        if scam_score > 0.5:
            reasons.append("scam_indicators")
            score -= scam_score

        # Check URL validity
        url_score = self._check_url(job)
        if url_score < 0.3:
            reasons.append("invalid_url")
            score += url_score - 0.3

        # Check posting freshness
        fresh_score = self._check_freshness(job)
        if fresh_score < 0.3:
            reasons.append("too_old")
            score += fresh_score - 0.3

        # Check data completeness
        complete_score = self._check_completeness(job)
        if complete_score < 0.5:
            reasons.append("incomplete_data")
            score += complete_score - 0.5

        # Check for staffing agency
        if self._is_staffing_agency(job):
            reasons.append("staffing_agency")
            score -= 0.3

        # Clamp score
        score = max(0.0, min(1.0, score))
        is_valid = score >= 0.5 and len(reasons) == 0

        return is_valid, round(score, 3), reasons

    def _check_scam(self, job: dict) -> float:
        text = f"{job.get('title', '')} {job.get('description', '')}".lower()
        hits = sum(1 for indicator in self.SCAM_INDICATORS if indicator in text)
        return min(hits * 0.3, 1.0)

    def _check_url(self, job: dict) -> float:
        url = job.get("url", "")
        if not url:
            return 0.0
        if not url.startswith(("http://", "https://")):
            return 0.1
        if len(url) < 10:
            return 0.2
        return 1.0

    def _check_freshness(self, job: dict) -> float:
        posting_date = job.get("posting_date")
        if not posting_date:
            return 0.5  # Unknown, give benefit of doubt

        if isinstance(posting_date, str):
            try:
                posting_date = datetime.fromisoformat(posting_date.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                return 0.5

        if not posting_date.tzinfo:
            posting_date = posting_date.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        age_days = (now - posting_date).days

        if age_days <= self.max_age_days:
            return 1.0
        elif age_days <= self.max_age_days * 2:
            return 0.5
        else:
            return 0.1

    def _check_completeness(self, job: dict) -> float:
        required_fields = ["title", "company", "url"]
        optional_fields = ["country", "description", "posting_date", "experience_level"]

        required_score = sum(1 for f in required_fields if job.get(f)) / len(required_fields)
        optional_score = sum(1 for f in optional_fields if job.get(f)) / len(optional_fields)

        return required_score * 0.7 + optional_score * 0.3

    def _is_staffing_agency(self, job: dict) -> bool:
        company = job.get("company", "").lower()
        description = job.get("description", "").lower()
        text = f"{company} {description}"
        return any(kw in text for kw in self.STAFFING_KEYWORDS)
