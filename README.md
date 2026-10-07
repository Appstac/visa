# Visa Slot Tracker

Logs US visa appointment slot sightings (from CheckVisaSlots' public
"latest availability" page) every ~5 minutes from an always-on home laptop,
pushes them to the `data` branch of this repo, and shows the trends at
**https://visa-slot-tracker.vercel.app** (reads the `data` branch directly,
so it updates by itself).

## Set up the home laptop (Windows, one time)
1. Install **Git** (https://git-scm.com/download/win) and **Python 3**
   (https://www.python.org/downloads/ - tick "Add python.exe to PATH").
2. Open Command Prompt and run:
   ```
   cd %USERPROFILE%
   git clone https://github.com/Appstac/visa
   ```
3. Open the new `visa\laptop` folder and double-click **setup.bat**.
   Sign in to GitHub as Appstac if a window asks. That's it.

`setup.bat` does a first check and push, adds the logger to Windows startup,
starts it in the background, and stops the laptop sleeping on AC power.
Also set **lid close action -> Do nothing** (plugged in), and keep Windows signed in.

- Log: `visa\laptop\logger.log`
- Stop / remove from startup: `visa\laptop\stop_logger.bat`
- Track more visa types: edit `config.json` (on GitHub or the laptop); the
  laptop pulls config changes about once an hour.

## Layout
- `laptop/run_logger.py` - loop: fetch -> save to `databranch/` (data branch) -> push.
- `scripts/poll.py`, `scripts/cvs_parser.py` - fetch + parse the public page.
- `web/index.html` - dashboard (Vercel serves `web/`).
- `data` branch - `sightings.json`, `sightings.csv`, `status.json`.

Reads public data only; never logs in to any visa portal.
