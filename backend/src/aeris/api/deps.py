from __future__ import annotations

import threading

from aeris.config import get_settings
from aeris.rag.embeddings import build_embeddings
from aeris.rag.llm import build_chat_model
from aeris.rag.service import RagService
from aeris.rag.store import open_store

_lock = threading.Lock()
_service: RagService | None = None


def get_rag_service() -> RagService:
    """Built lazily on first request and then shared; tests replace it via dependency_overrides."""
    
    global _service
    if _service is None:
        with _lock:
            if _service is None:
                settings = get_settings()
                store = open_store(settings, build_embeddings(settings))
                _service = RagService(store, build_chat_model(settings), settings)
    return _service


def reset_rag_service() -> None:
    """For tests: forget the shared service."""
    global _service
    with _lock:
        _service = None
