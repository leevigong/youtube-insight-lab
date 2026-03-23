# Phase 4: 트렌드 추적 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 인기 영상 데이터를 DB에 축적하고, 시간에 따른 키워드/통계 트렌드를 분석하는 API를 제공한다.

**Architecture:** SQLAlchemy 2.0 ORM으로 TrendingVideo 모델을 정의하고 SQLite에 저장한다. Collector 서비스가 YouTube API에서 모든 assignable 카테고리의 인기 영상을 수집하고, APScheduler가 매일 00:00 UTC에 자동 수집을 실행한다. 트렌드 조회 엔드포인트가 일별 키워드 빈도와 카테고리별 시계열 통계를 반환한다.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, APScheduler, pytest

**Spec:** `docs/superpowers/specs/2026-03-20-phase4-trend-tracking-design.md`

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `pyproject.toml` | sqlalchemy, apscheduler 의존성 추가 |
| Modify | `app/config.py` | database_url 설정 추가 |
| Create | `app/database.py` | SQLAlchemy 엔진, 세션, Base, get_db |
| Create | `app/models.py` | TrendingVideo ORM 모델 |
| Modify | `app/schemas.py` | CollectResponse, DailyKeywordCount, TrendKeyword, KeywordTrend, DailyStats, TimelineTrend 추가 |
| Create | `app/services/collector.py` | collect_trending_videos 수집 로직 |
| Create | `app/routers/trends.py` | POST /collect, GET /trends/keywords, GET /trends/timeline |
| Create | `app/scheduler.py` | APScheduler 설정 + 수집 작업 등록 |
| Modify | `app/main.py` | trends router 등록 + lifespan으로 스케줄러 연동 |
| Create | `tests/test_collector.py` | Collector 서비스 테스트 |
| Create | `tests/test_trends.py` | 트렌드 엔드포인트 테스트 |

---

### Task 1: 의존성 추가 + Config 수정

**Files:**
- Modify: `pyproject.toml`
- Modify: `app/config.py`

- [ ] **Step 1: pyproject.toml에 sqlalchemy, apscheduler 추가**
```toml
# pyproject.toml — dependencies 배열에 추가
dependencies = [
    "fastapi",
    "uvicorn",
    "google-api-python-client",
    "pandas",
    "pydantic-settings",
    "python-dotenv",
    "sqlalchemy",
    "apscheduler",
]
```

- [ ] **Step 2: config.py에 database_url 필드 추가**
```python
# app/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    youtube_api_key: str
    database_url: str = "sqlite:///./data/trending.db"

    model_config = {"env_file": ".env"}


REGION_CODE = "KR"


def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 3: 의존성 설치 확인**
```bash
uv sync
# Expected: 정상 설치 완료
```

- [ ] **Step 4: 기존 테스트 통과 확인**
```bash
python -m pytest tests/ -q
# Expected: all passed
```

- [ ] **Step 5: 커밋**
```bash
git add pyproject.toml app/config.py uv.lock
git commit -m "feat: add sqlalchemy, apscheduler deps and database_url config"
```

---

### Task 2: DB 설정 + ORM 모델

**Files:**
- Create: `app/database.py`
- Create: `app/models.py`
- Create: `tests/test_collector.py` (모델 테스트만 우선)

- [ ] **Step 1: 모델 테스트 작성 (tests/test_collector.py)**
```python
# tests/test_collector.py
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import TrendingVideo


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_trending_video_model_creation():
    db = _make_session()
    video = TrendingVideo(
        video_id="abc123",
        category_id="10",
        title="Test Video",
        channel_title="Test Channel",
        view_count=1000,
        like_count=50,
        comment_count=10,
        published_at="2026-03-19T12:00:00Z",
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    assert video.id is not None
    assert video.video_id == "abc123"
    assert video.category_id == "10"
    assert video.title == "Test Video"
    assert video.collected_at is not None


def test_trending_video_duplicate_video_id_allowed():
    db = _make_session()
    v1 = TrendingVideo(
        video_id="abc123",
        category_id="10",
        title="Test Video Day 1",
        channel_title="Channel",
        view_count=1000,
        like_count=50,
        comment_count=10,
        published_at="2026-03-19T12:00:00Z",
    )
    v2 = TrendingVideo(
        video_id="abc123",
        category_id="10",
        title="Test Video Day 2",
        channel_title="Channel",
        view_count=2000,
        like_count=100,
        comment_count=20,
        published_at="2026-03-19T12:00:00Z",
    )
    db.add_all([v1, v2])
    db.commit()

    results = db.query(TrendingVideo).filter_by(video_id="abc123").all()
    assert len(results) == 2
```

- [ ] **Step 2: 테스트 실패 확인**
```bash
python -m pytest tests/test_collector.py -q
# Expected: ModuleNotFoundError (database, models 없음)
```

- [ ] **Step 3: app/database.py 생성**
```python
# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import get_settings


settings = get_settings()
engine = create_engine(
    settings.database_url, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: app/models.py 생성**
```python
# app/models.py
from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TrendingVideo(Base):
    __tablename__ = "trending_videos"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[str] = mapped_column(String(20), index=True)
    category_id: Mapped[str] = mapped_column(String(10), index=True)
    title: Mapped[str] = mapped_column(String(200))
    channel_title: Mapped[str] = mapped_column(String(100))
    view_count: Mapped[int]
    like_count: Mapped[int]
    comment_count: Mapped[int]
    published_at: Mapped[str] = mapped_column(String(30))
    collected_at: Mapped[datetime] = mapped_column(default=func.now(), index=True)
```

- [ ] **Step 5: 테스트 통과 확인**
```bash
python -m pytest tests/test_collector.py -q
# Expected: 2 passed
```

- [ ] **Step 6: 커밋**
```bash
git add app/database.py app/models.py tests/test_collector.py
git commit -m "feat: add database setup and TrendingVideo ORM model"
```

---

### Task 3: 스키마 추가

**Files:**
- Modify: `app/schemas.py`

- [ ] **Step 1: 스키마 테스트 추가 (tests/test_trends.py)**
```python
# tests/test_trends.py
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
```

- [ ] **Step 2: 테스트 실패 확인**
```bash
python -m pytest tests/test_trends.py -q
# Expected: ImportError (CollectResponse 등 없음)
```

- [ ] **Step 3: schemas.py에 새 스키마 추가**
```python
# app/schemas.py — 기존 코드 아래에 추가

class CollectResponse(BaseModel):
    collected_categories: int
    collected_videos: int
    collected_at: str


class DailyKeywordCount(BaseModel):
    date: str
    count: int


class TrendKeyword(BaseModel):
    keyword: str
    daily: list[DailyKeywordCount]


class KeywordTrend(BaseModel):
    days: int
    keywords: list[TrendKeyword]


class DailyStats(BaseModel):
    date: str
    avg_view_count: float
    avg_like_count: float
    video_count: int


class TimelineTrend(BaseModel):
    category_id: str
    days: int
    daily_stats: list[DailyStats]
```

- [ ] **Step 4: 테스트 통과 확인**
```bash
python -m pytest tests/test_trends.py -q
# Expected: 5 passed
```

- [ ] **Step 5: 커밋**
```bash
git add app/schemas.py tests/test_trends.py
git commit -m "feat: add trend tracking schemas"
```

---

### Task 4: Collector 서비스

**Files:**
- Create: `app/services/collector.py`
- Modify: `tests/test_collector.py`

- [ ] **Step 1: collector 테스트 추가 (tests/test_collector.py에 추가)**
```python
# tests/test_collector.py — 기존 코드 아래에 추가
from unittest.mock import MagicMock

from app.services.collector import collect_trending_videos
from app.services.youtube import YouTubeService
from app.schemas import Category, Video, VideoStats


MOCK_CATEGORIES_RESPONSE = {
    "items": [
        {"id": "10", "snippet": {"title": "Music", "assignable": True}},
        {"id": "20", "snippet": {"title": "Gaming", "assignable": True}},
        {"id": "99", "snippet": {"title": "Not Assignable", "assignable": False}},
    ]
}

MOCK_VIDEOS_RESPONSE = {
    "items": [
        {
            "id": "vid1",
            "snippet": {
                "title": "Popular Music Video",
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
                "title": "Another Video",
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


def _make_mock_youtube_service():
    mock_client = MagicMock()
    mock_client.videoCategories().list().execute.return_value = (
        MOCK_CATEGORIES_RESPONSE
    )
    mock_client.videos().list().execute.return_value = MOCK_VIDEOS_RESPONSE
    return YouTubeService(client=mock_client)


def test_collect_trending_videos():
    db = _make_session()
    service = _make_mock_youtube_service()

    result = collect_trending_videos(db=db, youtube_service=service)

    assert result.collected_categories == 2  # assignable만
    assert result.collected_videos == 4  # 2 카테고리 x 2 영상
    assert result.collected_at is not None

    videos = db.query(TrendingVideo).all()
    assert len(videos) == 4


def test_collect_dedup_within_same_run():
    db = _make_session()
    mock_client = MagicMock()
    mock_client.videoCategories().list().execute.return_value = {
        "items": [
            {"id": "10", "snippet": {"title": "Music", "assignable": True}},
            {"id": "20", "snippet": {"title": "Gaming", "assignable": True}},
        ]
    }
    # 두 카테고리 모두 같은 영상 반환 (vid1, vid2)
    mock_client.videos().list().execute.return_value = MOCK_VIDEOS_RESPONSE
    service = YouTubeService(client=mock_client)

    result = collect_trending_videos(db=db, youtube_service=service)

    # vid1, vid2가 카테고리 10에서 수집 → 카테고리 20에서는 중복이므로 스킵
    assert result.collected_videos == 2

    videos = db.query(TrendingVideo).all()
    assert len(videos) == 2


def test_collect_empty_categories():
    db = _make_session()
    mock_client = MagicMock()
    mock_client.videoCategories().list().execute.return_value = {"items": []}
    service = YouTubeService(client=mock_client)

    result = collect_trending_videos(db=db, youtube_service=service)

    assert result.collected_categories == 0
    assert result.collected_videos == 0
```

- [ ] **Step 2: 테스트 실패 확인**
```bash
python -m pytest tests/test_collector.py::test_collect_trending_videos -q
# Expected: ImportError (collector 없음)
```

- [ ] **Step 3: app/services/collector.py 생성**
```python
# app/services/collector.py
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import TrendingVideo
from app.schemas import CollectResponse
from app.services.youtube import YouTubeService

logger = logging.getLogger(__name__)


def collect_trending_videos(
    db: Session, youtube_service: YouTubeService
) -> CollectResponse:
    categories = youtube_service.get_categories()
    assignable = [c for c in categories if c.assignable]

    seen_video_ids: set[str] = set()
    total_videos = 0

    for category in assignable:
        videos = youtube_service.get_popular_videos(category.id)
        for video in videos:
            if video.id in seen_video_ids:
                continue
            seen_video_ids.add(video.id)

            record = TrendingVideo(
                video_id=video.id,
                category_id=category.id,
                title=video.title,
                channel_title=video.channel_title,
                view_count=video.stats.view_count,
                like_count=video.stats.like_count,
                comment_count=video.stats.comment_count,
                published_at=video.published_at,
            )
            db.add(record)
            total_videos += 1

    db.commit()

    collected_at = datetime.now(timezone.utc).isoformat()
    logger.info(
        "Collected %d videos from %d categories",
        total_videos,
        len(assignable),
    )

    return CollectResponse(
        collected_categories=len(assignable),
        collected_videos=total_videos,
        collected_at=collected_at,
    )
```

- [ ] **Step 4: 테스트 통과 확인**
```bash
python -m pytest tests/test_collector.py -q
# Expected: 5 passed
```

- [ ] **Step 5: 커밋**
```bash
git add app/services/collector.py tests/test_collector.py
git commit -m "feat: add collector service for trending video collection"
```

---

### Task 5: POST /collect 엔드포인트

**Files:**
- Create: `app/routers/trends.py`
- Modify: `app/main.py`
- Modify: `tests/test_trends.py`

- [ ] **Step 1: POST /collect 엔드포인트 테스트 추가 (tests/test_trends.py에 추가)**
```python
# tests/test_trends.py — 기존 코드 아래에 추가
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.routers.categories import get_youtube_service
from app.services.youtube import YouTubeService


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

_test_engine = create_engine("sqlite:///:memory:")
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


def test_post_collect(client):
    response = client.post("/collect")

    assert response.status_code == 200
    data = response.json()
    assert data["collected_categories"] == 1
    assert data["collected_videos"] == 1
    assert "collected_at" in data
```

- [ ] **Step 2: 테스트 실패 확인**
```bash
python -m pytest tests/test_trends.py::test_post_collect -q
# Expected: 404 (엔드포인트 없음)
```

- [ ] **Step 3: app/routers/trends.py 생성 (POST /collect만)**
```python
# app/routers/trends.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.schemas import CollectResponse
from app.services.collector import collect_trending_videos
from app.services.youtube import YouTubeService

router = APIRouter()


def get_youtube_service(settings: Settings = Depends(get_settings)) -> YouTubeService:
    return YouTubeService(settings=settings)


@router.post("/collect", response_model=CollectResponse)
def collect(
    db: Session = Depends(get_db),
    youtube_service: YouTubeService = Depends(get_youtube_service),
) -> CollectResponse:
    return collect_trending_videos(db=db, youtube_service=youtube_service)
```

- [ ] **Step 4: main.py에 trends router 등록**
```python
# app/main.py
from fastapi import FastAPI

from app.routers.categories import router as categories_router
from app.routers.trends import router as trends_router

app = FastAPI(title="yt-insight-lab")

app.include_router(categories_router)
app.include_router(trends_router)


@app.get("/")
def root():
    return {"message": "yt-insight-lab"}
```

- [ ] **Step 5: 테스트 통과 확인**
```bash
python -m pytest tests/test_trends.py::test_post_collect -q
# Expected: 1 passed
```

- [ ] **Step 6: 커밋**
```bash
git add app/routers/trends.py app/main.py tests/test_trends.py
git commit -m "feat: add POST /collect endpoint for manual trending video collection"
```

---

### Task 6: GET /trends/keywords 엔드포인트

**Files:**
- Modify: `app/routers/trends.py`
- Modify: `tests/test_trends.py`

- [ ] **Step 1: keywords 엔드포인트 테스트 추가 (tests/test_trends.py에 추가)**
```python
# tests/test_trends.py — 기존 코드 아래에 추가
from datetime import datetime, timedelta, timezone

from app.models import TrendingVideo


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
```

- [ ] **Step 2: 테스트 실패 확인**
```bash
python -m pytest tests/test_trends.py::test_get_trends_keywords -q
# Expected: 404 또는 AttributeError
```

- [ ] **Step 3: trends.py에 GET /trends/keywords 엔드포인트 추가**
```python
# app/routers/trends.py — 기존 코드 아래에 추가
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from app.models import TrendingVideo
from app.schemas import (
    CollectResponse,
    DailyKeywordCount,
    TrendKeyword,
    KeywordTrend,
    DailyStats,
    TimelineTrend,
)


@router.get("/trends/keywords", response_model=KeywordTrend)
def get_keyword_trends(
    days: int = 7,
    db: Session = Depends(get_db),
) -> KeywordTrend:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    videos = db.query(TrendingVideo).filter(TrendingVideo.collected_at >= cutoff).all()

    # 일별 키워드 빈도 집계
    # {keyword: {date_str: count}}
    keyword_daily: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for video in videos:
        date_str = video.collected_at.strftime("%Y-%m-%d")
        words = video.title.split()
        for word in words:
            if len(word) > 1:
                keyword_daily[word][date_str] += 1

    # 총 빈도 기준 상위 10개
    keyword_totals = {
        kw: sum(daily.values()) for kw, daily in keyword_daily.items()
    }
    top_keywords = sorted(keyword_totals, key=keyword_totals.get, reverse=True)[:10]

    keywords = []
    for kw in top_keywords:
        daily = [
            DailyKeywordCount(date=date, count=count)
            for date, count in sorted(keyword_daily[kw].items())
        ]
        keywords.append(TrendKeyword(keyword=kw, daily=daily))

    return KeywordTrend(days=days, keywords=keywords)
```

- [ ] **Step 4: 테스트 통과 확인**
```bash
python -m pytest tests/test_trends.py -q
# Expected: all passed
```

- [ ] **Step 5: 커밋**
```bash
git add app/routers/trends.py tests/test_trends.py
git commit -m "feat: add GET /trends/keywords endpoint for keyword trend analysis"
```

---

### Task 7: GET /trends/timeline 엔드포인트

**Files:**
- Modify: `app/routers/trends.py`
- Modify: `tests/test_trends.py`

- [ ] **Step 1: timeline 엔드포인트 테스트 추가 (tests/test_trends.py에 추가)**
```python
# tests/test_trends.py — 기존 코드 아래에 추가

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
```

- [ ] **Step 2: 테스트 실패 확인**
```bash
python -m pytest tests/test_trends.py::test_get_trends_timeline -q
# Expected: 404
```

- [ ] **Step 3: trends.py에 GET /trends/timeline 엔드포인트 추가**
```python
# app/routers/trends.py — 기존 코드 아래에 추가

@router.get("/trends/timeline", response_model=TimelineTrend)
def get_timeline_trends(
    category_id: str,
    days: int = 7,
    db: Session = Depends(get_db),
) -> TimelineTrend:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    videos = (
        db.query(TrendingVideo)
        .filter(
            TrendingVideo.category_id == category_id,
            TrendingVideo.collected_at >= cutoff,
        )
        .all()
    )

    # 일별 집계
    daily_data: dict[str, list[TrendingVideo]] = defaultdict(list)
    for video in videos:
        date_str = video.collected_at.strftime("%Y-%m-%d")
        daily_data[date_str].append(video)

    daily_stats = []
    for date_str in sorted(daily_data):
        vids = daily_data[date_str]
        avg_views = sum(v.view_count for v in vids) / len(vids)
        avg_likes = sum(v.like_count for v in vids) / len(vids)
        daily_stats.append(
            DailyStats(
                date=date_str,
                avg_view_count=avg_views,
                avg_like_count=avg_likes,
                video_count=len(vids),
            )
        )

    return TimelineTrend(
        category_id=category_id,
        days=days,
        daily_stats=daily_stats,
    )
```

- [ ] **Step 4: 테스트 통과 확인**
```bash
python -m pytest tests/test_trends.py -q
# Expected: all passed
```

- [ ] **Step 5: 전체 테스트 통과 확인**
```bash
python -m pytest tests/ -q
# Expected: all passed
```

- [ ] **Step 6: 커밋**
```bash
git add app/routers/trends.py tests/test_trends.py
git commit -m "feat: add GET /trends/timeline endpoint for category time-series stats"
```

---

### Task 8: Scheduler

**Files:**
- Create: `app/scheduler.py`
- Modify: `app/main.py`

- [ ] **Step 1: scheduler 테스트 작성 (tests/test_trends.py에 추가)**
```python
# tests/test_trends.py — 기존 코드 아래에 추가
from unittest.mock import patch

from app.scheduler import create_scheduler


def test_scheduler_creates_job():
    scheduler = create_scheduler()
    jobs = scheduler.get_jobs()

    assert len(jobs) == 1
    assert jobs[0].id == "collect_trending"
    assert jobs[0].name == "collect_trending_videos"


def test_scheduler_not_running_by_default():
    scheduler = create_scheduler()
    assert not scheduler.running
```

- [ ] **Step 2: 테스트 실패 확인**
```bash
python -m pytest tests/test_trends.py::test_scheduler_creates_job -q
# Expected: ImportError (scheduler 없음)
```

- [ ] **Step 3: app/scheduler.py 생성**
```python
# app/scheduler.py
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import SessionLocal, engine, Base
from app.services.collector import collect_trending_videos
from app.services.youtube import YouTubeService
from app.config import get_settings

logger = logging.getLogger(__name__)


def _run_collection():
    """스케줄러에서 호출되는 수집 작업"""
    try:
        settings = get_settings()
        youtube_service = YouTubeService(settings=settings)
        db = SessionLocal()
        try:
            result = collect_trending_videos(db=db, youtube_service=youtube_service)
            logger.info(
                "Scheduled collection complete: %d videos from %d categories",
                result.collected_videos,
                result.collected_categories,
            )
        finally:
            db.close()
    except Exception:
        logger.exception("Scheduled collection failed")


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _run_collection,
        trigger=CronTrigger(hour=0, minute=0, timezone="UTC"),
        id="collect_trending",
        name="collect_trending_videos",
        replace_existing=True,
    )
    return scheduler
```

- [ ] **Step 4: main.py에 lifespan 이벤트로 스케줄러 연동**
```python
# app/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import engine, Base
from app.routers.categories import router as categories_router
from app.routers.trends import router as trends_router
from app.scheduler import create_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    scheduler = create_scheduler()
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="yt-insight-lab", lifespan=lifespan)

app.include_router(categories_router)
app.include_router(trends_router)


@app.get("/")
def root():
    return {"message": "yt-insight-lab"}
```

- [ ] **Step 5: 테스트 통과 확인**
```bash
python -m pytest tests/test_trends.py -q
# Expected: all passed
```

- [ ] **Step 6: 전체 테스트 통과 확인**
```bash
python -m pytest tests/ -q
# Expected: all passed
```

- [ ] **Step 7: 커밋**
```bash
git add app/scheduler.py app/main.py tests/test_trends.py
git commit -m "feat: add APScheduler for daily trending video collection"
```
