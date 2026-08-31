"""
src/data_prep/decision_agent.py

Decision Agent -- turns the raw risk_summary_<date>.json (produced by
run_risk_agent.py) into plain-language, operator-style alerts:
  - which transformers are at risk, ranked by severity
  - a load-shed priority order (worst first)
  - a plain-language statement of the voltage-instability window

This is deliberately simple and rule-based (no ML) -- transparent and
defensible for a hackathon demo where judges may ask "how does this decide
what's risky."

Usage (standalone):
    python src/data_prep/decision_agent.py
    python src/data_prep/decision_agent.py --summary outputs/risk_summary_2018-07-25.json

Output:
    outputs/decision_alerts_<date>.json
    Console: plain-language alert text

Also importable:
    from src.data_prep.decision_agent import generate_decision

so the FastAPI /decision endpoint can call the same logic without
shelling out to a subprocess.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional


# Severity bands for plain-language framing. Purely for wording, not new logic --
# the underlying numbers (peak_pct_loaded, crossed_threshold) already come from
# run_risk_agent.py.
def _severity_label(peak_pct: float) -> str:
    if peak_pct >= 135:
        return "critical"
    elif peak_pct >= 115:
        return "high"
    else:
        return "elevated"


def generate_decision(summary: dict, heat_alert: dict = None) -> dict:
    """
    summary: the dict loaded from risk_summary_<date>.json, with shape
        {"transformer_risk": {...}, "voltage_instability": {...}}

    Returns a decision dict with plain-language alerts and a load-shed
    priority list, ready to serialize to JSON or print.
    """
    xfmr_risk = summary.get("transformer_risk", {})
    voltage = summary.get("voltage_instability", {})

    at_risk = {
        name: info for name, info in xfmr_risk.items()
        if info.get("crossed_threshold")
    }
    # already sorted by peak_pct_loaded descending, coming from run_risk_agent.py,
    # but re-sort defensively in case this summary came from elsewhere.
    ranked = sorted(at_risk.items(), key=lambda kv: kv[1]["peak_pct_loaded"], reverse=True)

    load_shed_priority = [name for name, _ in ranked]

    alerts = []
    for name, info in ranked:
        sev = _severity_label(info["peak_pct_loaded"])
        peak_time = info.get("peak_time")
        hours_over = info.get("hours_over_threshold")

        if peak_time is not None and hours_over is not None:
            message = (
                f"Transformer {name} reached {info['peak_pct_loaded']}% of rated "
                f"capacity at {peak_time} and stayed over threshold for "
                f"{hours_over} hours -- {sev} risk of thermal damage "
                f"or localized outage if this heat pattern continues."
            )
        else:
            message = (
                f"Transformer {name} is currently at {info['peak_pct_loaded']}% of "
                f"rated capacity (live snapshot) -- {sev} risk of thermal damage "
                f"or localized outage if this heat pattern continues."
            )

        alerts.append({
            "transformer": name,
            "severity": sev,
            "peak_pct_loaded": info["peak_pct_loaded"],
            "peak_time": peak_time,
            "hours_over_threshold": hours_over,
            "message": message,
        })
    n_noncon = voltage.get("non_converged_intervals", 0)
    total = voltage.get("total_intervals", 0)
    hours = voltage.get("non_converged_hours", 0)
    if n_noncon > 0 and voltage.get("non_converged_windows"):
        first = voltage["non_converged_windows"][0]["timestamp"]
        last = voltage["non_converged_windows"][-1]["timestamp"]
        voltage_message = (
            f"The power-flow solver failed to find a stable solution for {n_noncon} of "
            f"{total} intervals ({hours} hours), between {first} and {last}. This is a "
            f"recognized proxy for voltage instability under extreme heat-driven demand, "
            f"separate from the transformer overload findings above."
        )
    else:
        voltage_message = "No voltage instability detected -- solver converged for all intervals."

    top_line = (
        f"{len(load_shed_priority)} transformers are at risk under today's heat-driven demand. "
        f"Highest priority for load-shed or reinforcement: {load_shed_priority[0]}."
        if load_shed_priority else
        "No transformers exceeded the risk threshold today."
    )

    if heat_alert and heat_alert.get("has_active_heat_alert"):
        alert = heat_alert["alerts"][0]
        heat_alert_message = (
            f"NOAA has an active {alert['event']} in effect for this area "
            f"(expires {alert['expires']}) -- this is real, live confirmation that "
            f"today's heat-driven transformer risk is not hypothetical."
        )
    elif heat_alert:
        heat_alert_message = "NOAA reports no active heat alert for this area at this time."
    else:
        heat_alert_message = None

    return {
        "headline": top_line,
        "load_shed_priority": load_shed_priority,
        "transformer_alerts": alerts,
        "voltage_instability_message": voltage_message,
        "heat_alert_message": heat_alert_message,
    }
def print_decision(decision: dict) -> None:
    print("\n=== DECISION AGENT: PLAIN-LANGUAGE ALERT ===\n")
    print(decision["headline"])
    print()
    for alert in decision["transformer_alerts"]:
        print(f"[{alert['severity'].upper()}] {alert['message']}")
    print()
    print(decision["voltage_instability_message"])
    print()
    if decision.get("heat_alert_message"):
        print(decision["heat_alert_message"])
        print()
    if decision["load_shed_priority"]:
        print("Recommended load-shed / reinforcement priority order:")
        for i, name in enumerate(decision["load_shed_priority"], 1):
            print(f"  {i}. {name}")
            
def _latest_summary_file(outdir: Path) -> Optional[Path]:
    matches = sorted(outdir.glob("risk_summary_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=None,
                         help="Path to risk_summary_<date>.json. Defaults to the most recent one in --outdir.")
    parser.add_argument("--outdir", type=Path, default=Path("outputs"))
    args = parser.parse_args()

    summary_path = args.summary or _latest_summary_file(args.outdir)
    if summary_path is None or not summary_path.exists():
        sys.exit(f"ERROR: no risk_summary_*.json found. Run run_risk_agent.py first, "
                  f"or pass --summary explicitly.")

    with open(summary_path) as f:
        summary = json.load(f)

    decision = generate_decision(summary)

    # date suffix mirrors the input filename, e.g. risk_summary_2018-07-25.json -> ..._2018-07-25.json
    suffix = summary_path.stem.replace("risk_summary_", "")
    out_path = args.outdir / f"decision_alerts_{suffix}.json"
    with open(out_path, "w") as f:
        json.dump(decision, f, indent=2)

    print_decision(decision)
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()