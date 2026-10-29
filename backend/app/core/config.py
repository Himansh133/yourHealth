from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://yourhealth:yourhealth@localhost:5432/yourhealth"
    jwt_secret: str = Field(default="dev-only-insecure-secret-change-me-0000", min_length=32)  # HS256 needs >= 32 bytes
    session_days: int = 7
    # Secure cookies need HTTPS; set COOKIE_SECURE=false only for local http dev/tests.
    cookie_secure: bool = True

    s3_endpoint: str = "http://localhost:8333"
    s3_access_key: str = "yourhealth"
    s3_secret_key: str = "yourhealth-dev-secret"
    s3_bucket: str = "yourhealth-docs"

    redis_url: str = "redis://localhost:6379/0"

    # Any OpenAI-compatible chat API; default is GMI Cloud.
    llm_base_url: str = "https://api.gmi-serving.com/v1"
    llm_api_key: str = ""
    llm_model: str = ""

    refdata_dir: Path = Path(__file__).resolve().parents[3] / "refdata" / "seed"


settings = Settings()
