# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    anthropic_api_key: str

    claude_model_sonnet: str = "claude-sonnet-5"
    claude_model_haiku: str = "claude-haiku-4-5-20251001"

    claude_max_tokens: int = 4096
    claude_timeout: int = 60
    claude_max_retries: int = 2

    embedding_model_name: str = "dragonkue/multilingual-e5-small-ko-v2"

    chroma_path: str = "./chroma_data"
    chroma_collection_name: str = "policy_sections"
    policy_docs_path: str = "./data/policies"

    chatbot_top_k: int = 2
    chatbot_max_distance: float = 0.5
    chatbot_history_limit: int = 10

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
