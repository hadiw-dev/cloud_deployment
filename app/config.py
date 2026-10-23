from functools import lru_cache

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    database_url: SecretStr
    log_level: str = "INFO"

    @field_validator("log_level")
    @classmethod
    def require_known_log_level(cls, value: str) -> str:
        import logging

        normalized = value.upper()
        if not isinstance(logging.getLevelName(normalized), int):
            raise ValueError("LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR, or CRITICAL")
        return normalized

    @field_validator("database_url")
    @classmethod
    def require_postgresql(cls, value: SecretStr) -> SecretStr:
        try:
            url = make_url(value.get_secret_value())
            if url.drivername != "postgresql+psycopg" or not url.database:
                raise ValueError
        except Exception:
            raise ValueError(
                "DATABASE_URL must be a postgresql+psycopg URL with a database"
            ) from None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
