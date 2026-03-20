from googleapiclient.discovery import build
from fastapi import HTTPException

from app.config import Settings, REGION_CODE
from app.schemas import Category, Video, VideoStats


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

    def get_popular_videos(self, category_id: str) -> list[Video]:
        try:
            response = (
                self.client.videos()
                .list(
                    part="snippet,statistics",
                    chart="mostPopular",
                    videoCategoryId=category_id,
                    regionCode=REGION_CODE,
                    maxResults=20,
                )
                .execute()
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"YouTube API error: {e}")

        return [
            Video(
                id=item["id"],
                title=item["snippet"]["title"],
                channel_title=item["snippet"]["channelTitle"],
                published_at=item["snippet"]["publishedAt"],
                stats=VideoStats(
                    view_count=int(item["statistics"]["viewCount"]),
                    like_count=int(item["statistics"]["likeCount"]),
                    comment_count=int(item["statistics"]["commentCount"]),
                ),
            )
            for item in response.get("items", [])
        ]
