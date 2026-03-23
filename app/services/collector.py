import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import TrendingVideo
from app.schemas import CollectResponse
from app.services.youtube import YouTubeService

logger = logging.getLogger(__name__)


def collect_trending_videos(
    db: Session, youtube_service: YouTubeService
) -> CollectResponse:
    categories = youtube_service.get_categories()
    assignable = [c for c in categories if c.assignable]

    seen_video_ids: set[str] = set()
    total_videos = 0

    collected_categories = 0
    for category in assignable:
        try:
            videos = youtube_service.get_popular_videos_with_details(category.id)
        except Exception:
            logger.warning(
                "Failed to fetch videos for category %s (%s), skipping",
                category.id,
                category.title,
            )
            continue
        collected_categories += 1
        for video in videos:
            if video.id in seen_video_ids:
                continue
            seen_video_ids.add(video.id)

            record = TrendingVideo(
                video_id=video.id,
                category_id=category.id,
                title=video.title,
                channel_title=video.channel_title,
                view_count=video.stats.view_count,
                like_count=video.stats.like_count,
                comment_count=video.stats.comment_count,
                published_at=video.published_at,
                video_type=video.video_type,
                duration_seconds=video.duration_seconds,
            )
            db.add(record)
            total_videos += 1

    db.commit()

    collected_at = datetime.now(timezone.utc).isoformat()
    logger.info(
        "Collected %d videos from %d categories",
        total_videos,
        len(assignable),
    )

    return CollectResponse(
        collected_categories=collected_categories,
        collected_videos=total_videos,
        collected_at=collected_at,
    )
