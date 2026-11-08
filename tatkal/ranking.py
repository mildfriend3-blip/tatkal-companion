"""Rank candidate trains for a saved journey using user-supplied official results.

This module is deliberately offline: it does not scrape IRCTC/RailOne or claim
that candidate availability is live. Candidates should be copied/exported by
the user from an authorised source and saved as a JSON array.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

AVAILABILITY_ORDER = {
    "AVAILABLE": 0,
    "CONFIRMED": 0,
    "RAC": 1,
    "WAITLIST": 2,
    "WL": 2,
    "REGRET": 3,
    "NOT AVAILABLE": 3,
    "CLOSED": 3,
    "UNKNOWN": 4,
}


def load_candidates(path: str | Path) -> list[dict[str, Any]]:
    """Load and validate a JSON array of candidate train records."""
    try:
        data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read candidate JSON: {exc}") from exc
    if not isinstance(data, list):
        raise ValueError("candidate file must contain a JSON array")
    if not data:
        raise ValueError("candidate file contains no trains")
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"candidate #{index} must be a JSON object")
        for field in ("train_number", "train_name", "from", "to", "travel_class"):
            if not str(item.get(field, "")).strip():
                raise ValueError(f"candidate #{index} is missing {field}")
        item["from"] = str(item["from"]).strip().upper()
        item["to"] = str(item["to"]).strip().upper()
        item["travel_class"] = str(item["travel_class"]).strip().upper()
        item["availability"] = str(item.get("availability", "UNKNOWN")).strip().upper()
        try:
            item["duration_minutes"] = int(item["duration_minutes"])
            item["fare"] = float(item["fare"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"candidate #{index} needs numeric duration_minutes and fare"
            ) from exc
        if item["duration_minutes"] <= 0 or item["fare"] < 0:
            raise ValueError(f"candidate #{index} has invalid duration or fare")
    return data


def rank_candidates(
    journey: dict[str, Any],
    candidates: list[dict[str, Any]],
    max_fare: float | None = None,
) -> list[dict[str, Any]]:
    """Filter to the saved journey and rank by availability, budget, time, fare."""
    route = (journey["from"].upper(), journey["to"].upper())
    travel_class = journey["travel_class"].upper()
    matching = [
        dict(item) for item in candidates
        if (item["from"].upper(), item["to"].upper()) == route
        and item["travel_class"].upper() == travel_class
    ]
    if not matching:
        raise ValueError(
            f"no candidates match {route[0]}->{route[1]} in {travel_class}"
        )

    def key(item: dict[str, Any]) -> tuple:
        status = item.get("availability", "UNKNOWN").upper()
        availability_rank = AVAILABILITY_ORDER.get(status, 4)
        over_budget = max_fare is not None and item["fare"] > max_fare
        return (
            availability_rank,
            1 if over_budget else 0,
            item["duration_minutes"],
            item["fare"],
            str(item["departure"] if item.get("departure") else "99:99"),
            str(item["train_number"]),
        )

    matching.sort(key=key)
    for index, item in enumerate(matching, start=1):
        item["rank"] = index
        item["over_budget"] = max_fare is not None and item["fare"] > max_fare
    return matching
