from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.routers.videos import get_youtube_service as get_videos_youtube_service
from app.schemas import (
    CategoryAnalysis,
    DurationDistribution,
    KeywordFrequency,
    VideoDetail,
    VideoStats,
)
from app.services.youtube import YouTubeService

MOCK_VIDEO_DETAIL_RESPONSE = {
    "items": [
        {
            "id": "abc123",
            "snippet": {
                "title": "테스트 영상 제목",
                "channelTitle": "테스트 채널",
                "publishedAt": "2026-03-19T12:00:00Z",
                "tags": ["태그1", "태그2"],
                "thumbnails": {
                    "default": {"url": "https://i.ytimg.com/vi/abc123/default.jpg"},
                    "medium": {"url": "https://i.ytimg.com/vi/abc123/mqdefault.jpg"},
                    "high": {"url": "https://i.ytimg.com/vi/abc123/hqdefault.jpg"},
                    "maxres": {
                        "url": "https://i.ytimg.com/vi/abc123/maxresdefault.jpg"
                    },
                },
            },
            "statistics": {
                "viewCount": "150000",
                "likeCount": "3000",
                "commentCount": "200",
            },
            "contentDetails": {"duration": "PT15M33S"},
        }
    ]
}

MOCK_VIDEO_NO_OPTIONAL_FIELDS = {
    "items": [
        {
            "id": "xyz789",
            "snippet": {
                "title": "태그 없는 영상",
                "channelTitle": "채널",
                "publishedAt": "2026-03-18T08:00:00Z",
                "thumbnails": {
                    "default": {"url": "https://i.ytimg.com/vi/xyz789/default.jpg"},
                    "high": {"url": "https://i.ytimg.com/vi/xyz789/hqdefault.jpg"},
                },
            },
            "statistics": {"viewCount": "500"},
            "contentDetails": {"duration": "PT30S"},
        }
    ]
}

MOCK_POPULAR_WITH_DETAILS_RESPONSE = {
    "items": [
        {
            "id": "vid1",
            "snippet": {
                "title": "인기 영상 하나",
                "channelTitle": "채널A",
                "publishedAt": "2026-03-18T10:00:00Z",
                "tags": ["음악", "팝"],
                "thumbnails": {
                    "high": {"url": "https://i.ytimg.com/vi/vid1/hqdefault.jpg"}
                },
            },
            "statistics": {
                "viewCount": "200000",
                "likeCount": "5000",
                "commentCount": "300",
            },
            "contentDetails": {"duration": "PT4M30S"},
        },
        {
            "id": "vid2",
            "snippet": {
                "title": "인기 영상 둘",
                "channelTitle": "채널B",
                "publishedAt": "2026-03-17T14:30:00Z",
                "thumbnails": {
                    "default": {"url": "https://i.ytimg.com/vi/vid2/default.jpg"}
                },
            },
            "statistics": {"viewCount": "100000"},
            "contentDetails": {"duration": "PT1H2M"},
        },
    ]
}


def _mock_video_detail_service():
    mock_client = MagicMock()
    mock_client.videos().list().execute.return_value = MOCK_VIDEO_DETAIL_RESPONSE
    return YouTubeService(client=mock_client)


@pytest.fixture()
def client():
    app.dependency_overrides[get_videos_youtube_service] = _mock_video_detail_service
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_video_detail_schema():
    detail = VideoDetail(
        id="abc123",
        title="테스트 영상",
        channel_title="테스트 채널",
        published_at="2026-03-19T12:00:00Z",
        stats=VideoStats(view_count=150000, like_count=3000, comment_count=200),
        duration_seconds=933,
        video_type="regular",
        tags=["키워드1", "키워드2"],
        thumbnail_url="https://i.ytimg.com/vi/abc123/maxresdefault.jpg",
    )
    assert detail.id == "abc123"
    assert detail.duration_seconds == 933
    assert detail.video_type == "regular"
    assert detail.tags == ["키워드1", "키워드2"]


def test_video_detail_empty_tags():
    detail = VideoDetail(
        id="abc123",
        title="테스트 영상",
        channel_title="테스트 채널",
        published_at="2026-03-19T12:00:00Z",
        stats=VideoStats(view_count=100, like_count=0, comment_count=0),
        duration_seconds=60,
        video_type="shorts",
        tags=[],
        thumbnail_url="https://example.com/thumb.jpg",
    )
    assert detail.tags == []
    assert detail.video_type == "shorts"


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
        category_id="10",
        video_count=20,
        keywords=[KeywordFrequency(keyword="뮤직비디오", count=8)],
        avg_upload_hour=15.3,
        avg_duration_seconds=245.7,
        duration_distribution=DurationDistribution(short=5, medium=12, long=3),
        thumbnail_urls=["https://example.com/thumb1.jpg"],
    )
    assert analysis.category_id == "10"
    assert analysis.video_count == 20
    assert len(analysis.keywords) == 1


def test_get_video_detail_includes_video_type(client):
    response = client.get("/videos/abc123/detail")
    assert response.status_code == 200
    data = response.json()
    assert "video_type" in data
    assert data["video_type"] == "regular"


def test_get_video_details():
    mock_youtube = MagicMock()
    mock_youtube.videos().list().execute.return_value = MOCK_VIDEO_DETAIL_RESPONSE
    service = YouTubeService(client=mock_youtube)
    detail = service.get_video_details("abc123")
    assert detail.id == "abc123"
    assert detail.duration_seconds == 933
    assert detail.tags == ["태그1", "태그2"]
    assert detail.thumbnail_url == "https://i.ytimg.com/vi/abc123/maxresdefault.jpg"
    assert detail.stats.view_count == 150000


def test_get_video_details_no_optional_fields():
    mock_youtube = MagicMock()
    mock_youtube.videos().list().execute.return_value = MOCK_VIDEO_NO_OPTIONAL_FIELDS
    service = YouTubeService(client=mock_youtube)
    detail = service.get_video_details("xyz789")
    assert detail.tags == []
    assert detail.stats.like_count == 0
    assert detail.stats.comment_count == 0
    assert detail.duration_seconds == 30
    assert detail.thumbnail_url == "https://i.ytimg.com/vi/xyz789/hqdefault.jpg"


def test_get_video_details_not_found():
    mock_youtube = MagicMock()
    mock_youtube.videos().list().execute.return_value = {"items": []}
    service = YouTubeService(client=mock_youtube)
    with pytest.raises(HTTPException) as exc_info:
        service.get_video_details("nonexistent")
    assert exc_info.value.status_code == 404


def test_get_video_details_api_error():
    mock_youtube = MagicMock()
    mock_youtube.videos().list().execute.side_effect = Exception("API error")
    service = YouTubeService(client=mock_youtube)
    with pytest.raises(HTTPException) as exc_info:
        service.get_video_details("abc123")
    assert exc_info.value.status_code == 502


def test_get_popular_videos_with_details():
    mock_youtube = MagicMock()
    mock_youtube.videos().list().execute.return_value = (
        MOCK_POPULAR_WITH_DETAILS_RESPONSE
    )
    service = YouTubeService(client=mock_youtube)
    videos = service.get_popular_videos_with_details("10")
    assert len(videos) == 2
    assert videos[0].id == "vid1"
    assert videos[0].duration_seconds == 270
    assert videos[0].tags == ["음악", "팝"]
    assert videos[1].id == "vid2"
    assert videos[1].duration_seconds == 3720
    assert videos[1].tags == []
    assert videos[1].stats.like_count == 0


def test_get_video_detail_endpoint(client):
    response = client.get("/videos/abc123/detail")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "abc123"
    assert data["duration_seconds"] == 933
    assert data["tags"] == ["태그1", "태그2"]
    assert data["stats"]["view_count"] == 150000
