from app.schemas import (
    CollectResponse,
    DailyKeywordCount,
    TrendKeyword,
    KeywordTrend,
    DailyStats,
    TimelineTrend,
)


def test_collect_response_schema():
    resp = CollectResponse(
        collected_categories=15,
        collected_videos=285,
        collected_at="2026-03-20T09:00:00Z",
    )
    assert resp.collected_categories == 15
    assert resp.collected_videos == 285


def test_keyword_trend_schema():
    trend = KeywordTrend(
        days=7,
        keywords=[
            TrendKeyword(
                keyword="뮤직비디오",
                daily=[DailyKeywordCount(date="2026-03-14", count=15)],
            )
        ],
    )
    assert trend.days == 7
    assert len(trend.keywords) == 1
    assert trend.keywords[0].keyword == "뮤직비디오"


def test_timeline_trend_schema():
    trend = TimelineTrend(
        category_id="10",
        days=7,
        daily_stats=[
            DailyStats(
                date="2026-03-14",
                avg_view_count=125000.0,
                avg_like_count=2500.0,
                video_count=20,
            )
        ],
    )
    assert trend.category_id == "10"
    assert trend.daily_stats[0].avg_view_count == 125000.0


def test_keyword_trend_empty():
    trend = KeywordTrend(days=7, keywords=[])
    assert trend.keywords == []


def test_timeline_trend_empty():
    trend = TimelineTrend(category_id="10", days=7, daily_stats=[])
    assert trend.daily_stats == []
