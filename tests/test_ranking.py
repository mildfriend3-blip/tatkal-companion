"""Tests for offline train candidate ranking."""
import json
import tempfile
import unittest
from pathlib import Path

from tatkal.ranking import load_candidates, rank_candidates


JOURNEY = {"from": "NDLS", "to": "BCT", "travel_class": "3A"}


class RankingTests(unittest.TestCase):
    def setUp(self):
        self.candidates = [
            {"train_number": "2", "train_name": "Slower available",
             "from": "NDLS", "to": "BCT", "travel_class": "3A",
             "availability": "AVAILABLE", "duration_minutes": 900, "fare": 2000},
            {"train_number": "1", "train_name": "Fast waitlist",
             "from": "NDLS", "to": "BCT", "travel_class": "3A",
             "availability": "WAITLIST", "duration_minutes": 500, "fare": 1500},
            {"train_number": "3", "train_name": "Other route",
             "from": "BOM", "to": "BCT", "travel_class": "3A",
             "availability": "AVAILABLE", "duration_minutes": 100, "fare": 1000},
        ]

    def test_availability_precedes_speed_and_fare(self):
        ranked = rank_candidates(JOURNEY, self.candidates)
        self.assertEqual([item["train_number"] for item in ranked], ["2", "1"])
        self.assertEqual([item["rank"] for item in ranked], [1, 2])

    def test_budget_flag_does_not_hide_train(self):
        ranked = rank_candidates(JOURNEY, self.candidates, max_fare=1800)
        self.assertTrue(ranked[0]["over_budget"])

    def test_no_matching_route_raises(self):
        with self.assertRaisesRegex(ValueError, "no candidates match"):
            rank_candidates({"from": "JAT", "to": "SVDK", "travel_class": "SL"}, self.candidates)

    def test_load_candidates_validates_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidates.json"
            path.write_text(json.dumps(self.candidates), encoding="utf-8")
            loaded = load_candidates(path)
            self.assertEqual(loaded[0]["from"], "NDLS")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "JSON array"):
                load_candidates(path)


if __name__ == "__main__":
    unittest.main()
