from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import TrendingVideo  # noqa: F401 — ensures table is registered
from app.routers.categories import get_youtube_service
from app.services.youtube import YouTubeService
from app.schemas import (
    CollectResponse,
    DailyKeywordCount,
    TrendKeyword,
    KeywordTrend,
    DailyStats,
    TimelineTrend,
)


MOCK_CATEGORIES_RESPONSE = {
    "items": [
        {"id": "10", "snippet": {"title": "Music", "assignable": True}},
    ]
}

MOCK_VIDEOS_RESPONSE = {
    "items": [
        {
            "id": "vid1",
            "snippet": {
                "title": "인기 뮤직비디오 공식",
                "channelTitle": "Channel A",
                "publishedAt": "2026-03-18T10:00:00Z",
            },
            "statistics": {
                "viewCount": "150000",
                "likeCount": "3000",
                "commentCount": "200",
            },
        },
    ]
}

_test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSession = sessionmaker(bind=_test_engine)


@pytest.fixture(autouse=True)
def _setup_db():
    Base.metadata.create_all(_test_engine)
    yield
    Base.metadata.drop_all(_test_engine)


def _override_get_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


def _mock_youtube_service():
    mock_client = MagicMock()
    mock_client.videoCategories().list().execute.return_value = (
        MOCK_CATEGORIES_RESPONSE
    )
    mock_client.videos().list().execute.return_value = MOCK_VIDEOS_RESPONSE
    return YouTubeService(client=mock_client)


@pytest.fixture()
def client():
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_youtube_service] = _mock_youtube_service
    yield TestClient(app)
    app.dependency_overrides.clear()


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


def test_post_collect(client):
    response = client.post("/collect")

    assert response.status_code == 200
    data = response.json()
    assert data["collected_categories"] == 1
    assert data["collected_videos"] == 1
    assert "collected_at" in data
