from __future__ import annotations

import asyncio
import hashlib
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import httpx
from fake_useragent import UserAgent
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import get_settings

_FALLBACK_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


@dataclass
class JobResult:
    """Standardized job result from any scraper."""
    source: str
    external_id: str
    title: str
    company: str
    url: str
    apply_url: Optional[str] = None
    description: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    remote_type: str = "unknown"
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    experience_level: Optional[str] = None
    employment_type: str = "unknown"
    visa_sponsorship: bool = False
    international_hiring: bool = False
    relocation_support: bool = False
    posting_date: Optional[datetime] = None
    closing_date: Optional[datetime] = None
    role_category: Optional[str] = None
    raw_data: dict = field(default_factory=dict)

    @property
    def fingerprint(self) -> str:
        key = f"{self.source}:{self.external_id}"
        return hashlib.md5(key.encode()).hexdigest()


class BaseScraper(ABC):
    """Base class for all job scrapers."""

    # Optional per-scraper overrides
    REFERER: Optional[str] = None
    EXTRA_HEADERS: dict = {}
    # Transient HTTP statuses worth a backoff + retry. Deterministic errors
    # (e.g. 500 from a rejected query shape) are intentionally excluded so we
    # fail fast instead of hammering the endpoint.
    RETRYABLE_STATUSES = {429, 502, 503, 504}

    def __init__(self):
        self.settings = get_settings()
        self.ua = UserAgent()
        self._client: Optional[httpx.AsyncClient] = None
        self._request_count = 0
        self._last_request_time = 0.0

    @property
    def name(self) -> str:
        return self.__class__.__name__

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                follow_redirects=True,
                limits=httpx.Limits(max_connections=10),
            )
        return self._client

    def _get_headers(self) -> dict:
        # Realistic browser-like headers reduce bot-blocking on HTML sources.
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            # "br" (Brotli) requires the brotli package (in requirements.txt) so
            # httpx can decode it; gzip/deflate are handled natively.
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        }
        if self.settings.user_agent_rotation:
            try:
                headers["User-Agent"] = self.ua.random
            except Exception:
                headers["User-Agent"] = _FALLBACK_UA
        else:
            headers["User-Agent"] = "JobIntelligenceBot/1.0"
        if self.REFERER:
            headers["Referer"] = self.REFERER
        headers.update(self.EXTRA_HEADERS)
        return headers

    async def _rate_limit(self):
        delay = random.uniform(
            self.settings.scrape_delay_min,
            self.settings.scrape_delay_max,
        )
        elapsed = time.time() - self._last_request_time
        if elapsed < delay:
            await asyncio.sleep(delay - elapsed)
        self._last_request_time = time.time()
        self._request_count += 1

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def fetch(self, url: str, **kwargs) -> httpx.Response:
        await self._rate_limit()
        client = await self.get_client()
        headers = self._get_headers()
        headers.update(kwargs.pop("headers", {}))

        logger.debug(f"[{self.name}] GET {url}")
        response = await client.get(url, headers=headers, **kwargs)

        # Rate-limited / transient server errors: honour Retry-After (capped),
        # then raise so tenacity retries with exponential backoff.
        if response.status_code in self.RETRYABLE_STATUSES:
            retry_after = self._parse_retry_after(response.headers.get("Retry-After"))
            if retry_after:
                logger.warning(
                    f"[{self.name}] {response.status_code} from {url}; "
                    f"waiting {retry_after:.1f}s (Retry-After)"
                )
                await asyncio.sleep(retry_after)

        response.raise_for_status()
        return response

    @staticmethod
    def _parse_retry_after(value: Optional[str], cap: float = 30.0) -> float:
        """Parse a Retry-After header (seconds form) into a capped float."""
        if not value:
            return 0.0
        try:
            return min(float(value), cap)
        except (ValueError, TypeError):
            return 0.0

    @abstractmethod
    async def scrape(self, **kwargs) -> list[JobResult]:
        """Scrape jobs and return standardized results."""
        ...

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
