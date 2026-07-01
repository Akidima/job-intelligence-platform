#!/usr/bin/env python3
"""Scheduler that runs the pipeline every 12 hours."""

import asyncio
import signal
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from src.pipeline import JobIntelligencePipeline
from src.storage.models import init_db

RUN_INTERVAL_SECONDS = 12 * 3600
running = True


def handle_signal(sig, frame):
    global running
    logger.info("Shutdown signal received")
    running = False


def setup_logging():
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.add(str(log_dir / "scheduler_{time}.log"), rotation="10 MB", retention="30 days")


async def run_once():
    pipeline = JobIntelligencePipeline()
    results = await pipeline.run()
    logger.info(f"Pipeline completed: {results.get('status')} - {results.get('valid_jobs', 0)} jobs")


async def main():
    global running
    setup_logging()
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    logger.info("Starting scheduler - runs every 12 hours")
    init_db()

    while running:
        logger.info("Running pipeline...")
        try:
            await run_once()
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")

        logger.info(f"Next run in {RUN_INTERVAL_SECONDS // 3600} hours")
        for _ in range(RUN_INTERVAL_SECONDS):
            if not running:
                break
            await asyncio.sleep(1)

    logger.info("Scheduler stopped")


if __name__ == "__main__":
    asyncio.run(main())
