from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from loguru import logger

from src.scrapers.base import BaseScraper, JobResult


class WelcomeToTheJungleScraper(BaseScraper):
    """Scraper for Welcome to the Jungle (welcometothejungle.com).

    WTTJ's website is bot-protected (DataDome), so we never scrape the HTML.
    Its job search is backed by Algolia, and the site ships a public,
    search-only Algolia key to every browser. We query that Algolia index
    directly over HTTP — fast, structured, and deployable without a browser.

    Configure the (public) credentials via ``WTTJ_ALGOLIA_APP_ID`` /
    ``WTTJ_ALGOLIA_API_KEY`` (see ``.env.example``). The key is referer-locked,
    so requests must carry the WTTJ ``Referer``/``Origin`` headers. Without
    credentials the scraper logs guidance and returns nothing.
    """

    SOURCE = "welcometothejungle"
    SITE = "https://www.welcometothejungle.com"
    REFERER = "https://www.welcometothejungle.com/"

    # Target country -> ISO country code for Algolia facet filtering.
    COUNTRY_CODES = {
        "United States": "US", "United Kingdom": "GB", "Germany": "DE",
        "Netherlands": "NL", "Ireland": "IE", "France": "FR", "Belgium": "BE",
        "Sweden": "SE", "Norway": "NO", "Denmark": "DK", "Finland": "FI",
        "Switzerland": "CH", "Austria": "AT", "Spain": "ES", "Portugal": "PT",
        "Italy": "IT", "Poland": "PL", "Czech Republic": "CZ",
        "Luxembourg": "LU", "Estonia": "EE", "Lithuania": "LT", "Latvia": "LV",
    }

    HITS_PER_PAGE = 30
    MAX_PAGES_PER_QUERY = 2
    MAX_RESULTS = 120

    async def scrape(self, **kwargs) -> list[JobResult]:
        app_id = self.settings.wttj_algolia_app_id
        api_key = self.settings.wttj_algolia_api_key
        if not (app_id and api_key):
            logger.info(
                f"[{self.name}] Skipping: set WTTJ_ALGOLIA_APP_ID / "
                f"WTTJ_ALGOLIA_API_KEY to enable (see .env.example)."
            )
            return []

        queries = kwargs.get("queries") or self.settings.active_queries()
        country_codes = self._target_country_codes()

        results: list[JobResult] = []
        seen: set[str] = set()

        for query in queries:
            try:
                hits = await self._search_algolia(query, country_codes)
            except Exception as e:
                logger.warning(f"[{self.name}] query '{query}' failed: {e}")
                continue

            for hit in hits:
                job = self._parse_hit(hit)
                if not job or job.fingerprint in seen:
                    continue
                seen.add(job.fingerprint)
                results.append(job)

            if len(results) >= self.MAX_RESULTS:
                break

        logger.info(f"[{self.name}] Scraped {len(results)} jobs")
        return results

    async def _search_algolia(self, query: str, country_codes: list[str]) -> list[dict]:
        app_id = self.settings.wttj_algolia_app_id
        api_key = self.settings.wttj_algolia_api_key
        index = self.settings.wttj_algolia_index
        url = f"https://{app_id.lower()}-dsn.algolia.net/1/indexes/{index}/query"
        headers = {
            "x-algolia-application-id": app_id,
            "x-algolia-api-key": api_key,
            "Content-Type": "application/json",
            # The search key is referer-restricted to welcometothejungle.com.
            "Referer": self.REFERER,
            "Origin": self.SITE,
        }
        # Country codes go in one OR-group so jobs in any target country match.
        facet = ""
        if country_codes:
            group = [f"offices.country_code:{c}" for c in country_codes]
            facet = f"&facetFilters={json.dumps([group])}"

        client = await self.get_client()
        hits: list[dict] = []
        for page in range(self.MAX_PAGES_PER_QUERY):
            await self._rate_limit()
            params = (
                f"query={query.replace(' ', '%20')}"
                f"&hitsPerPage={self.HITS_PER_PAGE}&page={page}{facet}"
            )
            resp = await client.post(url, headers=headers, json={"params": params})
            resp.raise_for_status()
            data = resp.json()
            page_hits = data.get("hits", [])
            hits.extend(page_hits)
            if page >= data.get("nbPages", 1) - 1 or not page_hits:
                break
        return hits

    def _parse_hit(self, hit: dict) -> Optional[JobResult]:
        try:
            title = hit.get("name") or hit.get("title", "")
            if not title:
                return None

            org = hit.get("organization") or {}
            if isinstance(org, dict):
                company = org.get("name", "")
                org_slug = org.get("slug", "")
            else:
                company, org_slug = str(org), ""
            job_slug = hit.get("slug", "")

            offices = hit.get("offices") or []
            country, city = "", ""
            if offices and isinstance(offices[0], dict):
                country = offices[0].get("country") or offices[0].get("country_code", "")
                city = offices[0].get("city") or ""

            url = (
                f"{self.SITE}/en/companies/{org_slug}/jobs/{job_slug}"
                if org_slug and job_slug
                else f"{self.SITE}/en/jobs"
            )

            posting_date = None
            published = hit.get("published_at")
            if published:
                try:
                    posting_date = datetime.fromisoformat(
                        str(published).replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            min_exp = hit.get("experience_level_minimum")
            experience_level = "Entry-Level"
            if isinstance(min_exp, (int, float)) and min_exp >= 4:
                experience_level = "Senior"

            remote = hit.get("remote")
            remote_type = remote if remote in ("full_remote", "partial", "no", "punctual") else "unknown"

            return JobResult(
                source=self.SOURCE,
                external_id=str(hit.get("objectID") or job_slug or url),
                title=title,
                company=company,
                url=url,
                apply_url=url,
                description=hit.get("summary", ""),
                country=country,
                city=city,
                remote_type=remote_type,
                salary_min=self._as_int(hit.get("salary_minimum")),
                salary_max=self._as_int(hit.get("salary_maximum")),
                salary_currency=hit.get("salary_currency"),
                employment_type=hit.get("contract_type", "unknown") or "unknown",
                experience_level=experience_level,
                posting_date=posting_date,
                raw_data=hit,
            )
        except Exception as e:
            logger.debug(f"[{self.name}] Failed to parse hit: {e}")
            return None

    @staticmethod
    def _as_int(value) -> Optional[int]:
        try:
            return int(value) if value not in (None, "") else None
        except (ValueError, TypeError):
            return None

    def _target_country_codes(self) -> list[str]:
        codes = []
        for loc in self.settings.target_locations:
            code = self.COUNTRY_CODES.get(loc)
            if code and code not in codes:
                codes.append(code)
        return codes
