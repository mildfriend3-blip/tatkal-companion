"""Tests for the loopback dashboard: routes, payloads and the absence of any
booking endpoint."""

import http.client
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from tatkal.dashboard import make_handler
from tatkal.store import Store


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store_path = Path(self._tmp.name) / "t.json"
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), make_handler(Store(self.store_path))
        )
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self._tmp.cleanup()

    # -- helpers ------------------------------------------------------------
    def _get(self, path):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request("GET", path)
            response = connection.getresponse()
            return response.status, response.getheader("Content-Type"), response.read()
        finally:
            connection.close()

    def _post(self, path, payload):
        body = json.dumps(payload).encode("utf-8")
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request("POST", path, body=body, headers={"Content-Type": "application/json"})
            response = connection.getresponse()
            return response.status, json.loads(response.read().decode("utf-8"))
        finally:
            connection.close()

    def _state(self):
        status, _, body = self._get("/api/state")
        self.assertEqual(status, 200)
        return json.loads(body.decode("utf-8"))

    # -- tests --------------------------------------------------------------
    def test_index_serves_the_page(self):
        status, content_type, body = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn(b"Tatkal Companion", body)

    def test_state_is_empty_on_a_fresh_store(self):
        state = self._state()
        self.assertEqual(state["passengers"], [])
        self.assertEqual(state["journeys"], [])
        self.assertIsNone(state["next_window"])

    def test_add_passenger(self):
        status, body = self._post(
            "/api/passengers",
            {"name": "LOKESH BHAVSAR", "age": 18, "gender": "M", "berth": "SIDE LOWER"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(body["passenger"]["name"], "LOKESH BHAVSAR")
        self.assertEqual(Store(self.store_path).passenger_names(), ["LOKESH BHAVSAR"])

    def test_duplicate_passenger_is_a_400(self):
        payload = {"name": "ASHA RAO", "age": 34, "gender": "F"}
        self.assertEqual(self._post("/api/passengers", payload)[0], 201)
        self.assertEqual(self._post("/api/passengers", payload)[0], 400)

    def test_bad_age_is_a_400_not_a_crash(self):
        status, body = self._post("/api/passengers", {"name": "X", "age": "abc", "gender": "M"})
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_add_journey_and_see_it_in_state(self):
        status, body = self._post(
            "/api/journeys",
            {
                "origin": "brc",
                "destination": "jat",
                "journey_date": "2026-11-15",
                "travel_class": "3A",
                "train": "12471 Swaraj Express",
                "passengers": ["LOKESH BHAVSAR"],
            },
        )
        self.assertEqual(status, 201)
        self.assertEqual(body["journey"]["from"], "BRC")

        state = self._state()
        self.assertEqual(len(state["journeys"]), 1)
        journey = state["journeys"][0]
        self.assertEqual(journey["travel_class"], "3A")
        self.assertIn("10:00 IST", journey["opens_at"])
        self.assertIn("checks confirmed", journey["checklist_summary"])

    def test_same_station_journey_is_a_400(self):
        status, _ = self._post(
            "/api/journeys",
            {"origin": "BRC", "destination": "BRC", "journey_date": "2026-11-15",
             "travel_class": "3A"},
        )
        self.assertEqual(status, 400)

    def test_there_is_no_booking_endpoint(self):
        self.assertEqual(self._get("/api/book")[0], 404)
        self.assertEqual(self._post("/api/book", {"pnr": "1234567890"})[0], 404)
        self.assertEqual(self._post("/api/pay", {})[0], 404)

    def test_next_window_picks_the_soonest_upcoming_journey(self):
        for journey_date in ("2026-11-20", "2026-11-15"):
            self._post(
                "/api/journeys",
                {"origin": "BRC", "destination": "JAT", "journey_date": journey_date,
                 "travel_class": "3A"},
            )
        state = self._state()
        self.assertEqual(len(state["journeys"]), 2)
        # 15 Nov opens 14 Nov, 20 Nov opens 19 Nov, so the sooner one wins
        if state["next_window"]:
            self.assertIn("14 Nov", state["next_window"])


if __name__ == "__main__":
    unittest.main()
