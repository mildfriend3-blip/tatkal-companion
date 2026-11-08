# Tatkal Companion local dashboard upgrade

This add-on provides a responsive local dashboard for Windows and Android (Termux). It uses the project's existing `tatkal.Store` JSON file, so saved passengers and journeys are shared with the CLI.

## What it does

- Local passenger master list and journey planner
- Tatkal window calculation and readiness overview
- Opens the official IRCTC website for you to use
- Runs on Windows and Android without a cloud server
- Keeps the dashboard bound to `127.0.0.1` (this device only)

## Important limitation

This is **not** an IRCTC booking bot. It does not log in, operate the booking UI, select seats, submit bookings, or make payments. No public individual booking API or authorized integration has been configured in this project. You complete booking and payment on the official service and verify success using the real PNR. A 30–40 second target cannot be guaranteed.

## Install on Windows

1. Install Python 3.10 or newer from https://www.python.org/downloads/ and enable **Add Python to PATH**.
2. Open PowerShell:

```powershell
git clone https://github.com/mildfriend3-blip/tatkal-companion.git
cd tatkal-companion
```

3. Copy the new `tatkal/dashboard.py` file from this upgrade into the repository's `tatkal` folder.
4. Install and launch:

```powershell
py -m pip install -e .
python -m tatkal.dashboard
```

Open `http://127.0.0.1:8765` if it does not open automatically. Stop with Ctrl+C.

## Install on Android (Termux)

```bash
pkg update && pkg install python git
git clone https://github.com/mildfriend3-blip/tatkal-companion.git
cd tatkal-companion
```

Copy the new `tatkal/dashboard.py` file from this upgrade into the repository's `tatkal` folder, then:

```bash
python -m pip install -e .
python -m tatkal.dashboard
```

Open `http://127.0.0.1:8765` in the phone browser. Keep Termux running while using the dashboard; stop with Ctrl+C.

## Add the launcher to `pyproject.toml`

Optional: to create a shorter `tatkal-dashboard` command, under `[project.scripts]`, add:

```toml
tatkal-dashboard = "tatkal.dashboard:main"
```

## Quick smoke test without installing the package

From the repository root:

```bash
python -m tatkal.dashboard
```

The dashboard stores data in `data/tatkal.json`, the same default store as the CLI. Back up that file privately; do not commit it.
