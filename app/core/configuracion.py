from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AFP SaaS User Management API"
    debug: bool = False

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/af_saas"
    )

    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    invitation_token_expire_hours: int = 48

    media_root: str = "app/media"
    media_url: str = "/media"
    frontend_base_url: str = "http://localhost:4200"

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    smtp_from_email: str = "no-reply@auxiliomecanico.local"

    cors_origins: str = "*"

    # Cloudinary / OpenAI (agregadas para permitir variables extra en .env)
    cloudinary_cloud_name: str | None = None
    cloudinary_api_key: str | None = None
    cloudinary_api_secret: str | None = None
    openai_api_key: str | None = None
    firebase_credentials_path: str | None = None
    FIREBASE_CREDENTIALS_PATH: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
