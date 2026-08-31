"""
src/data_prep/heat_data_agent.py

Heat Data Agent -- Layer 1 of the required architecture:
    FortyGuard API -> Heat Data Agent -> Demand Prediction Model ->
    Risk Agent -> Decision Agent -> Dashboard

Pulls LIVE hyperlocal heat data from FortyGuard's /v1/env_params endpoint
for a city's coordinates (see city_metadata.py), and extracts the heat
index -- the single number the Demand Prediction Model uses to estimate
cooling-driven electricity demand.

FortyGuard's analysis endpoints are async (submit -> poll -> result), so a
live call here typically takes several seconds to ~1 minute. For a live
demo, cache the result and refresh on a timer/button rather than calling
this on every page load.

Usage (standalone):
    python src/data_prep/heat_data_agent.py --city phoenix_az

Also importable:
    from src.data_prep.heat_data_agent import get_live_heat
"""

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

_QUICKSTART_DIR = Path(__file__).resolve().parents[2] / "temperature-api-quickstart"
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(_QUICKSTART_DIR))

# Load FORTYGUARD_API_KEY from temperature-api-quickstart/.env
load_dotenv(_QUICKSTART_DIR / ".env")

from city_metadata import get_city_metadata
from fortyguard import FortyGuardClient, FortyGuardError

def get_live_heat(city: str, verbose: bool = False, override_date: str = None) -> dict:
    """
    Returns a dict:
        {
            "city": city,
            "status": "ok" | "error",
            "heat_index_c": float | None,
            "heat_index_f": float | None,
            "apparent_temperature_c": float | None,
            "relative_humidity_pct": float | None,
            "raw": dict | None,      # full env_params result, for debugging/extra fields
            "source": "FortyGuard tOS Enterprise API (env_params)",
            "note": str | None,
        }

    Never raises -- FortyGuard/network failures are captured in "status"/"note"
    so callers can degrade gracefully (e.g. fall back to historical ResStock
    multiplier) instead of crashing a live demo.
    """
    meta = get_city_metadata(city)
    if meta is None:
        return {
            "city": city, "status": "error", "heat_index_c": None, "heat_index_f": None,
            "apparent_temperature_c": None, "relative_humidity_pct": None, "raw": None,
            "source": "FortyGuard tOS Enterprise API (env_params)",
            "note": f"No metadata (lat/lon) registered for city '{city}'.",
        }

    try:
        client = FortyGuardClient()
    except FortyGuardError as e:
        return {
            "city": city, "status": "error", "heat_index_c": None, "heat_index_f": None,
            "apparent_temperature_c": None, "relative_humidity_pct": None, "raw": None,
            "source": "FortyGuard tOS Enterprise API (env_params)",
            "note": f"FortyGuard client init failed: {e}",
        }

    today = override_date or date.today().isoformat()
    # env_params requires a `temperature` input (current ambient temp reading,
    # used as a baseline for derived metrics like apparent temperature). We
    # don't have a live thermometer, so we pass a placeholder and rely on
    # FortyGuard's own environmental analysis for heat_index_celsius, which
    # is independently computed from its own data sources, not from this input.
    now_utc = datetime.now(timezone.utc)
    hour_str = now_utc.strftime("%H:00")  # snap to top of the hour, not arbitrary minutes
    try:
        outcome = client.environmental_parameters(
            latitude=meta["lat"],
            longitude=meta["lon"],
            temperature=35.0,
            start_date=today,
            start_time=hour_str,
            filter_type=1,
            analysis=["heat_index_celsius", "apparent_temperature_celsius",
                      "relative_humidity_percent"],
            verbose=verbose,
        )
    except FortyGuardError as e:
        return {
            "city": city, "status": "error", "heat_index_c": None, "heat_index_f": None,
            "apparent_temperature_c": None, "relative_humidity_pct": None, "raw": None,
            "source": "FortyGuard tOS Enterprise API (env_params)",
            "note": f"FortyGuard env_params request failed: {e}",
        }

    result = outcome.get("result", {})
    locations = result.get("locations", [])
    if not locations:
        return {
            "city": city, "status": "error", "heat_index_c": None, "heat_index_f": None,
            "apparent_temperature_c": None, "relative_humidity_pct": None, "raw": result,
            "source": "FortyGuard tOS Enterprise API (env_params)",
            "note": "FortyGuard response had no 'locations' data.",
        }

    params = locations[0].get("parameters", {})
    def _first(key):
        vals = params.get(key)
        return vals[0] if vals else None
    heat_index_c = _first("heat_index_celsius")
    apparent_c = _first("apparent_temperature_celsius")
    humidity = _first("relative_humidity_percent")

    heat_index_f = (heat_index_c * 9 / 5 + 32) if heat_index_c is not None else None

    return {
        "city": city,
        "status": "ok",
        "heat_index_c": heat_index_c,
        "heat_index_f": round(heat_index_f, 1) if heat_index_f is not None else None,
        "apparent_temperature_c": apparent_c,
        "relative_humidity_pct": humidity,
        "raw": result,
        "source": "FortyGuard tOS Enterprise API (env_params)",
        "note": None if heat_index_c is not None else "heat_index_celsius missing from parameters.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city", type=str, required=True)
    parser.add_argument("--date", type=str, default=None,
                         help="Override date (YYYY-MM-DD) for testing, e.g. a known-good historical date.")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    result = get_live_heat(args.city, verbose=args.verbose, override_date=args.date)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()