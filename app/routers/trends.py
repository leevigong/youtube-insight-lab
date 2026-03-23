from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import TrendingVideo
from app.routers.categories import get_youtube_service
from app.schemas import (
    CollectResponse,
    DailyKeywordCount,
    DailyStats,
    KeywordTrend,
    TimelineTrend,
    TrendKeyword,
)
from app.services.collector import collect_trending_videos
from app.services.youtube import YouTubeService

router = APIRouter(tags=["트렌드"])


@router.post(
    "/collect",
    response_model=CollectResponse,
    summary="인기 동영상 수집",
    description="YouTube에서 카테고리별 인기 동영상을 수집하여 DB에 저장합니다.",
)
def collect(
    db: Session = Depends(get_db),
    youtube_service: YouTubeService = Depends(get_youtube_service),
) -> CollectResponse:
    return collect_trending_videos(db=db, youtube_service=youtube_service)


@router.get(
    "/trends/keywords",
    response_model=KeywordTrend,
    summary="키워드 트렌드 조회",
    description="지정 기간 내 인기 동영상 제목에서 추출한 상위 키워드의 일별 추이를 반환합니다.",
)
def get_keyword_trends(
    days: int = Query(default=7, ge=1, le=90, description="조회 기간 (일)"),
    video_type: str | None = Query(
        default=None,
        description="동영상 유형 필터 (regular: 일반, shorts: 쇼츠, 미지정 시 전체)",
    ),
    db: Session = Depends(get_db),
) -> KeywordTrend:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    query = db.query(TrendingVideo).filter(TrendingVideo.collected_at >= cutoff)
    if video_type:
        query = query.filter(TrendingVideo.video_type == video_type)
    videos = query.all()

    # 일별 키워드 빈도 집계
    # {keyword: {date_str: count}}
    keyword_daily: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for video in videos:
        date_str = video.collected_at.strftime("%Y-%m-%d")
        words = video.title.split()
        for word in words:
            if len(word) > 1:
                keyword_daily[word][date_str] += 1

    # 총 빈도 기준 상위 10개
    keyword_totals = {
        kw: sum(daily.values()) for kw, daily in keyword_daily.items()
    }
    top_keywords = sorted(keyword_totals, key=keyword_totals.get, reverse=True)[:10]

    keywords = []
    for kw in top_keywords:
        daily = [
            DailyKeywordCount(date=date, count=count)
            for date, count in sorted(keyword_daily[kw].items())
        ]
        keywords.append(TrendKeyword(keyword=kw, daily=daily))

    return KeywordTrend(days=days, keywords=keywords)


@router.get(
    "/trends/timeline",
    response_model=TimelineTrend,
    summary="타임라인 트렌드 조회",
    description="특정 카테고리의 일별 평균 조회수, 좋아요 수, 동영상 수 추이를 반환합니다.",
)
def get_timeline_trends(
    category_id: str = Query(description="카테고리 ID"),
    days: int = Query(default=7, ge=1, le=90, description="조회 기간 (일)"),
    video_type: str | None = Query(
        default=None,
        description="동영상 유형 필터 (regular: 일반, shorts: 쇼츠, 미지정 시 전체)",
    ),
    db: Session = Depends(get_db),
) -> TimelineTrend:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    query = db.query(TrendingVideo).filter(
        TrendingVideo.category_id == category_id,
        TrendingVideo.collected_at >= cutoff,
    )
    if video_type:
        query = query.filter(TrendingVideo.video_type == video_type)
    videos = query.all()

    # 일별 집계
    daily_data: dict[str, list[TrendingVideo]] = defaultdict(list)
    for video in videos:
        date_str = video.collected_at.strftime("%Y-%m-%d")
        daily_data[date_str].append(video)

    daily_stats = []
    for date_str in sorted(daily_data):
        vids = daily_data[date_str]
        avg_views = sum(v.view_count for v in vids) / len(vids)
        avg_likes = sum(v.like_count for v in vids) / len(vids)
        daily_stats.append(
            DailyStats(
                date=date_str,
                avg_view_count=avg_views,
                avg_like_count=avg_likes,
                video_count=len(vids),
            )
        )

    return TimelineTrend(
        category_id=category_id,
        days=days,
        daily_stats=daily_stats,
    )
