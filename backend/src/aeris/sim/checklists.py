from __future__ import annotations

from dataclasses import dataclass

NOT_REVIEWED = "not_reviewed"
REVIEWED = "reviewed"
NEEDS_ATTENTION = "needs_attention"
STATUSES = (NOT_REVIEWED, REVIEWED, NEEDS_ATTENTION)

SEMANTICS = (
    "Review progress inside AERIS only. A status does not certify that any real-world "
    "procedure was performed. Generic training examples, not manufacturer procedures."
)


@dataclass(frozen=True)
class ChecklistTemplate:
    key: str
    title: str
    items: tuple[str, ...]


TEMPLATES: tuple[ChecklistTemplate, ...] = (
    ChecklistTemplate("departure_review", "Departure review (generic training example)", (
        "Review the briefed takeoff flap setting",
        "Review whether the flap indication matches the briefing",
        "Review the configuration alert status shown in the simulation",
        "Review the departure and abnormal-event briefing notes",
    )),
    ChecklistTemplate("approach_review", "Approach review (generic training example)", (
        "Review the approach speed target against the airspeed trend",
        "Review the landing gear indication",
        "Review the vertical-speed (sink rate) trend",
        "Review the stabilised-approach criteria used in this training scenario",
    )),
    ChecklistTemplate("debrief_review", "Debrief review (generic training example)", (
        "Review the alerts raised during the session",
        "Review the timeline for deviations from the expected profile",
        "Note one lesson learned from this scenario",
    )),
)
