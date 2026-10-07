"""
Always-on logger for a home Windows laptop.

Every few minutes: fetch the public CheckVisaSlots page (scripts/poll.py),
save new sightings into the `data` branch checkout, and push to GitHub.
The Vercel dashboard reads the `data` branch, so it updates by itself.

Run by Task Scheduler at logon (see setup.bat). Manual use:
    python laptop\\run_logger.py           # run forever
    python laptop\\run_logger.py --once    # one check + push, then exit
Log file: laptop\\logger.log
"""
import datetime as dt
import json
import os
import random
import socket
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA_DIR = REPO / "databranch"
LOG = REPO / "laptop" / "logger.log"
LOCK_PORT = 47651              # stops two copies running at once
NO_WINDOW = 0x08000000 if os.name == "nt" else 0   # no console flashes under pythonw
CONFIG_REFRESH_EVERY = 12      # pull code/config from GitHub every N checks


def log(msg):
    line = f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    try:
        print(line, flush=True)
    except Exception:
        pass  # no console under pythonw
    try:
        if LOG.exists() and LOG.stat().st_size > 1_000_000:
            LOG.replace(LOG.with_suffix(".old.log"))
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def run(args, cwd, check=False):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                       creationflags=NO_WINDOW, timeout=180)
    if check and r.returncode:
        raise RuntimeError(f"{' '.join(args)} failed: {(r.stderr or r.stdout).strip()[:300]}")
    return r


def git(*args, cwd=DATA_DIR, check=False):
    return run(["git", *args], cwd, check)


def ensure_data_checkout():
    if (DATA_DIR / ".git").exists():
        return
    log("Setting up the data branch checkout...")
    has_remote = git("ls-remote", "--exit-code", "--heads", "origin", "data", cwd=REPO).returncode == 0
    if has_remote:
        git("fetch", "origin", "data:refs/remotes/origin/data", cwd=REPO, check=True)
        git("worktree", "prune", cwd=REPO)
        r = git("worktree", "add", "-B", "data", str(DATA_DIR), "origin/data", cwd=REPO)
        if r.returncode:
            raise RuntimeError(r.stderr.strip())
        git("branch", "--set-upstream-to=origin/data", "data", cwd=DATA_DIR)
    else:
        git("worktree", "add", "--detach", str(DATA_DIR), cwd=REPO, check=True)
        git("checkout", "--orphan", "data", check=True)
        git("rm", "-rf", "--quiet", ".")
    log("Data checkout ready.")


def push_changes():
    git("add", "-A")
    if git("diff", "--cached", "--quiet").returncode == 0:
        return False
    git("commit", "-q", "-m", f"data: {dt.datetime.now(dt.timezone.utc):%Y-%m-%dT%H:%MZ}", check=True)
    for attempt in range(3):
        r = git("push", "-q", "-u", "origin", "data")
        if r.returncode == 0:
            return True
        log(f"push failed ({r.stderr.strip()[:200]}); rebasing and retrying")
        git("pull", "--rebase", "-q", "origin", "data")
        time.sleep(5 * (attempt + 1))
    raise RuntimeError("could not push to GitHub after 3 tries")


def check_once():
    git("pull", "--rebase", "-q", "origin", "data")   # harmless if offline
    r = run([sys.executable, str(REPO / "scripts" / "poll.py"), str(DATA_DIR)], REPO)
    out = (r.stdout + r.stderr).strip().replace("\n", " | ")
    pushed = push_changes()
    log(f"{out}{'  -> pushed to GitHub' if pushed else ''}")


def poll_minutes():
    try:
        cfg = json.loads((REPO / "config.json").read_text())
        return max(3.0, float(cfg.get("poll_minutes", 5)))
    except Exception:
        return 5.0


def main():
    once = "--once" in sys.argv
    lock = socket.socket()
    try:
        lock.bind(("127.0.0.1", LOCK_PORT))
    except OSError:
        log("Another copy of the logger is already running - exiting.")
        return
    while True:   # e.g. laptop just booted and Wi-Fi isn't up yet
        try:
            ensure_data_checkout()
            break
        except Exception as e:
            log(f"ERROR preparing data checkout: {e}")
            if once:
                return
            time.sleep(60)
    n = 0
    while True:
        try:
            if n and n % CONFIG_REFRESH_EVERY == 0:
                git("pull", "-q", "--ff-only", cwd=REPO)    # picks up config/code edits
            check_once()
        except Exception as e:
            log(f"ERROR: {e}")
        if once:
            return
        n += 1
        time.sleep(poll_minutes() * 60 + random.uniform(-20, 20))


if __name__ == "__main__":
    main()
