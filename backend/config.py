"""
RippleGraph Configuration
Loads environment variables with sensible defaults for local development.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # FalkorDB connection
    falkordb_host: str = "localhost"
    falkordb_port: int = 6379
    falkordb_graph_name: str = "ripplgraph"
    falkordb_password: str | None = None
    falkordb_username: str | None = None

    # App settings
    log_level: str = "info"
    cors_origins: list[str] = ["*"]

    # Gemini LLM
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"


settings = Settings()
