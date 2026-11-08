"""End-to-end tour on throwaway data. Run: python demo.py"""

from __future__ import annotations

import tempfile
from datetime import date, datetime
from pathlib import Path

from tatkal.assistant import describe_journey, speed_checklist, upcoming
from tatkal.copilot import build_script
from tatkal.models import IST, Passenger
from tatkal.pnr import DemoPNRProvider
from tatkal.schedule import reminder_plan, tatkal_window
from tatkal.store import Store

JOURNEY_DATE = date(2026, 11, 9)
NOW = datetime(2026, 11, 8, 8, 0, tzinfo=IST)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = Store(Path(tmp) / "demo.json")
        store.add_passenger(Passenger("Asha Rao", 34, "F", "LOWER"))
        store.add_passenger(Passenger("Ravi Rao", 38, "M", "UPPER"))
        journey = store.add_journey(
            "NDLS", "BCT", JOURNEY_DATE, "3A",
            train="12951 Mumbai Rajdhani", passengers=["Asha Rao", "Ravi Rao"],
        )

        print("=" * 68)
        print("JOURNEY")
        print(describe_journey(journey))

        print("\nTATKAL WINDOW")
        window = tatkal_window(JOURNEY_DATE, "3A")
        print(window.describe())

        print("\nREMINDER PLAN")
        for reminder in reminder_plan(window):
            print("  " + reminder.describe())

        print("\nREADINESS CHECKLIST")
        _, items = speed_checklist(store, journey, now=NOW)
        for item in items:
            print("  " + item.render())

        print("\nDUE IN THE NEXT 3 HOURS (as of 08:00 IST)")
        for tracked, reminder in upcoming(store, now=NOW, within_minutes=180):
            print(f"  {tracked['from']}->{tracked['to']}  {reminder.describe()}")

        print("\nCO-PILOT SCRIPT (dry run)")
        for step in build_script(journey):
            print("  " + step.describe())

        print("\nPNR TRACKING (offline demo provider)")
        print(DemoPNRProvider().fetch("2718281828").summary())
        print("=" * 68)


if __name__ == "__main__":
    main()
