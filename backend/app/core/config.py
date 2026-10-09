from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "YouTube Watch Party API"
    environment: str = "development"
    database_url: str = "sqlite:///./watch_party.db"
    frontend_url: str = "http://localhost:5173"
    room_code_length: int = 6

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
