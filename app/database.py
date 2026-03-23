import logging
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import get_settings

logger = logging.getLogger(__name__)


settings = get_settings()

# SQLite 파일 경로의 디렉토리가 없으면 자동 생성
if settings.database_url.startswith("sqlite:///"):
    db_path = Path(settings.database_url.replace("sqlite:///", ""))
    db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def migrate_db(engine_instance):
    """기존 테이블에 새 컬럼이 없으면 추가합니다."""
    inspector = inspect(engine_instance)
    if "trending_videos" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("trending_videos")}
        with engine_instance.begin() as conn:
            if "video_type" not in columns:
                conn.execute(
                    text(
                        "ALTER TABLE trending_videos "
                        "ADD COLUMN video_type VARCHAR(10) DEFAULT 'regular'"
                    )
                )
                logger.info("Added video_type column to trending_videos")
            if "duration_seconds" not in columns:
                conn.execute(
                    text(
                        "ALTER TABLE trending_videos "
                        "ADD COLUMN duration_seconds INTEGER"
                    )
                )
                logger.info("Added duration_seconds column to trending_videos")


migrate_db(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
