import pytest
from pydantic import ValidationError

from config.settings import Settings

REQUIRED_ENV = {
    "DATABASE_URL": "postgresql+asyncpg://u:p@localhost:5432/main",
    "TEST_DATABASE_URL": "postgresql+asyncpg://u:p@localhost:5432/main_test",
    "OLLAMA_BASE_URL": "http://localhost:11434",
    "LLM_MODEL_MAIN": "qwen3.5:9b",
    "LLM_MODEL_INTENT": "qwen3.5:9b",
    "EMBEDDING_MODEL": "BAAI/bge-small-en-v1.5",
}


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    return monkeypatch


def test_loads_from_environment(env: pytest.MonkeyPatch) -> None:
    env.setenv("HEALTH_CHECK_TIMEOUT_S", "0.5")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert str(settings.database_url).endswith("/main")
    assert settings.llm_model_main == "qwen3.5:9b"
    assert settings.health_check_timeout_s == 0.5
    assert settings.llm_num_ctx_main == 8192
    assert settings.embedding_dim == 384


def test_missing_database_url_fails_fast(env: pytest.MonkeyPatch) -> None:
    env.delenv("DATABASE_URL")
    with pytest.raises(ValidationError, match="database_url"):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_empty_flipkart_credentials_become_none(env: pytest.MonkeyPatch) -> None:
    env.setenv("FLIPKART_AFFILIATE_ID", "")
    env.setenv("FLIPKART_AFFILIATE_TOKEN", "")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.flipkart_affiliate_id is None
    assert settings.flipkart_affiliate_token is None


def test_flipkart_token_is_not_leaked_in_repr(env: pytest.MonkeyPatch) -> None:
    env.setenv("FLIPKART_AFFILIATE_TOKEN", "super-secret-token")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert "super-secret-token" not in repr(settings)
    assert settings.flipkart_affiliate_token is not None
    assert settings.flipkart_affiliate_token.get_secret_value() == "super-secret-token"
