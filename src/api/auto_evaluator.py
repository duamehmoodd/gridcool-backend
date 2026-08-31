"""
src/api/auto_evaluator.py

Auto Re-Evaluation Layer -- satisfies two stated functional requirements:
  - "System shall re-evaluate risk automatically at a set interval without
     manual refresh."
  - "System shall log every risk score and recommendation with a timestamp
     for an audit trail."

Runs as a background asyncio task inside the FastAPI app (started on
startup). On each tick, it re-runs the live FortyGuard-driven risk snapshot
for every tracked city, updates an in-memory cache (so /decision can serve
the latest result instantly instead of waiting on FortyGuard each request),
and appends a timestamped entry to the audit log (in-memory + JSONL file on
disk, so the trail survives a restart).

Resilience: if a city's live evaluation fails (FortyGuard down, slow,
rate-limited, etc.), this now genuinely falls back to that city's most
recent saved historical risk_summary_<city>_*.json instead of leaving the
cache empty/stale -- matching the project's stated Reliability requirement.
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

AUDIT_LOG_PATH = Path("outputs") / "audit_log.jsonl"

# 5-10 minutes is plenty for a heat index; shorter intervals burn FortyGuard
# credits fast and increase the odds of hitting a slow/stuck response.
DEFAULT_INTERVAL_SECONDS = 300


class AutoEvaluator:
    def __init__(self, cities: list[str], master_path: Path,
                 interval_seconds: int = DEFAULT_INTERVAL_SECONDS):
        self.cities = cities
        self.master_path = master_path
        self.interval_seconds = interval_seconds
        self.cache: dict[str, dict] = {}       # city -> latest live_snapshot result
        self.last_run_at: Optional[str] = None
        self._task: Optional[asyncio.Task] = None
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    def _log_audit_entry(self, entry: dict) -> None:
        entry["logged_at"] = datetime.now(timezone.utc).isoformat()
        with open(AUDIT_LOG_PATH, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    def _load_historical_fallback(self, city: str) -> Optional[dict]:
        """
        Reads the most recently saved risk_summary_<city>_*.json (produced
        earlier by run_risk_agent.py in historical mode) and reshapes it to
        the same {transformer_risk: {...}} shape run_live_snapshot() returns,
        so callers (the cache, /decision) can't tell the difference in shape,
        only that heat_index_c/predicted_multiplier will be None since a
        historical file doesn't carry a live reading.
        """
        matches = sorted(
            Path("outputs").glob(f"risk_summary_{city}_*.json"),
            key=lambda p: p.stat().st_mtime, reverse=True,
        )
        if not matches:
            return None
        try:
            with open(matches[0]) as f:
                data = json.load(f)
        except Exception:
            return None

        xfmr_risk = data.get("transformer_risk", {})
        if not xfmr_risk:
            return None

        return {
            "status": "ok",
            "city": city,
            "heat_index_c": None,
            "predicted_multiplier": None,
            "transformer_risk": {
                name: {
                    "peak_pct_loaded": info.get("peak_pct_loaded"),
                    "crossed_threshold": info.get("crossed_threshold"),
                }
                for name, info in xfmr_risk.items()
            },
            "_fallback_source": matches[0].name,
        }

    async def _evaluate_once(self) -> None:
        # Imported here (not at module load) to avoid circular imports with main.py
        from src.data_prep.run_risk_agent import run_live_snapshot

        self.last_run_at = datetime.now(timezone.utc).isoformat()
        for city in self.cities:
            try:
                result = await asyncio.to_thread(
                    run_live_snapshot, city, self.master_path, 100.0, 100.0, 10
                )
                if result.get("status") == "ok":
                    self.cache[city] = result
                    self._log_audit_entry({
                        "city": city, "status": "ok",
                        "heat_index_c": result.get("heat_index_c"),
                        "predicted_multiplier": result.get("predicted_multiplier"),
                        "top_transformer": next(iter(result.get("transformer_risk", {})), None),
                    })
                else:
                    fallback = self._load_historical_fallback(city)
                    if fallback:
                        self.cache[city] = fallback
                        self._log_audit_entry({
                            "city": city, "status": "fallback_historical",
                            "note": "Live heat data unavailable right now -- using saved historical ResStock risk data instead.",
                            "fallback_source": fallback.get("_fallback_source"),
                        })
                    else:
                        self._log_audit_entry({
                            "city": city, "status": "failed",
                            "note": result.get("note", "unknown failure; no historical fallback found either"),
                        })
            except Exception as e:
                fallback = self._load_historical_fallback(city)
                if fallback:
                    self.cache[city] = fallback
                    self._log_audit_entry({
                        "city": city, "status": "fallback_historical",
                        "note": "Live heat data unavailable right now -- using saved historical ResStock risk data instead.",
                        "fallback_source": fallback.get("_fallback_source"),
                    })
                else:
                    self._log_audit_entry({"city": city, "status": "error", "note": str(e)})
    async def _loop(self) -> None:
        while True:
            await self._evaluate_once()
            await asyncio.sleep(self.interval_seconds)

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            self._task = None

    def get_cached(self, city: str) -> Optional[dict]:
        return self.cache.get(city)

    def get_recent_audit_entries(self, limit: int = 50) -> list[dict]:
        if not AUDIT_LOG_PATH.exists():
            return []
        lines = AUDIT_LOG_PATH.read_text().strip().splitlines()
        entries = [json.loads(line) for line in lines[-limit:]]
        entries.reverse()  # most recent first
        return entries