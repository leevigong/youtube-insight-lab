from app.schemas import Video, VideoStats, PopularVideosResponse


def test_video_stats_schema():
    stats = VideoStats(view_count=1000, like_count=50, comment_count=10)
    assert stats.view_count == 1000
    assert stats.like_count == 50
    assert stats.comment_count == 10


def test_video_schema():
    video = Video(
        id="abc123",
        title="Test Video",
        channel_title="Test Channel",
        published_at="2026-03-19T12:00:00Z",
        stats=VideoStats(view_count=1000, like_count=50, comment_count=10),
    )
    assert video.id == "abc123"
    assert video.title == "Test Video"
    assert video.channel_title == "Test Channel"
    assert video.stats.view_count == 1000


def test_popular_videos_response_schema():
    resp = PopularVideosResponse(
        category_id="10",
        videos=[
            Video(
                id="abc123",
                title="Test Video",
                channel_title="Test Channel",
                published_at="2026-03-19T12:00:00Z",
                stats=VideoStats(view_count=1000, like_count=50, comment_count=10),
            ),
        ],
    )
    assert resp.category_id == "10"
    assert len(resp.videos) == 1
