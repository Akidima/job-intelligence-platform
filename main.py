#!/usr/bin/env python3
"""Main entry point for the Job Intelligence Platform."""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger

from src.pipeline import JobIntelligencePipeline
from src.storage.models import init_db


def setup_logging():
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
        level="INFO",
    )
    logger.add(
        "data/logs/pipeline_{time}.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
    )


async def main():
    setup_logging()
    logger.info("=== Job Intelligence Platform ===")

    # Initialize database
    logger.info("Initializing database...")
    init_db()

    # Run pipeline
    user_profile = {
        "skills": ["sql", "excel", "python"],
        "experience_years": 1,
        "projects": ["retail dashboard", "etl pipeline"],
    }

    pipeline = JobIntelligencePipeline(user_profile=user_profile)
    results = await pipeline.run()

    # Print summary
    print("\n" + "=" * 60)
    print("  JOB INTELLIGENCE REPORT")
    print("=" * 60)
    print(f"  Run ID:       {results.get('run_id', 'N/A')}")
    print(f"  Status:       {results.get('status', 'N/A')}")
    print(f"  Raw Jobs:     {results.get('raw_jobs', 0)}")
    print(f"  Valid Jobs:   {results.get('valid_jobs', 0)}")
    print(f"  Rejected:     {results.get('rejected', 0)}")
    print(f"  Stored:       {results.get('stored_jobs', 0)}")

    analytics = results.get("analytics", {})
    summary = analytics.get("summary", {})
    print(f"\n  Companies:    {summary.get('unique_companies', 0)}")
    print(f"  Countries:    {summary.get('unique_locations', 0)}")
    print(f"  Remote %:     {summary.get('remote_percentage', 0)}%")
    print(f"  Visa Jobs:    {summary.get('visa_sponsorship_count', 0)}")

    top_skills = analytics.get("top_skills", [])[:5]
    if top_skills:
        print("\n  Top 5 Skills:")
        for s in top_skills:
            print(f"    - {s['skill']}: {s['count']} jobs")

    top_matches = results.get("job_matches_top_10", [])[:5]
    if top_matches:
        print("\n  Top 5 Job Matches:")
        for m in top_matches:
            print(f"    - {m['match_score']}% | {m['title']} @ {m['company']}")

    exports = results.get("exports", {})
    if exports:
        print("\n  Reports Generated:")
        for key, path in exports.items():
            if path:
                print(f"    - {key}: {path}")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
