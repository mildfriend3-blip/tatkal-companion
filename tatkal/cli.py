"""Command line interface for the Tatkal Travel Companion."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date, datetime

from .assistant import describe_journey, speed_checklist, upcoming
from .copilot import (
    TARGET_TOTAL_SECONDS,
    alert_schedule,
    build_script,
    countdown_text,
    notify,
    open_official_site,
    pacing_report,
    verdict,
    wait_until,
)
from .models import IST, Passenger
from .pnr import DemoPNRProvider
from .schedule import reminder_plan, tatkal_window
from .store import Store


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"expected a date like 2026-11-09, got {value!r}"
        ) from exc


QUOTING_HINT = (
    'hint: a name with a space must be quoted, e.g. '
    'tatkal add-passenger "LOKESH BHAVSAR" 18 M'
)


def _parse_age(value: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"expected a number, got {value!r}. A name with a space must be quoted: "
            'tatkal add-passenger "LOKESH BHAVSAR" 18 M'
        ) from exc


def _flatten_names(groups: list[list[str]] | None) -> list[str]:
    """`--passenger LOKESH BHAVSAR` (unquoted) becomes one name, not two."""
    names = []
    for group in groups or []:
        name = " ".join(part for part in group if part).strip()
        if name:
            names.append(name)
    return names


class _Parser(argparse.ArgumentParser):
    """Adds a quoting hint to the errors that quoting mistakes cause."""

    def error(self, message: str) -> None:
        if "invalid int value" in message or "unrecognized arguments" in message:
            print(QUOTING_HINT, file=sys.stderr)
        super().error(message)


def _pace_through(script) -> list[float] | None:
    """Walk the steps, timing each one. Returns None if the user stops."""
    print("\nGO. Press Enter after each step.\n")
    started = time.monotonic()
    timings: list[float] = []
    for step in script:
        print("  " + step.describe())
        try:
            input("     press Enter when done > ")
        except (EOFError, KeyboardInterrupt):
            print("\nstopped")
            return None
        done = time.monotonic() - started
        timings.append(done)
        print(f"     {done:5.1f}s  {verdict(done - step.offset_seconds)}\n")
    return timings


def _wait_with_alerts(window, now: datetime, open_site: bool) -> None:
    """Count down to the window, firing the T-10 / T-2 / T-0 nudges on the way."""
    alerts = alert_schedule(window.opens_at)
    pending = [(at, message) for at, message in alerts if at > now]
    print("\nwaiting for the window. Ctrl-C to stop.")
    while True:
        now = datetime.now(IST)
        if now >= window.opens_at:
            return
        while pending and now >= pending[0][0]:
            _, message = pending.pop(0)
            print(f"\n  ALERT: {message}")
            notify("Tatkal companion", message)
            if open_site and "OPEN" in message:
                if open_official_site():
                    print("  opened the official IRCTC page in your browser")
                else:
                    print("  could not open a browser here - open the IRCTC app yourself")
        print(f"\r  window opens in {countdown_text(window.opens_at, now)}  ", end="", flush=True)
        time.sleep(0.5)


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="tatkal",
        description="Tatkal Travel Companion: timings, reminders, readiness and PNR tracking.",
    )
    parser.add_argument("--store", default="data/tatkal.json", help="path to the JSON store")
    sub = parser.add_subparsers(dest="command", required=True)

    add_pax = sub.add_parser("add-passenger", help="save a passenger to the master list")
    add_pax.add_argument("name")
    add_pax.add_argument("age", type=_parse_age)
    add_pax.add_argument("gender", choices=["M", "F", "O"])
    add_pax.add_argument("--berth", default="NO PREFERENCE")
    add_pax.add_argument("--id-type", default="AADHAAR")

    sub.add_parser("passengers", help="list saved passengers")

    add_journey = sub.add_parser("add-journey", help="track a journey")
    add_journey.add_argument("--from", dest="origin", required=True)
    add_journey.add_argument("--to", dest="destination", required=True)
    add_journey.add_argument("--date", dest="journey_date", type=_parse_date, required=True)
    add_journey.add_argument("--class", dest="travel_class", required=True)
    add_journey.add_argument("--train")
    add_journey.add_argument(
        "--passenger", action="append", nargs="+", default=[], metavar="NAME",
        help="repeatable; multi-word names work unquoted",
    )

    sub.add_parser("journeys", help="list tracked journeys")

    window = sub.add_parser("window", help="when does tatkal open for a date and class")
    window.add_argument("--date", dest="journey_date", type=_parse_date, required=True)
    window.add_argument("--class", dest="travel_class", required=True)

    plan = sub.add_parser("plan", help="reminder plan for a tracked journey")
    plan.add_argument("journey_id")

    checklist = sub.add_parser("checklist", help="readiness checklist for a tracked journey")
    checklist.add_argument("journey_id")

    up = sub.add_parser("upcoming", help="reminders due in the next N minutes")
    up.add_argument("--within", type=int, default=180)

    track = sub.add_parser("track", help="PNR status (demo provider, offline data)")
    track.add_argument("pnr")

    go = sub.add_parser("go", help="one command: check, wait, alert, then pace the window")
    go.add_argument("journey_id")
    go.add_argument("--payment", choices=["wallet", "upi"], default="wallet")
    go.add_argument("--open", action="store_true", help="open the official IRCTC page at T-0")
    go.add_argument("--now", help="rehearse against a fixed time")
    go.add_argument("--no-wait", action="store_true", help="do not count down, start the steps now")

    copilot = sub.add_parser("copilot", help="pace yourself through the booking window")
    copilot.add_argument("journey_id")
    copilot.add_argument("--payment", choices=["wallet", "upi"], default="wallet")
    copilot.add_argument("--dry-run", action="store_true", help="print the script, do not time it")
    copilot.add_argument("--now", help="rehearse against a fixed time, e.g. 2026-11-08T09:55:00")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = Store(args.store)

    if args.command == "add-passenger":
        try:
            record = store.add_passenger(
                Passenger(
                    name=args.name,
                    age=args.age,
                    gender=args.gender,
                    berth_preference=args.berth,
                    id_type=args.id_type,
                )
            )
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(f"saved passenger {record['name']} ({record['age']}{record['gender']})")

    elif args.command == "passengers":
        names = store.passengers()
        if not names:
            print("no passengers saved yet")
        for pax in names:
            print(f"  {pax['name']:<24} {pax['age']:>3}{pax['gender']}  {pax['berth_preference']}")

    elif args.command == "add-journey":
        try:
            journey = store.add_journey(
                from_station=args.origin,
                to_station=args.destination,
                journey_date=args.journey_date,
                travel_class=args.travel_class,
                train=args.train,
                passengers=_flatten_names(args.passenger),
            )
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(describe_journey(journey))
        known = {name.lower() for name in store.passenger_names()}
        unknown = [n for n in journey["passengers"] if n.lower() not in known]
        if unknown:
            print(f"\nnote: not in your master list yet: {', '.join(unknown)}")
            print(f'      save with: tatkal add-passenger "{unknown[0]}" <age> <M|F|O>')

    elif args.command == "journeys":
        journeys = store.journeys()
        if not journeys:
            print("no journeys tracked yet")
        for journey in journeys:
            print(describe_journey(journey))

    elif args.command == "window":
        try:
            win = tatkal_window(args.journey_date, args.travel_class)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(win.describe())
        for reminder in reminder_plan(win):
            print(f"  {reminder.describe()}")

    elif args.command == "plan":
        try:
            journey = store.journey(args.journey_id)
        except KeyError as exc:
            print(f"error: {exc.args[0]}", file=sys.stderr)
            return 2
        win = tatkal_window(
            date.fromisoformat(journey["journey_date"]), journey["travel_class"]
        )
        print(win.describe())
        for reminder in reminder_plan(win):
            print(f"  {reminder.describe()}")

    elif args.command == "checklist":
        try:
            journey = store.journey(args.journey_id)
        except KeyError as exc:
            print(f"error: {exc.args[0]}", file=sys.stderr)
            return 2
        win, items = speed_checklist(store, journey, now=datetime.now(IST))
        print(win.describe())
        for item in items:
            print(f"  {item.render()}")
        open_items = sum(1 for item in items if item.done is False)
        print(f"\n{open_items} item(s) still open" if open_items else "\nall checkable items clear")

    elif args.command == "upcoming":
        pairs = upcoming(store, within_minutes=args.within)
        if not pairs:
            print(f"nothing due in the next {args.within} minutes")
        for journey, reminder in pairs:
            print(f"{journey['from']}->{journey['to']} {journey['journey_date']}  {reminder.describe()}")

    elif args.command == "track":
        try:
            print(DemoPNRProvider().fetch(args.pnr).summary())
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print("\n(demo data - offline sample, not a live railway lookup)")

    elif args.command == "go":
        try:
            journey = store.journey(args.journey_id)
        except KeyError as exc:
            print(f"error: {exc.args[0]}", file=sys.stderr)
            return 2
        window = tatkal_window(
            date.fromisoformat(journey["journey_date"]), journey["travel_class"]
        )
        script = build_script(journey, args.payment.upper())
        now = datetime.now(IST)
        if args.now:
            parsed = datetime.fromisoformat(args.now)
            now = parsed if parsed.tzinfo else parsed.replace(tzinfo=IST)

        print(describe_journey(journey))
        print(f"\n{window.describe()}")

        _, items = speed_checklist(store, journey, now=now)
        open_items = [item for item in items if item.done is False]
        confirm_items = [item for item in items if item.done is None]
        if open_items:
            print("\nstill open:")
            for item in open_items:
                print(f"  {item.render()}")
        print(
            f"\n{len(confirm_items)} thing(s) only you can confirm: "
            + ", ".join(item.label.split(",")[0] for item in confirm_items)
        )

        if not args.no_wait and now < window.opens_at:
            try:
                _wait_with_alerts(window, now, args.open)
            except KeyboardInterrupt:
                print("\nstopped")
                return 1
        elif now >= window.opens_at:
            print("\nwindow already open - starting now")
            if args.open:
                open_official_site()

        notify("Tatkal companion", "window is open, start now")
        timings = _pace_through(script)
        if timings is None:
            return 1
        print("SUMMARY")
        for step, duration, slip in pacing_report(timings, script):
            print(f"  T+{step.offset_seconds:>2}s  took {duration:5.1f}s  {verdict(slip)}")
        print(f"\ntotal {timings[-1]:.1f}s against a {TARGET_TOTAL_SECONDS}s target")

    elif args.command == "copilot":
        try:
            journey = store.journey(args.journey_id)
        except KeyError as exc:
            print(f"error: {exc.args[0]}", file=sys.stderr)
            return 2
        window = tatkal_window(
            date.fromisoformat(journey["journey_date"]), journey["travel_class"]
        )
        script = build_script(journey, args.payment.upper())
        now = datetime.now(IST)
        if args.now:
            parsed = datetime.fromisoformat(args.now)
            now = parsed if parsed.tzinfo else parsed.replace(tzinfo=IST)

        print(describe_journey(journey))
        print(f"\n{window.describe()}")

        if args.dry_run:
            print("\nSCRIPT (dry run, nothing is timed)")
            for step in script:
                print("  " + step.describe())
            print(f"\ntarget: payment confirmed by T+{TARGET_TOTAL_SECONDS}s")
            return 0

        if now < window.opens_at:
            print("\nwaiting for the window. Ctrl-C to stop.")
            notify("Tatkal companion", f"window opens in {countdown_text(window.opens_at, now)}")
            try:
                wait_until(window.opens_at)
            except KeyboardInterrupt:
                print("\nstopped")
                return 1
        else:
            print("\nwindow already open - starting now")

        notify("Tatkal companion", "window is open, start the script")
        timings = _pace_through(script)
        if timings is None:
            return 1

        print("SUMMARY")
        for step, duration, slip in pacing_report(timings, script):
            print(f"  T+{step.offset_seconds:>2}s  took {duration:5.1f}s  {verdict(slip)}")
        print(f"\ntotal {timings[-1]:.1f}s against a {TARGET_TOTAL_SECONDS}s target")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
