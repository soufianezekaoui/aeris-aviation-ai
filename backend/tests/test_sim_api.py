from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from aeris.config import Settings, get_settings
from aeris.db.errors import DatabaseUnavailableError
from aeris.db.models import ChecklistEvent, StateSnapshot
from aeris.db.session import get_db
from aeris.main import create_app
from aeris.sim.service import SIM_EPOCH

CONFIG = "takeoff_config_discrepancy"


@pytest.fixture
def client(engine):
    app = create_app()

    def override_db():
        with Session(engine, expire_on_commit=False) as s:
            yield s

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, max_sim_sessions=5)
    return TestClient(app)


def make(client, scenario="nominal_short_haul", **kw) -> dict:
    r = client.post("/api/sim/sessions", json={"scenario_id": scenario, **kw})
    assert r.status_code == 201, r.text
    return r.json()


def items(client, sid) -> list[dict]:
    body = client.get(f"/api/sim/sessions/{sid}/checklists").json()
    return [i for c in body["checklists"] for i in c["items"]]


# ================ basics / labelling
def test_scenarios_and_session_lifecycle(client):
    sc = client.get("/api/sim/scenarios").json()
    assert {s["id"] for s in sc["scenarios"]} >= {"nominal_short_haul", CONFIG}
    assert "fictional" in sc["scenarios"][0]["aircraft"]

    created = make(client, name="  My run  ")
    assert created["name"] == "My run" and created["snapshots"] == 667
    assert created["checklist_progress"] == {"reviewed": 0, "needs_attention": 0, "total": 11}
    sid = created["session_id"]
    assert client.get(f"/api/sim/sessions/{sid}").json()["session_id"] == sid
    assert [s["session_id"] for s in client.get("/api/sim/sessions").json()["sessions"]] == [sid]
    assert client.delete(f"/api/sim/sessions/{sid}").status_code == 204
    assert client.get(f"/api/sim/sessions/{sid}").status_code == 404


def test_every_simulation_response_is_labelled_synthetic_rule_04(client):
    sid = make(client, CONFIG)["session_id"]
    base = f"/api/sim/sessions/{sid}"
    for url in ("/api/sim/scenarios", "/api/sim/sessions", base, f"{base}/state",
                f"{base}/timeline", f"{base}/alerts", f"{base}/checklists"):
        body = client.get(url).json()
        assert body["synthetic"] is True, url
        assert "not live telemetry" in body["data_source"], url
        assert "not a certified aviation system" in body["disclaimer"], url


# =============== missing session / validation
@pytest.mark.parametrize("path", ["", "/state", "/timeline", "/alerts", "/checklists"])
def test_missing_session_is_a_typed_404(client, path):
    r = client.get(f"/api/sim/sessions/does-not-exist{path}")
    assert r.status_code == 404 and r.json()["error"] == "session_not_found"


def test_missing_session_on_write_and_delete(client):
    assert client.delete("/api/sim/sessions/nope").status_code == 404
    r = client.patch("/api/sim/sessions/nope/checklists/items/1", json={"status": "reviewed"})
    assert r.status_code == 404 and r.json()["error"] == "session_not_found"


def test_input_validation(client):
    bad = client.post("/api/sim/sessions", json={"scenario_id": "nope"})
    assert bad.status_code == 422 and bad.json()["error"] == "unknown_scenario"
    assert client.post("/api/sim/sessions",
                       json={"scenario_id": "nominal_short_haul", "seed": -1}).status_code == 422
    sid = make(client)["session_id"]
    assert client.get(f"/api/sim/sessions/{sid}/state?t=-5").status_code == 422
    assert client.get(f"/api/sim/sessions/{sid}/timeline?step=1").status_code == 422


def test_session_cap_returns_409(client):
    for _ in range(5):
        make(client)
    r = client.post("/api/sim/sessions", json={"scenario_id": "nominal_short_haul"})
    assert r.status_code == 409 and r.json()["error"] == "session_limit_reached"


# =============== state freshness (RULE-05)
def test_latest_state_has_session_id_and_snapshot_timestamp(client):
    created = make(client)
    body = client.get(f"/api/sim/sessions/{created['session_id']}/state").json()
    assert body["session_id"] == created["session_id"]
    assert body["freshness"] == "latest" and body["requested_t"] is None
    assert body["t_seconds"] == created["duration_s"]
    expected = SIM_EPOCH + timedelta(seconds=created["duration_s"])
    assert datetime.fromisoformat(body["snapshot_time"]) == expected
    assert datetime.fromisoformat(body["generated_at"]).tzinfo is not None
    assert body["state"]["phase"] == "LANDING" and body["state"]["altitude_ft"] == 0


def test_exact_held_and_stale_freshness_are_disclosed(client):
    sid = make(client, CONFIG)["session_id"]
    url = f"/api/sim/sessions/{sid}/state"

    exact = client.get(f"{url}?t=160").json()
    assert (exact["freshness"], exact["t_seconds"], exact["age_s"]) == ("exact", 160, 0)
    assert exact["warnings"] == []

    held = client.get(f"{url}?t=162").json()
    assert (held["freshness"], held["t_seconds"], held["age_s"]) == ("held", 160, 2)
    assert "2s earlier" in held["warnings"][0]

    stale = client.get(f"{url}?t=99999").json()
    assert stale["freshness"] == "stale" and stale["t_seconds"] == 3330
    assert "not a current state" in stale["warnings"][0]


def test_absent_state_is_disclosed_not_invented(client, engine):
    sid = make(client)["session_id"]
    with Session(engine) as s:
        s.execute(delete(StateSnapshot).where(StateSnapshot.session_id == sid))
        s.commit()
    body = client.get(f"/api/sim/sessions/{sid}/state").json()
    assert body["freshness"] == "absent" and body["state"] is None
    assert body["snapshot_time"] is None and body["warnings"]


def test_active_alerts_follow_simulated_time(client):
    sid = make(client, CONFIG)["session_id"]
    at = lambda t: client.get(f"/api/sim/sessions/{sid}/state?t={t}").json()  # noqa: E731
    assert at(100)["active_alerts"] == []
    during = at(160)["active_alerts"]
    assert [a["code"] for a in during] == ["TAKEOFF_CONFIG"] and during[0]["level"] == "critical"
    assert at(300)["active_alerts"] == []


def test_alerts_endpoint_as_of_time(client):
    sid = make(client, CONFIG)["session_id"]
    url = f"/api/sim/sessions/{sid}/alerts"
    assert client.get(f"{url}?t=100").json()["alerts"] == []
    live = client.get(f"{url}?t=160").json()
    assert live["as_of_t"] == 160 and live["alerts"][0]["active"] is True
    done = client.get(f"{url}?t=300").json()["alerts"][0]
    assert done["active"] is False and done["t_end"] == 230
    assert datetime.fromisoformat(done["start_time"]) == SIM_EPOCH + timedelta(seconds=150)
    assert client.get(url).json()["as_of_t"] == 3330


def test_timeline_downsamples_and_includes_endpoints_and_alerts(client):
    sid = make(client, CONFIG)["session_id"]
    body = client.get(f"/api/sim/sessions/{sid}/timeline?step=60").json()
    ts = [p["t"] for p in body["points"]]
    assert ts[0] == 0 and ts[-1] == 3330 and body["step_s"] == 60
    assert all(t % 60 == 0 for t in ts[:-1]) and len(ts) < 70
    assert [a["code"] for a in body["alerts"]] == ["TAKEOFF_CONFIG"]
    assert client.get(f"/api/sim/sessions/{sid}/timeline?step=7").json()["step_s"] == 10


# =============== checklists (RULE-07)
def test_checklist_structure_and_semantics(client):
    sid = make(client)["session_id"]
    body = client.get(f"/api/sim/sessions/{sid}/checklists").json()
    assert "does not certify" in body["semantics"]
    assert [c["key"] for c in body["checklists"]] == [
        "departure_review", "approach_review", "debrief_review"]
    assert all("generic training example" in c["title"].lower() for c in body["checklists"])
    assert body["progress"] == {"reviewed": 0, "needs_attention": 0, "total": 11}


def test_recording_a_review_updates_progress_and_audit_trail(client, engine):
    sid = make(client)["session_id"]
    first = items(client, sid)[0]
    url = f"/api/sim/sessions/{sid}/checklists/items/{first['id']}"

    r = client.patch(url, json={"status": "reviewed", "note": "  matches briefing  "})
    assert r.status_code == 200
    body = r.json()
    assert body["item"]["status"] == "reviewed" and body["item"]["note"] == "matches briefing"
    assert body["progress"]["reviewed"] == 1 and "does not certify" in body["semantics"]

    def events():
        with Session(engine) as s:
            return s.scalar(select(func.count()).select_from(ChecklistEvent))

    assert events() == 1
    client.patch(url, json={"status": "reviewed", "note": "matches briefing"})  # no change
    assert events() == 1
    client.patch(url, json={"status": "reviewed", "note": "edited note"})  # note only
    assert events() == 1
    client.patch(url, json={"status": "needs_attention"})
    assert events() == 2
    after = client.get(f"/api/sim/sessions/{sid}/checklists").json()["progress"]
    assert after == {"reviewed": 0, "needs_attention": 1, "total": 11}


def test_checklist_input_validation(client):
    sid = make(client)["session_id"]
    iid = items(client, sid)[0]["id"]
    url = f"/api/sim/sessions/{sid}/checklists/items/{iid}"
    assert client.patch(url, json={"status": "done"}).status_code == 422
    assert client.patch(url, json={"status": "reviewed", "note": "x" * 501}).status_code == 422
    assert client.patch(url, json={}).status_code == 422
    blank = client.patch(url, json={"status": "reviewed", "note": "   "}).json()
    assert blank["item"]["note"] is None


# =============== session isolation (RULE-06 / BR-07)
def test_checklist_progress_is_isolated_between_sessions(client):
    a = make(client)["session_id"]
    b = make(client)["session_id"]
    for item in items(client, a)[:3]:
        client.patch(f"/api/sim/sessions/{a}/checklists/items/{item['id']}",
                     json={"status": "reviewed"})
    assert client.get(f"/api/sim/sessions/{a}/checklists").json()["progress"]["reviewed"] == 3
    assert client.get(f"/api/sim/sessions/{b}/checklists").json()["progress"]["reviewed"] == 0
    assert {i["id"] for i in items(client, a)}.isdisjoint({i["id"] for i in items(client, b)})


def test_another_sessions_item_id_is_not_reachable(client):
    a = make(client)["session_id"]
    b = make(client)["session_id"]
    foreign = items(client, a)[0]
    r = client.patch(f"/api/sim/sessions/{b}/checklists/items/{foreign['id']}",
                     json={"status": "reviewed", "note": "attack"})
    assert r.status_code == 404 and r.json()["error"] == "item_not_found"
    untouched = items(client, a)[0]
    assert untouched["status"] == "not_reviewed" and untouched["note"] is None
    # indistinguishable from an id that does not exist at all
    r2 = client.patch(f"/api/sim/sessions/{b}/checklists/items/999999", json={"status": "reviewed"})
    assert r2.status_code == 404 and r2.json()["error"] == r.json()["error"]


def test_state_and_alerts_never_mix_sessions(client):
    with_alert = make(client, CONFIG)["session_id"]
    without = make(client, "nominal_short_haul")["session_id"]
    assert client.get(f"/api/sim/sessions/{with_alert}/alerts").json()["alerts"]
    assert client.get(f"/api/sim/sessions/{without}/alerts").json()["alerts"] == []
    assert client.get(f"/api/sim/sessions/{without}/state?t=160").json()["active_alerts"] == []
    assert client.get(f"/api/sim/sessions/{without}/state").json()["session_id"] == without


def test_deleting_one_session_leaves_the_other_intact(client):
    a = make(client)["session_id"]
    b = make(client)["session_id"]
    client.delete(f"/api/sim/sessions/{a}")
    assert client.get(f"/api/sim/sessions/{b}/state").status_code == 200
    assert len(items(client, b)) == 11


# =============== reliability / independence
def test_database_failure_is_typed_safe_and_does_not_break_the_rest(engine):
    app = create_app()

    def broken():
        raise DatabaseUnavailableError("Cannot connect to the database (postgresql://u:***@h/db)")
        yield  # pragma: no cover

    app.dependency_overrides[get_db] = broken
    c = TestClient(app)
    r = c.get("/api/sim/sessions")
    assert r.status_code == 503 and r.json()["error"] == "database_unavailable"
    assert "secret" not in r.text
    assert c.get("/health").status_code == 200  # document Q&A / liveness unaffected
    assert c.get("/api/sim/scenarios").status_code == 200  # static data needs no DB
