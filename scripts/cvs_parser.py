"""Parser for CheckVisaSlots' public latest-availability table."""
import datetime as dt
import re
from html.parser import HTMLParser


# ----------------------------------------------------------------- parsing --
class _TableParser(HTMLParser):
    """Collects every <table> as a list of rows of cell text."""

    def __init__(self):
        super().__init__()
        self.tables, self._row, self._cell, self._depth = [], None, None, 0

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._depth += 1
            self.tables.append([])
        elif tag == "tr" and self._depth:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.tables[-1].append(self._row)
            self._row = None
        elif tag == "table" and self._depth:
            self._depth -= 1

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


_REL_UNITS = {"sec": 1 / 60, "second": 1 / 60, "min": 1, "minute": 1,
              "hr": 60, "hour": 60, "day": 1440, "wk": 10080, "week": 10080,
              "month": 43200, "mo": 43200}


def parse_relative_minutes(text):
    """'1 hr 28 mins ago' -> 88.0 ; returns (minutes, precise) or (None, False)."""
    t = (text or "").lower()
    if "just now" in t:
        return 0.0, True
    total, found, coarse = 0.0, False, False
    for num, unit in re.findall(r"(\d+)\s*([a-z]+)", t):
        unit = unit.rstrip("s") if unit not in ("s",) else unit
        for key, mult in _REL_UNITS.items():
            if unit.startswith(key):
                total += int(num) * mult
                found = True
                coarse |= mult >= 1440
                break
    return (total, not coarse) if found else (None, False)


def parse_date(text, fmts):
    text = re.sub(r"\s+", " ", (text or "").strip())
    for f in fmts:
        try:
            return dt.datetime.strptime(text, f)
        except ValueError:
            pass
    return None


def to_int(text):
    m = re.search(r"\d+", text or "")
    return int(m.group()) if m else None


def parse_page(html, polled_at):
    """Return list of sighting dicts from the availability table."""
    p = _TableParser()
    p.feed(html)
    for table in p.tables:
        if not table:
            continue
        header = [h.lower() for h in table[0]]
        if not any("location" in h for h in header) or not any("last seen" in h for h in header):
            continue

        def col(*names):
            for i, h in enumerate(header):
                if any(n in h for n in names):
                    return i
            return None

        c_loc, c_type = col("location"), col("visa type")
        c_early, c_slots = col("earliest"), col("slots on")
        c_total, c_seen, c_rel = col("total dates"), col("last seen"), col("relative")
        out = []
        for row in table[1:]:
            def get(i):
                return row[i] if i is not None and i < len(row) else ""
            loc = get(c_loc).upper()
            if not loc:
                continue
            seen_raw = get(c_seen)
            rel_min, precise = parse_relative_minutes(get(c_rel))
            # 'Last Seen At' is rendered server-side in UTC; relative time is
            # timezone-proof, so prefer it whenever it's minute-precise.
            abs_utc = parse_date(seen_raw, ["%d %b %Y, %I:%M %p", "%d %b %Y %I:%M %p"])
            if rel_min is not None and (precise or abs_utc is None):
                seen = polled_at - dt.timedelta(minutes=rel_min)
            elif abs_utc is not None:
                seen = abs_utc.replace(tzinfo=dt.timezone.utc)
            else:
                seen = polled_at
            early = parse_date(get(c_early), ["%d %b, %y", "%d %b %y", "%d %b, %Y", "%d %b %Y"])
            out.append({
                "visa_type": get(c_type) or None,
                "location": loc,
                "is_ofc": loc.endswith("VAC"),
                "earliest_date": early.date().isoformat() if early else get(c_early),
                "slots_on_earliest": to_int(get(c_slots)),
                "total_dates": to_int(get(c_total)),
                "seen_at_utc": seen.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat(),
                "last_seen_raw": seen_raw or seen.isoformat(),
            })
        return out
    raise ValueError("Availability table not found - the page layout may have changed.")
