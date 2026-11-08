# Tatkal Travel Companion

[![tests](https://github.com/mildfriend3-blip/tatkal-companion/actions/workflows/ci.yml/badge.svg)](https://github.com/mildfriend3-blip/tatkal-companion/actions/workflows/ci.yml) [![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) [![python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

A preparation and tracking agent for Indian Railways tatkal bookings. It gets you
to the tatkal window with everything ready, so the booking itself takes you a few
seconds on the official IRCTC app or site.

It does **not** log in to IRCTC, does not select seats, does not pay, and does not
book. That is deliberate: automating those steps against IRCTC violates their
terms of service and Indian Railways rules, and bot-driven tatkal booking has led
to arrests under the IT Act. Anything claiming to do it in "20 seconds" is either
breaking those rules or lying about the speed.

## What it actually does

| Capability | Detail |
|---|---|
| Tatkal window | Correct open time for any date and class: 10:00 IST for AC (1A/2A/3A/3E/CC/EC/EA), 11:00 IST for non-AC (SL/2S), one day before the journey date |
| Reminder plan | T-120, T-30, T-10, T-2 and T-0 nudges, each with the one thing to do at that moment |
| Master list | Local passenger store with validation, so names and ages are settled before the window opens |
| Readiness checklist | Checks what it can against the store (passengers saved, window confirmed) and lists what only you can confirm (ID proof, wallet/UPI, signed in, backup connection) |
| Co-pilot pacing | A live T-0 countdown plus a pre-decided click order with a target second for each step, timed as you go, so nothing is a decision inside the window |
| PNR tracking | Provider interface with an offline deterministic demo provider; a slot for a permitted live data source |
| Local only | Everything lives in one JSON file. No credentials, no scraping, no network calls |

## Install

```bash
pip install "git+https://github.com/mildfriend3-blip/tatkal-companion.git"
tatkal --help
```

Or work from a clone, with no install at all:

```bash
git clone https://github.com/mildfriend3-blip/tatkal-companion.git
cd tatkal-companion
python demo.py
```

## Quick start

```bash
python demo.py                      # full tour on throwaway data, no setup

python -m tatkal.cli add-passenger "Asha Rao" 34 F --berth LOWER
python -m tatkal.cli add-journey --from NDLS --to BCT --date 2026-11-09 --class 3A \
    --train "12951 Mumbai Rajdhani" --passenger "Asha Rao"
python -m tatkal.cli journeys
python -m tatkal.cli window --date 2026-11-09 --class 3A
python -m tatkal.cli plan <journey-id>
python -m tatkal.cli checklist <journey-id>
python -m tatkal.cli upcoming --within 180
python -m tatkal.cli track 2718281828
python -m tatkal.cli copilot <journey-id> --dry-run
python -m tatkal.cli copilot <journey-id> --payment upi --now 2026-11-08T09:58:00
```

Or with the module form: `python -m tatkal.cli --store data/tatkal.json ...`

## Layout

```
tatkal/
  models.py      Passenger, BookingWindow, Reminder, class groups, IST timezone
  schedule.py    tatkal_window() and reminder_plan()
  store.py       JSON persistence for passengers and journeys
  assistant.py   speed_checklist(), upcoming(), describe_journey()
  pnr.py         PNRProvider protocol, DemoPNRProvider, OfficialAPIProvider slot
  copilot.py     build_script(), pacing_report(), countdown, desktop notify, wait_until()
  cli.py         argparse entry point
demo.py          end-to-end tour
tests/           30 unittest cases
```

## Tests

```bash
python -m unittest discover -s tests -v
```

Covers the 10:00/11:00 split, day-before arithmetic, reminder ordering, store
round-trips, duplicate and invalid input rejection, checklist state, and the
upcoming-reminder horizon. No network, no fixtures, no dependencies outside the
standard library.

## The co-pilot

`copilot` is the part that gives you speed without touching IRCTC. It counts down
to the window (with desktop notifications if `notify-send` exists, a terminal bell
otherwise), then walks you through a fixed click order. Each step carries the
second it should be done by; you press Enter after each one and it tells you
whether you are ahead, on time, or behind.

```bash
python -m tatkal.cli copilot <journey-id> --dry-run     # rehearse the script
python -m tatkal.cli copilot <journey-id> --payment upi # run it live
```

The 25-second target is what a prepared person can do; IRCTC's own page latency
sits on top and is outside anyone's control. Rehearse with `--dry-run` and
`--now` a few times before the real window.

### What this deliberately does not do

It never signs in to IRCTC, never fills the booking form, never pays. It also does
not try to pass itself off as a person: no faked browser identity, no relayed
traffic, no scripted human-like timing, no solving of human-verification checks.
Disguising a script does not make it permitted, it only moves the risk onto your
account. The honest levers for speed are preparation (master list, funded wallet,
saved search, a rehearsed script) and a good network.

## Going live with PNR data

`OfficialAPIProvider` is intentionally unimplemented. Put a permitted data source
there — a railway data partner or an authorised API with a key of your own — and
return a `PNRStatus`. Do not point it at IRCTC's own endpoints with scraped
session cookies.

## Extending it

Natural next steps for a final-year project: a Telegram or WhatsApp bot in front
of `assistant.py`, a calendar feed that emits the reminder plan as `.ics`, a
small web dashboard over the JSON store, or chart-preparation polling for a
tracked PNR once a permitted provider is wired in.
