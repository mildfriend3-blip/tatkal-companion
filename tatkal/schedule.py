"""Tatkal window arithmetic and the reminder plan built from it."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from .models import IST, TATKAL_OPEN_IST, BookingWindow, Reminder, class_group

DEFAULT_OFFSETS = (120, 30, 10, 2, 0)

_HINTS = {
    120: "check your IRCTC wallet balance and keep the UPI app you will pay with open",
    30: "sign in to IRCTC yourself and load your saved passenger master list",
    10: "final review: journey date, class, passenger names, ID proof",
    2: "keep the official IRCTC booking page open on your phone",
    0: "tatkal window OPEN - book now on the official IRCTC app or site",
}


def tatkal_window(journey_date: date, travel_class: str) -> BookingWindow:
    """Tatkal for `journey_date` opens the previous day at 10:00 or 11:00 IST."""
    group = class_group(travel_class)
    opens_at = datetime.combine(
        journey_date - timedelta(days=1), TATKAL_OPEN_IST[group], tzinfo=IST
    )
    return BookingWindow(
        journey_date=journey_date,
        travel_class=travel_class.strip().upper(),
        group=group,
        opens_at=opens_at,
    )


def reminder_plan(
    window: BookingWindow, offsets: tuple[int, ...] = DEFAULT_OFFSETS
) -> list[Reminder]:
    """Reminders in chronological order, ending at the opening moment."""
    plan: list[Reminder] = []
    for offset in sorted(set(offsets), reverse=True):
        at = window.opens_at - timedelta(minutes=offset)
        message = _HINTS.get(offset, f"tatkal window opens in {offset} minutes")
        plan.append(Reminder(at=at, offset_minutes=offset, message=message))
    return plan
