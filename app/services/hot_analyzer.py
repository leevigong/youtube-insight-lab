from collections import Counter
from datetime import datetime, timedelta, timezone

from app.schemas import (
    ContentPattern,
    HotResponse,
    HotVideo,
    KeywordFrequency,
)
from app.services.youtube import YouTubeService, detect_video_type


def analyze_hot_videos(
    keyword_id: int,
    keyword: str,
    youtube_service: YouTubeService,
    days: int = 3,
) -> HotResponse:
    # 최근 N일 이내 업로드된 영상만 검색
    published_after = (
        datetime.now(timezone.utc) - timedelta(days=days)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    videos = youtube_service.search_videos(
        keyword, max_results=20, published_after=published_after,
    )

    now = datetime.now(timezone.utc)

    hot_videos = []
    for v in videos:
        published = datetime.fromisoformat(v.published_at.replace("Z", "+00:00"))
        hours = max((now - published).total_seconds() / 3600, 1)
        views_per_hour = v.stats.view_count / hours
        video_type = detect_video_type(v.duration_seconds, v.title, v.tags)

        hot_videos.append(HotVideo(
            video_id=v.id,
            title=v.title,
            channel_title=v.channel_title,
            published_at=v.published_at,
            hours_since_upload=round(hours, 1),
            view_count=v.stats.view_count,
            like_count=v.stats.like_count,
            comment_count=v.stats.comment_count,
            views_per_hour=round(views_per_hour, 1),
            duration_seconds=v.duration_seconds,
            video_type=video_type,
            tags=v.tags,
        ))

    # 시간당 조회수 내림차순 정렬
    hot_videos.sort(key=lambda x: x.views_per_hour, reverse=True)

    # 상위 10개 영상 패턴 분석
    top_videos = hot_videos[:10]
    pattern = _analyze_pattern(top_videos)

    return HotResponse(
        keyword_id=keyword_id,
        keyword=keyword,
        hot_videos=hot_videos,
        pattern=pattern,
    )


def _analyze_pattern(videos: list[HotVideo]) -> ContentPattern:
    if not videos:
        return ContentPattern(
            top_title_keywords=[],
            avg_duration_seconds=0.0,
            avg_upload_hour=0.0,
            shorts_ratio=0.0,
            common_tags=[],
        )

    # 제목 키워드 추출
    all_words = []
    for v in videos:
        words = [w for w in v.title.split() if len(w) > 1]
        all_words.extend(words)
    top_keywords = Counter(all_words).most_common(10)
    title_keywords = [
        KeywordFrequency(keyword=w, count=c) for w, c in top_keywords
    ]

    # 평균 영상 길이
    avg_duration = sum(v.duration_seconds for v in videos) / len(videos)

    # 평균 업로드 시간
    hours = []
    for v in videos:
        published = datetime.fromisoformat(v.published_at.replace("Z", "+00:00"))
        hours.append(published.hour)
    avg_hour = sum(hours) / len(hours) if hours else 0.0

    # 쇼츠 비율
    shorts_count = sum(1 for v in videos if v.video_type == "shorts")
    shorts_ratio = shorts_count / len(videos)

    # 자주 사용된 태그
    all_tags = []
    for v in videos:
        all_tags.extend(v.tags)
    top_tags = Counter(all_tags).most_common(10)
    common_tags = [
        KeywordFrequency(keyword=t, count=c) for t, c in top_tags
    ]

    return ContentPattern(
        top_title_keywords=title_keywords,
        avg_duration_seconds=round(avg_duration, 1),
        avg_upload_hour=round(avg_hour, 1),
        shorts_ratio=round(shorts_ratio, 2),
        common_tags=common_tags,
    )
