#!/usr/bin/env python3
"""One-off backfill for the jobs.role_category column.

`init_db()` adds the column to existing databases, but rows stored before the
column existed have NULL role_category. This classifies each existing job's
title with the configured role taxonomy and fills the column in place.

Usage:
    python scripts/backfill_role_category.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger

from src.config.settings import get_settings
from src.storage.models import init_db, get_session_local, Job


def backfill() -> int:
    init_db()  # ensures the column exists
    settings = get_settings()
    session = get_session_local()()
    updated = 0
    try:
        for job in session.query(Job).all():
            category = settings.classify_role(job.title)
            if category and job.role_category != category:
                job.role_category = category
                updated += 1
        session.commit()
    finally:
        session.close()
    return updated


if __name__ == "__main__":
    count = backfill()
    logger.info(f"Backfilled role_category on {count} job(s)")
