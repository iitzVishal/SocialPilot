from typing import List, Union, Optional
from pydantic import AnyHttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "SocialPilot API"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # CORS Configuration
    ALLOWED_ORIGINS: Union[str, List[str]] = "http://localhost:5173,http://127.0.0.1:5173,https://socialpilot-frontend-indol.vercel.app"


    @property
    def cors_origins(self) -> List[str]:
        if isinstance(self.ALLOWED_ORIGINS, str):
            return [i.strip() for i in self.ALLOWED_ORIGINS.split(",") if i.strip()]
        return self.ALLOWED_ORIGINS

    # PostgreSQL Configuration
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_HOST: Optional[str] = None
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "socialpilot_db"
    DATABASE_URL: Optional[str] = None
    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    # MongoDB Configuration
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "socialpilot_mongo"

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: Optional[str] = None

    @model_validator(mode="after")
    def assemble_connections(self) -> "Settings":
        # Support Render/Heroku standard DATABASE_URL
        if not self.SQLALCHEMY_DATABASE_URI and self.DATABASE_URL:
            self.SQLALCHEMY_DATABASE_URI = self.DATABASE_URL

        # Normalize postgres:// scheme to postgresql:// for SQLAlchemy 2.0
        if self.SQLALCHEMY_DATABASE_URI and self.SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
            self.SQLALCHEMY_DATABASE_URI = self.SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)

        # Assemble PostgreSQL URI if not explicitly set
        server = self.POSTGRES_HOST or self.POSTGRES_SERVER
        if not self.SQLALCHEMY_DATABASE_URI:
            self.SQLALCHEMY_DATABASE_URI = f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{server}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

        # Assemble Redis URI if not explicitly set
        if not self.REDIS_URL:
            self.REDIS_URL = f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

        return self

    # Email Configuration
    EMAIL_PROVIDER: str = "console"
    EMAIL_FROM: str = "noreply@socialpilot.test"
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True
    FRONTEND_URL: str = "http://localhost:5173"
    RESEND_API_KEY: Optional[str] = None

    # OAuth Provider Configurations
    META_CLIENT_ID: Optional[str] = None
    META_CLIENT_SECRET: Optional[str] = None
    META_REDIRECT_URI: str = "http://127.0.0.1:8000/api/v1/oauth/facebook/callback"
    INSTAGRAM_REDIRECT_URI: str = "http://127.0.0.1:8000/api/v1/oauth/instagram/callback"

    LINKEDIN_CLIENT_ID: Optional[str] = None
    LINKEDIN_CLIENT_SECRET: Optional[str] = None
    LINKEDIN_REDIRECT_URI: str = "http://127.0.0.1:8000/api/v1/oauth/linkedin/callback"

    # Google Cloud Project Reference
    GOOGLE_CLOUD_PROJECT_ID: str = "socialpilot-507506"

    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://127.0.0.1:8000/api/v1/oauth/youtube/callback"

    X_CLIENT_ID: Optional[str] = None
    X_CLIENT_SECRET: Optional[str] = None
    X_REDIRECT_URI: str = "http://127.0.0.1:8000/api/v1/oauth/x/callback"

    PINTEREST_CLIENT_ID: Optional[str] = None
    PINTEREST_CLIENT_SECRET: Optional[str] = None
    PINTEREST_REDIRECT_URI: str = "http://127.0.0.1:8000/api/v1/oauth/pinterest/callback"

    # Security Configuration
    SECRET_KEY: str = "default-insecure-secret-key-please-change-in-env"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Media Storage Configuration
    MEDIA_STORAGE_BACKEND: str = "local"
    MEDIA_UPLOAD_DIR: str = "uploads/media"
    MEDIA_MAX_IMAGE_SIZE: int = 10 * 1024 * 1024  # 10 MB
    MEDIA_MAX_VIDEO_SIZE: int = 100 * 1024 * 1024  # 100 MB
    MEDIA_ALLOWED_MIME_TYPES: List[str] = [
        "image/jpeg",
        "image/png",
        "image/webp",
        "video/mp4",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
