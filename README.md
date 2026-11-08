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

## The one command you actually need

Once a passenger and a journey are saved, this is the whole thing:

```bash
tatkal go <journey-id> --payment wallet --open
```

It runs the readiness check, counts down to the window, sends the T-10 / T-2 / T-0
notifications (Termux on Android, `notify-send` on desktop, terminal bell
otherwise), opens the official IRCTC page at T-0 with `--open`, then paces you
through the click order, timing each step.

Rehearse it first with `--now` and `--no-wait`, which skip the real clock:

```bash
tatkal go <journey-id> --now 2026-11-14T09:58:00
tatkal go <journey-id> --no-wait
```

The one thing it cannot do is tap the buttons on the IRCTC app for you. That
would be automation of a service that forbids it, so the tool stops at telling you
what to tap, and when.

## Quick start

No setup at all, just watch it work:

```bash
python demo.py                      # full tour on throwaway data
```

For the real thing, follow the walkthrough below.

A command reference, once you are set up:

```bash
tatkal add-passenger NAME AGE M|F [--berth LOWER]
tatkal passengers
tatkal add-journey --from NDLS --to BCT --date 2026-11-12 --class 3A
tatkal journeys
tatkal window --date 2026-11-12 --class 3A
tatkal plan <journey-id>
tatkal checklist <journey-id>
tatkal copilot <journey-id> --dry-run
tatkal copilot <journey-id> --payment wallet
tatkal ics --out ~/tatkal-reminders.ics
tatkal upcoming --within 180
tatkal track <10-digit-pnr>
```

## Step-by-step: your first tatkal booking

Copy these in order. Every step shows the command and what you should see.

### 1. Save the people you travel with

```bash
tatkal add-passenger "YOUR NAME" 24 M --berth LOWER
tatkal add-passenger "SECOND PERSON" 22 F --berth UPPER
```

Each one prints `saved passenger ...`. This is your master list, so you never type
names inside the booking window.

```bash
tatkal passengers
```

### 2. Track the journey you want

```bash
tatkal add-journey --from NDLS --to BCT --date 2026-11-12 --class 3A \
  --train "12951 Mumbai Rajdhani" --passenger "YOUR NAME"
```

`--date` is the **travel date**, not the booking date. The command returns a
journey id of eight characters, for example `a6349c51`. Every command below uses
that id, so swap in your own.

```bash
tatkal journeys
```

### 3. Check when the window opens

```bash
tatkal window --date 2026-11-12 --class 3A
```

AC classes open at 10:00 IST and non-AC (SL, 2S) at 11:00 IST, one day before the
journey. The reminder ladder comes with it.

### 4. Read the reminder plan

```bash
tatkal plan a6349c51
```

To get those nudges on your phone even when this tool is not running, export them
to your calendar once:

```bash
tatkal ics --out ~/tatkal-reminders.ics
```

Open that file with your calendar app. Every reminder becomes an event with its
alarm already set, at T-120, T-30, T-10, T-2 and T-0. Add `--journey a6349c51`
to export a single journey.

### 5. Run the readiness check the night before

```bash
tatkal checklist a6349c51
```

`[x]` is checked and clear, `[ ]` is still open, `[~]` is something only you can
confirm (ID proof, wallet or UPI, being signed in).

### 6. Rehearse the click order

```bash
tatkal copilot a6349c51 --dry-run
```

Nothing is timed in a dry run. Do it two or three times so the order is muscle
memory before the real window.

### 7. Book, with the co-pilot pacing you

Be on the official IRCTC app or site a minute before the window, signed in, with
the wallet funded or the UPI app already open. Then:

```bash
tatkal copilot a6349c51 --payment wallet    # or: --payment upi
```

It counts down to T-0, then prints each step with the second it should be done by.
Press Enter after each step and it tells you whether you are ahead, on time, or
behind.

### 8. Track the ticket afterwards

```bash
tatkal track 2718281828
```

This uses the offline demo provider, so the data is sample data. Wire a permitted
data source into `OfficialAPIProvider` for live lookups.

### Where the data lives

Everything sits in one JSON file, `data/tatkal.json`, in the directory you run from.
Keep it elsewhere with the global `--store` flag, which goes **before** the
subcommand:

```bash
tatkal --store ~/tatkal.json passengers
tatkal --store ~/tatkal.json add-passenger "YOUR NAME" 24 M
```

`data/` is in `.gitignore`, so `git add .` never commits your passenger list.

### On Android (Termux)

The steps above are identical. For phone notifications, install the Termux:API app
and run `pkg install termux-api`, which gives the tool `termux-notification` and
`termux-open-url`. Without it, alerts fall back to a terminal bell.

## What it actually does

| Capability | Detail |
|---|---|
| Tatkal window | Correct open time for any date and class: 10:00 IST for AC (1A/2A/3A/3E/CC/EC/EA), 11:00 IST for non-AC (SL/2S), one day before the journey date |
| Reminder plan | T-120, T-30, T-10, T-2 and T-0 nudges, each with the one thing to do at that moment |
| Master list | Local passenger store with validation, so names and ages are settled before the window opens |
| Readiness checklist | Checks what it can against the store (passengers saved, window confirmed) and lists what only you can confirm (ID proof, wallet/UPI, signed in, backup connection) |
| Co-pilot pacing | A live T-0 countdown plus a pre-decided click order with a target second for each step, timed as you go, so nothing is a decision inside the window |
| Local dashboard | `tatkal-dashboard` serves a loopback-only page over the same JSON store: journeys, their windows, passenger entry and the checklist |
| Calendar export | `tatkal ics` writes the whole reminder ladder as an `.ics` file with alarms, so your phone calendar nudges you even if the terminal is closed |
| PNR tracking | Provider interface with an offline deterministic demo provider; a slot for a permitted live data source |
| Local only | Everything lives in one JSON file. No credentials, no scraping, no network calls |

## Local dashboard

If you would rather not live in a terminal, there is a loopback-only dashboard.
It runs on `127.0.0.1`, reads and writes the same JSON store, and never logs in,
drives a booking page, submits a booking or pays.

```bash
python -m tatkal.dashboard --port 8765
```

Or, after `pip install .`, use the console script:

```bash
tatkal-dashboard --port 8765
```

It prints the URL and opens your browser. On Windows PowerShell the same commands
work; if the browser does not open, paste the printed `http://127.0.0.1:8765/`
into it yourself. On Termux, run it and open the URL on the same phone.

What you can do there: see every tracked journey with its tatkal window, add a
passenger, add a journey, and read the readiness checklist per journey.

## Troubleshooting

### `argument age: invalid int value: 'BHAVSAR'`

The name has a space and was not quoted, so the shell split it into two words and
the second one landed in the age slot. Quote the whole name:

```bash
tatkal add-passenger "LOKESH BHAVSAR" 18 M --berth "SIDE LOWER"
```

`--berth` takes a single value as well, so `SIDE LOWER` needs quotes too.

### `unrecognized arguments: BHAVSAR`

Same cause, on `add-journey`. Quoting always works:

```bash
tatkal add-journey --from BRC --to JAT --date 2026-11-15 --class 3A \
  --train "12471 Swaraj Express" --passenger "LOKESH BHAVSAR"
```

From 0.2.1 `--passenger` also accepts an unquoted multi-word name, so
`--passenger LOKESH BHAVSAR` is read as one passenger. Quote anyway if you have
more than one passenger.

### `tatkal--store: command not found`

Missing space. `--store` also needs a value, and it goes before the subcommand:

```bash
tatkal --store ~/tatkal.json passengers
```

### `note: not in your master list yet: ...`

You tracked a journey with a name that is not saved. Save it so the readiness
checklist can check it:

```bash
tatkal add-passenger "LOKESH BHAVSAR" 18 M
```

## Layout

```
tatkal/
  models.py      Passenger, BookingWindow, Reminder, class groups, IST timezone
  schedule.py    tatkal_window() and reminder_plan()
  store.py       JSON persistence for passengers and journeys
  assistant.py   speed_checklist(), upcoming(), describe_journey()
  pnr.py         PNRProvider protocol, DemoPNRProvider, OfficialAPIProvider slot
  copilot.py     build_script(), pacing_report(), countdown, notify, open_official_site()
  calendar.py    build_calendar(), the reminder plan as an .ics file
  dashboard.py   loopback-only HTTP dashboard over the same store
  cli.py         argparse entry point
demo.py          end-to-end tour
tests/           65 unittest cases
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

## Live PNR data (optional, your own key)

`tatkal track` uses an offline demo provider by default, so the numbers are sample
data. For real lookups, point it at a PNR API you hold a key for:

```bash
export TATKAL_PNR_BASE_URL="https://api.example.in/api/v1"
export TATKAL_PNR_API_KEY="your_key"
tatkal track 1234567890 --live
```

The adapter calls `GET {base_url}/pnr/{pnr}` with an `x-api-key` header and reads
the `success` / `data` envelope that most Indian Railways aggregator APIs use. If
yours differs, subclass or adjust `HttpPNRProvider._parse` — it is one function.

### Why there is no "official" provider

Indian Railways does run an official NTES API, but it is issued to authorised
railway vendors under a `custID` / `custPass` header, and the specification says
the information is confidential and meant for railway-authorised personnel only.
There is no public official API for an individual developer.

Third-party APIs that sell keys are aggregators. They work, they are convenient,
and they are not authoritative — their own documentation tells you to confirm
anything critical on IRCTC. That is why this tool never treats their output as a
source of truth, and why `--live` is opt-in.

### What will never be in here

Automated login, seat selection, payment or booking against IRCTC or RailOne. That
is automation of a service that forbids it, and it is the one thing that would put
your own account and ID at risk.

## Extending it

Natural next steps for a final-year project: a Telegram or WhatsApp bot in front
of `assistant.py`, a calendar feed that emits the reminder plan as `.ics`, a
small web dashboard over the JSON store, or chart-preparation polling for a
tracked PNR once a permitted provider is wired in.

