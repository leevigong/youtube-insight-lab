from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.categories import get_youtube_service
from app.schemas import CollectResponse
from app.services.collector import collect_trending_videos
from app.services.youtube import YouTubeService

router = APIRouter()


@router.post("/collect", response_model=CollectResponse)
def collect(
    db: Session = Depends(get_db),
    youtube_service: YouTubeService = Depends(get_youtube_service),
) -> CollectResponse:
    return collect_trending_videos(db=db, youtube_service=youtube_service)
