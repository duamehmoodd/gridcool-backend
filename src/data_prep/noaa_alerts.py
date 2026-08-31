"""
src/data_prep/noaa_alerts.py

Fetches LIVE active weather alerts from NOAA's National Weather Service API
(api.weather.gov) for a given city's coordinates, and filters to
heat-relevant alerts (Excessive Heat Warning, Heat Advisory, etc.).

No API key required -- NOAA's API is free and public, but requires a
descriptive User-Agent header per their usage policy.

Design choice: this ALWAYS returns a valid, well-formed response, even when
there is no active heat alert for a city right now (which is the common
case -- most days, most places, have no active warning). A "no active
alerts" response is itself a real, honest finding ("NOAA confirms no
heat warning currently in effect"), not a failure state. This makes the
integration reliable for a live demo regardless of real-world conditions
on the day you present, while still being 100% real data, not fabricated.

Usage (standalone):
    python src/data_prep/noaa_alerts.py --city phoenix_az

Also importable:
    from src.data_prep.noaa_alerts import get_heat_alerts
"""

import argparse
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from city_metadata import get_city_metadata

NOAA_BASE_URL = "https://api.weather.gov/alerts/active"
USER_AGENT = "GridCoolUSA-Hackathon (contact: your-email@example.com)"  # NOAA requires a real contact

# Event types NOAA uses that count as "heat relevant" for this project.
HEAT_EVENT_KEYWORDS = ["heat", "excessive heat"]


def get_heat_alerts(city: str, timeout: float = 10.0) -> dict:
    """
    Returns a dict:
        {
            "city": city,
            "status": "ok" | "error",
            "has_active_heat_alert": bool,
            "alerts": [ {event, headline, severity, effective, expires, description}, ... ],
            "source": "NOAA National Weather Service (api.weather.gov)",
            "note": str (optional, e.g. explaining a fallback)
        }

    Never raises -- network/API failures are captured in the "status" and
    "note" fields instead, so callers (API endpoints, decision agent) can
    always render something sensible.
    """
    meta = get_city_metadata(city)
    if meta is None:
        return {
            "city": city,
            "status": "error",
            "has_active_heat_alert": False,
            "alerts": [],
            "source": "NOAA National Weather Service (api.weather.gov)",
            "note": f"No metadata (lat/lon) registered for city '{city}'.",
        }

    params = {"point": f"{meta['lat']},{meta['lon']}"}
    headers = {"User-Agent": USER_AGENT, "Accept": "application/geo+json"}

    try:
        resp = requests.get(NOAA_BASE_URL, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {
            "city": city,
            "status": "error",
            "has_active_heat_alert": False,
            "alerts": [],
            "source": "NOAA National Weather Service (api.weather.gov)",
            "note": f"NOAA API request failed: {e}",
        }

    features = data.get("features", [])
    heat_alerts = []
    for feature in features:
        props = feature.get("properties", {})
        event = (props.get("event") or "").lower()
        if any(kw in event for kw in HEAT_EVENT_KEYWORDS):
            heat_alerts.append({
                "event": props.get("event"),
                "headline": props.get("headline"),
                "severity": props.get("severity"),
                "effective": props.get("effective"),
                "expires": props.get("expires"),
                "description": (props.get("description") or "")[:500],  # keep responses reasonably sized
            })

    return {
        "city": city,
        "status": "ok",
        "has_active_heat_alert": len(heat_alerts) > 0,
        "alerts": heat_alerts,
        "source": "NOAA National Weather Service (api.weather.gov)",
        "note": (
            "No active heat alert for this location at request time -- this is a real, "
            "live check, not a placeholder."
            if not heat_alerts else None
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city", type=str, required=True,
                         help="City key, e.g. phoenix_az (see city_metadata.py)")
    args = parser.parse_args()

    result = get_heat_alerts(args.city)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()