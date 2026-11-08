import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

import contextlib
import io

from tatkal.assistant import speed_checklist, upcoming
from tatkal.cli import _flatten_names, _parse_age, main
from tatkal.cli import build_parser
from tatkal.copilot import (
    TARGET_TOTAL_SECONDS,
    alert_schedule,
    open_official_site,
    build_script,
    countdown_text,
    notify,
    pacing_report,
    pre_window_alerts,
    verdict,
)
from tatkal.models import IST, Passenger, class_group
from tatkal.pnr import DemoPNRProvider
from tatkal.schedule import reminder_plan, tatkal_window
from tatkal.store import Store


class ScheduleTests(unittest.TestCase):
    def test_ac_opens_at_10am_the_day_before(self):
        window = tatkal_window(date(2026, 11, 9), "3A")
        self.assertEqual(window.group, "AC")
        self.assertEqual(window.opens_at, datetime(2026, 11, 8, 10, 0, tzinfo=IST))

    def test_non_ac_opens_at_11am(self):
        window = tatkal_window(date(2026, 11, 9), "SL")
        self.assertEqual(window.group, "NON_AC")
        self.assertEqual(window.opens_at, datetime(2026, 11, 8, 11, 0, tzinfo=IST))

    def test_class_codes_are_case_insensitive(self):
        self.assertEqual(class_group("3a"), "AC")
        self.assertEqual(class_group("2s"), "NON_AC")

    def test_unknown_class_rejected(self):
        with self.assertRaises(ValueError):
            class_group("XX")

    def test_reminders_are_chronological_and_end_at_open(self):
        window = tatkal_window(date(2026, 11, 9), "3A")
        plan = reminder_plan(window)
        times = [r.at for r in plan]
        self.assertEqual(times, sorted(times))
        self.assertEqual(times[-1], window.opens_at)
        self.assertEqual(plan[-1].offset_minutes, 0)
        self.assertEqual(len(plan), len({r.offset_minutes for r in plan}))


class PassengerTests(unittest.TestCase):
    def test_bad_age_rejected(self):
        with self.assertRaises(ValueError):
            Passenger("Asha Rao", 0, "F")

    def test_bad_gender_rejected(self):
        with self.assertRaises(ValueError):
            Passenger("Asha Rao", 30, "X")

    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            Passenger("   ", 30, "F")


class StoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "t.json"
        self.store = Store(self.path)

    def tearDown(self):
        self._tmp.cleanup()

    def test_passenger_roundtrip(self):
        self.store.add_passenger(Passenger("Asha Rao", 34, "F", "LOWER"))
        reopened = Store(self.path)
        self.assertEqual(reopened.passenger_names(), ["Asha Rao"])
        self.assertEqual(reopened.passengers()[0]["berth_preference"], "LOWER")

    def test_duplicate_passenger_rejected_case_insensitively(self):
        self.store.add_passenger(Passenger("Asha Rao", 34, "F"))
        with self.assertRaises(ValueError):
            self.store.add_passenger(Passenger("asha rao", 30, "F"))

    def test_same_station_rejected(self):
        with self.assertRaises(ValueError):
            self.store.add_journey("NDLS", "NDLS", date(2026, 11, 9), "3A")

    def test_journey_normalises_station_and_class(self):
        journey = self.store.add_journey(
            "ndls", "bct", date(2026, 11, 9), "3a", passengers=["Asha Rao"]
        )
        self.assertEqual(journey["from"], "NDLS")
        self.assertEqual(journey["to"], "BCT")
        self.assertEqual(journey["travel_class"], "3A")
        self.assertEqual(self.store.journey(journey["id"])["passengers"], ["Asha Rao"])

    def test_unknown_journey_id(self):
        with self.assertRaises(KeyError):
            self.store.journey("nope")


class PNRTests(unittest.TestCase):
    def test_demo_provider_is_deterministic(self):
        provider = DemoPNRProvider()
        first = provider.fetch("1234567890")
        second = provider.fetch("1234567890")
        self.assertEqual(first, second)
        self.assertTrue(1 <= len(first.passengers) <= 4)

    def test_summary_mentions_train_and_pnr(self):
        summary = DemoPNRProvider().fetch("1234567890").summary()
        self.assertIn("1234567890", summary)
        self.assertIn("platform", summary)

    def test_short_pnr_rejected(self):
        with self.assertRaises(ValueError):
            DemoPNRProvider().fetch("123")


class AssistantTests(unittest.TestCase):
    def test_checklist_flags_a_passenger_missing_from_master_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "t.json")
            store.add_passenger(Passenger("Asha Rao", 34, "F"))
            journey = store.add_journey(
                "NDLS", "BCT", date(2026, 11, 9), "3A",
                passengers=["Asha Rao", "Ravi Rao"],
            )
            window, items = speed_checklist(
                store, journey, now=datetime(2026, 11, 8, 9, 0, tzinfo=IST)
            )
            self.assertEqual(window.opens_at.hour, 10)
            self.assertFalse(items[0].done)
            self.assertIn("Ravi Rao", items[0].note)

    def test_checklist_clear_when_everyone_is_saved(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "t.json")
            store.add_passenger(Passenger("Asha Rao", 34, "F"))
            journey = store.add_journey(
                "NDLS", "BCT", date(2026, 11, 9), "3A", passengers=["Asha Rao"]
            )
            _, items = speed_checklist(store, journey, now=datetime(2026, 11, 8, 9, 0, tzinfo=IST))
            self.assertTrue(items[0].done)
            self.assertFalse(any(item.done is False for item in items))

    def test_upcoming_stays_inside_the_horizon(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "t.json")
            store.add_journey("NDLS", "BCT", date(2026, 11, 9), "3A")
            now = datetime(2026, 11, 8, 8, 30, tzinfo=IST)
            pairs = upcoming(store, now=now, within_minutes=180)
            self.assertTrue(pairs)
            horizon = now + timedelta(minutes=180)
            for _, reminder in pairs:
                self.assertGreaterEqual(reminder.at, now)
                self.assertLessEqual(reminder.at, horizon)

    def test_upcoming_empty_when_window_is_far_away(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "t.json")
            store.add_journey("NDLS", "BCT", date(2026, 11, 9), "3A")
            now = datetime(2026, 11, 1, 8, 0, tzinfo=IST)
            self.assertEqual(upcoming(store, now=now, within_minutes=180), [])


class CopilotTests(unittest.TestCase):
    def _journey(self, payment_class="3A"):
        return {
            "id": "abcd1234",
            "from": "NDLS",
            "to": "BCT",
            "journey_date": "2026-11-09",
            "travel_class": payment_class,
            "class_group": "AC",
            "train": "12951 Mumbai Rajdhani",
            "passengers": ["Asha Rao", "Ravi Rao"],
        }

    def test_script_starts_at_zero_and_is_ordered(self):
        script = build_script(self._journey())
        self.assertEqual(script[0].offset_seconds, 0)
        offsets = [s.offset_seconds for s in script]
        self.assertEqual(offsets, sorted(offsets))
        self.assertEqual(offsets[-1], TARGET_TOTAL_SECONDS)

    def test_script_mentions_the_route_and_passenger_count(self):
        script = build_script(self._journey())
        text = " ".join(s.action + " " + s.detail for s in script)
        self.assertIn("NDLS -> BCT", text)
        self.assertIn("2 saved", text)

    def test_wallet_and_upi_scripts_differ(self):
        wallet = build_script(self._journey(), "WALLET")
        upi = build_script(self._journey(), "UPI")
        self.assertIn("IRCTC Wallet", " ".join(s.action for s in wallet))
        self.assertIn("UPI PIN", " ".join(s.action for s in upi))

    def test_bad_payment_mode_rejected(self):
        with self.assertRaises(ValueError):
            build_script(self._journey(), "CARD")

    def test_pacing_report_measures_slip(self):
        script = build_script(self._journey())
        elapsed = [float(s.offset_seconds) for s in script]
        report = pacing_report(elapsed, script)
        self.assertEqual(len(report), len(script))
        for _, _, slip in report:
            self.assertAlmostEqual(slip, 0.0)

    def test_pacing_report_flags_a_slow_run(self):
        script = build_script(self._journey())
        elapsed = [float(s.offset_seconds) + 5 for s in script]
        report = pacing_report(elapsed, script)
        self.assertTrue(all(slip > 3 for _, _, slip in report))
        self.assertIn("behind", verdict(report[0][2]))

    def test_pacing_report_rejects_short_timings(self):
        script = build_script(self._journey())
        with self.assertRaises(ValueError):
            pacing_report([1.0], script)

    def test_verdict_bands(self):
        self.assertEqual(verdict(-2), "ahead")
        self.assertEqual(verdict(0), "on time")
        self.assertIn("behind", verdict(9))

    def test_countdown_text(self):
        target = datetime(2026, 11, 8, 10, 0, tzinfo=IST)
        self.assertEqual(
            countdown_text(target, datetime(2026, 11, 8, 9, 58, 30, tzinfo=IST)),
            "01m 30s",
        )
        self.assertEqual(
            countdown_text(target, datetime(2026, 11, 8, 8, 0, tzinfo=IST)),
            "2h 00m 00s",
        )
        self.assertEqual(
            countdown_text(target, datetime(2026, 11, 8, 10, 0, tzinfo=IST)), "OPEN"
        )

    def test_pre_window_alerts_count_down(self):
        alerts = pre_window_alerts(datetime(2026, 11, 8, 10, 0, tzinfo=IST))
        leads = [lead for lead, _ in alerts]
        self.assertEqual(leads, sorted(leads, reverse=True))
        self.assertEqual(leads[-1], timedelta(0))


class CliQuotingTests(unittest.TestCase):
    """Names with spaces are the most common first-run mistake."""

    def test_flatten_names_joins_an_unquoted_multiword_name(self):
        self.assertEqual(_flatten_names([["LOKESH", "BHAVSAR"]]), ["LOKESH BHAVSAR"])

    def test_flatten_names_handles_several_passengers(self):
        groups = [["LOKESH", "BHAVSAR"], ["ASHA", "RAO"]]
        self.assertEqual(_flatten_names(groups), ["LOKESH BHAVSAR", "ASHA RAO"])

    def test_flatten_names_ignores_empty_input(self):
        self.assertEqual(_flatten_names(None), [])
        self.assertEqual(_flatten_names([]), [])

    def test_parse_age_rejects_words_and_mentions_quoting(self):
        with self.assertRaises(Exception) as ctx:
            _parse_age("BHAVSAR")
        self.assertIn("quoted", str(ctx.exception))

    def test_parse_age_accepts_a_number(self):
        self.assertEqual(_parse_age("18"), 18)

    def test_cli_saves_a_multiword_name_and_reuses_it_unquoted(self):
        with tempfile.TemporaryDirectory() as tmp:
            store_path = str(Path(tmp) / "t.json")
            quiet = contextlib.redirect_stdout(io.StringIO())
            with quiet:
                self.assertEqual(
                    main(["--store", store_path, "add-passenger", "LOKESH BHAVSAR", "18", "M",
                          "--berth", "SIDE LOWER"]), 0,
                )
                self.assertEqual(
                    main(["--store", store_path, "add-journey", "--from", "BRC", "--to", "JAT",
                          "--date", "2026-11-15", "--class", "3A",
                          "--passenger", "LOKESH", "BHAVSAR"]), 0,
                )
            self.assertEqual(Store(store_path).journeys()[0]["passengers"], ["LOKESH BHAVSAR"])

    def test_cli_hints_about_quoting_when_the_age_slot_gets_a_name(self):
        err = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            with contextlib.redirect_stderr(err), self.assertRaises(SystemExit):
                main(["--store", str(Path(tmp) / "t.json"), "add-passenger",
                      "LOKESH", "BHAVSAR", "M"])
        self.assertIn("quoted", err.getvalue())

    def test_cli_warns_when_a_journey_names_an_unsaved_passenger(self):
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            store_path = str(Path(tmp) / "t.json")
            with contextlib.redirect_stdout(out):
                main(["--store", store_path, "add-journey", "--from", "BRC", "--to", "JAT",
                      "--date", "2026-11-15", "--class", "3A",
                      "--passenger", "NOBODY SAVED"])
        self.assertIn("not in your master list", out.getvalue())


class OneCommandTests(unittest.TestCase):
    """`tatkal go` is the single command most people will run."""

    def test_alert_schedule_is_sorted_and_ends_at_the_window(self):
        opens = datetime(2026, 11, 14, 10, 0, tzinfo=IST)
        schedule = alert_schedule(opens)
        times = [at for at, _ in schedule]
        self.assertEqual(times, sorted(times))
        self.assertEqual(times[-1], opens)
        self.assertEqual(len(schedule), 3)

    def test_open_official_site_never_raises(self):
        self.assertIsInstance(open_official_site(), bool)

    def test_notify_never_raises(self):
        self.assertIsInstance(notify("test", "test"), bool)

    def test_go_command_is_registered_with_its_flags(self):
        args = build_parser().parse_args(
            ["go", "abc12345", "--payment", "upi", "--open", "--no-wait"]
        )
        self.assertEqual(args.command, "go")
        self.assertEqual(args.payment, "upi")
        self.assertTrue(args.open)
        self.assertTrue(args.no_wait)


if __name__ == "__main__":
    unittest.main()
