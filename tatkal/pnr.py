"""PNR status lookups behind a small provider interface.

`DemoPNRProvider` is offline and deterministic -- it exists so the project can be
demoed and tested without any network call. It is NOT real railway data.
Wire a permitted data source into `OfficialAPIProvider` to go live.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Protocol

_TRAINS = (
    ("12951", "Mumbai Rajdhani Express"),
    ("12301", "Howrah Rajdhani Express"),
    ("12627", "Karnataka Express"),
    ("12002", "Bhopal Shatabdi"),
    ("12841", "Coromandel Express"),
    ("12621", "Tamil Nadu Express"),
)

_STATUSES = ("CNF", "CNF", "CNF", "RAC", "WL")


@dataclass(frozen=True)
class PNRStatus:
    pnr: str
    train_number: str
    train_name: str
    chart_prepared: bool
    platform: str
    delay_minutes: int
    passengers: tuple[dict, ...]

    def summary(self) -> str:
        lines = [
            f"PNR {self.pnr}  |  {self.train_number} {self.train_name}",
            f"chart prepared: {'yes' if self.chart_prepared else 'no'}  |  "
            f"platform {self.platform}  |  running {self.delay_minutes} min late",
        ]
        for pax in self.passengers:
            lines.append(
                f"  passenger {pax['index']}: {pax['status']:<4} berth {pax['berth']}"
            )
        return "\n".join(lines)


class PNRProvider(Protocol):
    def fetch(self, pnr: str) -> PNRStatus: ...


class DemoPNRProvider:
    """Deterministic offline provider for demos and tests. Never real data."""

    def fetch(self, pnr: str) -> PNRStatus:
        code = pnr.strip()
        if not (code.isdigit() and len(code) == 10):
            raise ValueError("a PNR is 10 digits")
        seed = int(code)
        number, name = _TRAINS[seed % len(_TRAINS)]
        count = 1 + (seed % 4)
        passengers = []
        for i in range(count):
            status = _STATUSES[(seed // (i + 1)) % len(_STATUSES)]
            berth = (
                f"S{1 + (seed + i) % 12}/{1 + (seed * 3 + i) % 60}"
                if status == "CNF"
                else "-"
            )
            passengers.append({"index": i + 1, "status": status, "berth": berth})
        return PNRStatus(
            pnr=code,
            train_number=number,
            train_name=name,
            chart_prepared=(seed % 3 == 0),
            platform=str(1 + seed % 16),
            delay_minutes=(seed % 7) * 5,
            passengers=tuple(passengers),
        )


class OfficialAPIProvider:
    """Adapter slot for a permitted PNR data source."""

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("an API key is required")
        self.api_key = api_key

    def fetch(self, pnr: str) -> PNRStatus:
        raise NotImplementedError(
            "Connect an authorised PNR data source here. "
            "This project ships without one on purpose."
        )


class HttpPNRProvider:
    """Adapter for a third-party PNR API you hold a key for.

    Not official railway data. Vendor APIs aggregate public sources and can lag,
    so confirm anything that matters on IRCTC or RailOne.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 10.0,
        fetch_json=None,
    ) -> None:
        if not base_url:
            raise ValueError("base_url is required")
        if not api_key:
            raise ValueError("api_key is required")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._fetch_json = fetch_json or self._http_json

    def _http_json(self, url: str, headers: dict) -> dict:
        request = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def fetch(self, pnr: str) -> PNRStatus:
        code = pnr.strip()
        if not (code.isdigit() and len(code) == 10):
            raise ValueError("a PNR is 10 digits")
        payload = self._fetch_json(
            f"{self.base_url}/pnr/{code}",
            {"x-api-key": self.api_key, "accept": "application/json"},
        )
        return self._parse(code, payload)

    @staticmethod
    def _parse(code: str, payload: dict) -> PNRStatus:
        if not isinstance(payload, dict):
            raise ValueError("unexpected response from the PNR provider")
        if payload.get("success") is False:
            error = payload.get("error") or {}
            message = error.get("message") if isinstance(error, dict) else None
            raise ValueError(str(message or "the PNR provider returned an error"))

        body = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        train = body.get("train") or {}
        chart = body.get("chart") or {}
        chart_status = str(chart.get("status") or "").lower()

        passengers = []
        for index, item in enumerate(body.get("passengers") or [], start=1):
            current = item.get("current") or {}
            booking = item.get("booking") or {}
            passengers.append(
                {
                    "index": index,
                    "status": str(current.get("status") or booking.get("status") or "UNKNOWN"),
                    "berth": str(current.get("details") or booking.get("details") or "-"),
                }
            )

        return PNRStatus(
            pnr=code,
            train_number=str(train.get("number") or "-"),
            train_name=str(train.get("name") or "unknown train"),
            chart_prepared=("prepared" in chart_status and "not" not in chart_status),
            platform=str(body.get("platform") or "-"),
            delay_minutes=int(body.get("delayMinutes") or 0),
            passengers=tuple(passengers),
        )
