# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    anthropic_api_key: str

    claude_model_sonnet: str = "claude-sonnet-5"
    claude_model_haiku: str = "claude-haiku-4-5-20251001"

    claude_max_tokens: int = 4096
    claude_timeout: int = 60
    claude_max_retries: int = 2

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
