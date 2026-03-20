# Phase 3: 영상 상세 패턴 분석 설계

## 개요

카테고리별 인기 영상의 상세 정보를 조회하고, pandas를 활용해 패턴을 분석하는 기능.

## 엔드포인트

### `GET /videos/{id}/detail`

개별 영상의 상세 정보 조회.

**YouTube API 호출:**
- `videos.list(part="snippet,statistics,contentDetails", id=video_id, regionCode="KR")`

**응답:**
```json
{
  "id": "abc123",
  "title": "영상 제목",
  "channel_title": "채널명",
  "published_at": "2026-03-19T12:00:00Z",
  "stats": {"view_count": 150000, "like_count": 3000, "comment_count": 200},
  "duration_seconds": 933,
  "tags": ["키워드1", "키워드2"],
  "thumbnail_url": "https://i.ytimg.com/vi/abc123/maxresdefault.jpg"
}
```

### `GET /categories/{id}/analysis`

카테고리의 인기 영상 20개를 분석.

**로직:**
1. `videos.list(part="snippet,statistics,contentDetails", chart="mostPopular", videoCategoryId=id, regionCode="KR", maxResults=20)` 호출
2. pandas DataFrame으로 변환 후 분석

**응답:**
```json
{
  "category_id": "10",
  "video_count": 20,
  "keywords": [
    {"keyword": "뮤직비디오", "count": 8},
    {"keyword": "공식", "count": 5}
  ],
  "avg_upload_hour": 15.3,
  "avg_duration_seconds": 245.7,
  "duration_distribution": {"short": 5, "medium": 12, "long": 3},
  "thumbnail_urls": ["https://...", "https://..."]
}
```

## 스키마

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
    short: int    # < 240초 (4분)
    medium: int   # 240-1200초 (4-20분)
    long: int     # > 1200초 (20분)

class CategoryAnalysis(BaseModel):
    category_id: str
    video_count: int
    keywords: list[KeywordFrequency]
    avg_upload_hour: float
    avg_duration_seconds: float
    duration_distribution: DurationDistribution
    thumbnail_urls: list[str]
```

## 서비스 계층

### `services/youtube.py` 수정

- `get_video_details(video_id: str) -> VideoDetail` 추가
  - `contentDetails.duration` (ISO 8601, "PT15M33S") → 초 단위로 변환
  - `snippet.tags` → 리스트 (없으면 빈 리스트)
  - `snippet.thumbnails.maxres.url` → 없으면 `high.url` fallback
- `get_popular_videos_with_details(category_id: str) -> list[VideoDetail]` 추가
  - `part="snippet,statistics,contentDetails"` 로 한 번에 조회

### `services/analyzer.py` 신규

- `analyze_category(videos: list[VideoDetail]) -> CategoryAnalysis`
  - pandas DataFrame 생성
  - 제목 키워드 빈도: 제목을 공백 분리 → Counter → 상위 10개
  - 평균 업로드 시간대: `published_at` 파싱 → hour 추출 → 평균
  - 평균 영상 길이: `duration_seconds` 평균
  - 구간 분포: short(<240) / medium(240-1200) / long(>1200) 카운트
  - 섬네일 URL 목록

### ISO 8601 duration 파싱

`isodate` 라이브러리 또는 정규식으로 "PT15M33S" → 933초 변환. 정규식 방식 사용 (의존성 최소화):

```python
import re

def parse_duration(duration: str) -> int:
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds
```

## 라우터

### `routers/videos.py` 신규

- `GET /videos/{video_id}/detail` → `YouTubeService.get_video_details(video_id)`

### `routers/categories.py` 수정

- `GET /categories/{category_id}/analysis` → 영상 조회 + 분석

## 프로젝트 구조 변경

```
app/
├── services/
│   ├── youtube.py      # get_video_details, get_popular_videos_with_details 추가
│   └── analyzer.py     # 신규: analyze_category
├── routers/
│   ├── categories.py   # GET /categories/{id}/analysis 추가
│   └── videos.py       # 신규: GET /videos/{id}/detail
└── schemas.py          # VideoDetail, KeywordFrequency, DurationDistribution, CategoryAnalysis 추가
```

## 테스트 전략

- `tests/test_video_detail.py` — 영상 상세 엔드포인트 + 서비스 테스트
- `tests/test_analysis.py` — 분석 로직 테스트 (analyzer 단위 테스트 + 엔드포인트 통합)
- `parse_duration` 유틸 테스트
- YouTube API mock 처리
