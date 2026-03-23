# CLAUDE.md

## 프로젝트 개요

YouTube 인기 동영상 분석 API (FastAPI + SQLAlchemy)

## 기술 스택

- Python / FastAPI / Uvicorn
- SQLAlchemy (SQLite)
- Pydantic (스키마)
- APScheduler (수집 스케줄러)

## 프로젝트 구조

```
app/
  main.py          # FastAPI 앱 진입점
  config.py        # 환경변수 설정
  database.py      # DB 연결
  models.py        # SQLAlchemy 모델
  schemas.py       # Pydantic 스키마
  scheduler.py     # 수집 스케줄러
  routers/         # API 엔드포인트
  services/        # 비즈니스 로직
```

## 개발 명령어

```bash
uv run uvicorn app.main:app --reload   # 서버 실행
uv run pytest                          # 테스트
uv run ruff check .                    # 린트
```

## API 문서 (Swagger) 규칙

### 모든 API 문서는 한글로 작성한다

- `summary`, `description`, `Field(description=...)`, `Query(description=...)` 모두 한글
- Swagger UI(`/docs`)에서 한글로 보여야 한다

### 엔드포인트 작성 시 필수 항목

```python
@router.get(
    "/path",
    response_model=ResponseModel,
    summary="한글 요약 (한 줄)",
    description="한글 상세 설명",
    responses={404: {"description": "리소스를 찾을 수 없음"}},
)
```

### 스키마 필드에 반드시 description 추가

```python
class Video(BaseModel):
    id: str = Field(description="YouTube 동영상 ID")
    title: str = Field(description="동영상 제목")
```

### 쿼리 파라미터에 description 추가

```python
days: int = Query(default=7, ge=1, le=90, description="조회 기간 (일)")
```

### 라우터에 한글 태그 설정

```python
router = APIRouter(prefix="/categories", tags=["카테고리"])
```

## 커밋 컨벤션

- `feat:` 새 기능
- `fix:` 버그 수정
- `docs:` 문서
- `refactor:` 리팩토링
