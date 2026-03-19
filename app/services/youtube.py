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
