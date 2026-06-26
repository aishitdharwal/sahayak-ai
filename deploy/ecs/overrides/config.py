"""
ECS config — adds Redis and Postgres connection strings.

Diff from EC2 config.py:
  + REDIS_URL         (ElastiCache endpoint)
  + POSTGRES_URL      (RDS endpoint — for both app DB and LangGraph checkpoints)
  - DATABASE_URL      (SQLite gone)
  - GRAPH_CHECKPOINT_DB (SQLite gone)

Everything else is identical.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str

    intent_model: str = "claude-haiku-4-5-20251001"
    reasoning_model: str = "claude-sonnet-4-6"

    # ECS: SQLite replaced by RDS Postgres.
    # One connection string handles both app data and LangGraph checkpoints.
    # Format: postgresql+asyncpg://user:password@rds-endpoint:5432/sahayak
    postgres_url: str

    # ECS: ChromaDB persists to an EFS volume mounted at this path.
    # The ECS task definition mounts the EFS access point here.
    chroma_persist_dir: str = "/mnt/efs/chroma_db"

    # ECS: Redis for WebSocket pub/sub across multiple Fargate tasks.
    # Format: redis://elasticache-endpoint:6379
    redis_url: str

    environment: str = "production"
    frontend_url: str  # CloudFront distribution URL, e.g. https://d1234.cloudfront.net

    langfuse_secret_key: str = ""
    langfuse_public_key: str = ""
    langfuse_base_url: str = "https://cloud.langfuse.com"

    @property
    def langfuse_enabled(self) -> bool:
        return bool(self.langfuse_secret_key and self.langfuse_public_key)


settings = Settings()
