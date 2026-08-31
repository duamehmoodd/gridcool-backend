"""
src/api/fortyguard_extra.py

Thin wrappers around two FortyGuard endpoints we haven't used yet:
  - Create Heatmap  -> GeoJSON temperature tiles for a city's AOI
  - Environmental Parameters -> heat index, humidity, wet-bulb, AQI, solar

Both FortyGuard endpoints are async (submit -> poll -> result), so this
module handles that pattern once, here, instead of repeating it per-caller.

Results are cached in-memory for CACHE_TTL_SECONDS per (city, param-set)
key, since these are moderately expensive calls and the dashboard polls
every ~30s -- we don't want every poll to hit FortyGuard fresh.

Requires FORTYGUARD_API_KEY in the environment (loaded from .env by
whatever loads env vars at app startup).
"""

import os
import time
import requests
from datetime import datetime, timezone, timedelta

from src.data_prep.city_metadata import get_city_metadata

FORTYGUARD_BASE = "https://api.fortyguard.com/v1"
CACHE_TTL_SECONDS = 300  # 5 min -- heat doesn't change second to second
POLL_INTERVAL_SECONDS = 3
POLL_MAX_ATTEMPTS = 40  # ~2 min ceiling


def _api_key() -> str:
    key = os.environ.get("FORTYGUARD_API_KEY")
    if not key:
        raise RuntimeError(
            "FORTYGUARD_API_KEY not set. Check temperature-api-quickstart/.env "
            "is loaded (e.g. via python-dotenv) before this module is used."
        )
    return key


def _headers() -> dict:
    return {"api-key": _api_key(), "Content-Type": "application/json"}


def _submit(endpoint: str, payload: dict) -> str:
    resp = requests.post(f"{FORTYGUARD_BASE}/{endpoint}", headers=_headers(), json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("error"):
        raise RuntimeError(f"FortyGuard {endpoint} submit error: {data}")
    return data["data"]["activity_id"]


def _poll(activity_id: str) -> dict:
    status_url = f"{FORTYGUARD_BASE}/status/{activity_id}"
    for _ in range(POLL_MAX_ATTEMPTS):
        resp = requests.get(status_url, headers=_headers(), timeout=30)
        resp.raise_for_status()
        status_data = resp.json()["data"]
        status = status_data.get("status", "").lower()
        if status in ("completed", "succeeded"):
            return status_data.get("result", {})
        if status in ("failed", "error"):
            raise RuntimeError(f"FortyGuard activity {activity_id} failed: {status_data}")
        time.sleep(POLL_INTERVAL_SECONDS)
    raise TimeoutError(f"FortyGuard activity {activity_id} did not complete in time.")


# ---- simple in-memory cache -------------------------------------------------
_cache: dict = {}  # key -> (expires_at_epoch, value)


def _cache_get(key):
    entry = _cache.get(key)
    if entry and entry[0] > time.time():
        return entry[1]
    return None


def _cache_set(key, value):
    _cache[key] = (time.time() + CACHE_TTL_SECONDS, value)


def _get_city_or_raise(city_id: str) -> dict:
    meta = get_city_metadata(city_id)
    if meta is None:
        raise ValueError(f"Unknown city '{city_id}'")
    return meta


def _bbox_for(meta: dict, half_width_deg: float = 0.06) -> dict:
    lat, lon = meta["lat"], meta["lon"]
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [lon - half_width_deg, lat - half_width_deg],
                        [lon + half_width_deg, lat - half_width_deg],
                        [lon + half_width_deg, lat + half_width_deg],
                        [lon - half_width_deg, lat + half_width_deg],
                        [lon - half_width_deg, lat - half_width_deg],
                    ]]
                },
            }
        ],
    }


# ---- public functions --------------------------------------------------------

def get_heatmap_tiles(city_id: str, granularity: int = 100) -> dict:
    """Live heatmap for the given city's small bounding box, current hour."""
    cache_key = ("heatmap", city_id, granularity)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    meta = _get_city_or_raise(city_id)
    from datetime import timedelta
    now = datetime.now(timezone.utc) - timedelta(days=3)
    payload = {
        "polygon_aoi": _bbox_for(meta),
        "date_time": {
            "start_date": now.strftime("%Y-%m-%d"),
            "start_time": now.strftime("%H:00"),
            "filter_type": 1,
        },
        "granularity": granularity,
    }

    try:
        activity_id = _submit("heatmap", payload)
        result = _poll(activity_id)
        out = {
            "status": "ok",
            "city": city_id,
            "city_name": meta["display_name"],
            "map_data": result.get("map_data"),
            "stats_data": result.get("stats_data"),
        }
    except Exception as e:
        out = {"status": "error", "city": city_id, "error": str(e)}

    _cache_set(cache_key, out)
    return out


def get_env_params(city_id: str, temperature_c: float) -> dict:
    """Environmental parameters (heat index, humidity, wet-bulb, AQI, solar)."""
    cache_key = ("env_params", city_id, round(temperature_c, 1))
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    meta = _get_city_or_raise(city_id)
    now = datetime.now(timezone.utc)
    payload = {
        "latitude": meta["lat"],
        "longitude": meta["lon"],
        "temperature": temperature_c,
        "date_time": {
            "start_date": now.strftime("%Y-%m-%d"),
            "start_time": now.strftime("%H:00"),
            "filter_type": 1,
        },
    }

    try:
        activity_id = _submit("env_params", payload)
        result = _poll(activity_id)
        locations = result.get("locations", [])
        loc = locations[0] if locations else {}
        params = loc.get("parameters", {})
        solar = loc.get("solar_irradiance", {}).get("clear_sky", {})

        def first(v):
            return v[0] if isinstance(v, list) and v else v

        out = {
            "status": "ok",
            "city": city_id,
            "city_name": meta["display_name"],
            "heat_index_c": first(params.get("heat_index_celsius")),
            "apparent_temp_c": first(params.get("apparent_temperature_celsius")),
            "wet_bulb_c": first(params.get("wet_bulb_temperature_celsius")),
            "humidity_pct": first(params.get("relative_humidity_percent")),
            "aqi": first(params.get("air_quality:idx")),
            "aqi_pm2p5": first(params.get("air_quality_pm2p5:idx")),
            "aqi_o3": first(params.get("air_quality_o3:idx")),
            "solar_ghi": solar.get("ghi"),
            "solar_dni": solar.get("dni"),
        }
    except Exception as e:
        out = {"status": "error", "city": city_id, "error": str(e)}

    _cache_set(cache_key, out)
    return out