"""
Background scheduler for periodic maintenance tasks.

Uses APScheduler to run jobs inside the FastAPI process.
Currently schedules one job: daily cleanup of station events older than 7 days.

The scheduler is started and stopped via the FastAPI lifespan context manager
in main.py, so it starts with the server and shuts down cleanly with it.
"""

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import SessionLocal
from app import models

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def run_cleanup() -> None:
    """
    Delete station events older than 7 days.

    Alerts are never deleted — they are permanent historical records.
    Runs as a scheduled job; uses its own DB session independent of any request.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    with SessionLocal() as db:
        deleted = (
            db.query(models.StationEvent)
            .filter(models.StationEvent.received_at < cutoff)
            .delete(synchronize_session=False)
        )
        db.commit()

    logger.info("Scheduled cleanup complete — deleted %d events older than 7 days.", deleted)


def start_scheduler() -> None:
    """
    Register all jobs and start the scheduler.

    Cleanup runs daily at 03:00 UTC (05:00 Barcelona time in summer).
    Called once during application startup.
    """
    scheduler.add_job(
        run_cleanup,
        trigger=CronTrigger(hour=3, minute=0, timezone="UTC"),
        id="daily_cleanup",
        name="Delete station events older than 7 days",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — daily cleanup scheduled at 03:00 UTC.")


def stop_scheduler() -> None:
    """
    Gracefully shut down the scheduler.

    Called during application shutdown to avoid running jobs
    after the database connection is closed.
    """
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")