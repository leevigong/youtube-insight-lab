from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.schemas import VideoDetail
from app.services.youtube import YouTubeService

router = APIRouter(prefix="/videos", tags=["동영상"])


def get_youtube_service(settings: Settings = Depends(get_settings)) -> YouTubeService:
    return YouTubeService(settings=settings)


@router.get(
    "/{video_id}/detail",
    response_model=VideoDetail,
    summary="동영상 상세 조회",
    description="특정 동영상의 상세 정보(통계, 태그, 썸네일 등)를 반환합니다.",
    responses={404: {"description": "동영상을 찾을 수 없음"}},
)
def get_video_detail(
    video_id: str,
    service: YouTubeService = Depends(get_youtube_service),
) -> VideoDetail:
    return service.get_video_details(video_id)
