import pytest
from unittest.mock import MagicMock

from fastapi import HTTPException

from app.schemas import Video, VideoStats, PopularVideosResponse
from app.services.youtube import YouTubeService


MOCK_VIDEOS_RESPONSE = {
    "items": [
        {
            "id": "vid1",
            "snippet": {
                "title": "Popular Video 1",
                "channelTitle": "Channel A",
                "publishedAt": "2026-03-18T10:00:00Z",
            },
            "statistics": {
                "viewCount": "150000",
                "likeCount": "3000",
                "commentCount": "200",
            },
        },
        {
            "id": "vid2",
            "snippet": {
                "title": "Popular Video 2",
                "channelTitle": "Channel B",
                "publishedAt": "2026-03-17T08:30:00Z",
            },
            "statistics": {
                "viewCount": "80000",
                "likeCount": "1500",
                "commentCount": "100",
            },
        },
    ]
}


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


def test_get_popular_videos():
    mock_youtube = MagicMock()
    mock_youtube.videos().list().execute.return_value = MOCK_VIDEOS_RESPONSE

    service = YouTubeService(client=mock_youtube)
    videos = service.get_popular_videos("10")

    assert len(videos) == 2
    assert videos[0].id == "vid1"
    assert videos[0].title == "Popular Video 1"
    assert videos[0].channel_title == "Channel A"
    assert videos[0].published_at == "2026-03-18T10:00:00Z"
    assert videos[0].stats.view_count == 150000
    assert videos[0].stats.like_count == 3000
    assert videos[0].stats.comment_count == 200
    assert videos[1].id == "vid2"


def test_get_popular_videos_api_error():
    mock_youtube = MagicMock()
    mock_youtube.videos().list().execute.side_effect = Exception("API quota exceeded")

    service = YouTubeService(client=mock_youtube)

    with pytest.raises(HTTPException) as exc_info:
        service.get_popular_videos("10")

    assert exc_info.value.status_code == 502
    assert "API quota exceeded" in exc_info.value.detail
