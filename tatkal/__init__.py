"""Tatkal Travel Companion -- prep, pacing and tracking, not automated booking."""

from .calendar import build_calendar
from .assistant import ChecklistItem, describe_journey, speed_checklist, upcoming
from .copilot import (
    IRCTC_SEARCH_URL,
    TARGET_TOTAL_SECONDS,
    alert_schedule,
    open_official_site,
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
from .pnr import DemoPNRProvider, HttpPNRProvider, PNRStatus, OfficialAPIProvider
from .schedule import reminder_plan, tatkal_window
from .store import Store

__version__ = "0.5.0"

__all__ = [
    "IRCTC_SEARCH_URL",
    "IST",
    "BookingWindow",
    "ChecklistItem",
    "DemoPNRProvider",
    "HttpPNRProvider",
    "OfficialAPIProvider",
    "PNRStatus",
    "Passenger",
    "Reminder",
    "Step",
    "Store",
    "TARGET_TOTAL_SECONDS",
    "alert_schedule",
    "build_calendar",
    "build_script",
    "class_group",
    "countdown_text",
    "describe_journey",
    "notify",
    "open_official_site",
    "pacing_report",
    "pre_window_alerts",
    "reminder_plan",
    "speed_checklist",
    "tatkal_window",
    "upcoming",
    "verdict",
    "wait_until",
]
