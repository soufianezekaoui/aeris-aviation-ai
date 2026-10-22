from __future__ import annotations

from functools import lru_cache

from aeris.config import get_settings
from aeris.rag.embeddings import build_embeddings
from aeris.rag.llm import build_chat_model
from aeris.rag.service import RagService
from aeris.rag.store import open_store


@lru_cache
def get_rag_service() -> RagService:
    """Built lazily on first request; tests replace it with dependency_overrides."""
    settings = get_settings()
    store = open_store(settings, build_embeddings(settings))
    return RagService(store, build_chat_model(settings), settings)
