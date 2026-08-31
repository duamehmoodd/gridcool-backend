"""
run_risk_agent.py (v2 — multi-transformer scan for PNNL IEEE9500 feeder)

Purpose:
    Updated Risk Agent for the PNNL IEEE9500 feeder, which has 1,305
    transformers (unlike IEEE123's 8 regulators). Instead of monitoring
    one hardcoded transformer, this version:
      1. Automatically filters to RESIDENTIAL-scale transformers only
         (<= MAX_RESIDENTIAL_KVA), excluding substation-scale transformers.
      2. Runs the power flow across the day with heat-scaled loads.
      3. Ranks all residential transformers by peak %loading.
      4. Reports the top N most-stressed transformers -- this is the
         actual "which neighborhood transformer is at risk" answer.

    NOTE per proposal Section 2.3/9 (MODELED/ASSUMED disclosure):
      - PNNL IEEE9500 is a public synthetic test feeder, not real
        Phoenix utility infrastructure.
      - The load multiplier is derived from STATEWIDE Arizona ResStock
        cooling data, applied uniformly -- a simplification.

Usage:
    python run_risk_agent.py \
        --master data/grid/PNNL_IEEE9500/Master-bal-initial-config.dss \
        --cooling-csv data/load/az_singlefamily_cooling.csv \
        --date 2018-07-25 \
        --threshold 100 \
        --max-residential-kva 100 \
        --top-n 10

Output:
    outputs/risk_timeseries_<date>.csv   -- top N transformers, full day
    outputs/risk_summary_<date>.json     -- peak stats per top transformer
    Console: plain-language ranked summary.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd
import opendssdirect as dss

COOLING_COL = "out.electricity.cooling.energy_consumption.kwh"
TIMESTAMP_COL = "timestamp"


def load_feeder(master_path: Path) -> None:
    if not master_path.exists():
        sys.exit(f"ERROR: master file not found: {master_path}")

    print(f"Loading feeder from {master_path} ...")
    original_cwd = Path.cwd()
    try:
        os.chdir(master_path.parent)
        result = dss.Command(f"Redirect {master_path.name}")
        if result:
            print(f"WARNING from OpenDSS: {result}")
    finally:
        os.chdir(original_cwd)

    dss.Solution.Solve()
    if not dss.Solution.Converged():
        sys.exit("ERROR: initial power flow did not converge. Check feeder files.")
    print("Initial power flow converged OK.")
def configure_solver():
    dss.Solution.MaxControlIterations(100)
    dss.Solution.MaxIterations(100)
    dss.Solution.Convergence(0.001)
    dss.Text.Command("Set ControlMode=STATIC")
def solve_with_ramp(nominal: dict, target_mult: float, steps: int = 20) -> bool:
    """
    Ramps load gradually up to target_mult, solving at each intermediate
    step, instead of jumping straight from the previous state to a
    stressed multiplier in one solve. Keeps the solver near a known-good
    solution at each step rather than asking it to find a stressed
    solution cold. Returns True if the FINAL solve converged.
    """
    for step in range(1, steps + 1):
        step_mult = target_mult * (step / steps)
        for name, base_kw in nominal.items():
            dss.Loads.Name(name)
            dss.Loads.kW(base_kw * step_mult)
        dss.Solution.Solve()
    return dss.Solution.Converged()

def get_residential_transformers(max_kva: float) -> list:
    all_names = dss.Transformers.AllNames()
    residential = []
    for name in all_names:
        dss.Transformers.Name(name)
        kva = dss.Transformers.kVA()
        if kva <= max_kva:
            residential.append(name)
    print(f"Total transformers: {len(all_names)}")
    print(f"Residential-scale (<= {max_kva} kVA): {len(residential)}")
    print(f"Excluded (substation/feeder-scale): {len(all_names) - len(residential)}")
    return residential


def capture_nominal_loads() -> dict:
    nominal = {}
    for name in dss.Loads.AllNames():
        dss.Loads.Name(name)
        nominal[name] = dss.Loads.kW()
    print(f"Captured nominal kW for {len(nominal)} loads.")
    return nominal


def load_cooling_day(csv_path: Path, date: str) -> pd.DataFrame:
    if not csv_path.exists():
        sys.exit(f"ERROR: cooling CSV not found: {csv_path}")

    # Different ResStock export releases use slightly different column
    # naming (single vs double dot before 'kwh'). Read just the header
    # first, then match whichever variant is actually present.
    header = pd.read_csv(csv_path, nrows=0).columns.tolist()
    cooling_col_variants = [
        "out.electricity.cooling.energy_consumption.kwh",
        "out.electricity.cooling.energy_consumption..kwh",
    ]
    cooling_col = next((c for c in cooling_col_variants if c in header), None)
    if cooling_col is None:
        sys.exit(f"ERROR: no recognized cooling column found in {csv_path}. "
                  f"Checked: {cooling_col_variants}")

    df = pd.read_csv(csv_path, usecols=[TIMESTAMP_COL, cooling_col])
    df = df.rename(columns={cooling_col: COOLING_COL})  # normalize downstream
    df[TIMESTAMP_COL] = pd.to_datetime(df[TIMESTAMP_COL])
    day_df = df[df[TIMESTAMP_COL].dt.date.astype(str) == date].copy()
    if day_df.empty:
        sys.exit(f"ERROR: no rows found for date {date} in {csv_path}")
    mean_val = day_df[COOLING_COL].mean()
    day_df["multiplier"] = day_df[COOLING_COL] / mean_val
    return day_df.sort_values(TIMESTAMP_COL).reset_index(drop=True)

def pct_loaded(transformer_name: str) -> float:
    """
    Returns the WORST (highest) %loading across all windings of this
    transformer, correctly matching each winding's current to its OWN
    rated amps (computed from that winding's own kVA/kV, not mixing
    windings -- the bug that produced impossible 3000%+ readings on
    3-winding center-tapped service transformers).
    """
    dss.Transformers.Name(transformer_name)
    dss.Circuit.SetActiveElement(f"Transformer.{transformer_name}")

    num_windings = dss.Transformers.NumWindings()
    all_currents = dss.CktElement.CurrentsMagAng()[0::2]  # magnitudes only
    num_conductors = dss.CktElement.NumConductors()

    worst_pct = 0.0

    for wdg in range(1, num_windings + 1):
        dss.Transformers.Wdg(wdg)
        wdg_kva = dss.Transformers.kVA()
        wdg_kv = dss.Transformers.kV()
        if wdg_kva <= 0 or wdg_kv <= 0:
            continue
        normamps = (wdg_kva / wdg_kv)  # rated amps for THIS winding

        start = (wdg - 1) * num_conductors
        end = start + num_conductors
        wdg_currents = all_currents[start:end]
        if not wdg_currents:
            continue

        max_amp = max(wdg_currents)
        pct = (max_amp / normamps) * 100
        if pct > worst_pct:
            worst_pct = pct

    return worst_pct
def run_timeseries(nominal: dict, day_df: pd.DataFrame, candidates: list) -> tuple:
    rows = []
    non_converged = []  # NEW: track skipped intervals
    n = len(day_df)
    for i, r in day_df.iterrows():
        mult = r["multiplier"]
        converged: bool = solve_with_ramp(nominal, mult)
        if not converged:
            print(f"  WARNING: no convergence at {r[TIMESTAMP_COL]}, mult={mult:.3f}, skipping interval.")
            non_converged.append({
                "timestamp": str(r[TIMESTAMP_COL]),
                "multiplier": round(float(mult), 3),
            })
            continue

        for xfmr in candidates:
            pct = pct_loaded(xfmr)
            rows.append({
                "timestamp": r[TIMESTAMP_COL],
                "transformer": xfmr,
                "pct_loaded": pct,
            })

        if (i + 1) % 24 == 0 or (i + 1) == n:
            print(f"  Solved {i + 1}/{n} intervals...")

    return pd.DataFrame(rows), non_converged  # NEW: return both
def find_top_n_at_peak(nominal: dict, day_df: pd.DataFrame, candidates: list, top_n: int) -> list:
    """
    Fast first pass: solve only at the day's peak multiplier to find which
    transformers are worth tracking in full detail (avoids solving 96
    intervals x 1000+ transformers, which would be extremely slow).
    """
    peak_row = day_df.loc[day_df["multiplier"].idxmax()]
    print(f"\nFinding top {top_n} stressed transformers at peak "
          f"(multiplier={peak_row['multiplier']:.2f}, {peak_row[TIMESTAMP_COL]})...")
    solve_with_ramp(nominal, peak_row["multiplier"])
    results = [(name, pct_loaded(name)) for name in candidates]
    results.sort(key=lambda x: x[1], reverse=True)

    top = [name for name, pct in results[:top_n]]
    print("Top candidates at peak:")
    for name, pct in results[:top_n]:
        print(f"  {name:15s}  {pct:6.1f}%")
    return top

def summarize_risk(results: pd.DataFrame, threshold: float, non_converged: list, total_intervals: int) -> dict:
    xfmr_summary = {}
    for xfmr, group in results.groupby("transformer"):
        peak_row = group.loc[group["pct_loaded"].idxmax()]
        crossed = group["pct_loaded"] > threshold
        xfmr_summary[xfmr] = {
            "peak_pct_loaded": round(float(peak_row["pct_loaded"]), 1),
            "peak_time": str(peak_row["timestamp"]),
            "threshold_pct": threshold,
            "crossed_threshold": bool(crossed.any()),
            "hours_over_threshold": round(crossed.sum() * 0.25, 2),
        }
    xfmr_summary = dict(sorted(xfmr_summary.items(), key=lambda kv: kv[1]["peak_pct_loaded"], reverse=True))

    # NEW: voltage instability block
    voltage_instability = {
        "non_converged_intervals": len(non_converged),
        "total_intervals": total_intervals,
        "non_converged_hours": round(len(non_converged) * 0.25, 2),
        "non_converged_windows": non_converged,
        "interpretation": (
            "Intervals where the power-flow solver failed to reach a stable solution "
            "under this heat-driven demand scenario. Non-convergence at high load is a "
            "recognized proxy for voltage instability / collapse risk, not a data error."
        ),
    }

    return {
        "transformer_risk": xfmr_summary,
        "voltage_instability": voltage_instability,
    }

def print_plain_language_summary(summary: dict) -> None:
    xfmr_summary = summary["transformer_risk"]
    vi = summary["voltage_instability"]

    print("\n=== RISK SUMMARY (ranked by peak loading) ===")
    for xfmr, info in xfmr_summary.items():
        status = "AT RISK" if info["crossed_threshold"] else "OK"
        print(f"\nTransformer: {xfmr}  [{status}]")
        print(f"  Peak loading: {info['peak_pct_loaded']}% of rated capacity")
        print(f"  Occurs at:    {info['peak_time']}")
        if info["crossed_threshold"]:
            print(f"  Over {info['threshold_pct']}% threshold for "
                  f"{info['hours_over_threshold']} hours on this day.")
        else:
            print(f"  Stayed under the {info['threshold_pct']}% threshold all day.")

    print("\n=== VOLTAGE INSTABILITY (solver non-convergence) ===")
    print(f"  {vi['non_converged_intervals']} of {vi['total_intervals']} intervals "
          f"({vi['non_converged_hours']} hours) did not converge.")
    if vi["non_converged_intervals"] > 0:
        first = vi["non_converged_windows"][0]["timestamp"]
        last = vi["non_converged_windows"][-1]["timestamp"]
        print(f"  Window: {first} → {last}")
        print(f"  {vi['interpretation']}")
def run_live_snapshot(city: str, master_path: Path, max_residential_kva: float,
                       threshold: float, top_n: int) -> dict:
    """
    Runs one live risk snapshot for a city using real-time FortyGuard heat data.
    Returns a dict (not printed) so this is callable from both CLI and API.
    """
    from demand_model import predict_multiplier_from_heat

    load_feeder(master_path)
    configure_solver()
    residential = get_residential_transformers(max_residential_kva)
    nominal = capture_nominal_loads()

    live = predict_multiplier_from_heat(city, verbose=False)
    if live["status"] != "ok":
        return {"status": "error", "city": city, "note": live["note"]}

    mult = live["predicted_multiplier"]
    for name, base_kw in nominal.items():
        dss.Loads.Name(name)
        dss.Loads.kW(base_kw * mult)
    dss.Solution.Solve()

    results = [(name, pct_loaded(name)) for name in residential]
    results.sort(key=lambda x: x[1], reverse=True)
    top = results[:top_n]

    return {
        "status": "ok",
        "city": city,
        "heat_index_c": live["heat_index_c"],
        "predicted_multiplier": mult,
        "transformer_risk": {
            name: {"peak_pct_loaded": round(pct, 1), "crossed_threshold": pct > threshold}
            for name, pct in top
        },
    }
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path,
                         default=Path("data/grid/PNNL_IEEE9500/Master-bal-initial-config.dss"))
    parser.add_argument("--city", type=str, default="phoenix_az",
                         help="City folder name under data/load/<city>/cooling.csv")
    parser.add_argument("--date", type=str, default="2018-07-25")
    parser.add_argument("--threshold", type=float, default=100.0)
    parser.add_argument("--max-residential-kva", type=float, default=100.0,
                         help="Transformers above this kVA are excluded as substation-scale")
    parser.add_argument("--top-n", type=int, default=10,
                         help="Number of most-stressed transformers to track in detail")
    parser.add_argument("--outdir", type=Path, default=Path("outputs"))
    parser.add_argument("--live", action="store_true",
                         help="Use live FortyGuard heat data for a single-snapshot risk check, "
                              "instead of the historical ResStock day curve.")
    args = parser.parse_args()

    if args.live:
        result = run_live_snapshot(args.city, args.master, args.max_residential_kva,
                                     args.threshold, args.top_n)
        print(json.dumps(result, indent=2))
        return

    load_feeder(args.master)
    configure_solver()
    residential = get_residential_transformers(args.max_residential_kva)
    nominal = capture_nominal_loads()
    
    cooling_csv = Path("data/load") / args.city / "cooling.csv"
    day_df = load_cooling_day(cooling_csv, args.date)
    # Fast pass: find the worst offenders at peak load only
    top_candidates = find_top_n_at_peak(nominal, day_df, residential, args.top_n)

    # Full day timeseries, but only for the top candidates (keeps runtime reasonable)
    print(f"\nRunning full-day power flow for top {len(top_candidates)} transformers "
          f"across {len(day_df)} intervals...")
    results, non_converged = run_timeseries(nominal, day_df, top_candidates)   # CHANGED: unpack tuple

    if results.empty:
        sys.exit("ERROR: no successful power flow solves -- nothing to report.")

    args.outdir.mkdir(parents=True, exist_ok=True)
    ts_path = args.outdir / f"risk_timeseries_{args.city}_{args.date}.csv"
    results.to_csv(ts_path, index=False)
    print(f"\nSaved: {ts_path}")

    summary = summarize_risk(results, args.threshold, non_converged, len(day_df))  # CHANGED: extra args
    summary_path = args.outdir / f"risk_summary_{args.city}_{args.date}.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Saved: {summary_path}")

    print_plain_language_summary(summary)


if __name__ == "__main__":
    main()