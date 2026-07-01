from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/job_intelligence"
    )
    redis_url: str = Field(default="redis://localhost:6379/0")

    # Scraping
    scrape_delay_min: float = Field(default=1.0)
    scrape_delay_max: float = Field(default=3.0)
    max_concurrent_requests: int = Field(default=5)
    user_agent_rotation: bool = Field(default=True)
    max_job_age_days: int = Field(default=14)
    jobs_per_run_min: int = Field(default=50)
    jobs_per_run_max: int = Field(default=100)

    # API Keys
    adzuna_app_id: Optional[str] = Field(default=None)
    adzuna_app_key: Optional[str] = Field(default=None)
    remotive_api_key: Optional[str] = Field(default=None)

    # Welcome to the Jungle. Optional: if you paste the public (search-only)
    # Algolia credentials from the site's network requests, the scraper queries
    # Algolia directly (reliable). Left blank, it falls back to WTTJ's public
    # REST API on a best-effort basis.
    wttj_algolia_app_id: Optional[str] = Field(default=None)
    wttj_algolia_api_key: Optional[str] = Field(default=None)
    wttj_algolia_index: str = Field(default="wttj_jobs_production_en")

    # Notifications
    slack_webhook_url: Optional[str] = Field(default=None)
    discord_webhook_url: Optional[str] = Field(default=None)

    # App
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    data_dir: str = Field(default=str(DATA_DIR))

    # Target config
    target_titles: list[str] = Field(default=[
        "Data Analyst", "Junior Data Analyst", "Graduate Data Analyst",
        "Business Analyst", "Product Analyst", "Analytics Engineer",
        "Data Engineer", "Junior Data Engineer", "BI Developer",
        "Business Intelligence Analyst", "Reporting Analyst",
        "Revenue Operations Analyst", "Marketing Analyst",
        "Business Development Analyst", "Business Development Associate",
        "Junior Data Scientist", "Decision Scientist", "Insights Analyst",
        "Operations Analyst", "Commercial Analyst",
        # Business development
        "Business Development Representative", "Sales Development Representative",
        "Partnerships Analyst", "Growth Analyst",
        # Customer service / success / support
        "Customer Service Representative", "Customer Support Specialist",
        "Customer Success Associate", "Customer Experience Analyst",
        "Technical Support Specialist", "Client Support Associate",
    ])

    # Enabled role categories. Disable a category by removing it here.
    enabled_role_categories: list[str] = Field(default=[
        "analytics", "business_development", "customer_service",
    ])

    # Title-match keywords per category. A job is kept by the discovery filter
    # when its title contains any keyword from an enabled category (substring,
    # case-insensitive). This is the single source of truth for "what counts as
    # a relevant role" across all scrapers and the orchestrator.
    role_category_match: dict[str, list[str]] = Field(default={
        "analytics": [
            "data analyst", "data analytics", "analytics analyst", "business analyst",
            "product analyst", "analytics engineer", "data engineer", "bi analyst",
            "bi developer", "business intelligence", "reporting analyst",
            "insights analyst", "data scientist", "decision scientist", "ml engineer",
            "revenue analyst", "marketing analyst", "operations analyst",
            "commercial analyst", "financial analyst", "risk analyst",
        ],
        "business_development": [
            "business development", "business developer", "bd analyst",
            "bd representative", "sales development", "sdr", "bdr",
            "partnerships analyst", "partnership analyst", "partnerships associate",
            "growth analyst", "market research analyst", "commercial development",
        ],
        "customer_service": [
            "customer service", "customer support", "customer success",
            "customer experience", "customer care", "customer advisor",
            "client support", "client service", "client services",
            "support specialist", "support agent", "support representative",
            "support analyst", "help desk", "helpdesk", "service desk",
            "technical support", "csr",
        ],
    })

    # Search-query terms per category, used by query-driven scrapers
    # (LinkedIn, Adzuna, Welcome to the Jungle, Remotive categories).
    role_category_queries: dict[str, list[str]] = Field(default={
        "analytics": [
            "data analyst", "business analyst", "analytics engineer",
            "data engineer", "business intelligence analyst", "data scientist",
            "marketing analyst", "operations analyst",
        ],
        "business_development": [
            "business development analyst", "business development representative",
            "sales development representative", "partnerships analyst",
        ],
        "customer_service": [
            "customer service", "customer support",
            "customer success", "customer experience",
        ],
    })

    target_locations: list[str] = Field(default=[
        "United States", "United Kingdom", "Germany", "Netherlands",
        "Ireland", "France", "Belgium", "Sweden", "Norway", "Denmark",
        "Finland", "Switzerland", "Austria", "Spain", "Portugal",
        "Italy", "Poland", "Czech Republic", "Luxembourg",
        "Estonia", "Lithuania", "Latvia",
    ])

    target_experience_levels: list[str] = Field(default=[
        "Internship", "Graduate", "Entry-Level", "Associate",
        "Junior", "0-3 years",
    ])

    def active_match_keywords(self) -> list[str]:
        """All title-match keywords for the enabled role categories."""
        kws: list[str] = []
        for cat in self.enabled_role_categories:
            kws.extend(self.role_category_match.get(cat, []))
        return kws

    def active_queries(self) -> list[str]:
        """De-duplicated search-query terms for the enabled role categories."""
        seen: set[str] = set()
        out: list[str] = []
        for cat in self.enabled_role_categories:
            for q in self.role_category_queries.get(cat, []):
                if q.lower() not in seen:
                    seen.add(q.lower())
                    out.append(q)
        return out

    def classify_role(self, title: str) -> Optional[str]:
        """Return the role category a title belongs to, or None if no match."""
        t = (title or "").lower()
        for cat in self.enabled_role_categories:
            if any(kw in t for kw in self.role_category_match.get(cat, [])):
                return cat
        return None


def get_settings() -> Settings:
    return Settings()
