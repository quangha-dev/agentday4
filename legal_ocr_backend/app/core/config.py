from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Legal OCR API"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./data/legal_ocr.db"
    qdrant_url: str | None = None
    qdrant_path: Path = Path("./data/qdrant")
    qdrant_collection: str = "legal_provisions"
    embedding_model: str = "BAAI/bge-m3"
    enable_transformer_embedding: bool = False
    upload_dir: Path = Path("./data/uploads")
    page_image_dir: Path = Path("./data/page_images")
    export_dir: Path = Path("./data/exports")
    tesseract_cmd: str | None = None
    ocr_languages: str = "vie+eng"
    max_upload_mb: int = 100
    frontend_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    llm_cleanup_provider: str = "openrouter"
    llm_cleanup_model: str = "openai/gpt-4o-mini"
    openrouter_api_key: str | None = None
    openai_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("frontend_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    def ensure_directories(self) -> None:
        for path in (self.upload_dir, self.page_image_dir, self.export_dir, self.qdrant_path):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
