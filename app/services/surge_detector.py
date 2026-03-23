from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import Keyword, KeywordVideo
from app.schemas import SurgeResponse, SurgeVideo


def detect_surge(
    db: Session, keyword_id: int, days: int = 7
) -> SurgeResponse:
    keyword = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not keyword:
        return SurgeResponse(keyword_id=keyword_id, keyword="", surge_videos=[])

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    videos = (
        db.query(KeywordVideo)
        .filter(
            KeywordVideo.keyword_id == keyword_id,
            KeywordVideo.collected_at >= cutoff,
        )
        .order_by(KeywordVideo.collected_at)
        .all()
    )

    # video_id별로 수집 이력을 그룹핑
    # {video_id: [(collected_at, view_count, title, channel_title), ...]}
    video_history: dict[str, list[tuple[datetime, int, str, str]]] = defaultdict(list)
    for v in videos:
        video_history[v.video_id].append(
            (v.collected_at, v.view_count, v.title, v.channel_title)
        )

    # 각 영상의 증가율 계산 (최신 vs 직전)
    growth_rates: dict[str, float] = {}
    video_data: dict[str, dict] = {}

    for video_id, history in video_history.items():
        if len(history) < 2:
            continue

        # 시간순 정렬 후 최신 2개 비교
        history.sort(key=lambda x: x[0])
        prev_collected, prev_views, _, _ = history[-2]
        curr_collected, curr_views, title, channel = history[-1]

        if prev_views == 0:
            growth_rate = float(curr_views) if curr_views > 0 else 0.0
        else:
            growth_rate = (curr_views - prev_views) / prev_views

        growth_rates[video_id] = growth_rate
        video_data[video_id] = {
            "title": title,
            "channel_title": channel,
            "current_view_count": curr_views,
            "previous_view_count": prev_views,
            "view_increase": curr_views - prev_views,
            "growth_rate": growth_rate,
        }

    if not growth_rates:
        return SurgeResponse(
            keyword_id=keyword_id, keyword=keyword.keyword, surge_videos=[]
        )

    # 평균 증가율 계산
    avg_growth = sum(growth_rates.values()) / len(growth_rates)

    surge_videos = []
    for video_id, rate in growth_rates.items():
        reasons = []

        # 기준 1: 증가율 200% 이상
        if rate >= 2.0:
            reasons.append(f"조회수 증가율 {rate:.1f}배 (기준: 2.0배)")

        # 기준 2: 평균 대비 3배 이상
        if avg_growth > 0 and rate >= avg_growth * 3:
            reasons.append(
                f"평균 증가율({avg_growth:.2f}배) 대비 {rate / avg_growth:.1f}배"
            )

        if reasons:
            data = video_data[video_id]
            surge_videos.append(
                SurgeVideo(
                    video_id=video_id,
                    title=data["title"],
                    channel_title=data["channel_title"],
                    current_view_count=data["current_view_count"],
                    previous_view_count=data["previous_view_count"],
                    view_increase=data["view_increase"],
                    growth_rate=round(data["growth_rate"], 2),
                    avg_growth_rate=round(avg_growth, 2),
                    surge_reason=" / ".join(reasons),
                )
            )

    # 증가율 높은 순 정렬
    surge_videos.sort(key=lambda x: x.growth_rate, reverse=True)

    return SurgeResponse(
        keyword_id=keyword_id,
        keyword=keyword.keyword,
        surge_videos=surge_videos,
    )
