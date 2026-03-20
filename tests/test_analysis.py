from app.schemas import VideoDetail, VideoStats, CategoryAnalysis, KeywordFrequency, DurationDistribution
from app.services.analyzer import analyze_category


def _make_video(id, title, published_at, duration_seconds, tags=None, thumbnail_url="https://example.com/thumb.jpg"):
    return VideoDetail(
        id=id, title=title, channel_title="채널", published_at=published_at,
        stats=VideoStats(view_count=1000, like_count=50, comment_count=10),
        duration_seconds=duration_seconds, tags=tags or [], thumbnail_url=thumbnail_url,
    )


SAMPLE_VIDEOS = [
    _make_video("v1", "뮤직비디오 공식 MV", "2026-03-19T10:00:00Z", 180, thumbnail_url="https://example.com/v1.jpg"),
    _make_video("v2", "뮤직비디오 라이브 공연", "2026-03-19T14:00:00Z", 600, thumbnail_url="https://example.com/v2.jpg"),
    _make_video("v3", "공식 무대 영상", "2026-03-19T20:00:00Z", 1500, thumbnail_url="https://example.com/v3.jpg"),
]


def test_analyze_category_keywords():
    result = analyze_category("10", SAMPLE_VIDEOS)
    keyword_map = {k.keyword: k.count for k in result.keywords}
    assert keyword_map["뮤직비디오"] == 2
    assert keyword_map["공식"] == 2
    assert all(len(k.keyword) > 1 for k in result.keywords)


def test_analyze_category_avg_upload_hour():
    result = analyze_category("10", SAMPLE_VIDEOS)
    assert round(result.avg_upload_hour, 1) == 14.7


def test_analyze_category_avg_duration():
    result = analyze_category("10", SAMPLE_VIDEOS)
    assert result.avg_duration_seconds == 760.0


def test_analyze_category_duration_distribution():
    result = analyze_category("10", SAMPLE_VIDEOS)
    assert result.duration_distribution.short == 1
    assert result.duration_distribution.medium == 1
    assert result.duration_distribution.long == 1


def test_analyze_category_thumbnail_urls():
    result = analyze_category("10", SAMPLE_VIDEOS)
    assert result.thumbnail_urls == ["https://example.com/v1.jpg", "https://example.com/v2.jpg", "https://example.com/v3.jpg"]


def test_analyze_category_video_count():
    result = analyze_category("10", SAMPLE_VIDEOS)
    assert result.category_id == "10"
    assert result.video_count == 3


def test_analyze_category_keywords_max_10():
    videos = [_make_video(f"v{i}", f"word{i} extra{i} bonus", "2026-03-19T12:00:00Z", 300) for i in range(11)]
    result = analyze_category("10", videos)
    assert len(result.keywords) <= 10
