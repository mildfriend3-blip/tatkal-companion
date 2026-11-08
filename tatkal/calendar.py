"""Calendar export: the reminder plan as an .ics feed.

Import the file once into any calendar app and the nudges arrive even when this
tool, the terminal, or the phone's battery saver is not cooperating.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from .models import IST
from .schedule import reminder_plan, tatkal_window

PRODID = "-//Tatkal Travel Companion//EN"
CALENDAR_NAME = "Tatkal reminders"


def _escape(text: str) -> str:
    """RFC 5545 text escaping."""
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _fold(line: str, limit: int = 73) -> list[str]:
    """Fold a content line so no line exceeds 75 octets."""
    if len(line) <= limit:
        return [line]
    chunks = [line[:limit]]
    rest = line[limit:]
    while rest:
        chunks.append(" " + rest[: limit - 1])
        rest = rest[limit - 1 :]
    return chunks


def _utc_stamp(moment: datetime) -> str:
    """Calendar times are stored in UTC, whatever zone you are in."""
    return moment.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_calendar(journeys: list[dict], now: datetime | None = None) -> str:
    """One VEVENT per reminder for each journey, each with a display alarm."""
    now = now or datetime.now(IST)
    stamp = _utc_stamp(now)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{CALENDAR_NAME}",
    ]

    for journey in journeys:
        journey_date = date.fromisoformat(journey["journey_date"])
        window = tatkal_window(journey_date, journey["travel_class"])
        route = f"{journey['from']}-{journey['to']}"
        travel_class = journey["travel_class"]

        for reminder in reminder_plan(window):
            label = (
                f"Tatkal window OPEN: {travel_class} {route}"
                if reminder.offset_minutes == 0
                else f"Tatkal T-{reminder.offset_minutes}: {travel_class} {route}"
            )
            lines += [
                "BEGIN:VEVENT",
                f"UID:{journey['id']}-t{reminder.offset_minutes}@tatkal-companion",
                f"DTSTAMP:{stamp}",
                f"DTSTART:{_utc_stamp(reminder.at)}",
                f"DTEND:{_utc_stamp(reminder.at + timedelta(minutes=5))}",
                *_fold(f"SUMMARY:{_escape(label)}"),
                *_fold(f"DESCRIPTION:{_escape(reminder.message)}"),
                "BEGIN:VALARM",
                "TRIGGER:PT0M",
                "ACTION:DISPLAY",
                *_fold(f"DESCRIPTION:{_escape(label)}"),
                "END:VALARM",
                "END:VEVENT",
            ]

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
