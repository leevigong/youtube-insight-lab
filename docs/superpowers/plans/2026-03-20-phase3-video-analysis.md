# Phase 3: 영상 상세 패턴 분석 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 카테고리별 인기 영상의 상세 정보 조회 및 pandas 기반 패턴 분석(키워드 빈도, 업로드 시간대, 영상 길이 분포) 기능을 구현한다.

**Architecture:** `YouTubeService`에 `get_video_details`와 `get_popular_videos_with_details` 메서드를 추가하여 YouTube API의 `snippet,statistics,contentDetails`를 조회한다. 새로운 `AnalyzerService`에서 pandas DataFrame을 활용해 키워드 빈도, 평균 업로드 시간대, 영상 길이 분포를 분석한다. 개별 영상 상세는 `routers/videos.py`에, 카테고리 분석은 기존 `routers/categories.py`에 엔드포인트를 추가한다.

**Tech Stack:** Python 3.11+, FastAPI, pandas, google-api-python-client, pytest

**Spec:** `docs/superpowers/specs/2026-03-20-phase3-video-analysis-design.md`

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `app/schemas.py` | `VideoDetail`, `KeywordFrequency`, `DurationDistribution`, `CategoryAnalysis` 스키마 추가 |
| Modify | `app/services/youtube.py` | `parse_duration` 유틸, `get_video_details`, `get_popular_videos_with_details` 추가 |
| Create | `app/services/analyzer.py` | `analyze_category` 분석 함수 |
| Create | `app/routers/videos.py` | `GET /videos/{video_id}/detail` 엔드포인트 |
| Modify | `app/routers/categories.py` | `GET /categories/{category_id}/analysis` 엔드포인트 추가 |
| Modify | `app/main.py` | `videos` 라우터 등록 |
| Create | `tests/test_parse_duration.py` | `parse_duration` 유닛 테스트 |
| Create | `tests/test_video_detail.py` | 영상 상세 서비스 + 엔드포인트 테스트 |
| Create | `tests/test_analysis.py` | 분석 로직 단위 테스트 + 엔드포인트 통합 테스트 |

---

### Task 1: 스키마 추가

**Files:**
- Modify: `app/schemas.py`
- Create: `tests/test_video_detail.py`

- [ ] **Step 1: 스키마 테스트 작성**

`tests/test_video_detail.py`:
```python
from app.schemas import (
    VideoDetail,
    VideoStats,
    KeywordFrequency,
    DurationDistribution,
    CategoryAnalysis,
)


def test_video_detail_schema():
    detail = VideoDetail(
        id="abc123",
        title="테스트 영상",
        channel_title="테스트 채널",
        published_at="2026-03-19T12:00:00Z",
        stats=VideoStats(view_count=150000, like_count=3000, comment_count=200),
        duration_seconds=933,
        tags=["키워드1", "키워드2"],
        thumbnail_url="https://i.ytimg.com/vi/abc123/maxresdefault.jpg",
    )
    assert detail.id == "abc123"
    assert detail.duration_seconds == 933
    assert detail.tags == ["키워드1", "키워드2"]
    assert detail.thumbnail_url.startswith("https://")


def test_video_detail_empty_tags():
    detail = VideoDetail(
        id="abc123",
        title="테스트 영상",
        channel_title="테스트 채널",
        published_at="2026-03-19T12:00:00Z",
        stats=VideoStats(view_count=100, like_count=0, comment_count=0),
        duration_seconds=60,
        tags=[],
        thumbnail_url="https://example.com/thumb.jpg",
    )
    assert detail.tags == []


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
    assert analysis.avg_upload_hour == 15.3
```

```bash
cd /Users/daeunisnn/dev/yt-insight-lab && python -m pytest tests/test_video_detail.py -v
# Expected: FAILED (ImportError — schemas not yet defined)
```

- [ ] **Step 2: 스키마 구현**

`app/schemas.py` 끝에 추가:
```python
class VideoDetail(BaseModel):
    id: str
    title: str
    channel_title: str
    published_at: str
    stats: VideoStats
    duration_seconds: int
    tags: list[str]
    thumbnail_url: str


class KeywordFrequency(BaseModel):
    keyword: str
    count: int


class DurationDistribution(BaseModel):
    short: int
    medium: int
    long: int


class CategoryAnalysis(BaseModel):
    category_id: str
    video_count: int
    keywords: list[KeywordFrequency]
    avg_upload_hour: float
    avg_duration_seconds: float
    duration_distribution: DurationDistribution
    thumbnail_urls: list[str]
```

```bash
cd /Users/daeunisnn/dev/yt-insight-lab && python -m pytest tests/test_video_detail.py -v
# Expected: all 5 tests PASSED
```

- [ ] **Step 3: 커밋**

```bash
cd /Users/daeunisnn/dev/yt-insight-lab && git add app/schemas.py tests/test_video_detail.py && git commit -m "feat: add VideoDetail, KeywordFrequency, DurationDistribution, CategoryAnalysis schemas"
```

---

### Task 2: parse_duration 유틸

**Files:**
- Modify: `app/services/youtube.py`
- Create: `tests/test_parse_duration.py`

- [ ] **Step 1: parse_duration 테스트 작성**

`tests/test_parse_duration.py`:
```python
import pytest

from app.services.youtube import parse_duration


@pytest.mark.parametrize(
    "duration, expected",
    [
        ("PT15M33S", 933),
        ("PT1H2M3S", 3723),
        ("PT30S", 30),
        ("PT10M", 600),
        ("PT1H", 3600),
        ("PT0S", 0),
        ("PT1H30M", 5400),
        ("", 0),
        ("INVALID", 0),
    ],
)
def test_parse_duration(duration: str, expected: int):
    assert parse_duration(duration) == expected
```

```bash
cd /Users/daeunisnn/dev/yt-insight-lab && python -m pytest tests/test_parse_duration.py -v
# Expected: FAILED (ImportError — parse_duration not yet defined)
```

- [ ] **Step 2: parse_duration 구현**

`app/services/youtube.py` 파일 상단에 `import re` 추가, 클래스 정의 전에 함수 추가:
```python
import re


def parse_duration(duration: str) -> int:
    """Convert ISO 8601 duration (e.g. 'PT15M33S') to seconds."""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds
```

```bash
cd /Users/daeunisnn/dev/yt-insight-lab && python -m pytest tests/test_parse_duration.py -v
# Expected: all 9 tests PASSED
```

- [ ] **Step 3: 커밋**

```bash
cd /Users/daeunisnn/dev/yt-insight-lab && git add app/services/youtube.py tests/test_parse_duration.py && git commit -m "feat: add parse_duration utility for ISO 8601 duration conversion"
```

---

### Task 3: YouTubeService 메서드 추가

**Files:**
- Modify: `app/services/youtube.py`
- Modify: `tests/test_video_detail.py`

- [ ] **Step 1: get_video_details 서비스 테스트 작성**

`tests/test_video_detail.py`에 추가:
```python
from unittest.mock import MagicMock

from fastapi import HTTPException
import pytest

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
                    "maxres": {"url": "https://i.ytimg.com/vi/abc123/maxresdefault.jpg"},
                },
            },
            "statistics": {
                "viewCount": "150000",
                "likeCount": "3000",
                "commentCount": "200",
            },
            "contentDetails": {
                "duration": "PT15M33S",
            },
        }
    ]
}


def test_get_video_details():
    mock_youtube = MagicMock()
    mock_youtube.videos().list().execute.return_value = MOCK_VIDEO_DETAIL_RESPONSE

    service = YouTubeService(client=mock_youtube)
    detail = service.get_video_details("abc123")

    assert detail.id == "abc123"
    assert detail.title == "테스트 영상 제목"
    assert detail.channel_title == "테스트 채널"
    assert detail.published_at == "2026-03-19T12:00:00Z"
    assert detail.duration_seconds == 933
    assert detail.tags == ["태그1", "태그2"]
    assert detail.thumbnail_url == "https://i.ytimg.com/vi/abc123/maxresdefault.jpg"
    assert detail.stats.view_count == 150000
    assert detail.stats.like_count == 3000
    assert detail.stats.comment_count == 200


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
            "statistics": {
                "viewCount": "500",
            },
            "contentDetails": {
                "duration": "PT30S",
            },
        }
    ]
}


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
```

```bash
cd /Users/daeunisnn/dev/yt-insight-lab && python -m pytest tests/test_video_detail.py::test_get_video_details -v
# Expected: FAILED (AttributeError — method not yet defined)
```

- [ ] **Step 2: get_video_details 구현**

`app/services/youtube.py` — import에 `VideoDetail` 추가, `YouTubeService` 클래스에 메서드 추가:

import 수정:
```python
from app.schemas import Category, Video, VideoStats, VideoDetail
```

`YouTubeService` 클래스에 추가:
```python
    def _get_thumbnail_url(self, thumbnails: dict) -> str:
        """Pick best available thumbnail: maxres > high > medium > default."""
        for key in ("maxres", "high", "medium", "default"):
            if key in thumbnails:
                return thumbnails[key]["url"]
        return ""

    def get_video_details(self, video_id: str) -> VideoDetail:
        try:
            response = (
                self.client.videos()
                .list(part="snippet,statistics,contentDetails", id=video_id)
                .execute()
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"YouTube API error: {e}")

        items = response.get("items", [])
        if not items:
            raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")

        item = items[0]
        snippet = item["snippet"]
        stats = item["statistics"]
        content = item["contentDetails"]

        return VideoDetail(
            id=item["id"],
            title=snippet["title"],
            channel_title=snippet["channelTitle"],
            published_at=snippet["publishedAt"],
            stats=VideoStats(
                view_count=int(stats.get("viewCount", 0)),
                like_count=int(stats.get("likeCount", 0)),
                comment_count=int(stats.get("commentCount", 0)),
            ),
            duration_seconds=parse_duration(content["duration"]),
            tags=snippet.get("tags", []),
            thumbnail_url=self._get_thumbnail_url(snippet.get("thumbnails", {})),
        )
```

```bash
cd /Users/daeunisnn/dev/yt-insight-lab && python -m pytest tests/test_video_detail.py -v
# Expected: all 9 tests PASSED
```

- [ ] **Step 3: get_popular_videos_with_details 테스트 작성**

`tests/test_video_detail.py`에 추가:
```python
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
                    "high": {"url": "https://i.ytimg.com/vi/vid1/hqdefault.jpg"},
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
                    "default": {"url": "https://i.ytimg.com/vi/vid2/default.jpg"},
                },
            },
            "statistics": {
                "viewCount": "100000",
            },
            "contentDetails": {"duration": "PT1H2M"},
        },
    ]
}


def test_get_popular_videos_with_details():
    mock_youtube = MagicMock()
    mock_youtube.videos().list().execute.return_value = MOCK_POPULAR_WITH_DETAILS_RESPONSE

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
```

```bash
cd /Users/daeunisnn/dev/yt-insight-lab && python -m pytest tests/test_video_detail.py::test_get_popular_videos_with_details -v
# Expected: FAILED (AttributeError — method not yet defined)
```

- [ ] **Step 4: get_popular_videos_with_details 구현**

`YouTubeService` 클래스에 추가:
```python
    def get_popular_videos_with_details(self, category_id: str) -> list[VideoDetail]:
        try:
            response = (
                self.client.videos()
                .list(
                    part="snippet,statistics,contentDetails",
                    chart="mostPopular",
                    videoCategoryId=category_id,
                    regionCode=REGION_CODE,
                    maxResults=20,
                )
                .execute()
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"YouTube API error: {e}")

        results = []
        for item in response.get("items", []):
            snippet = item["snippet"]
            stats = item["statistics"]
            content = item["contentDetails"]
            results.append(
                VideoDetail(
                    id=item["id"],
                    title=snippet["title"],
                    channel_title=snippet["channelTitle"],
                    published_at=snippet["publishedAt"],
                    stats=VideoStats(
                        view_count=int(stats.get("viewCount", 0)),
                        like_count=int(stats.get("likeCount", 0)),
                        comment_count=int(stats.get("commentCount", 0)),
                    ),
                    duration_seconds=parse_duration(content["duration"]),
                    tags=snippet.get("tags", []),
                    thumbnail_url=self._get_thumbnail_url(
                        snippet.get("thumbnails", {})
                    ),
                )
            )
        return results
```

```bash
cd /Users/daeunisnn/dev/yt-insight-lab && python -m pytest tests/test_video_detail.py -v
# Expected: all 10 tests PASSED
```

- [ ] **Step 5: 커밋**

```bash
cd /Users/daeunisnn/dev/yt-insight-lab && git add app/services/youtube.py tests/test_video_detail.py && git commit -m "feat: add get_video_details and get_popular_videos_with_details to YouTubeService"
```

---

### Task 4: Analyzer 서비스

**Files:**
- Create: `app/services/analyzer.py`
- Create: `tests/test_analysis.py`

- [ ] **Step 1: analyzer 테스트 작성**

`tests/test_analysis.py`:
```python
from app.schemas import (
    VideoDetail,
    VideoStats,
    CategoryAnalysis,
    KeywordFrequency,
    DurationDistribution,
)
from app.services.analyzer import analyze_category


def _make_video(
    id: str,
    title: str,
    published_at: str,
    duration_seconds: int,
    tags: list[str] | None = None,
    thumbnail_url: str = "https://example.com/thumb.jpg",
) -> VideoDetail:
    return VideoDetail(
        id=id,
        title=title,
        channel_title="채널",
        published_at=published_at,
        stats=VideoStats(view_count=1000, like_count=50, comment_count=10),
        duration_seconds=duration_seconds,
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


def test_analyze_category_keywords():
    result = analyze_category("10", SAMPLE_VIDEOS)

    keyword_map = {k.keyword: k.count for k in result.keywords}
    assert keyword_map["뮤직비디오"] == 2
    assert keyword_map["공식"] == 2
    # 1-char words like "MV" (2 chars, included) should appear; single-char excluded
    assert all(len(k.keyword) > 1 for k in result.keywords)


def test_analyze_category_avg_upload_hour():
    result = analyze_category("10", SAMPLE_VIDEOS)

    # hours: 10, 14, 20 → avg = 14.666...
    assert round(result.avg_upload_hour, 1) == 14.7


def test_analyze_category_avg_duration():
    result = analyze_category("10", SAMPLE_VIDEOS)

    # durations: 180, 600, 1500 → avg = 760
    assert result.avg_duration_seconds == 760.0


def test_analyze_category_duration_distribution():
    result = analyze_category("10", SAMPLE_VIDEOS)

    assert result.duration_distribution.short == 1    # 180 < 240
    assert result.duration_distribution.medium == 1   # 240 <= 600 <= 1200
    assert result.duration_distribution.long == 1     # 1500 > 1200


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
    # 11 distinct 2+ char words → top 10 only
    videos = [
        _make_video(
            f"v{i}",
            f"word{i} extra{i} bonus",
            f"2026-03-19T12:00:00Z",
            300,
        )
        for i in range(11)
    ]
    result = analyze_category("10", videos)
    assert len(result.keywords) <= 10
```

```bash
cd /Users/daeunisnn/dev/yt-insight-lab && python -m pytest tests/test_analysis.py -v
# Expected: FAILED (ModuleNotFoundError — analyzer.py doesn't exist)
```

- [ ] **Step 2: analyzer 구현**

`app/services/analyzer.py`:
```python
from collections import Counter
from datetime import datetime

import pandas as pd

from app.schemas import (
    CategoryAnalysis,
    DurationDistribution,
    KeywordFrequency,
    VideoDetail,
)


def analyze_category(category_id: str, videos: list[VideoDetail]) -> CategoryAnalysis:
    """Analyze a list of popular videos for a category."""
    df = pd.DataFrame([v.model_dump() for v in videos])

    # Keywords: split titles by space, remove 1-char words, top 10
    all_words: list[str] = []
    for title in df["title"]:
        words = [w for w in title.split() if len(w) > 1]
        all_words.extend(words)
    top_keywords = Counter(all_words).most_common(10)
    keywords = [KeywordFrequency(keyword=w, count=c) for w, c in top_keywords]

    # Average upload hour (UTC)
    hours = [datetime.fromisoformat(p.replace("Z", "+00:00")).hour for p in df["published_at"]]
    avg_upload_hour = round(sum(hours) / len(hours), 1) if hours else 0.0

    # Average duration
    avg_duration_seconds = float(df["duration_seconds"].mean())

    # Duration distribution
    short_count = int((df["duration_seconds"] < 240).sum())
    medium_count = int(((df["duration_seconds"] >= 240) & (df["duration_seconds"] <= 1200)).sum())
    long_count = int((df["duration_seconds"] > 1200).sum())
    duration_distribution = DurationDistribution(
        short=short_count, medium=medium_count, long=long_count
    )

    # Thumbnail URLs
    thumbnail_urls = df["thumbnail_url"].tolist()

    return CategoryAnalysis(
        category_id=category_id,
        video_count=len(videos),
        keywords=keywords,
        avg_upload_hour=avg_upload_hour,
        avg_duration_seconds=avg_duration_seconds,
        duration_distribution=duration_distribution,
        thumbnail_urls=thumbnail_urls,
    )
```

```bash
cd /Users/daeunisnn/dev/yt-insight-lab && python -m pytest tests/test_analysis.py -v
# Expected: all 7 tests PASSED
```

- [ ] **Step 3: 커밋**

```bash
cd /Users/daeunisnn/dev/yt-insight-lab && git add app/services/analyzer.py tests/test_analysis.py && git commit -m "feat: add AnalyzerService with analyze_category for pattern analysis"
```

---

### Task 5: 라우터 + 엔드포인트

**Files:**
- Create: `app/routers/videos.py`
- Modify: `app/routers/categories.py`
- Modify: `app/main.py`
- Modify: `tests/test_video_detail.py`
- Modify: `tests/test_analysis.py`

- [ ] **Step 1: videos 라우터 엔드포인트 테스트 작성**

`tests/test_video_detail.py`에 추가:
```python
from fastapi.testclient import TestClient

from app.main import app
from app.routers.videos import get_youtube_service as get_videos_youtube_service


def _mock_video_detail_service():
    mock_client = MagicMock()
    mock_client.videos().list().execute.return_value = MOCK_VIDEO_DETAIL_RESPONSE
    return YouTubeService(client=mock_client)


@pytest.fixture()
def client():
    app.dependency_overrides[get_videos_youtube_service] = _mock_video_detail_service
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_video_detail_endpoint(client):
    response = client.get("/videos/abc123/detail")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "abc123"
    assert data["title"] == "테스트 영상 제목"
    assert data["duration_seconds"] == 933
    assert data["tags"] == ["태그1", "태그2"]
    assert data["thumbnail_url"] == "https://i.ytimg.com/vi/abc123/maxresdefault.jpg"
    assert data["stats"]["view_count"] == 150000
```

```bash
cd /Users/daeunisnn/dev/yt-insight-lab && python -m pytest tests/test_video_detail.py::test_get_video_detail_endpoint -v
# Expected: FAILED (ModuleNotFoundError — videos.py router doesn't exist)
```

- [ ] **Step 2: videos 라우터 구현 + main.py 등록**

`app/routers/videos.py`:
```python
from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.schemas import VideoDetail
from app.services.youtube import YouTubeService

router = APIRouter()


def get_youtube_service(settings: Settings = Depends(get_settings)) -> YouTubeService:
    return YouTubeService(settings=settings)


@router.get("/videos/{video_id}/detail", response_model=VideoDetail)
def get_video_detail(
    video_id: str,
    service: YouTubeService = Depends(get_youtube_service),
) -> VideoDetail:
    return service.get_video_details(video_id)
```

`app/main.py` 수정 — videos 라우터 등록:
```python
from fastapi import FastAPI

from app.routers.categories import router as categories_router
from app.routers.videos import router as videos_router

app = FastAPI(title="yt-insight-lab")

app.include_router(categories_router)
app.include_router(videos_router)


@app.get("/")
def root():
    return {"message": "yt-insight-lab"}
```

```bash
cd /Users/daeunisnn/dev/yt-insight-lab && python -m pytest tests/test_video_detail.py::test_get_video_detail_endpoint -v
# Expected: PASSED
```

- [ ] **Step 3: categories analysis 엔드포인트 테스트 작성**

`tests/test_analysis.py`에 추가:
```python
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.categories import get_youtube_service
from app.services.youtube import YouTubeService


MOCK_POPULAR_DETAILS_API_RESPONSE = {
    "items": [
        {
            "id": "vid1",
            "snippet": {
                "title": "뮤직비디오 공식 MV",
                "channelTitle": "채널A",
                "publishedAt": "2026-03-19T10:00:00Z",
                "tags": ["음악"],
                "thumbnails": {
                    "high": {"url": "https://example.com/vid1.jpg"},
                },
            },
            "statistics": {"viewCount": "100000", "likeCount": "2000", "commentCount": "100"},
            "contentDetails": {"duration": "PT3M"},
        },
        {
            "id": "vid2",
            "snippet": {
                "title": "뮤직비디오 라이브 무대",
                "channelTitle": "채널B",
                "publishedAt": "2026-03-19T14:00:00Z",
                "thumbnails": {
                    "default": {"url": "https://example.com/vid2.jpg"},
                },
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


def test_category_analysis_endpoint(analysis_client):
    response = analysis_client.get("/categories/10/analysis")

    assert response.status_code == 200
    data = response.json()
    assert data["category_id"] == "10"
    assert data["video_count"] == 2
    assert len(data["keywords"]) > 0
    assert data["avg_upload_hour"] == 12.0  # hours 10,14 → avg 12.0
    assert data["avg_duration_seconds"] == 390.0  # 180 + 600 → avg 390
    assert data["duration_distribution"]["short"] == 1  # 180 < 240
    assert data["duration_distribution"]["medium"] == 1  # 600 in [240,1200]
    assert len(data["thumbnail_urls"]) == 2
```

```bash
cd /Users/daeunisnn/dev/yt-insight-lab && python -m pytest tests/test_analysis.py::test_category_analysis_endpoint -v
# Expected: FAILED (404 — endpoint not yet defined)
```

- [ ] **Step 4: categories analysis 엔드포인트 구현**

`app/routers/categories.py` 수정:
```python
from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.schemas import CategoriesResponse, PopularVideosResponse, CategoryAnalysis
from app.services.youtube import YouTubeService
from app.services.analyzer import analyze_category

router = APIRouter()


def get_youtube_service(settings: Settings = Depends(get_settings)) -> YouTubeService:
    return YouTubeService(settings=settings)


@router.get("/categories", response_model=CategoriesResponse)
def list_categories(
    service: YouTubeService = Depends(get_youtube_service),
) -> CategoriesResponse:
    categories = service.get_categories()
    return CategoriesResponse(categories=categories)


@router.get("/categories/{category_id}/videos", response_model=PopularVideosResponse)
def list_popular_videos(
    category_id: str,
    service: YouTubeService = Depends(get_youtube_service),
) -> PopularVideosResponse:
    videos = service.get_popular_videos(category_id)
    return PopularVideosResponse(category_id=category_id, videos=videos)


@router.get("/categories/{category_id}/analysis", response_model=CategoryAnalysis)
def get_category_analysis(
    category_id: str,
    service: YouTubeService = Depends(get_youtube_service),
) -> CategoryAnalysis:
    videos = service.get_popular_videos_with_details(category_id)
    return analyze_category(category_id, videos)
```

```bash
cd /Users/daeunisnn/dev/yt-insight-lab && python -m pytest tests/test_analysis.py -v
# Expected: all 8 tests PASSED
```

- [ ] **Step 5: 전체 테스트 실행**

```bash
cd /Users/daeunisnn/dev/yt-insight-lab && python -m pytest -v
# Expected: ALL tests PASSED (test_popular_videos, test_video_detail, test_parse_duration, test_analysis)
```

- [ ] **Step 6: 커밋**

```bash
cd /Users/daeunisnn/dev/yt-insight-lab && git add app/routers/videos.py app/routers/categories.py app/main.py tests/test_video_detail.py tests/test_analysis.py && git commit -m "feat: add GET /videos/{id}/detail and GET /categories/{id}/analysis endpoints"
```
