from app.schemas import (
    VideoDetail, VideoStats, KeywordFrequency, DurationDistribution, CategoryAnalysis,
)


def test_video_detail_schema():
    detail = VideoDetail(
        id="abc123", title="테스트 영상", channel_title="테스트 채널",
        published_at="2026-03-19T12:00:00Z",
        stats=VideoStats(view_count=150000, like_count=3000, comment_count=200),
        duration_seconds=933, tags=["키워드1", "키워드2"],
        thumbnail_url="https://i.ytimg.com/vi/abc123/maxresdefault.jpg",
    )
    assert detail.id == "abc123"
    assert detail.duration_seconds == 933
    assert detail.tags == ["키워드1", "키워드2"]


def test_video_detail_empty_tags():
    detail = VideoDetail(
        id="abc123", title="테스트 영상", channel_title="테스트 채널",
        published_at="2026-03-19T12:00:00Z",
        stats=VideoStats(view_count=100, like_count=0, comment_count=0),
        duration_seconds=60, tags=[], thumbnail_url="https://example.com/thumb.jpg",
    )
    assert detail.tags == []


def test_keyword_frequency_schema():
    kf = KeywordFrequency(keyword="뮤직비디오", count=8)
    assert kf.keyword == "뮤직비디오"
    assert kf.count == 8


def test_duration_distribution_schema():
    dd = DurationDistribution(short=5, medium=12, long=3)
    assert dd.short == 5
    assert dd.medium == 12
    assert dd.long == 3


def test_category_analysis_schema():
    analysis = CategoryAnalysis(
        category_id="10", video_count=20,
        keywords=[KeywordFrequency(keyword="뮤직비디오", count=8)],
        avg_upload_hour=15.3, avg_duration_seconds=245.7,
        duration_distribution=DurationDistribution(short=5, medium=12, long=3),
        thumbnail_urls=["https://example.com/thumb1.jpg"],
    )
    assert analysis.category_id == "10"
    assert analysis.video_count == 20
    assert len(analysis.keywords) == 1
