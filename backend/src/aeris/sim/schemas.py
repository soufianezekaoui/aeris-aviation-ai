from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from aeris import SAFETY_DISCLAIMER

DATA_SOURCE = "synthetic simulation (not live telemetry)"


class Labelled(BaseModel):
    synthetic: Literal[True] = True
    data_source: str = DATA_SOURCE
    disclaimer: str = SAFETY_DISCLAIMER


class ScenarioOut(BaseModel):
    id: str
    name: str
    description: str
    learning_goal: str
    duration_s: int
    aircraft: str


class ScenariosResponse(Labelled):
    scenarios: list[ScenarioOut]


class CreateSessionRequest(BaseModel):
    scenario_id: str = Field(min_length=1, max_length=64)
    seed: int | None = Field(default=None, ge=0, le=2**31 - 1)
    name: str | None = Field(default=None, max_length=120)

    @field_validator("name")
    @classmethod
    def _blank_is_none(cls, v: str | None) -> str | None:
        return (v.strip() or None) if v else None


class Progress(BaseModel):
    reviewed: int
    needs_attention: int
    total: int


class SessionOut(Labelled):
    session_id: str
    scenario_id: str
    name: str
    seed: int
    duration_s: int
    sample_interval_s: int
    sim_start: datetime = Field(description="Start of the FICTIONAL simulated clock (UTC).")
    created_at: datetime = Field(description="When this session record was created (real UTC).")
    snapshots: int
    alert_count: int
    checklist_progress: Progress


class SessionsResponse(Labelled):
    sessions: list[SessionOut]


class StateValues(BaseModel):
    phase: str
    altitude_ft: float
    airspeed_kt: float
    vertical_speed_fpm: float
    heading_deg: float
    flap_deg: int
    gear_down: bool
    n1_pct: float
    fuel_kg: float


class AlertOut(BaseModel):
    id: int
    code: str
    level: Literal["caution", "warning", "critical"]
    message: str
    t_start: int
    t_end: int | None
    start_time: datetime = Field(description="Simulated UTC time the alert was raised.")
    end_time: datetime | None
    active: bool


Freshness = Literal["latest", "exact", "held", "stale", "absent"]


class StateResponse(Labelled):
    session_id: str
    scenario_id: str
    freshness: Freshness
    requested_t: int | None
    t_seconds: int | None
    snapshot_time: datetime | None = Field(description="Simulated UTC time of the snapshot.")
    age_s: int | None = Field(description="Seconds between the requested time and the snapshot.")
    generated_at: datetime = Field(description="When this response was produced (real UTC).")
    state: StateValues | None
    active_alerts: list[AlertOut]
    warnings: list[str] = []


class TimelinePoint(BaseModel):
    t: int
    phase: str
    altitude_ft: float
    airspeed_kt: float
    vertical_speed_fpm: float


class TimelineResponse(Labelled):
    session_id: str
    scenario_id: str
    duration_s: int
    step_s: int
    sim_start: datetime
    points: list[TimelinePoint]
    alerts: list[AlertOut]


class AlertsResponse(Labelled):
    session_id: str
    as_of_t: int
    alerts: list[AlertOut]


class ChecklistItemOut(BaseModel):
    id: int
    position: int
    text: str
    status: Literal["not_reviewed", "reviewed", "needs_attention"]
    note: str | None
    updated_at: datetime


class ChecklistOut(BaseModel):
    key: str
    title: str
    items: list[ChecklistItemOut]
    progress: Progress


class ChecklistsResponse(Labelled):
    session_id: str
    semantics: str
    checklists: list[ChecklistOut]
    progress: Progress


class UpdateItemRequest(BaseModel):
    status: Literal["not_reviewed", "reviewed", "needs_attention"]
    note: str | None = Field(default=None, max_length=500)

    @field_validator("note")
    @classmethod
    def _strip(cls, v: str | None) -> str | None:
        return (v.strip() or None) if v else None


class UpdateItemResponse(Labelled):
    session_id: str
    semantics: str
    item: ChecklistItemOut
    progress: Progress
