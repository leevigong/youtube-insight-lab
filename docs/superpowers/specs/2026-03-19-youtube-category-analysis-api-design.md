# YouTube 카테고리별 인기 영상 분석 API 설계

## 개요

유튜브 알고리즘을 카테고리별로 분석하는 API 서비스. 미디어팀 내부 도구 및 일반 사용자 공개 서비스로 활용.

### 핵심 기능 (최종 목표)

- 카테고리별 인기 영상 목록 + 기본 통계 (조회수, 좋아요, 댓글 수)
- 영상 상세 패턴 분석 (제목 키워드, 업로드 시간대, 영상 길이, 섬네일)

### 제약 조건

- 지역: 한국(KR) 고정
- 데이터 소스: YouTube Data API v3
- 실시간 조회로 시작 → 나중에 DB 기반으로 확장

## 프로젝트 구조

```
app/
├── main.py              # FastAPI 앱 + 라우터 등록
├── config.py            # Settings (YOUTUBE_API_KEY, REGION_CODE="KR")
├── routers/
│   ├── __init__.py
│   └── categories.py    # 카테고리 관련 엔드포인트
├── services/
│   ├── __init__.py
│   └── youtube.py       # YouTube Data API 클라이언트
└── schemas.py           # Pydantic 응답 모델
```

## 설정 관리

- `pydantic-settings`의 `BaseSettings`로 `.env`에서 `YOUTUBE_API_KEY` 로드 (기존 `python-dotenv`는 `pydantic-settings`가 내부적으로 사용하므로 유지)
- `pyproject.toml`에 `pydantic-settings` 의존성 추가 필요
- `REGION_CODE`는 `"KR"` 고정 상수
- API 키 미설정 시 서버 시작 단계에서 검증 실패

## 스키마

```python
class Category(BaseModel):
    id: str
    title: str
    assignable: bool  # 영상에 태그 가능한 카테고리 여부

class CategoriesResponse(BaseModel):
    categories: list[Category]
```

응답 예시:
```json
{
  "categories": [
    {"id": "1", "title": "Film & Animation", "assignable": true},
    {"id": "10", "title": "Music", "assignable": true},
    {"id": "17", "title": "Sports", "assignable": true}
  ]
}
```

## 서비스 계층

`services/youtube.py` — YouTube Data API 클라이언트:

- `google-api-python-client`의 `build("youtube", "v3", developerKey=...)` 사용
- Phase 1 메서드: `get_categories()` — `videoCategories.list(part="snippet", regionCode="KR")`
- FastAPI의 `Depends`를 통해 Settings를 주입받아 클라이언트 생성

에러 처리:
- YouTube API 호출 실패 시 → `HTTPException(502)` 반환

## Phase별 로드맵

### Phase 1: 기반 구조 (현재)

**범위:** 프로젝트 구조 확립 + 카테고리 목록 API

**엔드포인트:**
- `GET /categories` — YouTube 공식 카테고리 목록 조회 (한국 기준)

**구현 항목:**
- `config.py` — pydantic-settings 기반 설정
- `services/youtube.py` — YouTube API 클라이언트 (`get_categories()`)
- `schemas.py` — `Category`, `CategoriesResponse` 모델
- `routers/categories.py` — `GET /categories` 엔드포인트
- `main.py` — 라우터 등록
- 의존성 추가: `pydantic-settings` (`pyproject.toml`에 추가)
- `tests/test_categories.py` — `/categories` 엔드포인트 테스트 (YouTube API mock 처리)

### Phase 2: 카테고리별 인기 영상 + 기본 통계

**엔드포인트:**
- `GET /categories/{id}/videos` — 특정 카테고리의 인기 영상 목록

**YouTube API 호출:**
- `youtube.videos.list(part="snippet,statistics", chart="mostPopular", videoCategoryId=id, regionCode="KR", maxResults=20)`

**응답 데이터:**
- 영상 제목, 채널명, 조회수, 좋아요 수, 댓글 수, 게시일

**구현 항목:**
- `services/youtube.py`에 `get_popular_videos(category_id)` 메서드 추가
- `schemas.py`에 `Video`, `VideoStats`, `PopularVideosResponse` 스키마 추가
- `routers/categories.py`에 엔드포인트 추가

### Phase 3: 영상 상세 패턴 분석

**엔드포인트:**
- `GET /videos/{id}/detail` — 개별 영상 상세 정보
- `GET /categories/{id}/analysis` — 카테고리 내 영상 패턴 분석

**분석 항목 (pandas 활용):**
- 제목 키워드 빈도 분석
- 평균 업로드 시간대
- 평균 영상 길이
- 섬네일 URL 목록

**구현 항목:**
- `services/youtube.py`에 `get_video_details(video_id)` 메서드 추가
- `services/analyzer.py` 신규 — pandas 기반 분석 로직
- `schemas.py`에 `VideoDetail`, `CategoryAnalysis` 스키마 추가
- `routers/videos.py` 신규 — 영상 상세 엔드포인트

### Phase 4: 트렌드 추적

**엔드포인트:**
- `GET /trends/keywords` — 인기 키워드 트렌드
- `GET /trends/timeline` — 시계열 트렌드 데이터

**구현 항목:**
- DB 도입 (SQLite 또는 PostgreSQL)
- 주기적 데이터 수집 로직
- `routers/trends.py` 신규
- `services/collector.py` 신규 — 데이터 수집기

### Phase 5: 서비스 확장

**구현 항목:**
- 스케줄러 (APScheduler 등) — 자동 데이터 수집
- 프론트엔드 대시보드
- 배포 환경 구성

## 테스트 전략

- `pytest` + FastAPI `TestClient` 사용
- YouTube API 호출은 `unittest.mock.patch`로 mock 처리
- Phase 1 테스트: `tests/test_categories.py` — `GET /categories` 응답 형식 및 데이터 검증
- 각 Phase별 엔드포인트에 대한 통합 테스트 추가
