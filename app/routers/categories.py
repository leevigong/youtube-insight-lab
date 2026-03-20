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
    category_id: str, service: YouTubeService = Depends(get_youtube_service)
) -> PopularVideosResponse:
    videos = service.get_popular_videos(category_id)
    return PopularVideosResponse(category_id=category_id, videos=videos)


@router.get("/categories/{category_id}/analysis", response_model=CategoryAnalysis)
def get_category_analysis(
    category_id: str, service: YouTubeService = Depends(get_youtube_service)
) -> CategoryAnalysis:
    videos = service.get_popular_videos_with_details(category_id)
    return analyze_category(category_id, videos)
