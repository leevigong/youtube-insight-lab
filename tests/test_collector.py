from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import TrendingVideo
from app.services.collector import collect_trending_videos
from app.services.youtube import YouTubeService


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


MOCK_CATEGORIES_RESPONSE = {
    "items": [
        {"id": "10", "snippet": {"title": "Music", "assignable": True}},
        {"id": "20", "snippet": {"title": "Gaming", "assignable": True}},
        {"id": "99", "snippet": {"title": "Not Assignable", "assignable": False}},
    ]
}

MOCK_VIDEOS_RESPONSE = {
    "items": [
        {
            "id": "vid1",
            "snippet": {
                "title": "Popular Music Video",
                "channelTitle": "Channel A",
                "publishedAt": "2026-03-18T10:00:00Z",
                "thumbnails": {"high": {"url": "https://example.com/vid1.jpg"}},
            },
            "statistics": {
                "viewCount": "150000",
                "likeCount": "3000",
                "commentCount": "200",
            },
            "contentDetails": {"duration": "PT5M30S"},
        },
        {
            "id": "vid2",
            "snippet": {
                "title": "Another Video",
                "channelTitle": "Channel B",
                "publishedAt": "2026-03-17T08:30:00Z",
                "thumbnails": {"high": {"url": "https://example.com/vid2.jpg"}},
            },
            "statistics": {
                "viewCount": "80000",
                "likeCount": "1500",
                "commentCount": "100",
            },
            "contentDetails": {"duration": "PT10M"},
        },
    ]
}


def _make_mock_youtube_service():
    mock_client = MagicMock()
    mock_client.videoCategories().list().execute.return_value = (
        MOCK_CATEGORIES_RESPONSE
    )
    mock_client.videos().list().execute.return_value = MOCK_VIDEOS_RESPONSE
    return YouTubeService(client=mock_client)


def test_collect_trending_videos():
    db = _make_session()
    service = _make_mock_youtube_service()

    result = collect_trending_videos(db=db, youtube_service=service)

    assert result.collected_categories == 2  # assignable만
    assert result.collected_videos == 2  # dedup: vid1, vid2 (same across categories)
    assert result.collected_at is not None

    videos = db.query(TrendingVideo).all()
    assert len(videos) == 2
    assert all(v.video_type == "regular" for v in videos)
    assert all(v.duration_seconds is not None for v in videos)


def test_collect_dedup_within_same_run():
    db = _make_session()
    mock_client = MagicMock()
    mock_client.videoCategories().list().execute.return_value = {
        "items": [
            {"id": "10", "snippet": {"title": "Music", "assignable": True}},
            {"id": "20", "snippet": {"title": "Gaming", "assignable": True}},
        ]
    }
    # 두 카테고리 모두 같은 영상 반환 (vid1, vid2)
    mock_client.videos().list().execute.return_value = MOCK_VIDEOS_RESPONSE
    service = YouTubeService(client=mock_client)

    result = collect_trending_videos(db=db, youtube_service=service)

    # vid1, vid2가 카테고리 10에서 수집 → 카테고리 20에서는 중복이므로 스킵
    assert result.collected_videos == 2

    videos = db.query(TrendingVideo).all()
    assert len(videos) == 2


def test_collect_empty_categories():
    db = _make_session()
    mock_client = MagicMock()
    mock_client.videoCategories().list().execute.return_value = {"items": []}
    service = YouTubeService(client=mock_client)

    result = collect_trending_videos(db=db, youtube_service=service)

    assert result.collected_categories == 0
    assert result.collected_videos == 0
