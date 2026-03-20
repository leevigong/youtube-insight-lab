from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import TrendingVideo


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_trending_video_model_creation():
    db = _make_session()
    video = TrendingVideo(
        video_id="abc123",
        category_id="10",
        title="Test Video",
        channel_title="Test Channel",
        view_count=1000,
        like_count=50,
        comment_count=10,
        published_at="2026-03-19T12:00:00Z",
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    assert video.id is not None
    assert video.video_id == "abc123"
    assert video.category_id == "10"
    assert video.title == "Test Video"
    assert video.collected_at is not None


def test_trending_video_duplicate_video_id_allowed():
    db = _make_session()
    v1 = TrendingVideo(
        video_id="abc123",
        category_id="10",
        title="Test Video Day 1",
        channel_title="Channel",
        view_count=1000,
        like_count=50,
        comment_count=10,
        published_at="2026-03-19T12:00:00Z",
    )
    v2 = TrendingVideo(
        video_id="abc123",
        category_id="10",
        title="Test Video Day 2",
        channel_title="Channel",
        view_count=2000,
        like_count=100,
        comment_count=20,
        published_at="2026-03-19T12:00:00Z",
    )
    db.add_all([v1, v2])
    db.commit()

    results = db.query(TrendingVideo).filter_by(video_id="abc123").all()
    assert len(results) == 2
