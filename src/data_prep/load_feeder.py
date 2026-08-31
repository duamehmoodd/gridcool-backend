"""
load_feeder.py

Purpose:
    Load the IEEE123 test feeder (OpenDSS format) and extract the basic
    grid topology needed for the USGridCool Risk Agent:
      - All bus names (used later for mapping load/transformer locations)
      - All transformers and their rated capacity (kVA)
      - All load points and their nominal kW rating

    This is Person 1's second core deliverable per the build plan
    (Days 1-2: "load the open feeder model and define the risk score").

    IMPORTANT (per proposal Section 2.3 / 9):
    IEEE123 is a PUBLIC TEST FEEDER, not a real Phoenix utility feeder.
    All transformer/load values printed here are MODELED/ASSUMED test-case
    data, used to demonstrate the pipeline -- not live utility telemetry.

Usage:
    python load_feeder.py --master data/grid/IEEE123/IEEE123Master.dss

Output:
    Console printout of bus list, transformer list w/ ratings, load list w/ ratings.
    outputs/grid_summary.json -- machine-readable version for later pipeline stages.
"""

import argparse
import json
import sys
import os
from pathlib import Path

import opendssdirect as dss


def load_feeder(master_path: Path) -> None:
    if not master_path.exists():
        sys.exit(f"ERROR: master file not found: {master_path}")

    print(f"Loading feeder from {master_path} ...")

    # OpenDSS needs to run from the directory containing the master file,
    # since it uses relative Redirect statements internally to pull in
    # Loads/Regulators/Switches/LineCodes.
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
        print("WARNING: power flow did not converge -- topology data is still usable, "
              "but voltage results (if used later) would not be reliable.")
    else:
        print("Power flow converged OK.")


def summarize_buses() -> list:
    buses = dss.Circuit.AllBusNames()
    print(f"\n--- Buses ({len(buses)}) ---")
    for b in buses:
        print(f"  {b}")
    return buses


def summarize_transformers() -> list:
    names = dss.Transformers.AllNames()
    print(f"\n--- Transformers ({len(names)}) ---")
    transformers = []
    for name in names:
        dss.Transformers.Name(name)
        kva = dss.Transformers.kVA()
        num_windings = dss.Transformers.NumWindings()
        print(f"  {name:20s}  rated={kva:>8.1f} kVA  windings={num_windings}")
        transformers.append({"name": name, "rated_kva": kva, "windings": num_windings})
    return transformers


def summarize_loads() -> list:
    names = dss.Loads.AllNames()
    print(f"\n--- Loads ({len(names)}) ---")
    loads = []
    for name in names:
        dss.Loads.Name(name)
        kw = dss.Loads.kW()
        bus = dss.CktElement.BusNames()[0] if dss.CktElement.BusNames() else "?"
        print(f"  {name:20s}  {kw:>8.2f} kW  @ bus {bus}")
        loads.append({"name": name, "kw": kw, "bus": bus})
    return loads


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--master",
        type=Path,
        default=Path("data/grid/IEEE123/IEEE123Master.dss"),
        help="Path to the feeder's OpenDSS master file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/grid_summary.json"),
        help="Path to save a JSON summary of the feeder",
    )
    args = parser.parse_args()

    load_feeder(args.master)

    buses = summarize_buses()
    transformers = summarize_transformers()
    loads = summarize_loads()

    summary = {
        "source": "IEEE123 test feeder (public, GridAPPS-D Powergrid-Models) -- MODELED/ASSUMED, not real utility data",
        "num_buses": len(buses),
        "buses": buses,
        "transformers": transformers,
        "loads": loads,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved summary: {args.output}")


if __name__ == "__main__":
    main()