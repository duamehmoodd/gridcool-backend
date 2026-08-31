"""
src/api/main.py

FastAPI wrapper around the GridCool risk agent (run_risk_agent.py).

Endpoints:
    GET  /health              -> quick liveness check
    GET  /risk-summary        -> latest saved risk_summary_<date>.json
    GET  /risk-timeseries     -> latest saved risk_timeseries_<date>.csv, as JSON
    POST /run                 -> kicks off a fresh run_risk_agent.py run in the
                                  background (non-blocking) and returns immediately
    GET  /run-status          -> poll this after POST /run to see if it's done

Design choice (per hackathon time constraints):
    Saved-results endpoints are instant and safe for a live demo -- no risk of
    a crash or multi-minute wait mid-presentation. /run is available if you
    want to prove the pipeline is live/real, but it runs in the background so
    it never blocks the demo.

Run with:
    uvicorn src.api.main:app --reload --port 8000
(run this from the GridCool project root, so relative paths below resolve correctly)
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.data_prep.noaa_alerts import get_heat_alerts
from src.data_prep.eia_demand import get_grid_demand
from src.data_prep.run_risk_agent import run_live_snapshot
from src.data_prep.decision_agent import generate_decision
from src.api.auto_evaluator import AutoEvaluator
from src.api.extra_routes import router as extra_router
from dotenv import load_dotenv
load_dotenv("temperature-api-quickstart/.env")

from fastapi import FastAPI

import os
# ---- Config: adjust these two paths/names if your layout differs ----------
PROJECT_ROOT = Path(__file__).resolve().parents[2]   # GridCool/
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
AGENT_SCRIPT = PROJECT_ROOT / "src" / "data_prep" / "run_risk_agent.py"
# -----------------------------------------------------------------------
app = FastAPI(title="GridCool Risk API")
app.include_router(extra_router)

# Allow the Node frontend (any localhost port) to call this during the hackathon.
# Tighten this to your actual frontend origin before any real deployment.



evaluator = AutoEvaluator(
    cities=["phoenix_az", "dallas_tx", "vegas_nv", "atlanta_ga", "sacramento_ca"],
    master_path=PROJECT_ROOT / "data/grid/PNNL_IEEE9500/Master-bal-initial-config.dss",
    interval_seconds=30, # 5 min; lower for demo if you want faster visible re-evaluation
)

@app.on_event("startup")
async def start_auto_eval():
    evaluator.start()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tracks the background /run process so /run-status can report on it.
_run_state = {"running": False, "returncode": None, "last_date": None}


def _latest_file(pattern: str) -> Optional[Path]:
    """Return the most recently modified file in outputs/ matching pattern, or None."""
    matches = sorted(OUTPUTS_DIR.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/risk-summary")
def get_risk_summary(city: Optional[str] = None):
    pattern = f"risk_summary_{city}_*.json" if city else "risk_summary_*.json"
    path = _latest_file(pattern)
    if path is None:
        raise HTTPException(status_code=404, detail="No risk_summary_*.json found in outputs/. Run the agent first.")
    with open(path) as f:
        data = json.load(f)
    return {"source_file": path.name, "data": data}


@app.get("/risk-timeseries")
def get_risk_timeseries(city: Optional[str] = None):
    pattern = f"risk_timeseries_{city}_*.csv" if city else "risk_timeseries_*.csv"
    path = _latest_file(pattern)
    if path is None:
        raise HTTPException(status_code=404, detail="No risk_timeseries_*.csv found in outputs/. Run the agent first.")
    df = pd.read_csv(path)
    return {"source_file": path.name, "rows": json.loads(df.to_json(orient="records"))}

from src.data_prep.run_risk_agent import run_live_snapshot

@app.get("/decision")
def get_decision(city: Optional[str] = None, prefer_live: bool = True):
    heat_alert = get_heat_alerts(city) if city else None

    data_mode = "historical"
    summary = None

    if prefer_live and city:
        cached = evaluator.get_cached(city)
        if cached and cached.get("status") == "ok":
            live_result = cached
        else:
            live_result = {"status": "error", "note": "no cached live data yet"}
        if live_result.get("status") == "ok":
            data_mode = "live"
            summary = {
                "transformer_risk": live_result["transformer_risk"],
                "voltage_instability": {},
            }

    if summary is None:
        pattern = f"risk_summary_{city}_*.json" if city else "risk_summary_*.json"
        path = _latest_file(pattern)
        if path is None:
            raise HTTPException(status_code=404, detail="No risk data available (live failed, no historical summary found). Run the agent first.")
        with open(path) as f:
            summary = json.load(f)

    decision = generate_decision(summary, heat_alert=heat_alert)
    decision["data_mode"] = data_mode
    return decision
@app.get("/live-risk-cached")
def live_risk_cached(city: str):
    """Instant — serves the auto-evaluator's cached latest result, no FortyGuard wait."""
    result = evaluator.get_cached(city)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No cached evaluation yet for '{city}'. Wait for the first auto-evaluation cycle or call /live-risk directly.")
    return result

@app.get("/audit-log")
def audit_log(limit: int = 50):
    return {"entries": evaluator.get_recent_audit_entries(limit)}

def _run_agent_blocking(city: str = "phoenix_az", date: str = "2018-07-25"):
    _run_state["running"] = True
    _run_state["returncode"] = None
    try:
        result = subprocess.run(
            [sys.executable, str(AGENT_SCRIPT), "--city", city, "--date", date],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=1800,
        )
        _run_state["returncode"] = result.returncode
        _run_state["stdout_tail"] = result.stdout[-2000:]
        _run_state["stderr_tail"] = result.stderr[-2000:]
    except Exception as e:
        _run_state["returncode"] = -1
        _run_state["stderr_tail"] = str(e)
    finally:
        _run_state["running"] = False


@app.post("/run")
def trigger_run(background_tasks: BackgroundTasks, city: str = "phoenix_az", date: str = "2018-07-25"):
    if _run_state["running"]:
        return {"status": "already_running"}
    background_tasks.add_task(_run_agent_blocking, city, date)
    return {"status": "started", "city": city, "date": date}

@app.get("/heat-alerts")
def heat_alerts(city: str):
    return get_heat_alerts(city)


@app.get("/grid-demand")
def grid_demand(city: str, hours: int = 24):
    api_key = os.environ.get("EIA_API_KEY")
    return get_grid_demand(city, api_key, hours=hours)

@app.get("/run-status")
def run_status():
    return _run_state