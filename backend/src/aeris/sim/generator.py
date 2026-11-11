from __future__ import annotations

import bisect
import random
from dataclasses import dataclass

from aeris.sim.scenarios import Keyframe, Scenario

# Illustrative fuel flow per phase, kg per second.
_BURN = {
    "TAXI": 0.15, "TAKEOFF": 1.6, "CLIMB": 1.3, "CRUISE": 0.7,
    "DESCENT": 0.25, "APPROACH": 0.45, "LANDING": 0.2,
}


@dataclass(frozen=True)
class Snap:
    t_seconds: int
    phase: str
    altitude_ft: float
    airspeed_kt: float
    vertical_speed_fpm: float
    heading_deg: float
    flap_deg: int
    gear_down: bool
    n1_pct: float
    fuel_kg: float


def _frame_at(frames: tuple[Keyframe, ...], times: list[int], t: float) -> Keyframe:
    
    # return the last frame at or before time t
    return frames[max(bisect.bisect_right(times, t) - 1, 0)]


def _lerp(frames: tuple[Keyframe, ...], times: list[int], t: float, attr: str) -> float:
    i = bisect.bisect_right(times, t)
    if i == 0:
        return getattr(frames[0], attr)
    if i >= len(frames):
        return getattr(frames[-1], attr)
    a, b = frames[i - 1], frames[i]
    span = b.t - a.t
    w = 0.0 if span == 0 else (t - a.t) / span
    return getattr(a, attr) + (getattr(b, attr) - getattr(a, attr)) * w


def generate(scenario: Scenario, seed: int, interval_s: int = 5) -> list[Snap]:
    if interval_s < 1:
        raise ValueError("interval_s must be >= 1")
    rng = random.Random(seed)
    frames = scenario.keyframes
    times = [f.t for f in frames]
    out: list[Snap] = []
    fuel = scenario.initial_fuel_kg

    for t in range(0, scenario.duration_s + 1, interval_s):
        f = _frame_at(frames, times, t)
        alt_clean = _lerp(frames, times, t, "alt_ft")
        alt_next = _lerp(frames, times, min(t + interval_s, scenario.duration_s), "alt_ft")
        vs = (alt_next - alt_clean) / interval_s * 60.0
        airborne = alt_clean > 50

        alt = max(0.0, alt_clean + (rng.gauss(0, 8) if airborne else 0.0))
        ias = max(0.0, _lerp(frames, times, t, "ias_kt") + (rng.gauss(0, 0.8) if t else 0.0))
        hdg = (_lerp(frames, times, t, "hdg_deg") + rng.gauss(0, 0.3)) % 360
        n1 = min(100.0, max(0.0, _lerp(frames, times, t, "n1_pct") + rng.gauss(0, 0.2)))
        vs = vs + (rng.gauss(0, 15) if airborne else 0.0)

        out.append(Snap(
            t_seconds=t, phase=f.phase, altitude_ft=round(alt, 1), airspeed_kt=round(ias, 1),
            vertical_speed_fpm=round(vs, 1), heading_deg=round(hdg, 1), flap_deg=f.flaps,
            gear_down=f.gear_down, n1_pct=round(n1, 1), fuel_kg=round(fuel, 1),
        ))
        fuel = max(0.0, fuel - _BURN[f.phase] * interval_s)
    return out
