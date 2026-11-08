"""Local JSON persistence for passengers and journeys."""

from __future__ import annotations

import json
import uuid
from datetime import date
from pathlib import Path

from .models import Passenger, class_group


class Store:
    """A small JSON store. Nothing leaves the machine."""

    def __init__(self, path: str | Path = "data/tatkal.json") -> None:
        self.path = Path(path)
        self._data: dict = {"passengers": [], "journeys": []}
        if self.path.exists():
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            self._data["passengers"] = loaded.get("passengers", [])
            self._data["journeys"] = loaded.get("journeys", [])

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # -- passengers ---------------------------------------------------------
    def add_passenger(self, passenger: Passenger) -> dict:
        record = passenger.as_dict()
        for existing in self._data["passengers"]:
            if existing["name"].lower() == record["name"].lower():
                raise ValueError(f"passenger {record['name']!r} is already saved")
        self._data["passengers"].append(record)
        self.save()
        return record

    def passengers(self) -> list[dict]:
        return list(self._data["passengers"])

    def passenger_names(self) -> list[str]:
        return [p["name"] for p in self._data["passengers"]]

    # -- journeys -----------------------------------------------------------
    def add_journey(
        self,
        from_station: str,
        to_station: str,
        journey_date: date,
        travel_class: str,
        train: str | None = None,
        passengers: list[str] | None = None,
    ) -> dict:
        origin = from_station.strip().upper()
        destination = to_station.strip().upper()
        if not origin or not destination:
            raise ValueError("both stations are required")
        if origin == destination:
            raise ValueError("from and to stations must differ")
        group = class_group(travel_class)
        record = {
            "id": uuid.uuid4().hex[:8],
            "from": origin,
            "to": destination,
            "journey_date": journey_date.isoformat(),
            "travel_class": travel_class.strip().upper(),
            "class_group": group,
            "train": train,
            "passengers": list(passengers or []),
        }
        self._data["journeys"].append(record)
        self.save()
        return record

    def update_journey(
        self,
        journey_id: str,
        *,
        travel_class: str | None = None,
        train: str | None = None,
    ) -> dict:
        """Update the selected train and/or class for a saved journey."""
        journey = self.journey(journey_id)
        if travel_class is not None:
            journey["travel_class"] = travel_class.strip().upper()
            journey["class_group"] = class_group(journey["travel_class"])
        if train is not None:
            journey["train"] = train.strip() or None
        self.save()
        return dict(journey)

    def journeys(self) -> list[dict]:
        return list(self._data["journeys"])

    def journey(self, journey_id: str) -> dict:
        for journey in self._data["journeys"]:
            if journey["id"] == journey_id:
                return journey
        raise KeyError(f"no journey with id {journey_id!r}")
