from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://yourhealth:yourhealth@localhost:5432/yourhealth"
    jwt_secret: str = "dev-only-insecure-secret-change-me-0000"  # >= 32 bytes for HS256
    session_days: int = 7
    # Secure cookies need HTTPS; set COOKIE_SECURE=false only for local http dev/tests.
    cookie_secure: bool = True


settings = Settings()
