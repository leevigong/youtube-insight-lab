from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    youtube_api_key: str
    anthropic_api_key: str = ""
    database_url: str = "sqlite:///./data/trending.db"

    model_config = {"env_file": ".env"}


REGION_CODE = "KR"


def get_settings() -> Settings:
    return Settings()
