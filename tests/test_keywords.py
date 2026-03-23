from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Keyword, KeywordVideo
from app.routers.keywords import get_youtube_service
from app.services.keyword_collector import collect_keyword_videos
from app.services.surge_detector import detect_surge
from app.services.youtube import YouTubeService

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


MOCK_SEARCH_RESPONSE = {
    "items": [
        {"id": {"videoId": "vid1"}},
        {"id": {"videoId": "vid2"}},
    ]
}

MOCK_DETAILS_RESPONSE = {
    "items": [
        {
            "id": "vid1",
            "snippet": {
                "title": "삼성전자 실적 분석",
                "channelTitle": "경제채널A",
                "publishedAt": "2026-03-20T10:00:00Z",
                "tags": ["삼성전자", "주식"],
                "thumbnails": {"high": {"url": "https://example.com/vid1.jpg"}},
            },
            "statistics": {
                "viewCount": "500000",
                "likeCount": "10000",
                "commentCount": "500",
            },
            "contentDetails": {"duration": "PT15M30S"},
        },
        {
            "id": "vid2",
            "snippet": {
                "title": "삼성전자 주가 전망 #shorts",
                "channelTitle": "경제채널B",
                "publishedAt": "2026-03-20T14:00:00Z",
                "thumbnails": {"high": {"url": "https://example.com/vid2.jpg"}},
            },
            "statistics": {
                "viewCount": "200000",
                "likeCount": "5000",
                "commentCount": "200",
            },
            "contentDetails": {"duration": "PT45S"},
        },
    ]
}


def _mock_youtube_service():
    mock_client = MagicMock()
    mock_client.search().list().execute.return_value = MOCK_SEARCH_RESPONSE
    mock_client.videos().list().execute.return_value = MOCK_DETAILS_RESPONSE
    return YouTubeService(client=mock_client)


@pytest.fixture()
def client():
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_youtube_service] = _mock_youtube_service
    yield TestClient(app)
    app.dependency_overrides.clear()


# --- 키워드 CRUD 테스트 ---


def test_create_keyword(client):
    response = client.post("/keywords", json={"keyword": "삼성전자"})
    assert response.status_code == 201
    data = response.json()
    assert data["keyword"] == "삼성전자"
    assert "id" in data
    assert "created_at" in data


def test_create_duplicate_keyword(client):
    client.post("/keywords", json={"keyword": "삼성전자"})
    response = client.post("/keywords", json={"keyword": "삼성전자"})
    assert response.status_code == 409


def test_list_keywords(client):
    client.post("/keywords", json={"keyword": "삼성전자"})
    client.post("/keywords", json={"keyword": "SK하이닉스"})

    response = client.get("/keywords")
    assert response.status_code == 200
    data = response.json()
    assert len(data["keywords"]) == 2


def test_list_keywords_empty(client):
    response = client.get("/keywords")
    assert response.status_code == 200
    assert response.json()["keywords"] == []


def test_delete_keyword(client):
    create_resp = client.post("/keywords", json={"keyword": "삼성전자"})
    keyword_id = create_resp.json()["id"]

    response = client.delete(f"/keywords/{keyword_id}")
    assert response.status_code == 204

    list_resp = client.get("/keywords")
    assert list_resp.json()["keywords"] == []


def test_delete_keyword_not_found(client):
    response = client.delete("/keywords/999")
    assert response.status_code == 404


# --- 키워드 수집 테스트 ---


def test_collect_keyword_videos():
    db = _TestSession()
    Base.metadata.create_all(_test_engine)

    kw = Keyword(keyword="삼성전자")
    db.add(kw)
    db.commit()
    db.refresh(kw)

    service = _mock_youtube_service()
    result = collect_keyword_videos(db=db, youtube_service=service)

    assert result.collected_keywords == 1
    assert result.collected_videos == 2

    videos = db.query(KeywordVideo).all()
    assert len(videos) == 2
    assert videos[0].keyword_id == kw.id
    db.close()


def test_collect_keyword_videos_empty():
    db = _TestSession()
    Base.metadata.create_all(_test_engine)

    service = _mock_youtube_service()
    result = collect_keyword_videos(db=db, youtube_service=service)

    assert result.collected_keywords == 0
    assert result.collected_videos == 0
    db.close()


def test_collect_endpoint(client):
    client.post("/keywords", json={"keyword": "삼성전자"})

    response = client.post("/keywords/collect")
    assert response.status_code == 200
    data = response.json()
    assert data["collected_keywords"] == 1
    assert data["collected_videos"] == 2


# --- 키워드 영상 조회 테스트 ---


def test_list_keyword_videos(client):
    # 키워드 등록 + 수집
    create_resp = client.post("/keywords", json={"keyword": "삼성전자"})
    keyword_id = create_resp.json()["id"]
    client.post("/keywords/collect")

    response = client.get(f"/keywords/{keyword_id}/videos")
    assert response.status_code == 200
    data = response.json()
    assert data["keyword"] == "삼성전자"
    assert len(data["videos"]) == 2


def test_list_keyword_videos_not_found(client):
    response = client.get("/keywords/999/videos")
    assert response.status_code == 404


# --- 급등 감지 테스트 ---


def _seed_surge_data(db_session):
    """급등 감지 테스트용 데이터 시딩"""
    kw = Keyword(keyword="삼성전자")
    db_session.add(kw)
    db_session.commit()
    db_session.refresh(kw)

    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    today = datetime.now(timezone.utc)

    videos = [
        # vid1: 어제 10만 → 오늘 50만 (5배 증가 = 급등)
        KeywordVideo(
            keyword_id=kw.id, video_id="vid1", title="삼성전자 대박 뉴스",
            channel_title="Ch1", published_at="2026-03-20T10:00:00Z",
            view_count=100000, like_count=2000, comment_count=100,
            video_type="regular", duration_seconds=600, collected_at=yesterday,
        ),
        KeywordVideo(
            keyword_id=kw.id, video_id="vid1", title="삼성전자 대박 뉴스",
            channel_title="Ch1", published_at="2026-03-20T10:00:00Z",
            view_count=500000, like_count=10000, comment_count=500,
            video_type="regular", duration_seconds=600, collected_at=today,
        ),
        # vid2: 어제 20만 → 오늘 22만 (0.1배 증가 = 정상)
        KeywordVideo(
            keyword_id=kw.id, video_id="vid2", title="삼성전자 일상 분석",
            channel_title="Ch2", published_at="2026-03-20T14:00:00Z",
            view_count=200000, like_count=4000, comment_count=200,
            video_type="regular", duration_seconds=900, collected_at=yesterday,
        ),
        KeywordVideo(
            keyword_id=kw.id, video_id="vid2", title="삼성전자 일상 분석",
            channel_title="Ch2", published_at="2026-03-20T14:00:00Z",
            view_count=220000, like_count=4400, comment_count=220,
            video_type="regular", duration_seconds=900, collected_at=today,
        ),
    ]
    for v in videos:
        db_session.add(v)
    db_session.commit()

    return kw


def test_detect_surge():
    db = _TestSession()
    Base.metadata.create_all(_test_engine)

    kw = _seed_surge_data(db)
    result = detect_surge(db, kw.id, days=7)

    assert result.keyword == "삼성전자"
    assert len(result.surge_videos) == 1
    assert result.surge_videos[0].video_id == "vid1"
    assert result.surge_videos[0].growth_rate == 4.0
    assert result.surge_videos[0].view_increase == 400000
    db.close()


def test_detect_surge_no_data():
    db = _TestSession()
    Base.metadata.create_all(_test_engine)

    kw = Keyword(keyword="테스트")
    db.add(kw)
    db.commit()
    db.refresh(kw)

    result = detect_surge(db, kw.id, days=7)
    assert result.surge_videos == []
    db.close()


def test_surge_endpoint(client):
    # 직접 DB에 시딩
    db = _TestSession()
    kw = _seed_surge_data(db)
    keyword_id = kw.id
    db.close()

    response = client.get(f"/keywords/{keyword_id}/surge?days=7")
    assert response.status_code == 200
    data = response.json()
    assert data["keyword"] == "삼성전자"
    assert len(data["surge_videos"]) == 1
    assert data["surge_videos"][0]["video_id"] == "vid1"


def test_surge_endpoint_not_found(client):
    response = client.get("/keywords/999/surge")
    assert response.status_code == 404


# --- Hot 분석 테스트 ---


def test_hot_endpoint(client):
    create_resp = client.post("/keywords", json={"keyword": "삼성전자"})
    keyword_id = create_resp.json()["id"]

    response = client.get(f"/keywords/{keyword_id}/hot?days=3")
    assert response.status_code == 200
    data = response.json()
    assert data["keyword"] == "삼성전자"
    assert len(data["hot_videos"]) == 2
    # 시간당 조회수 내림차순 정렬 확인
    assert data["hot_videos"][0]["views_per_hour"] >= data["hot_videos"][1]["views_per_hour"]
    # 패턴 분석 포함 확인
    assert "pattern" in data
    assert "top_title_keywords" in data["pattern"]
    assert "avg_duration_seconds" in data["pattern"]
    assert "shorts_ratio" in data["pattern"]


def test_hot_endpoint_not_found(client):
    response = client.get("/keywords/999/hot")
    assert response.status_code == 404


def test_hot_pattern_analysis(client):
    create_resp = client.post("/keywords", json={"keyword": "삼성전자"})
    keyword_id = create_resp.json()["id"]

    response = client.get(f"/keywords/{keyword_id}/hot?days=3")
    pattern = response.json()["pattern"]

    # vid2가 45초 shorts → shorts_ratio > 0
    assert pattern["shorts_ratio"] > 0
    assert pattern["avg_duration_seconds"] > 0
    assert len(pattern["top_title_keywords"]) > 0


# --- 스케줄러 테스트 ---


def test_scheduler_has_keyword_collection_job():
    from app.scheduler import create_scheduler

    scheduler = create_scheduler()
    jobs = scheduler.get_jobs()

    job_ids = [j.id for j in jobs]
    assert "collect_keyword_videos" in job_ids
    assert len(jobs) == 2  # trending + keyword
