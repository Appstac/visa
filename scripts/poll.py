"""
Runs in GitHub Actions. Fetches CheckVisaSlots' public latest-availability
page for each configured visa type, appends new sightings to
data/sightings.json + data/sightings.csv, and updates data/status.json.

Exit code is always 0 so a temporary site/network failure doesn't spam
failure emails; the error is recorded in status.json and shown on the
dashboard instead.
"""
import csv
import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cvs_parser import parse_page  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text())
DATA = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data"
URL = "https://checkvisaslots.com/latest-us-visa-availability/{slug}/"
UA = ("Mozilla/5.0 (compatible; VisaSlotTracker/1.0; personal trend log; "
      "polls every few minutes)")
FIELDS = ["slug", "visa_type", "location", "is_ofc", "earliest_date",
          "slots_on_earliest", "total_dates", "seen_at_utc", "last_seen_raw",
          "logged_at_utc"]
HEARTBEAT_MIN = 60   # rewrite status at least this often even with no news


def load(path, default):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    sightings = load(DATA / "sightings.json", [])
    status = load(DATA / "status.json", {"polls_total": 0, "polls_ok": 0})
    keys = {(s["slug"], s["location"], s["last_seen_raw"], s["earliest_date"]) for s in sightings}

    now = dt.datetime.now(dt.timezone.utc)
    now_s = now.isoformat(timespec="seconds")
    new_rows, errors = [], []
    for slug in CONFIG["visa_types"]:
        try:
            req = urllib.request.Request(URL.format(slug=slug), headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                html = r.read().decode("utf-8", "replace")
            for s in parse_page(html, now):
                k = (slug, s["location"], s["last_seen_raw"], s["earliest_date"])
                if k in keys:
                    continue
                keys.add(k)
                row = {**s, "slug": slug, "is_ofc": int(s["is_ofc"]), "logged_at_utc": now_s}
                new_rows.append(row)
        except Exception as e:  # recorded, not raised
            errors.append(f"{slug}: {e}"[:300])

    ok = not errors
    status["polls_total"] = status.get("polls_total", 0) + 1
    status["polls_ok"] = status.get("polls_ok", 0) + (1 if ok else 0)
    status.setdefault("first_poll_utc", now_s)
    status["last_poll_utc"] = now_s
    status["last_ok"] = ok
    if ok:
        status["last_success_utc"] = now_s
    else:
        status["last_error"] = {"at_utc": now_s, "error": "; ".join(errors)}
    status["visa_types"] = CONFIG["visa_types"]
    status["poll_minutes"] = CONFIG.get("poll_minutes", 5)

    last_write = status.get("last_written_utc")
    stale = (not last_write or
             (now - dt.datetime.fromisoformat(last_write)).total_seconds() > HEARTBEAT_MIN * 60)
    flipped = status.get("_prev_ok") is not None and status["_prev_ok"] != ok
    status["_prev_ok"] = ok

    if new_rows or stale or flipped or not (DATA / "status.json").exists():
        sightings.extend(new_rows)
        sightings.sort(key=lambda s: s["seen_at_utc"])
        status["last_written_utc"] = now_s
        status["sightings_total"] = len(sightings)
        (DATA / "sightings.json").write_text(json.dumps(sightings, separators=(",", ":")))
        with open(DATA / "sightings.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
            w.writeheader()
            w.writerows(sightings)
        (DATA / "status.json").write_text(json.dumps(status, indent=2))
        print(f"wrote: {len(new_rows)} new sighting(s); ok={ok}")
    else:
        print(f"no changes to write; ok={ok}")
    for e in errors:
        print("ERROR", e)


if __name__ == "__main__":
    main()
