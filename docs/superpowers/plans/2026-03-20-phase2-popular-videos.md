# Phase 2: 카테고리별 인기 영상 + 기본 통계 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 특정 카테고리의 인기 영상 목록과 기본 통계(조회수, 좋아요, 댓글 수)를 조회하는 `GET /categories/{id}/videos` 엔드포인트를 구현한다.

**Architecture:** `schemas.py`에 Video/VideoStats/PopularVideosResponse 스키마를 추가하고, `services/youtube.py`에 `get_popular_videos(category_id)` 메서드를 추가하며, `routers/categories.py`에 새 엔드포인트를 등록한다. YouTube Data API의 `videos.list(chart="mostPopular")` 호출을 사용한다.

**Tech Stack:** Python 3.11+, FastAPI, pydantic-settings, google-api-python-client, pytest

**Spec:** `docs/superpowers/specs/2026-03-19-youtube-category-analysis-api-design.md`

---

## File Map

| Action | Path | Responsibility |
|--------|------|---------------|
| Modify | `app/schemas.py` | `Video`, `VideoStats`, `PopularVideosResponse` 스키마 추가 |
| Modify | `app/services/youtube.py` | `get_popular_videos(category_id)` 메서드 추가 |
| Modify | `app/routers/categories.py` | `GET /categories/{id}/videos` 엔드포인트 추가 |
| Create | `tests/test_popular_videos.py` | 인기 영상 관련 테스트 |

---

### Task 1: 스키마 추가

**Files:**
- Modify: `app/schemas.py`
- Create: `tests/test_popular_videos.py`

- [ ] **Step 1: 테스트 작성 — Video, VideoStats, PopularVideosResponse 스키마 검증**

`tests/test_popular_videos.py` 생성:

```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_popular_videos.py -v`
Expected: FAIL — `ImportError: cannot import name 'Video' from 'app.schemas'`

- [ ] **Step 3: `app/schemas.py`에 스키마 추가**

기존 코드 아래에 추가:

```python
class VideoStats(BaseModel):
    view_count: int
    like_count: int
    comment_count: int


class Video(BaseModel):
    id: str
    title: str
    channel_title: str
    published_at: str
    stats: VideoStats


class PopularVideosResponse(BaseModel):
    category_id: str
    videos: list[Video]
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_popular_videos.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add app/schemas.py tests/test_popular_videos.py
git commit -m "feat: add Video, VideoStats, PopularVideosResponse schemas"
```

---

### Task 2: YouTubeService에 get_popular_videos 메서드 추가

**Files:**
- Modify: `app/services/youtube.py`
- Modify: `tests/test_popular_videos.py`

- [ ] **Step 1: 테스트 작성 — `get_popular_videos()` mock 테스트**

`tests/test_popular_videos.py`에 추가:

```python
from unittest.mock import MagicMock

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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_popular_videos.py::test_get_popular_videos -v`
Expected: FAIL — `AttributeError: 'YouTubeService' object has no attribute 'get_popular_videos'`

- [ ] **Step 3: `app/services/youtube.py`에 메서드 추가**

`YouTubeService` 클래스에 추가 (imports에 `Video`, `VideoStats` 추가):

```python
from app.schemas import Category, Video, VideoStats
```

`get_categories()` 메서드 아래에 추가:

```python
    def get_popular_videos(self, category_id: str) -> list[Video]:
        try:
            response = (
                self.client.videos()
                .list(
                    part="snippet,statistics",
                    chart="mostPopular",
                    videoCategoryId=category_id,
                    regionCode=REGION_CODE,
                    maxResults=20,
                )
                .execute()
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"YouTube API error: {e}")

        return [
            Video(
                id=item["id"],
                title=item["snippet"]["title"],
                channel_title=item["snippet"]["channelTitle"],
                published_at=item["snippet"]["publishedAt"],
                stats=VideoStats(
                    view_count=int(item["statistics"]["viewCount"]),
                    like_count=int(item["statistics"]["likeCount"]),
                    comment_count=int(item["statistics"]["commentCount"]),
                ),
            )
            for item in response.get("items", [])
        ]
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_popular_videos.py::test_get_popular_videos -v`
Expected: PASS

- [ ] **Step 5: 에러 경로 테스트 추가**

`tests/test_popular_videos.py`에 추가:

```python
from fastapi import HTTPException


def test_get_popular_videos_api_error():
    mock_youtube = MagicMock()
    mock_youtube.videos().list().execute.side_effect = Exception("API quota exceeded")

    service = YouTubeService(client=mock_youtube)

    with pytest.raises(HTTPException) as exc_info:
        service.get_popular_videos("10")

    assert exc_info.value.status_code == 502
    assert "API quota exceeded" in exc_info.value.detail
```

- [ ] **Step 6: 에러 테스트 통과 확인**

Run: `pytest tests/test_popular_videos.py::test_get_popular_videos_api_error -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add app/services/youtube.py tests/test_popular_videos.py
git commit -m "feat: add get_popular_videos method to YouTubeService"
```

---

### Task 3: 엔드포인트 추가

**Files:**
- Modify: `app/routers/categories.py`
- Modify: `tests/test_popular_videos.py`

- [ ] **Step 1: 테스트 작성 — `GET /categories/{id}/videos` 통합 테스트**

`tests/test_popular_videos.py`에 추가:

```python
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.categories import get_youtube_service


def _mock_youtube_service():
    mock_client = MagicMock()
    mock_client.videos().list().execute.return_value = MOCK_VIDEOS_RESPONSE
    return YouTubeService(client=mock_client)


@pytest.fixture()
def client():
    app.dependency_overrides[get_youtube_service] = _mock_youtube_service
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_popular_videos_endpoint(client):
    response = client.get("/categories/10/videos")

    assert response.status_code == 200
    data = response.json()
    assert data["category_id"] == "10"
    assert len(data["videos"]) == 2
    assert data["videos"][0]["id"] == "vid1"
    assert data["videos"][0]["title"] == "Popular Video 1"
    assert data["videos"][0]["channel_title"] == "Channel A"
    assert data["videos"][0]["stats"]["view_count"] == 150000
    assert data["videos"][0]["stats"]["like_count"] == 3000
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_popular_videos.py::test_get_popular_videos_endpoint -v`
Expected: FAIL — 404 (엔드포인트 미등록) 또는 405

- [ ] **Step 3: `app/routers/categories.py`에 엔드포인트 추가**

imports에 `PopularVideosResponse` 추가:

```python
from app.schemas import CategoriesResponse, PopularVideosResponse
```

기존 `list_categories` 함수 아래에 추가:

```python
@router.get("/categories/{category_id}/videos", response_model=PopularVideosResponse)
def list_popular_videos(
    category_id: str,
    service: YouTubeService = Depends(get_youtube_service),
) -> PopularVideosResponse:
    videos = service.get_popular_videos(category_id)
    return PopularVideosResponse(category_id=category_id, videos=videos)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_popular_videos.py -v`
Expected: 6 passed (스키마 3 + 서비스 1 + 에러 1 + 엔드포인트 1)

- [ ] **Step 5: 전체 테스트 통과 확인**

Run: `pytest -v`
Expected: 10 passed (기존 4 + 신규 6)

- [ ] **Step 6: Lint & format 확인**

Run: `ruff check . && ruff format --check .`
Expected: 에러 없음

- [ ] **Step 7: Commit**

```bash
git add app/routers/categories.py tests/test_popular_videos.py
git commit -m "feat: add GET /categories/{id}/videos endpoint"
```
