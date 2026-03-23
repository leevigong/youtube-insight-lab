import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import SessionLocal
from app.services.collector import collect_trending_videos
from app.services.youtube import YouTubeService
from app.config import get_settings

logger = logging.getLogger(__name__)


def _run_collection():
    """스케줄러에서 호출되는 수집 작업"""
    try:
        settings = get_settings()
        youtube_service = YouTubeService(settings=settings)
        db = SessionLocal()
        try:
            result = collect_trending_videos(db=db, youtube_service=youtube_service)
            logger.info(
                "Scheduled collection complete: %d videos from %d categories",
                result.collected_videos,
                result.collected_categories,
            )
        finally:
            db.close()
    except Exception:
        logger.exception("Scheduled collection failed")


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _run_collection,
        trigger=CronTrigger(hour=0, minute=0, timezone="UTC"),
        id="collect_trending",
        name="collect_trending_videos",
        replace_existing=True,
    )
    return scheduler
