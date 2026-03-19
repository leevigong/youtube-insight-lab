from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    youtube_api_key: str

    model_config = {"env_file": ".env"}


REGION_CODE = "KR"


def get_settings() -> Settings:
    return Settings()
