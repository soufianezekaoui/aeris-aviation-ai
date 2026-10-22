from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
    )

    app_env: str = "development"
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        description="Comma-separated list of allowed browser origins.",
    )

    # --------- LLM
    llm_provider: Literal["anthropic", "openai", "none"] = "none"
    llm_model: str = ""
    llm_api_key: SecretStr | None = None
    llm_temperature: float = 0.0
    llm_max_tokens: int = 1024

    # --------- Embeddings
    embedding_provider: Literal["fastembed", "openai", "hash"] = "fastembed"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_api_key: SecretStr | None = None

    # --------- Vector store / documents
    vector_store_dir: Path = BACKEND_DIR / "vector_store"
    collection_name: str = "aeris_documents"
    documents_dir: Path = REPO_ROOT / "knowledge" / "documents"

    # --------- Chunking
    chunk_size: int = Field(default=1000, ge=200)
    chunk_overlap: int = Field(default=150, ge=0)
    min_chunk_chars: int = Field(default=80, ge=1)

    # --------- Retrieval
    retrieval_top_k: int = Field(default=6, ge=1, le=20)
    # Cosine relevance (1 - distance). Calibrate per embedding model with `aeris eval`.
    min_relevance: float = Field(default=0.35, ge=0.0, le=1.0)
    max_question_chars: int = 1000

    # Reserved for Phase 2 (simulation + checklist data in PostgreSQL).
    database_url: str = "postgresql://postgres:postgres@localhost:5432/aeris"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def manifest_path(self) -> Path:
        return self.documents_dir / "manifest.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
