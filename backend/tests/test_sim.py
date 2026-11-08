from __future__ import annotations

from dataclasses import replace

import pytest
from sqlalchemy import func, select

from aeris.config import Settings
from aeris.db.models import ChecklistItem, SimAlert, SimSession, StateSnapshot
from aeris.sim.alerts import RULES, detect_alerts
from aeris.sim.checklists import SEMANTICS, STATUSES, TEMPLATES
from aeris.sim.errors import SessionLimitError, SessionNotFoundError, UnknownScenarioError
from aeris.sim.generator import Snap, generate
from aeris.sim.scenarios import PHASES, SCENARIOS
from aeris.sim.service import SIM_EPOCH, create_session, delete_session, get_session

NOMINAL = SCENARIOS["nominal_short_haul"]
CONFIG = SCENARIOS["takeoff_config_discrepancy"]
UNSTABLE = SCENARIOS["unstable_approach"]


def alerts_for(scenario):
    return detect_alerts(generate(scenario, scenario.default_seed), scenario)


# ================ generator
def test_generation_is_deterministic_per_seed():
    a = generate(NOMINAL, 7)
    assert a == generate(NOMINAL, 7)
    assert a != generate(NOMINAL, 8)


def test_series_shape_and_physical_sanity():
    snaps = generate(NOMINAL, 1, 5)
    assert [s.t_seconds for s in snaps] == list(range(0, NOMINAL.duration_s + 1, 5))
    assert snaps[0].altitude_ft == 0 and snaps[-1].altitude_ft == 0
    assert max(s.altitude_ft for s in snaps) == pytest.approx(33000, abs=60)
    assert all(s.phase in PHASES for s in snaps)
    assert all(0 <= s.n1_pct <= 100 and s.airspeed_kt >= 0 for s in snaps)
    fuel = [s.fuel_kg for s in snaps]
    assert fuel == sorted(fuel, reverse=True) and fuel[0] == NOMINAL.initial_fuel_kg
    # on the ground the altitude is exactly zero (noise only applies when airborne)
    assert all(s.altitude_ft == 0 for s in snaps if s.phase == "TAXI")


def test_phases_occur_in_order_and_vertical_speed_follows_altitude():
    snaps = generate(NOMINAL, 1, 5)
    order = [p for i, p in enumerate(s.phase for s in snaps) if i == 0 or p != snaps[i - 1].phase]
    assert order == list(PHASES)
    climb = [s for s in snaps if s.phase == "CLIMB" and 600 < s.t_seconds < 1400]
    descent = [s for s in snaps if s.phase == "DESCENT" and 2200 < s.t_seconds < 2600]
    assert all(s.vertical_speed_fpm > 500 for s in climb)
    assert all(s.vertical_speed_fpm < -500 for s in descent)


def test_invalid_interval_rejected():
    with pytest.raises(ValueError):
        generate(NOMINAL, 1, 0)


# ================ alerts
def test_nominal_flight_raises_no_alerts():
    assert alerts_for(NOMINAL) == []


def test_config_discrepancy_alert_window():
    (alert,) = alerts_for(CONFIG)
    assert (alert.code, alert.level) == ("TAKEOFF_CONFIG", "critical")
    assert alert.t_start == 150  # first TAKEOFF sample
    assert 225 <= alert.t_end <= 235  # clears once above 1,500 ft


def test_unstable_approach_alerts():
    by_code = {a.code: a for a in alerts_for(UNSTABLE)}
    assert set(by_code) == {"SINK_RATE", "SPEED_LOW"}
    assert by_code["SINK_RATE"].level == "critical"
    assert 3120 <= by_code["SINK_RATE"].t_start <= 3140
    assert by_code["SPEED_LOW"].level == "caution"


def snap(t, **kw) -> Snap:
    base = dict(t_seconds=t, phase="CRUISE", altitude_ft=30000.0, airspeed_kt=280.0,
                vertical_speed_fpm=0.0, heading_deg=90.0, flap_deg=0, gear_down=False,
                n1_pct=80.0, fuel_kg=5000.0)
    return Snap(**{**base, **kw})


def test_single_sample_blip_is_debounced_but_a_run_raises_an_alert():
    blip = [snap(0), snap(5, airspeed_kt=400.0), snap(10)]
    assert detect_alerts(blip, NOMINAL) == []
    run = [snap(0), snap(5, airspeed_kt=400.0), snap(10, airspeed_kt=401.0), snap(15)]
    (alert,) = detect_alerts(run, NOMINAL)
    assert (alert.code, alert.t_start, alert.t_end) == ("SPEED_HIGH", 5, 15)


def test_alert_still_active_at_end_has_no_end_time():
    snaps = [snap(0), snap(5, fuel_kg=900.0), snap(10, fuel_kg=890.0)]
    (alert,) = detect_alerts(snaps, NOMINAL)
    assert (alert.code, alert.t_start, alert.t_end) == ("LOW_FUEL", 5, None)


def test_gear_not_down_rule_and_thresholds_come_from_the_scenario():
    low = [snap(t, phase="APPROACH", altitude_ft=1200.0, gear_down=False) for t in (0, 5)]
    assert [a.code for a in detect_alerts(low, NOMINAL)] == ["GEAR_NOT_DOWN"]
    strict = replace(NOMINAL, limits=replace(NOMINAL.limits, max_speed_kt=250.0))
    fast = [snap(0, airspeed_kt=270.0), snap(5, airspeed_kt=270.0)]
    assert detect_alerts(fast, NOMINAL) == []
    assert [a.code for a in detect_alerts(fast, strict)] == ["SPEED_HIGH"]


def test_alert_levels_are_known_and_rule_codes_unique():
    assert {r.level for r in RULES} <= {"caution", "warning", "critical"}
    assert len({r.code for r in RULES}) == len(RULES)


# ================= checklists
def test_checklist_items_are_reviews_not_procedures_rule_07():
    for tpl in TEMPLATES:
        assert "generic training example" in tpl.title.lower()
        for item in tpl.items:
            assert item.split()[0] in {"Review", "Note"}, item
    assert "does not certify" in SEMANTICS
    assert STATUSES == ("not_reviewed", "reviewed", "needs_attention")


# ================= service
def counts(db, sid):
    return {
        m.__name__: db.scalar(select(func.count()).select_from(m).where(m.session_id == sid))
        for m in (StateSnapshot, SimAlert, ChecklistItem)
    }


def test_create_session_persists_everything_atomically(db):
    sim = create_session(db, "takeoff_config_discrepancy")
    assert sim.sim_start == SIM_EPOCH and sim.sim_start.year == 2030  # clearly fictional clock
    n_items = sum(len(t.items) for t in TEMPLATES)
    assert counts(db, sim.id) == {
        "StateSnapshot": CONFIG.duration_s // 5 + 1, "SimAlert": 1, "ChecklistItem": n_items,
    }
    assert {i.status for i in db.scalars(select(ChecklistItem))} == {"not_reviewed"}


def test_sessions_are_independent_copies_rule_06(db):
    a = create_session(db, "nominal_short_haul")
    b = create_session(db, "nominal_short_haul")
    assert a.id != b.id
    assert counts(db, a.id) == counts(db, b.id)
    delete_session(db, a.id)
    assert counts(db, a.id) == {"StateSnapshot": 0, "SimAlert": 0, "ChecklistItem": 0}
    assert counts(db, b.id)["StateSnapshot"] > 0  # the other session is untouched
    with pytest.raises(SessionNotFoundError):
        get_session(db, a.id)


def test_seed_makes_runs_reproducible_across_sessions(db):
    a = create_session(db, "nominal_short_haul", seed=5)
    b = create_session(db, "nominal_short_haul", seed=5)
    rows = lambda sid: [  # noqa: E731
        (s.t_seconds, s.altitude_ft, s.airspeed_kt)
        for s in db.scalars(select(StateSnapshot).where(StateSnapshot.session_id == sid)
                            .order_by(StateSnapshot.t_seconds))
    ]
    assert rows(a.id) == rows(b.id)


def test_unknown_scenario_and_session_limit_are_explicit_errors(db):
    with pytest.raises(UnknownScenarioError):
        create_session(db, "nope")
    cfg = Settings(_env_file=None, max_sim_sessions=1)
    create_session(db, "nominal_short_haul", settings=cfg)
    with pytest.raises(SessionLimitError):
        create_session(db, "nominal_short_haul", settings=cfg)
    assert db.scalar(select(func.count()).select_from(SimSession)) == 1  # nothing half-written


def test_failure_midway_leaves_no_partial_session(db, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("disk full")

    # snapshots are already inserted when the checklist rows are built
    monkeypatch.setattr("aeris.sim.service.ChecklistItem", boom)
    with pytest.raises(RuntimeError):
        create_session(db, "nominal_short_haul")
    assert db.scalar(select(func.count()).select_from(SimSession)) == 0
    assert db.scalar(select(func.count()).select_from(StateSnapshot)) == 0
