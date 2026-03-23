from pydantic import BaseModel


class Category(BaseModel):
    id: str
    title: str
    assignable: bool


class CategoriesResponse(BaseModel):
    categories: list[Category]


class VideoStats(BaseModel):
    view_count: int
    like_count: int
    comment_count: int


class Video(BaseModel):
    id: str
    title: str
    channel_title: str
    published_at: str
    stats: VideoStats


class PopularVideosResponse(BaseModel):
    category_id: str
    videos: list[Video]


class VideoDetail(BaseModel):
    id: str
    title: str
    channel_title: str
    published_at: str
    stats: VideoStats
    duration_seconds: int
    tags: list[str]
    thumbnail_url: str


class KeywordFrequency(BaseModel):
    keyword: str
    count: int


class DurationDistribution(BaseModel):
    short: int
    medium: int
    long: int


class CategoryAnalysis(BaseModel):
    category_id: str
    video_count: int
    keywords: list[KeywordFrequency]
    avg_upload_hour: float
    avg_duration_seconds: float
    duration_distribution: DurationDistribution
    thumbnail_urls: list[str]


class CollectResponse(BaseModel):
    collected_categories: int
    collected_videos: int
    collected_at: str


class DailyKeywordCount(BaseModel):
    date: str
    count: int


class TrendKeyword(BaseModel):
    keyword: str
    daily: list[DailyKeywordCount]


class KeywordTrend(BaseModel):
    days: int
    keywords: list[TrendKeyword]


class DailyStats(BaseModel):
    date: str
    avg_view_count: float
    avg_like_count: float
    video_count: int


class TimelineTrend(BaseModel):
    category_id: str
    days: int
    daily_stats: list[DailyStats]
