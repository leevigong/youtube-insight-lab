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
