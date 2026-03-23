from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.schemas import CategoriesResponse, PopularVideosResponse, CategoryAnalysis
from app.services.youtube import YouTubeService
from app.services.analyzer import analyze_category

router = APIRouter(prefix="/categories", tags=["카테고리"])


def get_youtube_service(settings: Settings = Depends(get_settings)) -> YouTubeService:
    return YouTubeService(settings=settings)


@router.get(
    "",
    response_model=CategoriesResponse,
    summary="카테고리 목록 조회",
    description="YouTube에서 사용 가능한 모든 동영상 카테고리를 반환합니다.",
)
def list_categories(
    service: YouTubeService = Depends(get_youtube_service),
) -> CategoriesResponse:
    categories = service.get_categories()
    return CategoriesResponse(categories=categories)


@router.get(
    "/{category_id}/videos",
    response_model=PopularVideosResponse,
    summary="카테고리별 인기 동영상 조회",
    description="특정 카테고리의 인기 동영상 목록을 반환합니다.",
)
def list_popular_videos(
    category_id: str, service: YouTubeService = Depends(get_youtube_service)
) -> PopularVideosResponse:
    videos = service.get_popular_videos(category_id)
    return PopularVideosResponse(category_id=category_id, videos=videos)


@router.get(
    "/{category_id}/analysis",
    response_model=CategoryAnalysis,
    summary="카테고리 분석",
    description="특정 카테고리의 인기 동영상을 분석하여 키워드 빈도, 평균 업로드 시간, 영상 길이 분포 등을 반환합니다.",
)
def get_category_analysis(
    category_id: str, service: YouTubeService = Depends(get_youtube_service)
) -> CategoryAnalysis:
    videos = service.get_popular_videos_with_details(category_id)
    return analyze_category(category_id, videos)
