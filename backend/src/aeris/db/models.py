from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from aeris.db.types import UTCDateTime


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    type_annotation_map = {datetime: UTCDateTime}


class SimSession(Base):
    __tablename__ = "sim_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scenario_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120))
    seed: Mapped[int] = mapped_column(Integer)
    sample_interval_s: Mapped[int] = mapped_column(Integer)
    duration_s: Mapped[int] = mapped_column(Integer)
    # Start of the *fictional* simulated clock; snapshot time = sim_start + t_seconds.
    sim_start: Mapped[datetime]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    snapshots: Mapped[list[StateSnapshot]] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )
    alerts: Mapped[list[SimAlert]] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )
    checklist_items: Mapped[list[ChecklistItem]] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )


class StateSnapshot(Base):
    __tablename__ = "sim_state_snapshots"
    __table_args__ = (UniqueConstraint("session_id", "t_seconds", name="uq_snapshot_session_t"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sim_sessions.id", ondelete="CASCADE"), index=True
    )
    t_seconds: Mapped[int] = mapped_column(Integer)
    phase: Mapped[str] = mapped_column(String(16))
    altitude_ft: Mapped[float] = mapped_column(Float)
    airspeed_kt: Mapped[float] = mapped_column(Float)
    vertical_speed_fpm: Mapped[float] = mapped_column(Float)
    heading_deg: Mapped[float] = mapped_column(Float)
    flap_deg: Mapped[int] = mapped_column(Integer)
    gear_down: Mapped[bool] = mapped_column(Boolean)
    n1_pct: Mapped[float] = mapped_column(Float)
    fuel_kg: Mapped[float] = mapped_column(Float)

    session: Mapped[SimSession] = relationship(back_populates="snapshots")


class SimAlert(Base):

    __tablename__ = "sim_alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sim_sessions.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(32))
    level: Mapped[str] = mapped_column(String(10))  # caution | warning | critical
    message: Mapped[str] = mapped_column(String(200))
    t_start: Mapped[int] = mapped_column(Integer)
    t_end: Mapped[int | None] = mapped_column(Integer, nullable=True)

    session: Mapped[SimSession] = relationship(back_populates="alerts")


class ChecklistItem(Base):

    __tablename__ = "sim_checklist_items"
    __table_args__ = (
        UniqueConstraint("session_id", "checklist_key", "position", name="uq_item_position"),
        Index("ix_item_session_key", "session_id", "checklist_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sim_sessions.id", ondelete="CASCADE"), index=True
    )
    checklist_key: Mapped[str] = mapped_column(String(40))
    position: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), default="not_reviewed")
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow)

    session: Mapped[SimSession] = relationship(back_populates="checklist_items")


class ChecklistEvent(Base):

    __tablename__ = "sim_checklist_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sim_sessions.id", ondelete="CASCADE"), index=True
    )
    item_id: Mapped[int] = mapped_column(
        ForeignKey("sim_checklist_items.id", ondelete="CASCADE"), index=True
    )
    from_status: Mapped[str] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20))
    at: Mapped[datetime] = mapped_column(default=utcnow)
