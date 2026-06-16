from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    inkpersona_env: str = Field(default="development", alias="INKPERSONA_ENV")
    inkpersona_api_host: str = Field(default="127.0.0.1", alias="INKPERSONA_API_HOST")
    inkpersona_api_port: int = Field(default=8000, alias="INKPERSONA_API_PORT")
    inkpersona_allowed_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="INKPERSONA_ALLOWED_ORIGINS",
    )
    inkpersona_max_upload_mb: int = Field(default=12, alias="INKPERSONA_MAX_UPLOAD_MB")
    inkpersona_request_timeout_seconds: int = Field(default=90, alias="INKPERSONA_REQUEST_TIMEOUT_SECONDS")
    inkpersona_log_level: str = Field(default="info", alias="INKPERSONA_LOG_LEVEL")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_temperature: float = Field(default=0.2, alias="OPENAI_TEMPERATURE")
    openai_max_output_tokens: int = Field(default=3500, alias="OPENAI_MAX_OUTPUT_TOKENS")

    inkpersona_storage_dir: str = Field(default="./storage", alias="INKPERSONA_STORAGE_DIR")
    inkpersona_report_retention_days: int = Field(default=0, alias="INKPERSONA_REPORT_RETENTION_DAYS")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.inkpersona_allowed_origins.split(",") if origin.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.inkpersona_max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
