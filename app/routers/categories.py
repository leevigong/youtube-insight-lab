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
