# Phase 4: 트렌드 추적 설계

## 개요

인기 영상 데이터를 DB에 축적하고, 시간에 따른 키워드/통계 트렌드를 분석하는 기능.

## DB 설계

### 기술 스택

- **ORM:** SQLAlchemy 2.0
- **DB:** SQLite (시작) → PostgreSQL 전환 가능 (SQLAlchemy 추상화)
- **의존성 추가:** `sqlalchemy`

### `app/database.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = "sqlite:///./data/trending.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
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

### `app/models.py` — ORM 모델

```python
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

## 데이터 수집

### `POST /collect`

수동 수집 트리거. 모든 assignable 카테고리의 인기 영상을 DB에 저장.

**로직:**
1. `GET /categories`로 assignable 카테고리 목록 조회
2. 각 카테고리별 `get_popular_videos(category_id)` 호출
3. `TrendingVideo` 레코드로 DB 저장
4. 수집 결과 반환 (카테고리 수, 영상 수)

**응답:**
```json
{
  "collected_categories": 15,
  "collected_videos": 285,
  "collected_at": "2026-03-20T09:00:00Z"
}
```

### 자동 수집 (하루 1회)

- APScheduler 사용
- `app/scheduler.py` — 스케줄러 설정 + 수집 작업 등록
- FastAPI lifespan 이벤트로 시작/종료 관리
- 의존성 추가: `apscheduler`

## 엔드포인트

### `GET /trends/keywords?days=7`

기간별 인기 키워드 트렌드.

**로직:**
1. `collected_at` 기준 최근 N일 데이터 조회
2. 일별로 제목 키워드 빈도 집계
3. 상위 10개 키워드의 일별 변화 반환

**응답:**
```json
{
  "days": 7,
  "keywords": [
    {"keyword": "뮤직비디오", "daily": [
      {"date": "2026-03-14", "count": 15},
      {"date": "2026-03-15", "count": 18}
    ]},
    {"keyword": "공식", "daily": [
      {"date": "2026-03-14", "count": 10},
      {"date": "2026-03-15", "count": 12}
    ]}
  ]
}
```

### `GET /trends/timeline?category_id=10&days=7`

카테고리별 시계열 통계.

**로직:**
1. 특정 카테고리의 최근 N일 데이터 조회
2. 일별 평균 조회수, 좋아요, 영상 수 집계

**응답:**
```json
{
  "category_id": "10",
  "days": 7,
  "daily_stats": [
    {"date": "2026-03-14", "avg_view_count": 125000, "avg_like_count": 2500, "video_count": 20},
    {"date": "2026-03-15", "avg_view_count": 130000, "avg_like_count": 2700, "video_count": 20}
  ]
}
```

## 스키마

```python
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

## 프로젝트 구조 변경

```
app/
├── database.py         # 신규: SQLAlchemy 엔진/세션
├── models.py           # 신규: TrendingVideo ORM
├── scheduler.py        # 신규: APScheduler 설정
├── services/
│   └── collector.py    # 신규: 데이터 수집 로직
├── routers/
│   └── trends.py       # 신규: 트렌드 엔드포인트 + POST /collect
└── schemas.py          # CollectResponse, TrendKeyword, KeywordTrend, DailyStats, TimelineTrend 추가
```

## 의존성 추가

```toml
dependencies = [
    ...,
    "sqlalchemy",
    "apscheduler",
]
```

## 테스트 전략

- `tests/test_collector.py` — 수집 로직 테스트 (YouTube API mock + in-memory SQLite)
- `tests/test_trends.py` — 트렌드 엔드포인트 테스트
- 테스트 시 in-memory SQLite (`sqlite:///:memory:`) 사용으로 격리
- DB 세션 의존성 오버라이드로 테스트 DB 주입
