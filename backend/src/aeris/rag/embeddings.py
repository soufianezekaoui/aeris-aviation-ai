from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

from langchain_core.embeddings import Embeddings

from aeris.config import Settings
from aeris.rag.errors import ConfigError

_STOP = frozenset(
    "a an and are as at be by for from has had have in is it its of on or that the this to was "
    "were what which who why how when where with did does do not".split()
)


class HashingEmbeddings(Embeddings):
    """Offline, deterministic *lexical* embeddings (signed feature hashing, no IDF).

    For tests and smoke checks only: it matches shared words, not meaning.
    """

    def __init__(self, dim: int = 1024) -> None:
        self.dim = dim

    def _embed(self, text: str) -> list[float]:
        tokens = [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOP]
        vec = [0.0] * self.dim
        for token, count in Counter(tokens).items():
            digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
            idx = int.from_bytes(digest[:4], "big") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[idx] += sign * (1.0 + math.log(count))
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


class FastEmbedEmbeddings(Embeddings):
    """Local ONNX embeddings (no PyTorch). The model downloads on first use."""

    def __init__(self, model_name: str) -> None:
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise ConfigError(
                'fastembed is not installed. Run: pip install -e ".[local-embeddings]"'
            ) from exc
        self._model = TextEmbedding(model_name=model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [vec.tolist() for vec in self._model.passage_embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        return next(iter(self._model.query_embed(text))).tolist()


def build_embeddings(settings: Settings) -> Embeddings:
    provider = settings.embedding_provider
    if provider == "hash":
        return HashingEmbeddings()
    if provider == "fastembed":
        return FastEmbedEmbeddings(settings.embedding_model)
    if provider == "openai":
        if settings.embedding_model.startswith("BAAI/"):
            raise ConfigError(
                "EMBEDDING_PROVIDER=openai needs an OpenAI model, e.g. "
                "EMBEDDING_MODEL=text-embedding-3-small"
            )
        key = settings.embedding_api_key or settings.llm_api_key
        if key is None:
            raise ConfigError("EMBEDDING_PROVIDER=openai requires EMBEDDING_API_KEY")
        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError as exc:  # pragma: no cover
            raise ConfigError('Run: pip install -e ".[openai]"') from exc
        return OpenAIEmbeddings(model=settings.embedding_model, api_key=key.get_secret_value())
    raise ConfigError(f"unknown embedding provider: {provider}")  # pragma: no cover


def embedding_fingerprint(settings: Settings) -> str:
    """Identifies the embedding space an index was built in."""
    model = "hashing-1024" if settings.embedding_provider == "hash" else settings.embedding_model
    return f"{settings.embedding_provider}:{model}"
