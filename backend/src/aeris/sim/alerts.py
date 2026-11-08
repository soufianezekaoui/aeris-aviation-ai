from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from aeris.sim.generator import Snap
from aeris.sim.scenarios import Scenario


@dataclass(frozen=True)
class Rule:
    code: str
    level: str            # caution | warning | critical
    message: str
    applies: Callable[[Snap, Scenario], bool]
    min_samples: int = 2  # debounce: a one-sample blip is not an alert


@dataclass(frozen=True)
class AlertInterval:
    code: str
    level: str
    message: str
    t_start: int
    t_end: int | None     # None = still active at the end of the data


RULES: tuple[Rule, ...] = (
    Rule(
        "TAKEOFF_CONFIG", "critical",
        "TAKEOFF CONFIG: flaps not at the briefed setting (training scenario)",
        lambda s, sc: s.phase in ("TAKEOFF", "CLIMB")
        and s.altitude_ft < 1500
        and s.flap_deg != sc.limits.briefed_takeoff_flaps,
    ),
    Rule(
        "SINK_RATE", "critical", "SINK RATE: descent rate high close to the ground",
        lambda s, sc: 20 < s.altitude_ft < 1000 and s.vertical_speed_fpm < -2000,
    ),
    Rule(
        "GEAR_NOT_DOWN", "warning", "GEAR: not down below 1500 ft on approach",
        lambda s, sc: s.phase == "APPROACH" and s.altitude_ft < 1500 and not s.gear_down,
    ),
    Rule(
        "SPEED_HIGH", "warning", "SPEED: above the scenario's maximum speed",
        lambda s, sc: s.altitude_ft > 20 and s.airspeed_kt > sc.limits.max_speed_kt,
    ),
    Rule(
        "SPEED_LOW", "caution", "SPEED: below the scenario's minimum approach speed",
        lambda s, sc: s.phase == "APPROACH"
        and 20 < s.altitude_ft < 1500
        and s.airspeed_kt < sc.limits.min_approach_speed_kt,
    ),
    Rule(
        "LOW_FUEL", "caution", "FUEL: below the scenario's reserve level",
        lambda s, sc: s.fuel_kg < sc.limits.fuel_reserve_kg,
    ),
)


def detect_alerts(snaps: list[Snap], scenario: Scenario) -> list[AlertInterval]:
    """Turn per-sample rule hits into debounced intervals.

    ``t_start`` is the first sample of the qualifying run; ``t_end`` is the first sample
    where the condition no longer holds, so an alert is active for t_start <= t < t_end.
    """
    found: list[AlertInterval] = []
    for rule in RULES:
        run_start: int | None = None
        run_len = 0
        for s in snaps:
            if rule.applies(s, scenario):
                if run_start is None:
                    run_start = s.t_seconds
                run_len += 1
            else:
                if run_start is not None and run_len >= rule.min_samples:
                    found.append(AlertInterval(rule.code, rule.level, rule.message,
                                               run_start, s.t_seconds))
                run_start, run_len = None, 0
        if run_start is not None and run_len >= rule.min_samples:
            found.append(AlertInterval(rule.code, rule.level, rule.message, run_start, None))
    return sorted(found, key=lambda a: (a.t_start, a.code))
