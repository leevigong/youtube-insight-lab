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
