from __future__ import annotations


class DatabaseUnavailableError(RuntimeError):
    """The database cannot be reached or is misconfigured. The message never contains secrets."""
