from __future__ import annotations

import logging
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from aeris.config import Settings, get_settings
from aeris.db.errors import DatabaseUnavailableError
from aeris.db.models import Base

log = logging.getLogger(__name__)
_init_lock = threading.Lock()
_initialised: set[str] = set()


def normalize_url(url: str) -> str:
    for plain in ("postgresql://", "postgres://"):
        if url.startswith(plain):
            return "postgresql+psycopg://" + url[len(plain) :]
    return url


def redact(url: str) -> str:
    return make_url(normalize_url(url)).render_as_string(hide_password=True)


def make_engine(url: str) -> Engine:
    url = normalize_url(url)
    if url.startswith("sqlite"):
        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool  # one shared connection for in-memory DBs
        else:
            path = make_url(url).database
            if path:
                from pathlib import Path

                Path(path).parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(url, **kwargs)

        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _):  # SQLite ignores foreign keys unless asked
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

        return engine
    return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})


@lru_cache
def _engine_for(url: str) -> Engine:
    return make_engine(url)


def get_engine(settings: Settings | None = None) -> Engine:
    return _engine_for((settings or get_settings()).resolved_database_url)


def init_db(engine: Engine) -> None:
    key = str(engine.url)
    if key in _initialised:
        return
    with _init_lock:
        if key in _initialised:
            return
        try:
            Base.metadata.create_all(engine)
        except ImportError as exc:
            raise DatabaseUnavailableError(
            ) from exc
        except OperationalError as exc:
            log.error("database connection failed: %s", exc.__class__.__name__)
            raise DatabaseUnavailableError(
                f"Cannot connect to the database ({redact(key)}). Check DATABASE_URL, or leave "
                "it blank to use the built-in SQLite file."
            ) from exc
        _initialised.add(key)


def reset_caches() -> None:
    _engine_for.cache_clear()
    _initialised.clear()


def get_db() -> Iterator[Session]:
    engine = get_engine()
    init_db(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as session:
        try:
            yield session
        except OperationalError as exc:
            session.rollback()
            raise DatabaseUnavailableError("The database became unavailable.") from exc


@contextmanager
def session_scope(settings: Settings | None = None) -> Iterator[Session]:
    engine = get_engine(settings)
    init_db(engine)
    with sessionmaker(engine, expire_on_commit=False)() as session:
        yield session

