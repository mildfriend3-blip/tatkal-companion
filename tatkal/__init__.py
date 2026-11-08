"""Tatkal Travel Companion -- prep, pacing and tracking, not automated booking."""

from .assistant import ChecklistItem, describe_journey, speed_checklist, upcoming
from .copilot import (
    TARGET_TOTAL_SECONDS,
    Step,
    build_script,
    countdown_text,
    notify,
    pacing_report,
    pre_window_alerts,
    verdict,
    wait_until,
)
from .models import IST, BookingWindow, Passenger, Reminder, class_group
from .pnr import DemoPNRProvider, PNRStatus, OfficialAPIProvider
from .schedule import reminder_plan, tatkal_window
from .store import Store

__version__ = "0.2.1"

__all__ = [
    "IST",
    "BookingWindow",
    "ChecklistItem",
    "DemoPNRProvider",
    "OfficialAPIProvider",
    "PNRStatus",
    "Passenger",
    "Reminder",
    "Step",
    "Store",
    "TARGET_TOTAL_SECONDS",
    "build_script",
    "class_group",
    "countdown_text",
    "describe_journey",
    "notify",
    "pacing_report",
    "pre_window_alerts",
    "reminder_plan",
    "speed_checklist",
    "tatkal_window",
    "upcoming",
    "verdict",
    "wait_until",
]
