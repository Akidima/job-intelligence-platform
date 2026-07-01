from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from loguru import logger

from src.scrapers.remoteok import RemoteOKScraper
from src.scrapers.remoscraper import RemotiveScraper
from src.scrapers.greenhouse import GreenhouseScraper
from src.scrapers.smartrecruiters import SmartRecruitersScraper
from src.scrapers.adzuna import AdzunaScraper
from src.scrapers.linkedin_rss import LinkedInRSSScraper
from src.scrapers.welcometothejungle import WelcomeToTheJungleScraper
from src.scrapers.base import BaseScraper, JobResult
from src.config.settings import get_settings


class JobDiscoveryEngine:
    """Orchestrates all scrapers to discover jobs from multiple sources."""

    def __init__(self):
        self.settings = get_settings()
        self.scrapers: list[BaseScraper] = []
        self._init_scrapers()

    def _init_scrapers(self):
        self.scrapers = [
            RemoteOKScraper(),
            RemotiveScraper(),
            GreenhouseScraper(),
            SmartRecruitersScraper(),
            AdzunaScraper(),
            LinkedInRSSScraper(),
            WelcomeToTheJungleScraper(),
        ]

    async def discover_all(self) -> list[JobResult]:
        """Run all scrapers concurrently and return combined results."""
        run_id = str(uuid.uuid4())[:8]
        logger.info(f"[Discovery] Starting run {run_id} with {len(self.scrapers)} scrapers")

        all_results: list[JobResult] = []
        errors = []

        tasks = [self._run_scraper(scraper) for scraper in self.scrapers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for scraper, result in zip(self.scrapers, results):
            if isinstance(result, Exception):
                logger.error(f"[Discovery] {scraper.name} failed: {result}")
                errors.append({"scraper": scraper.name, "error": str(result)})
            elif isinstance(result, list):
                all_results.extend(result)
                logger.info(f"[Discovery] {scraper.name}: {len(result)} jobs")

        # Filter for entry-level only
        entry_level = self._filter_entry_level(all_results)

        # Deduplicate
        unique = self._deduplicate(entry_level)

        # Filter by target locations
        location_filtered = self._filter_locations(unique)

        logger.info(
            f"[Discovery] Run {run_id} complete: "
            f"{len(all_results)} raw -> {len(entry_level)} entry-level -> "
            f"{len(unique)} unique -> {len(location_filtered)} in target locations"
        )

        # Clean up scraper connections
        for scraper in self.scrapers:
            await scraper.close()

        return location_filtered

    async def _run_scraper(self, scraper: BaseScraper) -> list[JobResult]:
        try:
            return await scraper.scrape()
        except Exception as e:
            logger.error(f"[Discovery] {scraper.name} error: {e}")
            return []

    def _filter_entry_level(self, jobs: list[JobResult]) -> list[JobResult]:
        """Keep entry-level jobs that belong to an enabled role category.

        A job is kept when it (1) is not a senior posting, (2) is not an
        obviously irrelevant manual-labour role, (3) matches at least one of the
        enabled role categories (analytics / business development / customer
        service — see settings.role_category_match), and (4) reads as
        entry-level. The matched category is recorded on the job for downstream
        analytics.
        """
        target_levels = [l.lower() for l in self.settings.target_experience_levels]
        target_keywords = [
            "junior", "jr", "entry", "graduate", "intern", "associate",
            "trainee", "starter", "beginner", "0-3", "0-2", "0-1",
            "entry-level", "entry level",
        ]
        exclude_keywords = [
            "senior", "sr.", "sr ", "lead", "principal", "staff",
            "director", "vp", "head of", "chief", "manager",
        ]

        # Irrelevant manual-labour / unrelated roles. Note: customer service and
        # call-centre roles are intentionally NOT excluded — they are a target
        # category now (see settings.role_category_match["customer_service"]).
        irrelevant_exclude = [
            "caretaker", "housekeeper", "cleaner", "driver", "warehouse",
            "cashier", "bartender", "cook", "chef", "construction",
            "laborer", "mechanic", "electrician", "plumber", "nurse",
            "caregiver", "security guard", "janitor", "landscaping",
            "courier", "packer", "assembly", "factory", "welder",
        ]

        filtered = []
        for job in jobs:
            title_lower = job.title.lower()

            # Exclude obviously irrelevant roles
            if any(kw in title_lower for kw in irrelevant_exclude):
                continue

            # Explicitly exclude senior positions
            if any(kw in title_lower for kw in exclude_keywords):
                continue

            # Must belong to an enabled role category
            category = self.settings.classify_role(job.title)
            if not category:
                continue

            # Check if matches entry-level criteria
            is_entry = False
            if job.experience_level and job.experience_level.lower() in target_levels:
                is_entry = True
            if any(kw in title_lower for kw in target_keywords):
                is_entry = True

            if is_entry:
                job.role_category = category
                filtered.append(job)

        return filtered

    def _deduplicate(self, jobs: list[JobResult]) -> list[JobResult]:
        """Remove duplicate jobs based on fingerprint."""
        seen = set()
        unique = []

        for job in jobs:
            # Also check title+company similarity
            key = f"{job.title.lower().strip()}:{job.company.lower().strip()}"
            if key not in seen and job.fingerprint not in seen:
                seen.add(key)
                seen.add(job.fingerprint)
                unique.append(job)

        return unique

    def _filter_locations(self, jobs: list[JobResult]) -> list[JobResult]:
        """Keep jobs in target locations or remote."""
        targets = [loc.lower() for loc in self.settings.target_locations]
        remote_keywords = ["remote", "worldwide", "anywhere", "global", "eu", "emea"]

        filtered = []
        for job in jobs:
            country = (job.country or "").lower()
            # Keep remote jobs
            if any(kw in country for kw in remote_keywords):
                filtered.append(job)
                continue
            # Keep jobs in target locations
            if any(target in country for target in targets):
                filtered.append(job)

        return filtered