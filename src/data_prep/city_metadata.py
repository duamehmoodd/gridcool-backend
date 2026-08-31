"""
src/data_prep/city_metadata.py

Static metadata for each supported city -- used by both the NOAA heat-alert
integration (needs lat/lon) and the EIA grid-demand integration (needs a
balancing authority / respondent code).

To add a new city here: add one entry. Everything downstream (NOAA, EIA,
API endpoints) reads from this dict, so no other file needs to change.

EIA balancing authority (BA) codes used below are the standard EIA-930
respondent codes:
    ERCO = ERCOT (Texas)
    CISO = California ISO
    SOCO = Southern Company (Georgia/Southeast)
    NEVP = Nevada Power (NV Energy)
    AZPS = Arizona Public Service

If a city's real utility isn't an EIA-930 respondent on its own, the nearest
regional BA is used instead -- this is standard practice, since EIA-930
reports at the balancing-authority level, not city level.
"""

CITY_METADATA = {
    "phoenix_az": {
        "display_name": "Phoenix, AZ",
        "state": "AZ",
        "lat": 33.4484,
        "lon": -112.0740,
        "eia_ba_code": "AZPS",
        "eia_ba_name": "Arizona Public Service",
    },
    "dallas_tx": {
        "display_name": "Dallas, TX",
        "state": "TX",
        "lat": 32.7767,
        "lon": -96.7970,
        "eia_ba_code": "ERCO",
        "eia_ba_name": "ERCOT",
    },
    "vegas_nv": {
        "display_name": "Las Vegas, NV",
        "state": "NV",
        "lat": 36.1699,
        "lon": -115.1398,
        "eia_ba_code": "NEVP",
        "eia_ba_name": "Nevada Power (NV Energy)",
    },
    "atlanta_ga": {
        "display_name": "Atlanta, GA",
        "state": "GA",
        "lat": 33.7490,
        "lon": -84.3880,
        "eia_ba_code": "SOCO",
        "eia_ba_name": "Southern Company",
    },
    "sacramento_ca": {
        "display_name": "Sacramento, CA",
        "state": "CA",
        "lat": 38.5816,
        "lon": -121.4944,
        "eia_ba_code": "CISO",
        "eia_ba_name": "California ISO",
    },
}


def get_city_metadata(city: str) -> dict:
    """Returns metadata dict for a city key, or None if not found."""
    return CITY_METADATA.get(city)