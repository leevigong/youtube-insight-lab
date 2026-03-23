from datetime import datetime

from sqlalchemy import Integer, String, func
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
    video_type: Mapped[str] = mapped_column(String(10), default="regular", index=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(default=func.now(), index=True)
