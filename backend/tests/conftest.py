from __future__ import annotations

import pytest

from aeris.config import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


import tempfile  # noqa: E402

from sqlalchemy.orm import Session  # noqa: E402

from aeris.db.models import Base  # noqa: E402
from aeris.db.session import make_engine, reset_caches  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_db_caches():
    reset_caches()
    yield
    reset_caches()


@pytest.fixture(scope="session")
def pg_url():
    pgserver = pytest.importorskip("pgserver")
    server = pgserver.get_server(tempfile.mkdtemp(prefix="aeris-pg-"))
    yield server.get_uri()
    server.cleanup()


@pytest.fixture(params=["sqlite", "postgres"])
def db_url(request, tmp_path):
    if request.param == "sqlite":
        return f"sqlite:///{tmp_path / 'test.db'}"
    return request.getfixturevalue("pg_url")


@pytest.fixture
def engine(db_url):
    eng = make_engine(db_url)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def db(engine):
    with Session(engine, expire_on_commit=False) as session:
        yield session
