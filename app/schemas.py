from pydantic import BaseModel, Field


class Category(BaseModel):
    id: str = Field(description="YouTube 카테고리 ID")
    title: str = Field(description="카테고리 이름")
    assignable: bool = Field(description="동영상에 할당 가능 여부")


class CategoriesResponse(BaseModel):
    categories: list[Category] = Field(description="카테고리 목록")


class VideoStats(BaseModel):
    view_count: int = Field(description="조회수")
    like_count: int = Field(description="좋아요 수")
    comment_count: int = Field(description="댓글 수")


class Video(BaseModel):
    id: str = Field(description="YouTube 동영상 ID")
    title: str = Field(description="동영상 제목")
    channel_title: str = Field(description="채널명")
    published_at: str = Field(description="게시일시 (ISO 8601)")
    stats: VideoStats = Field(description="조회수/좋아요/댓글 통계")


class PopularVideosResponse(BaseModel):
    category_id: str = Field(description="카테고리 ID")
    videos: list[Video] = Field(description="인기 동영상 목록")


class VideoDetail(BaseModel):
    id: str = Field(description="YouTube 동영상 ID")
    title: str = Field(description="동영상 제목")
    channel_title: str = Field(description="채널명")
    published_at: str = Field(description="게시일시 (ISO 8601)")
    stats: VideoStats = Field(description="조회수/좋아요/댓글 통계")
    duration_seconds: int = Field(description="영상 길이 (초)")
    tags: list[str] = Field(description="태그 목록")
    thumbnail_url: str = Field(description="썸네일 이미지 URL")


class KeywordFrequency(BaseModel):
    keyword: str = Field(description="키워드")
    count: int = Field(description="출현 횟수")


class DurationDistribution(BaseModel):
    short: int = Field(description="짧은 영상 수 (4분 이하)")
    medium: int = Field(description="중간 영상 수 (4~20분)")
    long: int = Field(description="긴 영상 수 (20분 초과)")


class CategoryAnalysis(BaseModel):
    category_id: str = Field(description="카테고리 ID")
    video_count: int = Field(description="분석 대상 동영상 수")
    keywords: list[KeywordFrequency] = Field(description="키워드 빈도 목록")
    avg_upload_hour: float = Field(description="평균 업로드 시간 (0~23)")
    avg_duration_seconds: float = Field(description="평균 영상 길이 (초)")
    duration_distribution: DurationDistribution = Field(description="영상 길이 분포")
    thumbnail_urls: list[str] = Field(description="썸네일 URL 목록")


class CollectResponse(BaseModel):
    collected_categories: int = Field(description="수집된 카테고리 수")
    collected_videos: int = Field(description="수집된 동영상 수")
    collected_at: str = Field(description="수집 일시 (ISO 8601)")


class DailyKeywordCount(BaseModel):
    date: str = Field(description="날짜 (YYYY-MM-DD)")
    count: int = Field(description="출현 횟수")


class TrendKeyword(BaseModel):
    keyword: str = Field(description="키워드")
    daily: list[DailyKeywordCount] = Field(description="일별 출현 횟수")


class KeywordTrend(BaseModel):
    days: int = Field(description="조회 기간 (일)")
    keywords: list[TrendKeyword] = Field(description="상위 키워드 트렌드")


class DailyStats(BaseModel):
    date: str = Field(description="날짜 (YYYY-MM-DD)")
    avg_view_count: float = Field(description="일 평균 조회수")
    avg_like_count: float = Field(description="일 평균 좋아요 수")
    video_count: int = Field(description="동영상 수")


class TimelineTrend(BaseModel):
    category_id: str = Field(description="카테고리 ID")
    days: int = Field(description="조회 기간 (일)")
    daily_stats: list[DailyStats] = Field(description="일별 통계")
