from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

# 项目根目录：backend 的上一级
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

    # File paths
    upload_dir: str = str(PROJECT_ROOT / "data" / "uploads")
    export_dir: str = str(PROJECT_ROOT / "data" / "exports")

    # CORS
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Rate limiting
    rate_limit_per_minute: int = 60

    # Auth
    secret_key: str = "change-this-to-a-random-secret-key"
    access_token_expire_minutes: int = 1440  # 24 hours

    model_config = {
        "env_file": str(PROJECT_ROOT / ".env"),
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
