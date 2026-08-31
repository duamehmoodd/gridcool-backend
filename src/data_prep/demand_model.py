"""
src/data_prep/demand_model.py

Demand Prediction Model -- Layer 2 of the required architecture:
    FortyGuard API -> Heat Data Agent -> Demand Prediction Model ->
    Risk Agent -> Decision Agent -> Dashboard

Converts a LIVE heat index reading (from heat_data_agent.py) into a
cooling-demand multiplier -- the same kind of number run_risk_agent.py
already consumes from historical ResStock data (mult = cooling_kwh /
mean_cooling_kwh across a day).

Why this calibration approach, not a black-box model:
    We don't have a trained ML demand model (out of scope for a hackathon
    timeline), and a fabricated one would be worse than an honest, simple,
    EXPLAINABLE mapping -- which also matches this project's stated
    Explainability requirement. So instead we anchor the live heat index to
    the REAL peak multiplier each city already showed in its historical
    ResStock run (already computed and stored in risk_summary_<city>_<date>.json
    indirectly via the day's data). This is a simple piecewise-linear
    calibration: as heat index rises from a comfortable baseline toward each
    city's own historically-observed peak conditions, the multiplier scales
    from 1.0 (no extra cooling load) toward that city's known historical
    peak multiplier -- not an invented number, but a reasonable interpolation
    grounded in real prior data for that specific city.

    This is explicitly a MODELED/ASSUMED simplification, consistent with the
    project's stated labeling requirement (proposal Section 2.3, 9). It is
    NOT a claim of forecasting accuracy.

Usage (standalone):
    python src/data_prep/demand_model.py --city phoenix_az

Also importable:
    from src.data_prep.demand_model import predict_multiplier_from_heat
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from heat_data_agent import get_live_heat

# Comfortable baseline heat index (deg C) below which we assume no extra
# AC-driven demand beyond normal (multiplier = 1.0).
BASELINE_HEAT_INDEX_C = 27.0

# Each city's known peak multiplier + the heat index that roughly produced it,
# from the historical ResStock runs already completed. This anchors the live
# model to real, previously observed data per city instead of one generic
# curve for the whole country (different climates respond differently).
#
# heat_index_at_peak_c is an approximation of that city's July 25, 2018 peak
# conditions -- update these if you re-run historical data and get a more
# precise figure per city.
CITY_CALIBRATION = {
    "phoenix_az":    {"peak_multiplier": 1.54, "heat_index_at_peak_c": 43.0},
    "dallas_tx":     {"peak_multiplier": 1.67, "heat_index_at_peak_c": 41.0},
    "vegas_nv":      {"peak_multiplier": 1.54, "heat_index_at_peak_c": 44.0},
    "atlanta_ga":    {"peak_multiplier": 1.84, "heat_index_at_peak_c": 40.0},
    "sacramento_ca": {"peak_multiplier": 1.88, "heat_index_at_peak_c": 39.0},
}

DEFAULT_CALIBRATION = {"peak_multiplier": 1.6, "heat_index_at_peak_c": 41.0}


def predict_multiplier_from_heat_index(city: str, heat_index_c: float) -> float:
    """
    Piecewise-linear: multiplier = 1.0 at BASELINE_HEAT_INDEX_C, scaling up to
    that city's known peak_multiplier at heat_index_at_peak_c. Clamped so a
    reading above the historical peak doesn't extrapolate wildly, and a
    reading below baseline never goes under 1.0 (a mild day isn't modeled as
    REDUCING demand below normal in this simple version).
    """
    cal = CITY_CALIBRATION.get(city, DEFAULT_CALIBRATION)
    peak_mult = cal["peak_multiplier"]
    peak_hi = cal["heat_index_at_peak_c"]

    if heat_index_c <= BASELINE_HEAT_INDEX_C:
        return 1.0
    if heat_index_c >= peak_hi:
        return peak_mult

    frac = (heat_index_c - BASELINE_HEAT_INDEX_C) / (peak_hi - BASELINE_HEAT_INDEX_C)
    return round(1.0 + frac * (peak_mult - 1.0), 3)


def predict_multiplier_from_heat(city: str, verbose: bool = False) -> dict:
    """
    Full pipeline: pulls live heat via heat_data_agent, then predicts the
    multiplier. Returns a dict with both the raw heat data and the derived
    multiplier, or a graceful error/fallback if live heat data isn't available.
    """
    heat = get_live_heat(city, verbose=verbose)

    if heat["status"] != "ok" or heat["heat_index_c"] is None:
        return {
            "city": city,
            "status": "fallback",
            "predicted_multiplier": None,
            "heat_index_c": None,
            "heat_source": heat,
            "note": (
                "Live FortyGuard heat data unavailable -- caller should fall back "
                "to the historical ResStock multiplier for this city instead."
            ),
        }

    mult = predict_multiplier_from_heat_index(city, heat["heat_index_c"])
    cal = CITY_CALIBRATION.get(city, DEFAULT_CALIBRATION)

    return {
        "city": city,
        "status": "ok",
        "predicted_multiplier": mult,
        "heat_index_c": heat["heat_index_c"],
        "heat_index_f": heat["heat_index_f"],
        "calibration_used": cal,
        "heat_source": heat,
        "note": (
            f"Modeled/assumed: linear interpolation between baseline "
            f"({BASELINE_HEAT_INDEX_C}C -> 1.0x) and this city's historical peak "
            f"({cal['heat_index_at_peak_c']}C -> {cal['peak_multiplier']}x)."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city", type=str, required=True)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    result = predict_multiplier_from_heat(args.city, verbose=args.verbose)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()