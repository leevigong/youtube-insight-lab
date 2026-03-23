from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.categories import get_youtube_service
from app.schemas import VideoDetail, VideoStats
from app.services.analyzer import analyze_category
from app.services.youtube import YouTubeService


def _make_video(
    id,
    title,
    published_at,
    duration_seconds,
    tags=None,
    thumbnail_url="https://example.com/thumb.jpg",
    video_type="regular",
):
    return VideoDetail(
        id=id,
        title=title,
        channel_title="채널",
        published_at=published_at,
        stats=VideoStats(view_count=1000, like_count=50, comment_count=10),
        duration_seconds=duration_seconds,
        video_type=video_type,
        tags=tags or [],
        thumbnail_url=thumbnail_url,
    )


SAMPLE_VIDEOS = [
    _make_video(
        "v1",
        "뮤직비디오 공식 MV",
        "2026-03-19T10:00:00Z",
        180,
        thumbnail_url="https://example.com/v1.jpg",
    ),
    _make_video(
        "v2",
        "뮤직비디오 라이브 공연",
        "2026-03-19T14:00:00Z",
        600,
        thumbnail_url="https://example.com/v2.jpg",
    ),
    _make_video(
        "v3",
        "공식 무대 영상",
        "2026-03-19T20:00:00Z",
        1500,
        thumbnail_url="https://example.com/v3.jpg",
    ),
]

MOCK_POPULAR_DETAILS_API_RESPONSE = {
    "items": [
        {
            "id": "vid1",
            "snippet": {
                "title": "뮤직비디오 공식 MV",
                "channelTitle": "채널A",
                "publishedAt": "2026-03-19T10:00:00Z",
                "tags": ["음악"],
                "thumbnails": {"high": {"url": "https://example.com/vid1.jpg"}},
            },
            "statistics": {
                "viewCount": "100000",
                "likeCount": "2000",
                "commentCount": "100",
            },
            "contentDetails": {"duration": "PT3M"},
        },
        {
            "id": "vid2",
            "snippet": {
                "title": "뮤직비디오 라이브 무대",
                "channelTitle": "채널B",
                "publishedAt": "2026-03-19T14:00:00Z",
                "thumbnails": {"default": {"url": "https://example.com/vid2.jpg"}},
            },
            "statistics": {"viewCount": "50000"},
            "contentDetails": {"duration": "PT10M"},
        },
    ]
}


def _mock_analysis_youtube_service():
    mock_client = MagicMock()
    mock_client.videos().list().execute.return_value = MOCK_POPULAR_DETAILS_API_RESPONSE
    return YouTubeService(client=mock_client)


@pytest.fixture()
def analysis_client():
    app.dependency_overrides[get_youtube_service] = _mock_analysis_youtube_service
    yield TestClient(app)
    app.dependency_overrides.clear()


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
    assert result.thumbnail_urls == [
        "https://example.com/v1.jpg",
        "https://example.com/v2.jpg",
        "https://example.com/v3.jpg",
    ]


def test_analyze_category_video_count():
    result = analyze_category("10", SAMPLE_VIDEOS)
    assert result.category_id == "10"
    assert result.video_count == 3


def test_analyze_category_keywords_max_10():
    videos = [
        _make_video(f"v{i}", f"word{i} extra{i} bonus", "2026-03-19T12:00:00Z", 300)
        for i in range(11)
    ]
    result = analyze_category("10", videos)
    assert len(result.keywords) <= 10


def test_category_analysis_endpoint(analysis_client):
    response = analysis_client.get("/categories/10/analysis")
    assert response.status_code == 200
    data = response.json()
    assert data["category_id"] == "10"
    assert data["video_count"] == 2
    assert len(data["keywords"]) > 0
    assert data["avg_upload_hour"] == 12.0
    assert data["avg_duration_seconds"] == 390.0
    assert data["duration_distribution"]["short"] == 1
    assert data["duration_distribution"]["medium"] == 1
    assert len(data["thumbnail_urls"]) == 2
