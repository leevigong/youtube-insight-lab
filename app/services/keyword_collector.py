import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Keyword, KeywordVideo
from app.schemas import KeywordCollectResponse
from app.services.youtube import YouTubeService, detect_video_type

logger = logging.getLogger(__name__)


def collect_keyword_videos(
    db: Session, youtube_service: YouTubeService
) -> KeywordCollectResponse:
    keywords = db.query(Keyword).all()
    if not keywords:
        return KeywordCollectResponse(
            collected_keywords=0,
            collected_videos=0,
            collected_at=datetime.now(timezone.utc).isoformat(),
        )

    total_videos = 0
    collected_keywords = 0

    for kw in keywords:
        try:
            videos = youtube_service.search_videos(kw.keyword)
        except Exception:
            logger.warning(
                "Failed to search videos for keyword '%s', skipping",
                kw.keyword,
            )
            continue
        collected_keywords += 1
        for video in videos:
            video_type = detect_video_type(
                video.duration_seconds, video.title, video.tags
            )
            record = KeywordVideo(
                keyword_id=kw.id,
                video_id=video.id,
                title=video.title,
                channel_title=video.channel_title,
                published_at=video.published_at,
                view_count=video.stats.view_count,
                like_count=video.stats.like_count,
                comment_count=video.stats.comment_count,
                video_type=video_type,
                duration_seconds=video.duration_seconds,
            )
            db.add(record)
            total_videos += 1

    db.commit()

    collected_at = datetime.now(timezone.utc).isoformat()
    logger.info(
        "Collected %d videos for %d keywords",
        total_videos,
        collected_keywords,
    )

    return KeywordCollectResponse(
        collected_keywords=collected_keywords,
        collected_videos=total_videos,
        collected_at=collected_at,
    )
