"""Orchestration: readiness checklist, upcoming reminders, journey summaries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from .models import IST, BookingWindow
from .schedule import reminder_plan, tatkal_window
from .store import Store


@dataclass(frozen=True)
class ChecklistItem:
    """`done` is True/False when the agent can check it, None when only you can."""

    label: str
    done: bool | None
    note: str = ""

    def render(self) -> str:
        mark = {True: "[x]", False: "[ ]", None: "[~]"}[self.done]
        return f"{mark} {self.label}" + (f"  -- {self.note}" if self.note else "")


def speed_checklist(
    store: Store, journey: dict, now: datetime | None = None
) -> tuple[BookingWindow, list[ChecklistItem]]:
    """What has to be true before the window opens, checked against the store."""
    now = now or datetime.now(IST)
    journey_date = date.fromisoformat(journey["journey_date"])
    window = tatkal_window(journey_date, journey["travel_class"])

    saved = {name.lower() for name in store.passenger_names()}
    wanted = journey.get("passengers") or []
    missing = [name for name in wanted if name.lower() not in saved]

    if wanted:
        passengers_item = ChecklistItem(
            label="Passengers saved in your IRCTC master list",
            done=not missing,
            note=(
                f"not saved yet: {', '.join(missing)}"
                if missing
                else f"{len(wanted)} passenger(s) ready"
            ),
        )
    else:
        passengers_item = ChecklistItem(
            label="Passengers saved in your IRCTC master list",
            done=None,
            note="no passengers attached to this journey yet",
        )

    items = [
        passengers_item,
        ChecklistItem(
            "ID proof carried, names match the master list",
            None,
            "Aadhaar / voter ID / passport as accepted by IRCTC",
        ),
        ChecklistItem(
            "IRCTC wallet topped up, or the UPI app ready",
            None,
            "tatkal fares carry an extra tatkal charge",
        ),
        ChecklistItem(
            "Signed in to the official IRCTC app or site",
            None,
            "you sign in yourself; this agent never logs in or pays for you",
        ),
        ChecklistItem(
            "Backup connection ready",
            None,
            "second SIM or hotspot in case the primary network stalls",
        ),
        ChecklistItem(
            "Tatkal window confirmed",
            True,
            window.describe(),
        ),
    ]
    if now > window.opens_at:
        items.append(
            ChecklistItem(
                "Window already open",
                True,
                f"opened {window.opens_at.strftime('%d %b %Y, %H:%M IST')}",
            )
        )
    return window, items


def upcoming(
    store: Store, now: datetime | None = None, within_minutes: int = 180
) -> list[tuple[dict, object]]:
    """Reminders falling between now and now + within_minutes, soonest first."""
    now = now or datetime.now(IST)
    horizon = now + timedelta(minutes=within_minutes)
    pairs = []
    for journey in store.journeys():
        journey_date = date.fromisoformat(journey["journey_date"])
        window = tatkal_window(journey_date, journey["travel_class"])
        for reminder in reminder_plan(window):
            if now <= reminder.at <= horizon:
                pairs.append((journey, reminder))
    pairs.sort(key=lambda pair: pair[1].at)
    return pairs


def describe_journey(journey: dict) -> str:
    train = journey.get("train") or "train not set"
    pax = ", ".join(journey.get("passengers") or []) or "no passengers attached"
    return (
        f"{journey['from']} -> {journey['to']}  "
        f"{journey['journey_date']}  {journey['travel_class']}  "
        f"({train})  [{journey['id']}]\n"
        f"    passengers: {pax}"
    )
