"""
src/data_prep/eia_demand.py

Fetches LIVE regional electricity demand from the EIA (U.S. Energy
Information Administration) Open Data API v2, for a city's balancing
authority (grid operator), e.g. ERCOT for Dallas, CAISO for Sacramento.

Requires a free EIA API key: https://www.eia.gov/opendata/register.php
Pass it via --api-key, or set the EIA_API_KEY environment variable.

Design choice (matches noaa_alerts.py): always returns a well-formed
response, with real recent hourly demand data. If the API call fails
(bad key, network issue, etc.), the failure is captured in "status"/"note"
rather than raising, so callers can degrade gracefully instead of crashing
a live demo.

Usage (standalone):
    python src/data_prep/eia_demand.py --city dallas_tx --api-key YOUR_KEY
    (or set EIA_API_KEY env var and omit --api-key)

Also importable:
    from src.data_prep.eia_demand import get_grid_demand
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from city_metadata import get_city_metadata

EIA_BASE_URL = "https://api.eia.gov/v2/electricity/rto/region-data/data/"


def get_grid_demand(city: str, api_key: str, hours: int = 24, timeout: float = 10.0) -> dict:
    """
    Returns a dict:
        {
            "city": city,
            "status": "ok" | "error",
            "ba_code": str,
            "ba_name": str,
            "demand_mwh": [ {period, value}, ... ]  (most recent `hours` hourly points)
            "source": "EIA Open Data API (api.eia.gov)",
            "note": str (optional)
        }

    Never raises -- failures are captured in "status"/"note".
    """
    meta = get_city_metadata(city)
    if meta is None:
        return {
            "city": city, "status": "error", "ba_code": None, "ba_name": None,
            "demand_mwh": [], "source": "EIA Open Data API (api.eia.gov)",
            "note": f"No metadata registered for city '{city}'.",
        }

    if not api_key:
        return {
            "city": city, "status": "error",
            "ba_code": meta["eia_ba_code"], "ba_name": meta["eia_ba_name"],
            "demand_mwh": [], "source": "EIA Open Data API (api.eia.gov)",
            "note": "No EIA API key provided (pass --api-key or set EIA_API_KEY env var).",
        }

    params = {
        "api_key": api_key,
        "frequency": "hourly",
        "data[0]": "value",
        "facets[respondent][]": meta["eia_ba_code"],
        "facets[type][]": "D",  # D = Demand
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": hours,
    }

    try:
        resp = requests.get(EIA_BASE_URL, params=params, timeout=timeout)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        return {
            "city": city, "status": "error",
            "ba_code": meta["eia_ba_code"], "ba_name": meta["eia_ba_name"],
            "demand_mwh": [], "source": "EIA Open Data API (api.eia.gov)",
            "note": f"EIA API request failed: {e}",
        }

    rows = payload.get("response", {}).get("data", [])
    if not rows:
        return {
            "city": city, "status": "error",
            "ba_code": meta["eia_ba_code"], "ba_name": meta["eia_ba_name"],
            "demand_mwh": [], "source": "EIA Open Data API (api.eia.gov)",
            "note": "EIA API returned no data rows for this balancing authority.",
        }

    demand_points = [
        {"period": row.get("period"), "value_mwh": row.get("value")}
        for row in rows
    ]
    # API returns newest-first; flip to chronological order for charting.
    demand_points.reverse()

    return {
        "city": city,
        "status": "ok",
        "ba_code": meta["eia_ba_code"],
        "ba_name": meta["eia_ba_name"],
        "demand_mwh": demand_points,
        "source": "EIA Open Data API (api.eia.gov)",
        "note": None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city", type=str, required=True,
                         help="City key, e.g. dallas_tx (see city_metadata.py)")
    parser.add_argument("--api-key", type=str, default=os.environ.get("EIA_API_KEY"),
                         help="EIA API key. Defaults to EIA_API_KEY env var if not passed.")
    parser.add_argument("--hours", type=int, default=24)
    args = parser.parse_args()

    result = get_grid_demand(args.city, args.api_key, hours=args.hours)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()