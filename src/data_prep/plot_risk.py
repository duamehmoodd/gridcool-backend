"""
plot_risk.py

Purpose:
    Plot each monitored transformer/regulator's %loading across the demo day,
    with the risk threshold overlaid, so the July 25 heat-driven overload
    (reg1a hitting 139.3%) is immediately visible -- this is the single
    chart that best tells the USGridCool story.

Usage:
    python plot_risk.py --input outputs/risk_timeseries_2018-07-25.csv --threshold 100

Output:
    outputs/figures/risk_2018-07-25.png
"""

import argparse
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path,
                         default=Path("outputs/risk_timeseries_2018-07-25.csv"))
    parser.add_argument("--threshold", type=float, default=100.0)
    parser.add_argument("--output", type=Path,
                         default=Path("outputs/figures/risk_2018-07-25.png"))
    args = parser.parse_args()

    df = pd.read_csv(args.input, parse_dates=["timestamp"])

    fig, ax = plt.subplots(figsize=(10, 5))
    for xfmr, group in df.groupby("transformer"):
        ax.plot(group["timestamp"], group["pct_loaded"], linewidth=2, label=xfmr)

    ax.axhline(args.threshold, color="red", linestyle="--", linewidth=1.5,
               label=f"{args.threshold:.0f}% threshold")
    ax.fill_between(
        df["timestamp"], args.threshold, df["pct_loaded"].max() * 1.05,
        where=(df["pct_loaded"] > args.threshold), color="red", alpha=0.1
    )

    ax.set_title("Transformer/Regulator Loading — Heat-Driven Demand Day")
    ax.set_xlabel("Time of day")
    ax.set_ylabel("% of rated capacity")
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(args.output, dpi=150)
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()