from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and environment configurations."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # General Project Info
    PROJECT_NAME: str = "AI Surveillance System - Border/Night Monitoring"
    API_V1_STR: str = "/api/v1"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = True

    # Storage Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "data" / "uploads"

    # Input Constraints
    MAX_UPLOAD_SIZE_BYTES: int = 500 * 1024 * 1024  # 500 MB
    ALLOWED_EXTENSIONS: List[str] = [".mp4", ".avi", ".mov", ".mkv"]
    ALLOWED_MIME_TYPES: List[str] = [
        "video/mp4",
        "video/x-msvideo",
        "video/quicktime",
        "video/x-matroska",
        "video/mkv",
        "application/octet-stream",  # Fallback for some clients
    ]

    def ensure_directories(self) -> None:
        """Ensure necessary runtime directories exist."""
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
