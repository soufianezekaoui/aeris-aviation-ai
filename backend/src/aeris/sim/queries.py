from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from aeris.db.models import (
    ChecklistEvent,
    ChecklistItem,
    SimAlert,
    SimSession,
    StateSnapshot,
)
from aeris.sim.checklists import SEMANTICS, STATUSES, TEMPLATES
from aeris.sim.errors import InvalidStatusError, ItemNotFoundError
from aeris.sim.schemas import (
    AlertOut,
    ChecklistItemOut,
    ChecklistOut,
    ChecklistsResponse,
    Progress,
    StateResponse,
    StateValues,
    TimelinePoint,
    TimelineResponse,
)

TITLES = {t.key: t.title for t in TEMPLATES}


def sim_time(sim: SimSession, t: int) -> datetime:
    return sim.sim_start + timedelta(seconds=t)


def is_active(alert: SimAlert, t: int) -> bool:
    return alert.t_start <= t and (alert.t_end is None or t < alert.t_end)


def alert_out(sim: SimSession, a: SimAlert, at_t: int) -> AlertOut:
    return AlertOut(
        id=a.id, code=a.code, level=a.level, message=a.message, t_start=a.t_start, t_end=a.t_end,
        start_time=sim_time(sim, a.t_start),
        end_time=sim_time(sim, a.t_end) if a.t_end is not None else None,
        active=is_active(a, at_t),
    )


def session_alerts(db: Session, sim_id: str) -> list[SimAlert]:
    return list(db.scalars(
        select(SimAlert)
        .where(SimAlert.session_id == sim_id)
        .order_by(SimAlert.t_start, SimAlert.id)
    ))


def items_for(db: Session, sim_id: str) -> list[ChecklistItem]:
    return list(db.scalars(
        select(ChecklistItem).where(ChecklistItem.session_id == sim_id)
        .order_by(ChecklistItem.checklist_key, ChecklistItem.position)
    ))


def progress_of(items: list[ChecklistItem]) -> Progress:
    c = Counter(i.status for i in items)
    return Progress(reviewed=c["reviewed"], needs_attention=c["needs_attention"], total=len(items))


def state_at(db: Session, sim: SimSession, t: int | None) -> StateResponse:
    """The latest snapshot at or before ``t`` (or the final one when ``t`` is None), with an
    explicit statement of how fresh it is (RULE-05)."""
    query = select(StateSnapshot).where(StateSnapshot.session_id == sim.id)
    if t is not None:
        query = query.where(StateSnapshot.t_seconds <= t)
    snap = db.scalars(query.order_by(StateSnapshot.t_seconds.desc()).limit(1)).first()
    base = dict(session_id=sim.id, scenario_id=sim.scenario_id, requested_t=t,
                generated_at=datetime.now(UTC))
    if snap is None:
        return StateResponse(
            **base, freshness="absent", t_seconds=None, snapshot_time=None, age_s=None,
            state=None, active_alerts=[],
            warnings=["No state snapshot exists for this session at the requested time."],
        )

    warnings: list[str] = []
    age = 0 if t is None else t - snap.t_seconds
    if t is None:
        freshness = "latest"
    elif t > sim.duration_s:
        freshness = "stale"
        warnings.append(
            f"Requested t={t}s is past the end of the simulation ({sim.duration_s}s). Showing "
            "the final snapshot, which is not a current state."
        )
    elif age == 0:
        freshness = "exact"
    else:
        freshness = "held"
        warnings.append(
            f"No sample at t={t}s; showing the sample from t={snap.t_seconds}s ({age}s earlier)."
        )

    active = [alert_out(sim, a, snap.t_seconds) for a in session_alerts(db, sim.id)
              if is_active(a, snap.t_seconds)]
    return StateResponse(
        **base, freshness=freshness, t_seconds=snap.t_seconds,
        snapshot_time=sim_time(sim, snap.t_seconds), age_s=age,
        state=StateValues(
            phase=snap.phase, altitude_ft=snap.altitude_ft, airspeed_kt=snap.airspeed_kt,
            vertical_speed_fpm=snap.vertical_speed_fpm, heading_deg=snap.heading_deg,
            flap_deg=snap.flap_deg, gear_down=snap.gear_down, n1_pct=snap.n1_pct,
            fuel_kg=snap.fuel_kg,
        ),
        active_alerts=active, warnings=warnings,
    )


def timeline(db: Session, sim: SimSession, step_s: int) -> TimelineResponse:
    """Downsampled series for charting. The step is rounded up to a multiple of the sampling
    interval and the final snapshot is always included."""
    step = max(sim.sample_interval_s, -(-step_s // sim.sample_interval_s) * sim.sample_interval_s)
    rows = db.scalars(
        select(StateSnapshot).where(StateSnapshot.session_id == sim.id)
        .order_by(StateSnapshot.t_seconds)
    ).all()
    keep = [r for i, r in enumerate(rows) if r.t_seconds % step == 0 or i == len(rows) - 1]
    return TimelineResponse(
        session_id=sim.id, scenario_id=sim.scenario_id, duration_s=sim.duration_s, step_s=step,
        sim_start=sim.sim_start,
        points=[TimelinePoint(t=r.t_seconds, phase=r.phase, altitude_ft=r.altitude_ft,
                              airspeed_kt=r.airspeed_kt, vertical_speed_fpm=r.vertical_speed_fpm)
                for r in keep],
        alerts=[alert_out(sim, a, sim.duration_s) for a in session_alerts(db, sim.id)],
    )


def item_out(i: ChecklistItem) -> ChecklistItemOut:
    return ChecklistItemOut(id=i.id, position=i.position, text=i.text, status=i.status,
                            note=i.note, updated_at=i.updated_at)


def checklists(db: Session, sim: SimSession) -> ChecklistsResponse:
    items = items_for(db, sim.id)
    grouped: dict[str, list[ChecklistItem]] = {}
    for i in items:
        grouped.setdefault(i.checklist_key, []).append(i)
    order = [t.key for t in TEMPLATES if t.key in grouped]
    return ChecklistsResponse(
        session_id=sim.id, semantics=SEMANTICS, progress=progress_of(items),
        checklists=[ChecklistOut(key=k, title=TITLES.get(k, k),
                                 items=[item_out(i) for i in grouped[k]],
                                 progress=progress_of(grouped[k])) for k in order],
    )


def update_item(
    db: Session, sim: SimSession, item_id: int, status: str, note: str | None
) -> tuple[ChecklistItem, Progress]:
    """Record a review status. The lookup is scoped to this session, so an item that belongs
    to another session is indistinguishable from one that does not exist (RULE-06)."""
    if status not in STATUSES:
        raise InvalidStatusError(f"status must be one of {STATUSES}")
    item = db.scalars(
        select(ChecklistItem).where(ChecklistItem.id == item_id,
                                    ChecklistItem.session_id == sim.id)
    ).first()
    if item is None:
        raise ItemNotFoundError(f"no checklist item {item_id} in this session")
    now = datetime.now(UTC)
    changed = False
    if item.status != status:
        db.add(ChecklistEvent(session_id=sim.id, item_id=item.id, from_status=item.status,
                              to_status=status, at=now))
        item.status = status
        changed = True
    if item.note != note:
        item.note = note
        changed = True
    if changed:
        item.updated_at = now
    db.commit()
    return item, progress_of(items_for(db, sim.id))
