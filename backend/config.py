from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str

    # TRADEOFF: Two models instead of one.
    # Haiku handles Node 1 (intent classification) — it's deterministic structured extraction,
    # doesn't need deep reasoning. Roughly 20x cheaper per token than Sonnet.
    # Sonnet handles Nodes 2 & 3 — policy interpretation and judgment require it.
    # In production, this single routing decision cuts LLM costs by ~60-70%.
    intent_model: str = "claude-haiku-4-5-20251001"
    reasoning_model: str = "claude-sonnet-4-6"

    database_url: str = "sqlite:///./sahayak.db"
    chroma_persist_dir: str = "./chroma_db"
    graph_checkpoint_db: str = "./checkpoints.db"

    environment: str = "development"
    frontend_url: str = "http://localhost:5173"

    # Langfuse observability — set all three to enable tracing
    langfuse_secret_key: str = ""
    langfuse_public_key: str = ""
    langfuse_base_url: str = "https://cloud.langfuse.com"

    @property
    def langfuse_enabled(self) -> bool:
        return bool(self.langfuse_secret_key and self.langfuse_public_key)


settings = Settings()
