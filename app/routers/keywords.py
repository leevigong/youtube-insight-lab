from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.models import Keyword, KeywordVideo
from app.schemas import (
    KeywordCollectResponse,
    KeywordCreate,
    KeywordListResponse,
    KeywordResponse,
    KeywordVideoItem,
    KeywordVideosResponse,
    SurgeResponse,
)
from app.services.keyword_collector import collect_keyword_videos
from app.services.surge_detector import detect_surge
from app.services.youtube import YouTubeService

router = APIRouter(prefix="/keywords", tags=["키워드"])


def get_youtube_service(settings: Settings = Depends(get_settings)) -> YouTubeService:
    return YouTubeService(settings=settings)


@router.post(
    "",
    response_model=KeywordResponse,
    status_code=201,
    summary="키워드 등록",
    description="관심 키워드를 등록합니다. 등록된 키워드는 매일 자동으로 관련 영상을 수집합니다.",
    responses={409: {"description": "이미 등록된 키워드"}},
)
def create_keyword(
    body: KeywordCreate,
    db: Session = Depends(get_db),
) -> KeywordResponse:
    existing = db.query(Keyword).filter(Keyword.keyword == body.keyword).first()
    if existing:
        raise HTTPException(status_code=409, detail="이미 등록된 키워드입니다.")

    keyword = Keyword(keyword=body.keyword)
    db.add(keyword)
    db.commit()
    db.refresh(keyword)

    return KeywordResponse(
        id=keyword.id,
        keyword=keyword.keyword,
        created_at=keyword.created_at.isoformat(),
    )


@router.get(
    "",
    response_model=KeywordListResponse,
    summary="키워드 목록 조회",
    description="등록된 모든 관심 키워드를 반환합니다.",
)
def list_keywords(
    db: Session = Depends(get_db),
) -> KeywordListResponse:
    keywords = db.query(Keyword).order_by(Keyword.created_at.desc()).all()
    return KeywordListResponse(
        keywords=[
            KeywordResponse(
                id=kw.id,
                keyword=kw.keyword,
                created_at=kw.created_at.isoformat(),
            )
            for kw in keywords
        ]
    )


@router.delete(
    "/{keyword_id}",
    status_code=204,
    summary="키워드 삭제",
    description="키워드와 관련 수집 데이터를 모두 삭제합니다.",
    responses={404: {"description": "키워드를 찾을 수 없음"}},
)
def delete_keyword(
    keyword_id: int = Path(description="삭제할 키워드 ID"),
    db: Session = Depends(get_db),
) -> None:
    keyword = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="키워드를 찾을 수 없습니다.")

    db.query(KeywordVideo).filter(KeywordVideo.keyword_id == keyword_id).delete()
    db.delete(keyword)
    db.commit()


@router.get(
    "/{keyword_id}/videos",
    response_model=KeywordVideosResponse,
    summary="키워드 영상 목록 조회",
    description="특정 키워드로 수집된 영상 목록을 반환합니다.",
    responses={404: {"description": "키워드를 찾을 수 없음"}},
)
def list_keyword_videos(
    keyword_id: int = Path(description="키워드 ID"),
    days: int = Query(default=7, ge=1, le=90, description="조회 기간 (일)"),
    video_type: str | None = Query(
        default=None,
        description="동영상 유형 필터 (regular: 일반, shorts: 쇼츠, 미지정 시 전체)",
    ),
    db: Session = Depends(get_db),
) -> KeywordVideosResponse:
    keyword = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="키워드를 찾을 수 없습니다.")

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    query = db.query(KeywordVideo).filter(
        KeywordVideo.keyword_id == keyword_id,
        KeywordVideo.collected_at >= cutoff,
    )
    if video_type:
        query = query.filter(KeywordVideo.video_type == video_type)

    videos = query.order_by(KeywordVideo.view_count.desc()).all()

    return KeywordVideosResponse(
        keyword_id=keyword.id,
        keyword=keyword.keyword,
        videos=[
            KeywordVideoItem(
                video_id=v.video_id,
                title=v.title,
                channel_title=v.channel_title,
                published_at=v.published_at,
                view_count=v.view_count,
                like_count=v.like_count,
                comment_count=v.comment_count,
                video_type=v.video_type,
                duration_seconds=v.duration_seconds,
                collected_at=v.collected_at.isoformat(),
            )
            for v in videos
        ],
    )


@router.get(
    "/{keyword_id}/surge",
    response_model=SurgeResponse,
    summary="조회수 급등 영상 조회",
    description="특정 키워드에서 조회수가 급등한 영상을 반환합니다. "
    "증가율 200% 이상 또는 키워드 평균 대비 3배 이상이면 급등으로 판정합니다.",
    responses={404: {"description": "키워드를 찾을 수 없음"}},
)
def get_surge_videos(
    keyword_id: int = Path(description="키워드 ID"),
    days: int = Query(default=7, ge=1, le=90, description="조회 기간 (일)"),
    db: Session = Depends(get_db),
) -> SurgeResponse:
    keyword = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="키워드를 찾을 수 없습니다.")

    return detect_surge(db, keyword_id, days)


@router.post(
    "/collect",
    response_model=KeywordCollectResponse,
    summary="키워드 영상 수동 수집",
    description="등록된 모든 키워드에 대해 YouTube 영상을 즉시 수집합니다.",
)
def collect(
    db: Session = Depends(get_db),
    youtube_service: YouTubeService = Depends(get_youtube_service),
) -> KeywordCollectResponse:
    return collect_keyword_videos(db=db, youtube_service=youtube_service)
