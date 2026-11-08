from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from aeris.config import Settings, get_settings
from aeris.db.models import ChecklistItem, SimAlert, SimSession, StateSnapshot
from aeris.sim.alerts import detect_alerts
from aeris.sim.checklists import NOT_REVIEWED, TEMPLATES
from aeris.sim.errors import SessionLimitError, SessionNotFoundError, UnknownScenarioError
from aeris.sim.generator import generate
from aeris.sim.scenarios import get_scenario

SAMPLE_INTERVAL_S = 5
# Start of the fictional simulated clock. A future date, so it can never pass for real data.
SIM_EPOCH = datetime(2030, 1, 1, 8, 0, tzinfo=UTC)


def create_session(
    db: Session,
    scenario_id: str,
    *,
    seed: int | None = None,
    name: str | None = None,
    settings: Settings | None = None,
) -> SimSession:
    settings = settings or get_settings()
    scenario = get_scenario(scenario_id)
    if scenario is None:
        raise UnknownScenarioError(f"unknown scenario: {scenario_id}")
    if db.scalar(select(func.count()).select_from(SimSession)) >= settings.max_sim_sessions:
        raise SessionLimitError(
            f"Session limit reached ({settings.max_sim_sessions}). Delete a session first."
        )

    seed = scenario.default_seed if seed is None else seed
    snaps = generate(scenario, seed, SAMPLE_INTERVAL_S)
    alerts = detect_alerts(snaps, scenario)

    try:
        sim = SimSession(
            scenario_id=scenario.id, name=name or scenario.name, seed=seed,
            sample_interval_s=SAMPLE_INTERVAL_S, duration_s=scenario.duration_s,
            sim_start=SIM_EPOCH,
        )
        db.add(sim)
        db.flush()
        db.execute(insert(StateSnapshot), [
            {"session_id": sim.id, "t_seconds": s.t_seconds, "phase": s.phase,
             "altitude_ft": s.altitude_ft, "airspeed_kt": s.airspeed_kt,
             "vertical_speed_fpm": s.vertical_speed_fpm, "heading_deg": s.heading_deg,
             "flap_deg": s.flap_deg, "gear_down": s.gear_down, "n1_pct": s.n1_pct,
             "fuel_kg": s.fuel_kg}
            for s in snaps
        ])
        db.add_all(
            SimAlert(session_id=sim.id, code=a.code, level=a.level, message=a.message,
                     t_start=a.t_start, t_end=a.t_end)
            for a in alerts
        )
        now = datetime.now(UTC)
        db.add_all(
            ChecklistItem(session_id=sim.id, checklist_key=tpl.key, position=i, text=text,
                          status=NOT_REVIEWED, updated_at=now)
            for tpl in TEMPLATES
            for i, text in enumerate(tpl.items)
        )
        db.commit()  # one transaction: a session is created completely or not at all
    except Exception:
        db.rollback()
        raise
    return sim


def list_sessions(db: Session) -> list[SimSession]:
    return list(db.scalars(select(SimSession).order_by(SimSession.created_at.desc())))


def get_session(db: Session, session_id: str) -> SimSession:
    sim = db.get(SimSession, session_id)
    if sim is None:
        raise SessionNotFoundError(f"no simulation session with id {session_id!r}")
    return sim


def delete_session(db: Session, session_id: str) -> None:
    get_session(db, session_id)
    db.execute(delete(SimSession).where(SimSession.id == session_id))  # DB-level cascade
    db.commit()
