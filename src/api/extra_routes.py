"""
src/api/extra_routes.py

New endpoints, additive to your existing main.py:
  GET /cities              -- static metadata for all 5 demo cities
  GET /heatmap-tiles?city= -- live FortyGuard heatmap GeoJSON + stats
  GET /env-intel?city=     -- live FortyGuard environmental parameters

Wire into your existing main.py with:
    from src.api.extra_routes import router as extra_router
    app.include_router(extra_router)
"""

from fastapi import APIRouter, HTTPException, Query

from src.data_prep.city_metadata import CITY_METADATA, get_city_metadata
from src.api.fortyguard_extra import get_heatmap_tiles, get_env_params

router = APIRouter()


@router.get("/cities")
def cities():
    """Static metadata for all 5 demo cities."""
    return {"cities": [{"id": cid, **meta} for cid, meta in CITY_METADATA.items()]}


@router.get("/heatmap-tiles")
def heatmap_tiles(city: str = Query(..., description="City id, e.g. phoenix_az")):
    if get_city_metadata(city) is None:
        raise HTTPException(status_code=404, detail=f"Unknown city '{city}'")

    result = get_heatmap_tiles(city)
    if result["status"] == "error":
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.get("/env-intel")
def env_intel(
    city: str = Query(..., description="City id, e.g. phoenix_az"),
    temperature_c: float = Query(..., description="Current ambient temp in Celsius"),
):
    if get_city_metadata(city) is None:
        raise HTTPException(status_code=404, detail=f"Unknown city '{city}'")

    result = get_env_params(city, temperature_c)
    if result["status"] == "error":
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.get("/env-intel-all")
def env_intel_all(temperature_c: float = Query(35.0)):
    """Environmental parameters for ALL 5 cities in one call, for the Heat Intel tab."""
    out = []
    for city_id in CITY_METADATA:
        out.append(get_env_params(city_id, temperature_c))
    return {"cities": out}