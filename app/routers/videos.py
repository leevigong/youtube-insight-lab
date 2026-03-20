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
