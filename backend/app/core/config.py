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

    # Where the frontend is served: share links and their QR codes point here.
    public_base_url: str = "http://localhost:5173"
    share_session_minutes: int = 30

    # Search models (plan 10.5), ONNX files under models_dir. Missing files or disabled: keyword search only.
    embeddings_enabled: bool = True
    models_dir: Path = Path(__file__).resolve().parents[2] / "models"
    embedding_model: str = "bge-m3/onnx/model.onnx"  # 8-bit, less RAM: bge-m3-int8/onnx/model_int8.onnx
    embedding_tokenizer: str = "bge-m3/onnx/tokenizer.json"
    reranker_model: str = "bge-reranker-v2-m3/onnx/model.onnx"  # 8-bit: bge-reranker-v2-m3/onnx/model_int8.onnx
    reranker_tokenizer: str = "bge-reranker-v2-m3/tokenizer.json"

    refdata_dir: Path = Path(__file__).resolve().parents[3] / "refdata" / "seed"


settings = Settings()
