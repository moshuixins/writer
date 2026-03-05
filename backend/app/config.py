from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import model_validator
from functools import lru_cache

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"

    # Database
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'writer.db'}"

    # OpenViking
    openviking_server_url: str = "http://127.0.0.1:1933"
    openviking_config_file: str = str(PROJECT_ROOT / "data" / "openviking" / "ov.conf")
    openviking_root_api_key: str = "ov-writer-secret-key-change-me"
    openviking_shared_backend_dir: str = str(PROJECT_ROOT / "data" / "openviking" / "workspace" / "_staging")
    openviking_shared_ov_dir: str = "/app/data/_staging"

    # File paths
    upload_dir: str = str(PROJECT_ROOT / "data" / "uploads")
    export_dir: str = str(PROJECT_ROOT / "data" / "exports")
    books_dir: str = str(PROJECT_ROOT / "data" / "book")

    # Book learning
    book_augmentation_enabled: bool = True
    book_chunk_size: int = 800
    book_chunk_overlap: int = 120
    book_retrieval_top_k: int = 4
    book_style_top_k: int = 6

    # PDF OCR
    pdf_ocr_enabled: bool = True
    pdf_ocr_lang: str = "chi_sim+eng"
    pdf_ocr_dpi: int = 300
    pdf_ocr_max_pages: int = 500

    # CORS
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:9000,http://127.0.0.1:9000"

    # Rate limiting
    rate_limit_per_minute: int = 60

    # Auth
    secret_key: str = "change-this-to-a-random-secret-key"
    access_token_expire_minutes: int = 1440  # 24 hours

    # Initial admin bootstrap
    initial_admin_username: str = ""
    initial_admin_password: str = ""
    initial_admin_display_name: str = "admin"
    initial_admin_department: str = "admin"

    model_config = {
        "env_file": str(PROJECT_ROOT / ".env"),
        "extra": "ignore",
    }

    @model_validator(mode="after")
    def _validate_security_settings(self):
        insecure_secret = self.secret_key.strip() in {"", "change-this-to-a-random-secret-key"}
        insecure_ov_key = self.openviking_root_api_key.strip() in {"", "ov-writer-secret-key-change-me"}
        if insecure_secret:
            raise ValueError("SECRET_KEY must be overridden in .env for production safety")
        if insecure_ov_key:
            raise ValueError("OPENVIKING_ROOT_API_KEY must be overridden in .env for production safety")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
