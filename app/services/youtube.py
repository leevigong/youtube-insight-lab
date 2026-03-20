import re

from googleapiclient.discovery import build
from fastapi import HTTPException

from app.config import Settings, REGION_CODE
from app.schemas import Category, Video, VideoStats, VideoDetail


def parse_duration(duration: str) -> int:
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


class YouTubeService:
    def __init__(self, client=None, settings: Settings | None = None):
        if client:
            self.client = client
        elif settings:
            self.client = build("youtube", "v3", developerKey=settings.youtube_api_key)
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

    def _get_thumbnail_url(self, thumbnails: dict) -> str:
        for key in ("maxres", "high", "medium", "default"):
            if key in thumbnails:
                return thumbnails[key]["url"]
        return ""

    def get_video_details(self, video_id: str) -> VideoDetail:
        try:
            response = (
                self.client.videos()
                .list(part="snippet,statistics,contentDetails", id=video_id)
                .execute()
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"YouTube API error: {e}")
        items = response.get("items", [])
        if not items:
            raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")
        item = items[0]
        snippet = item["snippet"]
        stats = item["statistics"]
        content = item["contentDetails"]
        return VideoDetail(
            id=item["id"], title=snippet["title"],
            channel_title=snippet["channelTitle"],
            published_at=snippet["publishedAt"],
            stats=VideoStats(
                view_count=int(stats.get("viewCount", 0)),
                like_count=int(stats.get("likeCount", 0)),
                comment_count=int(stats.get("commentCount", 0)),
            ),
            duration_seconds=parse_duration(content["duration"]),
            tags=snippet.get("tags", []),
            thumbnail_url=self._get_thumbnail_url(snippet.get("thumbnails", {})),
        )

    def get_popular_videos_with_details(self, category_id: str) -> list[VideoDetail]:
        try:
            response = (
                self.client.videos()
                .list(
                    part="snippet,statistics,contentDetails",
                    chart="mostPopular", videoCategoryId=category_id,
                    regionCode=REGION_CODE, maxResults=20,
                )
                .execute()
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"YouTube API error: {e}")
        results = []
        for item in response.get("items", []):
            snippet = item["snippet"]
            stats = item["statistics"]
            content = item["contentDetails"]
            results.append(VideoDetail(
                id=item["id"], title=snippet["title"],
                channel_title=snippet["channelTitle"],
                published_at=snippet["publishedAt"],
                stats=VideoStats(
                    view_count=int(stats.get("viewCount", 0)),
                    like_count=int(stats.get("likeCount", 0)),
                    comment_count=int(stats.get("commentCount", 0)),
                ),
                duration_seconds=parse_duration(content["duration"]),
                tags=snippet.get("tags", []),
                thumbnail_url=self._get_thumbnail_url(snippet.get("thumbnails", {})),
            ))
        return results
