from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TrendingVideo(Base):
    __tablename__ = "trending_videos"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[str] = mapped_column(String(20), index=True)
    category_id: Mapped[str] = mapped_column(String(10), index=True)
    title: Mapped[str] = mapped_column(String(200))
    channel_title: Mapped[str] = mapped_column(String(100))
    view_count: Mapped[int]
    like_count: Mapped[int]
    comment_count: Mapped[int]
    published_at: Mapped[str] = mapped_column(String(30))
    collected_at: Mapped[datetime] = mapped_column(default=func.now(), index=True)


class Keyword(Base):
    __tablename__ = "keywords"

    id: Mapped[int] = mapped_column(primary_key=True)
    keyword: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())


class KeywordVideo(Base):
    __tablename__ = "keyword_videos"

    id: Mapped[int] = mapped_column(primary_key=True)
    keyword_id: Mapped[int] = mapped_column(ForeignKey("keywords.id", ondelete="CASCADE"), index=True)
    video_id: Mapped[str] = mapped_column(String(20), index=True)
    title: Mapped[str] = mapped_column(String(200))
    channel_title: Mapped[str] = mapped_column(String(100))
    published_at: Mapped[str] = mapped_column(String(30))
    view_count: Mapped[int]
    like_count: Mapped[int]
    comment_count: Mapped[int]
    video_type: Mapped[str] = mapped_column(String(10), default="regular")
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(default=func.now(), index=True)
