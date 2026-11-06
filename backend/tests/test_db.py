from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError, StatementError

from aeris.config import Settings
from aeris.db.errors import DatabaseUnavailableError
from aeris.db.models import (
    ChecklistEvent,
    ChecklistItem,
    SimAlert,
    SimSession,
    StateSnapshot,
)
from aeris.db.session import init_db, make_engine, normalize_url, redact

START = datetime(2030, 1, 1, 8, 0, tzinfo=UTC)


def new_session(**kw) -> SimSession:
    base = dict(scenario_id="demo", name="Demo", seed=1, sample_interval_s=5, duration_s=60,
                sim_start=START)
    return SimSession(**{**base, **kw})


def snap(sid, t, **kw) -> StateSnapshot:
    base = dict(session_id=sid, t_seconds=t, phase="CRUISE", altitude_ft=30000.0,
                airspeed_kt=280.0, vertical_speed_fpm=0.0, heading_deg=90.0, flap_deg=0,
                gear_down=False, n1_pct=80.0, fuel_kg=5000.0)
    return StateSnapshot(**{**base, **kw})


def populate(db, **kw) -> SimSession:
    s = new_session(**kw)
    db.add(s)
    db.flush()
    db.add_all([snap(s.id, 0), snap(s.id, 5)])
    db.add(SimAlert(session_id=s.id, code="X", level="caution", message="m", t_start=0))
    item = ChecklistItem(session_id=s.id, checklist_key="k", position=0, text="Review something")
    db.add(item)
    db.flush()
    db.add(ChecklistEvent(session_id=s.id, item_id=item.id,
                          from_status="not_reviewed", to_status="reviewed"))
    db.commit()
    return s


def count(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def test_roundtrip_and_timestamps_are_timezone_aware_utc(db):
    s = populate(db)
    db.expire_all()
    loaded = db.get(SimSession, s.id)
    assert loaded.sim_start == START and loaded.sim_start.tzinfo is not None
    assert loaded.created_at.utcoffset() == timedelta(0)
    assert count(db, StateSnapshot) == 2 and count(db, ChecklistItem) == 1


def test_non_utc_input_is_normalised_and_naive_is_rejected(db):
    plus2 = timezone(timedelta(hours=2))
    s = new_session(sim_start=datetime(2030, 1, 1, 10, 0, tzinfo=plus2))
    db.add(s)
    db.commit()
    db.expire_all()
    assert db.get(SimSession, s.id).sim_start == START  # 10:00+02:00 == 08:00Z
    db.add(new_session(sim_start=datetime(2030, 1, 1, 8, 0)))  # naive
    with pytest.raises((ValueError, StatementError)):
        db.commit()


def test_one_snapshot_per_session_and_time(db):
    s = populate(db)
    db.add(snap(s.id, 5))
    with pytest.raises(IntegrityError):
        db.commit()


def test_foreign_keys_are_enforced(db):
    db.add(snap("no-such-session", 0))
    with pytest.raises(IntegrityError):
        db.commit()


def test_db_level_cascade_removes_every_child_row(db):
    keep = populate(db, name="keep")
    gone = populate(db, name="gone")
    db.execute(delete(SimSession).where(SimSession.id == gone.id))  # Core delete, no ORM help
    db.commit()
    for model in (StateSnapshot, SimAlert, ChecklistItem, ChecklistEvent):
        rows = db.scalars(select(model)).all()
        assert rows and all(r.session_id == keep.id for r in rows), model.__name__
    assert count(db, SimSession) == 1


def test_orm_delete_also_cascades(db):
    s = populate(db)
    db.delete(s)
    db.commit()
    assert count(db, StateSnapshot) == count(db, ChecklistEvent) == 0


# =========== Config / session helpers
def test_url_normalisation_and_redaction():
    assert normalize_url("postgresql://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert normalize_url("postgres://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert normalize_url("sqlite:///x.db") == "sqlite:///x.db"
    shown = redact("postgresql://aeris:topsecret@db.example/aeris")
    assert "topsecret" not in shown and "aeris@db.example" in shown.replace(":***", "")


def test_blank_database_url_means_local_sqlite_file():
    s = Settings(_env_file=None, database_url="")
    assert s.resolved_database_url.startswith("sqlite:///")
    assert s.resolved_database_url.endswith("backend/data/aeris.db")
    assert Settings(_env_file=None, database_url="sqlite:///x.db").resolved_database_url == (
        "sqlite:///x.db"
    )


def test_unreachable_postgres_gives_safe_actionable_error():
    pytest.importorskip("psycopg")
    engine = make_engine("postgresql://aeris:topsecret@127.0.0.1:1/aeris")
    with pytest.raises(DatabaseUnavailableError) as exc:
        init_db(engine)
    assert "topsecret" not in str(exc.value)
    assert "DATABASE_URL" in str(exc.value)


def test_init_db_is_idempotent(engine):
    init_db(engine)
    init_db(engine)  # must not raise or recreate
