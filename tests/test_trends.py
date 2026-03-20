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


from datetime import datetime, timedelta, timezone


def _seed_videos(db_session):
    """테스트용 영상 데이터 시딩"""
    today = datetime.now(timezone.utc)
    yesterday = today - timedelta(days=1)

    videos = [
        TrendingVideo(
            video_id="v1",
            category_id="10",
            title="뮤직비디오 공식 테스트",
            channel_title="Ch1",
            view_count=100000,
            like_count=2000,
            comment_count=100,
            published_at="2026-03-18T10:00:00Z",
            collected_at=today,
        ),
        TrendingVideo(
            video_id="v2",
            category_id="10",
            title="뮤직비디오 인기 영상",
            channel_title="Ch2",
            view_count=200000,
            like_count=4000,
            comment_count=200,
            published_at="2026-03-18T10:00:00Z",
            collected_at=today,
        ),
        TrendingVideo(
            video_id="v3",
            category_id="20",
            title="뮤직비디오 공식 어제",
            channel_title="Ch3",
            view_count=50000,
            like_count=1000,
            comment_count=50,
            published_at="2026-03-17T10:00:00Z",
            collected_at=yesterday,
        ),
    ]
    for v in videos:
        db_session.add(v)
    db_session.commit()


@pytest.fixture()
def seeded_client():
    Base.metadata.create_all(_test_engine)
    db = _TestSession()
    _seed_videos(db)
    db.close()

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_youtube_service] = _mock_youtube_service
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(_test_engine)


def test_get_trends_keywords(seeded_client):
    response = seeded_client.get("/trends/keywords?days=7")

    assert response.status_code == 200
    data = response.json()
    assert data["days"] == 7
    assert isinstance(data["keywords"], list)
    assert len(data["keywords"]) > 0

    # "뮤직비디오"는 3개 영상 모두에 포함 → 가장 빈도 높음
    keyword_names = [k["keyword"] for k in data["keywords"]]
    assert "뮤직비디오" in keyword_names


def test_get_trends_keywords_excludes_short_words(seeded_client):
    response = seeded_client.get("/trends/keywords?days=7")

    data = response.json()
    keyword_names = [k["keyword"] for k in data["keywords"]]
    # 1글자 단어는 제외
    for kw in keyword_names:
        assert len(kw) > 1


def test_get_trends_keywords_empty():
    Base.metadata.create_all(_test_engine)
    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app)

    response = client.get("/trends/keywords?days=7")

    assert response.status_code == 200
    data = response.json()
    assert data["days"] == 7
    assert data["keywords"] == []

    app.dependency_overrides.clear()
    Base.metadata.drop_all(_test_engine)


def test_get_trends_timeline(seeded_client):
    response = seeded_client.get("/trends/timeline?category_id=10&days=7")

    assert response.status_code == 200
    data = response.json()
    assert data["category_id"] == "10"
    assert data["days"] == 7
    assert isinstance(data["daily_stats"], list)
    assert len(data["daily_stats"]) > 0

    # 카테고리 10: 오늘 v1(100000), v2(200000) → avg=150000
    today_stats = data["daily_stats"][-1]
    assert today_stats["avg_view_count"] == 150000.0
    assert today_stats["avg_like_count"] == 3000.0
    assert today_stats["video_count"] == 2


def test_get_trends_timeline_empty_category(seeded_client):
    response = seeded_client.get("/trends/timeline?category_id=99&days=7")

    assert response.status_code == 200
    data = response.json()
    assert data["category_id"] == "99"
    assert data["daily_stats"] == []


def test_get_trends_timeline_empty_db():
    Base.metadata.create_all(_test_engine)
    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app)

    response = client.get("/trends/timeline?category_id=10&days=7")

    assert response.status_code == 200
    data = response.json()
    assert data["daily_stats"] == []

    app.dependency_overrides.clear()
    Base.metadata.drop_all(_test_engine)
