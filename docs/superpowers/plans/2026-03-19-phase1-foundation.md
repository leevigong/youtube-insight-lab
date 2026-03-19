# Phase 1: 기반 구조 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** FastAPI 프로젝트 구조를 확립하고 YouTube 카테고리 목록 API(`GET /categories`)를 구현한다.

**Architecture:** pydantic-settings로 설정을 관리하고, services 계층에서 YouTube Data API를 호출하며, routers 계층에서 HTTP 엔드포인트를 노출한다. FastAPI의 Depends를 통해 의존성을 주입한다.

**Tech Stack:** Python 3.11+, FastAPI, pydantic-settings, google-api-python-client, pytest

**Spec:** `docs/superpowers/specs/2026-03-19-youtube-category-analysis-api-design.md`

---

## File Map

| Action | Path | Responsibility |
|--------|------|---------------|
| Modify | `pyproject.toml` | `pydantic-settings` 의존성 추가, `httpx` dev 의존성 추가 |
| Create | `app/config.py` | Settings 클래스 (API 키, 지역코드) |
| Create | `app/schemas.py` | Pydantic 응답 모델 |
| Create | `app/services/__init__.py` | 패키지 초기화 |
| Create | `app/services/youtube.py` | YouTube API 클라이언트 |
| Create | `app/routers/__init__.py` | 패키지 초기화 |
| Create | `app/routers/categories.py` | `GET /categories` 엔드포인트 |
| Modify | `app/main.py` | 라우터 등록 |
| Create | `tests/__init__.py` | 테스트 패키지 |
| Create | `tests/test_categories.py` | 엔드포인트 테스트 |

---

### Task 1: 의존성 추가 + 설정 모듈

**Files:**
- Modify: `pyproject.toml:6-12`
- Create: `app/config.py`
- Test: `tests/test_categories.py` (config 테스트 부분)

- [ ] **Step 1: `pyproject.toml`에 `pydantic-settings` 추가**

```toml
dependencies = [
    "fastapi",
    "uvicorn",
    "google-api-python-client",
    "pandas",
    "pydantic-settings",
    "python-dotenv",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "httpx",
    "ruff",
]
```

- [ ] **Step 2: 설치 확인**

Run: `pip install -e .`
Expected: 성공, pydantic-settings 설치됨

- [ ] **Step 3: `app/config.py` 작성**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    youtube_api_key: str

    model_config = {"env_file": ".env"}


REGION_CODE = "KR"


def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml app/config.py
git commit -m "feat: add pydantic-settings config module"
```

---

### Task 2: 스키마 정의

**Files:**
- Create: `app/schemas.py`

- [ ] **Step 1: 테스트 작성 — 스키마 검증**

`tests/test_categories.py` 생성:

```python
from app.schemas import Category, CategoriesResponse


def test_category_schema():
    cat = Category(id="10", title="Music", assignable=True)
    assert cat.id == "10"
    assert cat.title == "Music"
    assert cat.assignable is True


def test_categories_response_schema():
    resp = CategoriesResponse(
        categories=[
            Category(id="1", title="Film & Animation", assignable=True),
            Category(id="10", title="Music", assignable=True),
        ]
    )
    assert len(resp.categories) == 2
    assert resp.categories[0].id == "1"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_categories.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.schemas'`

- [ ] **Step 3: `app/schemas.py` 작성**

```python
from pydantic import BaseModel


class Category(BaseModel):
    id: str
    title: str
    assignable: bool


class CategoriesResponse(BaseModel):
    categories: list[Category]
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_categories.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add app/schemas.py tests/__init__.py tests/test_categories.py
git commit -m "feat: add Category and CategoriesResponse schemas"
```

---

### Task 3: YouTube 서비스

**Files:**
- Create: `app/services/__init__.py`
- Create: `app/services/youtube.py`
- Modify: `tests/test_categories.py`

- [ ] **Step 1: 테스트 작성 — `get_categories()` mock 테스트**

`tests/test_categories.py`에 추가:

```python
from unittest.mock import MagicMock, patch

from app.config import REGION_CODE
from app.services.youtube import YouTubeService


MOCK_CATEGORIES_RESPONSE = {
    "items": [
        {
            "id": "1",
            "snippet": {"title": "Film & Animation", "assignable": True},
        },
        {
            "id": "10",
            "snippet": {"title": "Music", "assignable": True},
        },
        {
            "id": "15",
            "snippet": {"title": "Pets & Animals", "assignable": False},
        },
    ]
}


def test_get_categories():
    mock_youtube = MagicMock()
    mock_youtube.videoCategories().list().execute.return_value = (
        MOCK_CATEGORIES_RESPONSE
    )

    service = YouTubeService(client=mock_youtube)
    categories = service.get_categories()

    assert len(categories) == 3
    assert categories[0].id == "1"
    assert categories[0].title == "Film & Animation"
    assert categories[0].assignable is True
    assert categories[2].assignable is False
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_categories.py::test_get_categories -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services'`

- [ ] **Step 3: 서비스 구현**

`app/services/__init__.py` — 빈 파일

`app/services/youtube.py`:

```python
from googleapiclient.discovery import build
from fastapi import HTTPException

from app.config import Settings, REGION_CODE
from app.schemas import Category


class YouTubeService:
    def __init__(self, client=None, settings: Settings | None = None):
        if client:
            self.client = client
        elif settings:
            self.client = build(
                "youtube", "v3", developerKey=settings.youtube_api_key
            )
        else:
            raise ValueError("Either client or settings must be provided")

    def get_categories(self) -> list[Category]:
        try:
            response = (
                self.client.videoCategories()
                .list(part="snippet", regionCode=REGION_CODE)
                .execute()
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"YouTube API error: {e}")

        return [
            Category(
                id=item["id"],
                title=item["snippet"]["title"],
                assignable=item["snippet"].get("assignable", False),
            )
            for item in response.get("items", [])
        ]
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_categories.py::test_get_categories -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/__init__.py app/services/youtube.py tests/test_categories.py
git commit -m "feat: add YouTubeService with get_categories method"
```

---

### Task 4: 라우터 + 엔드포인트

**Files:**
- Create: `app/routers/__init__.py`
- Create: `app/routers/categories.py`
- Modify: `tests/test_categories.py`

- [ ] **Step 1: 테스트 작성 — `GET /categories` 통합 테스트**

`tests/test_categories.py`에 추가:

```python
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.categories import get_youtube_service
from app.services.youtube import YouTubeService


def _mock_youtube_service():
    mock_client = MagicMock()
    mock_client.videoCategories().list().execute.return_value = (
        MOCK_CATEGORIES_RESPONSE
    )
    return YouTubeService(client=mock_client)


@pytest.fixture()
def client():
    app.dependency_overrides[get_youtube_service] = _mock_youtube_service
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_categories_endpoint(client):
    response = client.get("/categories")

    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    assert len(data["categories"]) == 3
    assert data["categories"][0]["id"] == "1"
    assert data["categories"][0]["title"] == "Film & Animation"
    assert data["categories"][0]["assignable"] is True
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_categories.py::test_get_categories_endpoint -v`
Expected: FAIL — 404 (라우터 미등록)

- [ ] **Step 3: 라우터 구현**

`app/routers/__init__.py` — 빈 파일

`app/routers/categories.py`:

```python
from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.schemas import CategoriesResponse
from app.services.youtube import YouTubeService

router = APIRouter()


def get_youtube_service(settings: Settings = Depends(get_settings)) -> YouTubeService:
    return YouTubeService(settings=settings)


@router.get("/categories", response_model=CategoriesResponse)
def list_categories(
    service: YouTubeService = Depends(get_youtube_service),
) -> CategoriesResponse:
    categories = service.get_categories()
    return CategoriesResponse(categories=categories)
```

- [ ] **Step 4: `app/main.py` 수정 — 라우터 등록**

```python
from fastapi import FastAPI

from app.routers.categories import router as categories_router

app = FastAPI(title="yt-insight-lab")

app.include_router(categories_router)


@app.get("/")
def root():
    return {"message": "yt-insight-lab"}
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `pytest tests/test_categories.py -v`
Expected: 4 passed

- [ ] **Step 6: Lint & format 확인**

Run: `ruff check . && ruff format .`
Expected: 에러 없음

- [ ] **Step 7: Commit**

```bash
git add app/routers/__init__.py app/routers/categories.py app/main.py tests/test_categories.py
git commit -m "feat: add GET /categories endpoint with router"
```
