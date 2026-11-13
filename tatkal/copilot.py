"""Local co-pilot: paces you through the booking window, second by second.

This module never talks to IRCTC. It keeps the clock, tells you the next action,
and reports how far ahead or behind you are. Everything runs on your machine.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timedelta

from .models import IST

# What a well-prepared person can realistically do, from tapping Book Ticket to
# confirming payment. IRCTC's own page latency sits on top of this and is not
# something any local tool can compress.
TARGET_TOTAL_SECONDS = 25


@dataclass(frozen=True)
class Step:
    """One action, with the second it should be finished by."""

    offset_seconds: int
    action: str
    detail: str = ""

    def describe(self) -> str:
        head = f"T+{self.offset_seconds:>2}s  {self.action}"
        return head + (f"\n         {self.detail}" if self.detail else "")


def build_script(journey: dict, payment_mode: str = "WALLET") -> list[Step]:
    """The click order for one journey, pre-decided so nothing is a decision live."""
    mode = payment_mode.strip().upper()
    if mode not in {"WALLET", "UPI"}:
        raise ValueError("payment_mode must be WALLET or UPI")

    route = f"{journey['from']} -> {journey['to']} on {journey['journey_date']}"
    travel_class = journey["travel_class"]
    count = len(journey.get("passengers") or [])

    if mode == "WALLET":
        pay_step = Step(
            18,
            "Tap Continue to Payment, choose IRCTC Wallet",
            "wallet is already funded, so no UPI PIN round trip",
        )
        confirm_step = Step(21, "Review and complete the payment on the official page", "follow the payment provider instructions yourself")
    else:
        pay_step = Step(
            18,
            "Tap Continue to Payment, choose UPI",
            "your UPI app is already open in the background",
        )
        confirm_step = Step(21, "Review and complete the UPI payment yourself", "never share your UPI PIN")

    return [
        Step(0, "Open IRCTC and start a Tatkal search", route),
        Step(2, "Enter From / To / Date from your saved journey, then find trains", "type and verify these details on the official page"),
        Step(6, f"Find and verify the train, select {travel_class}, then continue", journey.get("train") or "choose your train on the official page"),
        Step(10, f"Enter and verify passenger details ({count} name(s) in your saved brief)", "your saved list is a reference only; enter details on IRCTC yourself"),
        Step(14, "Review passenger details and preferences, then continue", "verify every field on the official page"),
        pay_step,
        confirm_step,
        Step(TARGET_TOTAL_SECONDS, "Check the official result and note the PNR if booking succeeded", "the tool cannot verify or submit a booking"),
    ]


def pacing_report(elapsed_by_step: list[float], script: list[Step]) -> list[tuple[Step, float, float]]:
    """Pair each step with how long it actually took and the slip vs target."""
    if len(elapsed_by_step) != len(script):
        raise ValueError(
            f"expected {len(script)} timings, got {len(elapsed_by_step)}"
        )
    report = []
    previous = 0.0
    for step, elapsed in zip(script, elapsed_by_step):
        duration = elapsed - previous
        previous = elapsed
        slip = elapsed - step.offset_seconds
        report.append((step, duration, slip))
    return report


def verdict(slip: float) -> str:
    if slip < 0:
        return "ahead"
    if slip <= 3:
        return "on time"
    return f"{slip:.0f}s behind"


def countdown_text(target: datetime, now: datetime | None = None) -> str:
    now = now or datetime.now(IST)
    remaining = (target - now).total_seconds()
    if remaining <= 0:
        return "OPEN"
    minutes, seconds = divmod(int(remaining), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {seconds:02d}s"
    return f"{minutes:02d}m {seconds:02d}s"


IRCTC_SEARCH_URL = "https://www.irctc.co.in/nget/train-search"


def notify(title: str, message: str) -> bool:
    """Phone or desktop notification if the machine has one, bell otherwise."""
    if shutil.which("termux-notification"):
        result = subprocess.run(
            ["termux-notification", "--title", title, "--content", message],
            check=False,
            capture_output=True,
        )
        if result.returncode == 0:
            return True
    if shutil.which("notify-send"):
        result = subprocess.run(
            ["notify-send", title, message], check=False, capture_output=True
        )
        if result.returncode == 0:
            return True
    print("\a", end="", flush=True)
    return False


def open_official_site(url: str = IRCTC_SEARCH_URL) -> bool:
    """Open the official page in the browser. Nothing is filled in or submitted."""
    for command in (["termux-open-url", url], ["xdg-open", url], ["open", url]):
        if shutil.which(command[0]):
            result = subprocess.run(command, check=False, capture_output=True)
            if result.returncode == 0:
                return True
    return False


def alert_schedule(window_opens_at: datetime) -> list[tuple[datetime, str]]:
    """The pre-window nudges as absolute times, soonest last."""
    pairs = [
        (window_opens_at - lead, message)
        for lead, message in pre_window_alerts(window_opens_at)
    ]
    pairs.sort(key=lambda pair: pair[0])
    return pairs


def wait_until(target: datetime, tick_seconds: float = 0.5) -> None:
    """Block until target, printing a live countdown. Local only, no network."""
    while True:
        now = datetime.now(IST)
        remaining = (target - now).total_seconds()
        if remaining <= 0:
            return
        print(f"\r  window opens in {countdown_text(target, now)}  ", end="", flush=True)
        time.sleep(min(tick_seconds, max(remaining, 0.05)))


def pre_window_alerts(window_opens_at: datetime) -> list[tuple[timedelta, str]]:
    """The two nudges worth a desktop popup, as (lead time, message)."""
    return [
        (timedelta(minutes=10), "Tatkal in 10 minutes: review passengers and ID proof"),
        (timedelta(minutes=2), "Tatkal in 2 minutes: booking page open, wallet or UPI ready"),
        (timedelta(0), "Tatkal window is OPEN: start the script now"),
    ]
