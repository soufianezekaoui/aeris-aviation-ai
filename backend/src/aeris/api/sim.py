from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aeris.config import Settings, get_settings
from aeris.db.models import SimSession, StateSnapshot
from aeris.db.session import get_db
from aeris.schemas import ErrorResponse
from aeris.sim import queries
from aeris.sim.checklists import SEMANTICS
from aeris.sim.scenarios import AIRCRAFT_LABEL, SCENARIOS
from aeris.sim.schemas import (
    AlertsResponse,
    ChecklistsResponse,
    CreateSessionRequest,
    ScenarioOut,
    ScenariosResponse,
    SessionOut,
    SessionsResponse,
    StateResponse,
    TimelineResponse,
    UpdateItemRequest,
    UpdateItemResponse,
)
from aeris.sim.service import create_session, delete_session, get_session, list_sessions

router = APIRouter(prefix="/api/sim", tags=["simulation"])
_ERR = {404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}}


def _session_out(db: Session, sim: SimSession) -> SessionOut:
    items = queries.items_for(db, sim.id)
    n_snaps = db.scalar(select(func.count()).select_from(StateSnapshot)
                        .where(StateSnapshot.session_id == sim.id))
    return SessionOut(
        session_id=sim.id, scenario_id=sim.scenario_id, name=sim.name, seed=sim.seed,
        duration_s=sim.duration_s, sample_interval_s=sim.sample_interval_s,
        sim_start=sim.sim_start, created_at=sim.created_at, snapshots=n_snaps or 0,
        alert_count=len(queries.session_alerts(db, sim.id)),
        checklist_progress=queries.progress_of(items),
    )


@router.get("/scenarios", response_model=ScenariosResponse, responses=_ERR,
            summary="Built-in synthetic scenarios")
def scenarios() -> ScenariosResponse:
    return ScenariosResponse(scenarios=[
        ScenarioOut(id=s.id, name=s.name, description=s.description,
                    learning_goal=s.learning_goal, duration_s=s.duration_s, aircraft=AIRCRAFT_LABEL)
        for s in SCENARIOS.values()
    ])


@router.post("/sessions", response_model=SessionOut, status_code=201, responses=_ERR,
             summary="Create a synthetic simulation session")
def create(body: CreateSessionRequest, db: Session = Depends(get_db),
           settings: Settings = Depends(get_settings)) -> SessionOut:
    sim = create_session(db, body.scenario_id, seed=body.seed, name=body.name, settings=settings)
    return _session_out(db, sim)


@router.get("/sessions", response_model=SessionsResponse, responses=_ERR,
            summary="List simulation sessions, newest first")
def sessions(db: Session = Depends(get_db)) -> SessionsResponse:
    return SessionsResponse(sessions=[_session_out(db, s) for s in list_sessions(db)])


@router.get("/sessions/{session_id}", response_model=SessionOut, responses=_ERR)
def session_detail(session_id: str, db: Session = Depends(get_db)) -> SessionOut:
    return _session_out(db, get_session(db, session_id))


@router.delete("/sessions/{session_id}", status_code=204, responses=_ERR,
               summary="Delete a session and everything that belongs to it")
def remove(session_id: str, db: Session = Depends(get_db)) -> Response:
    delete_session(db, session_id)
    return Response(status_code=204)


@router.get("/sessions/{session_id}/state", response_model=StateResponse, responses=_ERR,
            summary="Simulated flight state (latest, or as of simulated time t)")
def state(session_id: str, t: int | None = Query(default=None, ge=0, le=10**7),
          db: Session = Depends(get_db)) -> StateResponse:
    return queries.state_at(db, get_session(db, session_id), t)


@router.get("/sessions/{session_id}/timeline", response_model=TimelineResponse, responses=_ERR,
            summary="Downsampled series for charts, with alert intervals")
def timeline(session_id: str, step: int = Query(default=30, ge=5, le=600),
             db: Session = Depends(get_db)) -> TimelineResponse:
    return queries.timeline(db, get_session(db, session_id), step)


@router.get("/sessions/{session_id}/alerts", response_model=AlertsResponse, responses=_ERR,
            summary="Alerts raised up to simulated time t (default: end of the scenario)")
def alerts(session_id: str, t: int | None = Query(default=None, ge=0, le=10**7),
           db: Session = Depends(get_db)) -> AlertsResponse:
    sim = get_session(db, session_id)
    as_of = sim.duration_s if t is None else min(t, sim.duration_s)
    raised = [a for a in queries.session_alerts(db, sim.id) if a.t_start <= as_of]
    return AlertsResponse(session_id=sim.id, as_of_t=as_of,
                          alerts=[queries.alert_out(sim, a, as_of) for a in raised])


@router.get("/sessions/{session_id}/checklists", response_model=ChecklistsResponse,
            responses=_ERR, summary="Checklist review progress for one session")
def checklists(session_id: str, db: Session = Depends(get_db)) -> ChecklistsResponse:
    return queries.checklists(db, get_session(db, session_id))


@router.patch("/sessions/{session_id}/checklists/items/{item_id}",
              response_model=UpdateItemResponse, responses=_ERR,
              summary="Record a review status (application state only, not a real-world action)")
def update_checklist_item(session_id: str, item_id: int, body: UpdateItemRequest,
                          db: Session = Depends(get_db)) -> UpdateItemResponse:
    sim = get_session(db, session_id)
    item, progress = queries.update_item(db, sim, item_id, body.status, body.note)
    return UpdateItemResponse(session_id=sim.id, semantics=SEMANTICS,
                              item=queries.item_out(item), progress=progress)
