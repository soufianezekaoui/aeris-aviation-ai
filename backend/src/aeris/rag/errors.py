from __future__ import annotations


class ConfigError(RuntimeError):
    """Missing or inconsistent configuration (API key, model name, ...)."""


class IndexMismatchError(RuntimeError):
    """The index was built with a different embedding model than the one configured."""


class IndexEmptyError(RuntimeError):
    """Nothing has been ingested yet."""


class RetrievalError(RuntimeError):
    """Embedding or vector-store failure while searching."""


class UnknownDocumentError(ValueError):
    """A requested doc_id is not in the index."""
