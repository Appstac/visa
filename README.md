# Visa Slot Tracker

Logs US visa appointment slot sightings (from CheckVisaSlots' public
"latest availability" page) every ~5 minutes with GitHub Actions, and shows
the trends on a static dashboard hosted on Vercel.

- `scripts/poll.py`: run by `.github/workflows/poll.yml`; appends new sightings
  to the `data` branch (`sightings.json`, `sightings.csv`, `status.json`).
- `web/index.html`: dashboard; reads the data branch from raw.githubusercontent.com.
- `config.json`: visa types to track (slugs from
  https://checkvisaslots.com/latest-us-visa-availability/).

Reads public data only; never logs in to any visa portal.
