from __future__ import annotations

from dataclasses import dataclass

AIRCRAFT_LABEL = "Generic twin-jet airliner (fictional, not a real aircraft type)"
PHASES = ("TAXI", "TAKEOFF", "CLIMB", "CRUISE", "DESCENT", "APPROACH", "LANDING")


@dataclass(frozen=True)
class Keyframe:
    t: int
    alt_ft: float
    ias_kt: float
    hdg_deg: float
    n1_pct: float
    flaps: int
    gear_down: bool
    phase: str


@dataclass(frozen=True)
class Limits:
    briefed_takeoff_flaps: int = 15
    max_speed_kt: float = 320.0
    min_approach_speed_kt: float = 125.0
    fuel_reserve_kg: float = 1200.0


@dataclass(frozen=True)
class Scenario:
    id: str
    name: str
    description: str
    learning_goal: str
    keyframes: tuple[Keyframe, ...]
    limits: Limits = Limits()
    initial_fuel_kg: float = 6500.0
    default_seed: int = 42

    @property
    def duration_s(self) -> int:
        return self.keyframes[-1].t


K = Keyframe


def _departure(flaps: int) -> list[Keyframe]:
    return [
        K(0, 0, 0, 90, 24, flaps, True, "TAXI"),
        K(90, 0, 14, 90, 28, flaps, True, "TAXI"),
        K(150, 0, 0, 90, 26, flaps, True, "TAKEOFF"),
        K(190, 0, 145, 90, 92, flaps, True, "TAKEOFF"),
        K(200, 60, 152, 90, 92, flaps, True, "TAKEOFF"),
        K(215, 900, 170, 92, 90, flaps, True, "CLIMB"),
        K(225, 1500, 175, 95, 88, flaps, False, "CLIMB"),
        K(330, 5000, 215, 100, 86, 0, False, "CLIMB"),  # flaps retracted
        K(600, 15000, 270, 100, 85, 0, False, "CLIMB"),
        K(1500, 33000, 285, 100, 84, 0, False, "CRUISE"),
        K(2100, 33000, 285, 105, 84, 0, False, "DESCENT"),
        K(2160, 31200, 285, 105, 40, 0, False, "DESCENT"),
        K(2700, 10000, 250, 110, 38, 0, False, "DESCENT"),
        K(2900, 3000, 220, 118, 40, 0, False, "APPROACH"),
        K(3000, 2400, 190, 118, 45, 15, False, "APPROACH"),
        K(3050, 2000, 165, 118, 48, 15, True, "APPROACH"),
    ]


def _stable_arrival() -> list[Keyframe]:
    return [
        K(3150, 900, 145, 118, 52, 30, True, "APPROACH"),
        K(3250, 50, 138, 118, 50, 30, True, "APPROACH"),
        K(3260, 0, 135, 118, 40, 30, True, "LANDING"),
        K(3300, 0, 60, 118, 30, 30, True, "LANDING"),
        K(3330, 0, 15, 118, 22, 30, True, "LANDING"),
    ]


def _unstable_arrival() -> list[Keyframe]:
    return [
        K(3100, 1500, 150, 118, 52, 30, True, "APPROACH"),
        K(3120, 1100, 125, 118, 38, 30, True, "APPROACH"),
        K(3140, 350, 112, 118, 35, 30, True, "APPROACH"),  # steep, slow, low
        K(3170, 30, 108, 118, 30, 30, True, "APPROACH"),
        K(3180, 0, 105, 118, 28, 30, True, "LANDING"),
        K(3220, 0, 50, 118, 25, 30, True, "LANDING"),
        K(3250, 0, 15, 118, 22, 30, True, "LANDING"),
    ]


SCENARIOS: dict[str, Scenario] = {
    s.id: s
    for s in (
        Scenario(
            id="nominal_short_haul",
            name="Nominal short-haul flight",
            description="A complete, uneventful synthetic flight from taxi to landing roll.",
            learning_goal="Learn what normal parameter trends look like in each phase; no alerts "
            "are expected.",
            keyframes=tuple(_departure(15) + _stable_arrival()),
        ),
        Scenario(
            id="takeoff_config_discrepancy",
            name="Takeoff configuration discrepancy (training)",
            description="The flaps are not at the briefed takeoff setting during takeoff and "
            "initial climb.",
            learning_goal="Practise spotting a configuration alert and reviewing it against "
            "the briefing. Compare with the configuration findings in the Spanair report.",
            keyframes=tuple(_departure(0) + _stable_arrival()),
        ),
        Scenario(
            id="unstable_approach",
            name="Unstable approach (training)",
            description="A fast sink rate and low airspeed develop on short final.",
            learning_goal="Practise reading sink-rate and speed trends and the alerts they raise.",
            keyframes=tuple(_departure(15) + _unstable_arrival()),
        ),
    )
}


def get_scenario(scenario_id: str) -> Scenario | None:
    return SCENARIOS.get(scenario_id)
