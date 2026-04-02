"""Configuration settings for the AgentOps Demo Backend.

100% local — all services run on localhost / Docker network.
No cloud API keys required.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- API ---
    api_title: str = "AgentOps Demo API"
    api_version: str = "0.2.0"

    # --- CORS ---
    cors_origins: list[str] = [
        "http://localhost:3501",
        "http://127.0.0.1:3501",
        "http://localhost:4000",
        "http://frontend:4000",
    ]

    # --- LLM (Local Ollama) ---
    llm_base_url: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:14b"
    llm_temperature: float = 0.7
    llm_num_ctx: int = 8192

    # --- Embeddings (Local Ollama) ---
    embedding_model: str = "nomic-embed-text"

    # --- RAG ---
    chroma_persist_dir: str = "./chroma_data"
    docs_dir: str = "./data"
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # --- Orchestrator (Semantic Routing) ---
    relevance_threshold: float = 0.7

    # --- Langfuse (Local Docker instance) ---
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://localhost:3100"
    # Internal URL used by backend container to reach Langfuse
    langfuse_internal_host: str = "http://langfuse:3000"
    # Public URL for trace links returned to the browser
    langfuse_public_url: str = "http://localhost:3100"

    # --- Arize Phoenix (Library mode, runs in-process) ---
    phoenix_enabled: bool = True
    phoenix_port: int = 6006

    # --- Evaluation ---
    faithfulness_eval_enabled: bool = True

    # --- Langfuse Datasets ---
    langfuse_dataset_name: str = "agentops-demo"

    # --- Server ---
    log_level: str = "INFO"
    log_format: str = "text"  # "text" for dev, "json" for production


# Singleton
settings = Settings()
