"""
scale_loads_to_feeder.py

Purpose:
    Combine the two datasets prepared so far:
      1. IEEE123 feeder topology + nominal load ratings (outputs/grid_summary.json)
      2. NREL ResStock statewide AZ cooling-load timeseries (data/load/...)

    ...to produce a MODELED, time-varying load estimate for every load point
    on the feeder across a chosen demo day (default: the hottest cooling day
    found earlier, e.g. 2018-07-25).

    Method (explicitly labeled MODELED/ASSUMED per proposal Section 2.3/9):
      - Take the statewide cooling curve for the chosen day.
      - Convert it to a "multiplier" relative to that day's own average
        (multiplier = 1.0 at the day's average cooling load, >1 at peak,
        <1 overnight).
      - Apply the SAME multiplier to every feeder load's nominal kW rating.
      - This assumes each load's demand rises and falls proportionally with
        the statewide AC-driven demand curve -- a simplification used only
        because we do not have per-transformer historical demand data
        (that would require real utility SCADA access, which is explicitly
        out of scope for this hackathon prototype).

Usage:
    python scale_loads_to_feeder.py \
        --grid-summary outputs/grid_summary.json \
        --cooling-csv data/load/az_singlefamily_cooling.csv \
        --date 2018-07-25

Output:
    outputs/scaled_feeder_load_<date>.csv
        columns: timestamp, load_name, bus, nominal_kw, multiplier, scaled_kw
    outputs/feeder_total_load_<date>.csv
        columns: timestamp, total_feeder_kw
    Console: peak total feeder load and the time it occurs.
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

COOLING_COL = "out.electricity.cooling.energy_consumption.kwh"
TIMESTAMP_COL = "timestamp"


def load_grid_summary(path: Path) -> list:
    if not path.exists():
        sys.exit(f"ERROR: grid summary not found: {path}. "
                  f"Run load_feeder.py first.")
    with open(path) as f:
        data = json.load(f)
    loads = data.get("loads", [])
    if not loads:
        sys.exit("ERROR: no loads found in grid summary JSON.")
    print(f"Loaded {len(loads)} feeder loads from {path}")
    return loads


def load_cooling_day(csv_path: Path, date: str) -> pd.DataFrame:
    if not csv_path.exists():
        sys.exit(f"ERROR: cooling CSV not found: {csv_path}")

    df = pd.read_csv(csv_path, usecols=[TIMESTAMP_COL, COOLING_COL])
    df[TIMESTAMP_COL] = pd.to_datetime(df[TIMESTAMP_COL])

    day_df = df[df[TIMESTAMP_COL].dt.date.astype(str) == date].copy()
    if day_df.empty:
        sys.exit(f"ERROR: no rows found for date {date} in {csv_path}")

    print(f"Loaded {len(day_df)} cooling-load intervals for {date}")
    return day_df.sort_values(TIMESTAMP_COL).reset_index(drop=True)


def compute_multiplier(day_df: pd.DataFrame) -> pd.DataFrame:
    mean_val = day_df[COOLING_COL].mean()
    if mean_val == 0:
        sys.exit("ERROR: mean cooling load is zero, cannot compute multiplier.")
    day_df["multiplier"] = day_df[COOLING_COL] / mean_val
    return day_df


def scale_loads(loads: list, day_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for load in loads:
        for _, r in day_df.iterrows():
            rows.append({
                "timestamp": r[TIMESTAMP_COL],
                "load_name": load["name"],
                "bus": load["bus"],
                "nominal_kw": load["kw"],
                "multiplier": r["multiplier"],
                "scaled_kw": load["kw"] * r["multiplier"],
            })
    result = pd.DataFrame(rows)
    print(f"Generated {len(result):,} scaled load rows "
          f"({len(loads)} loads x {len(day_df)} intervals)")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid-summary", type=Path,
                         default=Path("outputs/grid_summary.json"))
    parser.add_argument("--cooling-csv", type=Path,
                         default=Path("data/load/az_singlefamily_cooling.csv"))
    parser.add_argument("--date", type=str, default="2018-07-25",
                         help="Demo day in YYYY-MM-DD format")
    parser.add_argument("--outdir", type=Path, default=Path("outputs"))
    args = parser.parse_args()

    loads = load_grid_summary(args.grid_summary)
    day_df = load_cooling_day(args.cooling_csv, args.date)
    day_df = compute_multiplier(day_df)

    scaled = scale_loads(loads, day_df)

    args.outdir.mkdir(parents=True, exist_ok=True)
    per_load_path = args.outdir / f"scaled_feeder_load_{args.date}.csv"
    scaled.to_csv(per_load_path, index=False)
    print(f"Saved per-load detail: {per_load_path}")

    totals = (
        scaled.groupby("timestamp")["scaled_kw"]
        .sum()
        .reset_index()
        .rename(columns={"scaled_kw": "total_feeder_kw"})
    )
    totals_path = args.outdir / f"feeder_total_load_{args.date}.csv"
    totals.to_csv(totals_path, index=False)
    print(f"Saved feeder total load curve: {totals_path}")

    peak_row = totals.loc[totals["total_feeder_kw"].idxmax()]
    print(f"\nPeak total feeder load: {peak_row['total_feeder_kw']:,.1f} kW "
          f"at {peak_row['timestamp']}")


if __name__ == "__main__":
    main()