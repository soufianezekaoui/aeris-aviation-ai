from __future__ import annotations


class SessionNotFoundError(LookupError):
    """No simulation session with that id (RULE-06: also what a foreign id looks like)."""


class ItemNotFoundError(LookupError):
    """No such checklist item inside this session."""


class UnknownScenarioError(ValueError):
    """The scenario id is not one of the built-in scenarios."""


class SessionLimitError(RuntimeError):
    """Too many sessions exist; delete some before creating more."""


class InvalidStatusError(ValueError):
    """Not an allowed checklist review status."""
