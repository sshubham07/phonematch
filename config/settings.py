"""Application settings, read from environment variables and `.env`."""

from functools import lru_cache

from pydantic import HttpUrl, PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: PostgresDsn
    test_database_url: PostgresDsn

    ollama_base_url: HttpUrl
    llm_model_main: str
    llm_model_intent: str
    llm_num_ctx_main: int = 8192
    llm_num_ctx_intent: int = 4096

    embedding_model: str
    embedding_dim: int = 384

    flipkart_affiliate_id: SecretStr | None = None
    flipkart_affiliate_token: SecretStr | None = None

    youtube_sleep_seconds: float = 4
    youtube_max_transcripts_per_run: int = 300
    gsmarena_sleep_seconds: float = 5

    health_check_timeout_s: float = 2
    log_level: str = "INFO"
    result_cache_ttl_hours: int = 24

    @field_validator("flipkart_affiliate_id", "flipkart_affiliate_token", mode="before")
    @classmethod
    def _empty_to_none(cls, value: object) -> object:
        return None if value == "" else value


@lru_cache
def get_settings() -> Settings:
    return Settings()
