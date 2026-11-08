"""Core data models for the Tatkal Travel Companion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

# Tatkal booking rules (Indian Railways): the window opens one day before the
# journey date -- 10:00 IST for AC classes, 11:00 IST for non-AC classes.
AC_CLASSES = frozenset({"1A", "2A", "3A", "3E", "CC", "EC", "EA"})
NON_AC_CLASSES = frozenset({"SL", "2S"})
ALL_CLASSES = AC_CLASSES | NON_AC_CLASSES
TATKAL_OPEN_IST = {"AC": time(10, 0), "NON_AC": time(11, 0)}

GENDERS = frozenset({"M", "F", "O"})
BERTH_PREFERENCES = (
    "NO PREFERENCE",
    "LOWER",
    "MIDDLE",
    "UPPER",
    "SIDE LOWER",
    "SIDE UPPER",
)


def class_group(travel_class: str) -> str:
    """Return 'AC' or 'NON_AC' for a travel class code."""
    code = travel_class.strip().upper()
    if code in AC_CLASSES:
        return "AC"
    if code in NON_AC_CLASSES:
        return "NON_AC"
    raise ValueError(
        f"unknown travel class {travel_class!r}; expected one of {sorted(ALL_CLASSES)}"
    )


@dataclass(frozen=True)
class Passenger:
    """A passenger record kept in the local master list."""

    name: str
    age: int
    gender: str
    berth_preference: str = "NO PREFERENCE"
    id_type: str = "AADHAAR"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("passenger name is required")
        if not 1 <= int(self.age) <= 120:
            raise ValueError("age must be between 1 and 120")
        if self.gender.strip().upper() not in GENDERS:
            raise ValueError("gender must be one of M, F, O")
        if self.berth_preference.strip().upper() not in BERTH_PREFERENCES:
            raise ValueError(
                f"berth preference must be one of {', '.join(BERTH_PREFERENCES)}"
            )

    def as_dict(self) -> dict:
        return {
            "name": self.name.strip(),
            "age": int(self.age),
            "gender": self.gender.strip().upper(),
            "berth_preference": self.berth_preference.strip().upper(),
            "id_type": self.id_type.strip().upper(),
        }


@dataclass(frozen=True)
class BookingWindow:
    """When tatkal booking opens for one journey."""

    journey_date: date
    travel_class: str
    group: str
    opens_at: datetime

    def describe(self) -> str:
        kind = "AC" if self.group == "AC" else "non-AC"
        return (
            f"{self.travel_class} ({kind}) for {self.journey_date.strftime('%d %b %Y')} "
            f"opens {self.opens_at.strftime('%d %b %Y, %H:%M IST')}"
        )


@dataclass(frozen=True)
class Reminder:
    """A single pre-window nudge."""

    at: datetime
    offset_minutes: int
    message: str

    def describe(self) -> str:
        return f"{self.at.strftime('%d %b %H:%M IST')}  T-{self.offset_minutes:>3} min  {self.message}"
