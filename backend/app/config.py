# backend/app/config.py
# Application settings via pydantic-settings
# Membaca konfigurasi dari environment variables / .env

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://user:pass@db:5432/cts"
    secret_key: str = "change-me-in-production"
    cors_origins: str = "http://localhost"

    class Config:
        env_file = ".env"


settings = Settings()
