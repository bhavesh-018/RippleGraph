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

    # App settings
    log_level: str = "info"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


settings = Settings()
