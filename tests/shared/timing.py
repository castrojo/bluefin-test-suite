"""Scenario timing helpers — write JSONL lines to /tmp/results/timings.jsonl."""

import json
import os
import time


RESULTS_DIR = "/tmp/results"
TIMINGS_FILE = os.path.join(RESULTS_DIR, "timings.jsonl")

# SLA thresholds (seconds). Override via env: TIMING_SLA_SCENARIO=30
SLA_SCENARIO_DEFAULT = int(os.environ.get("TIMING_SLA_SCENARIO", "30"))
SLA_VSCODE_LAUNCH = int(os.environ.get("TIMING_SLA_VSCODE", "15"))
SLA_STRICT = os.environ.get("TIMING_SLA_STRICT", "").lower() in ("1", "true", "yes")


def record_start(context):
    """Call in before_scenario to stamp start time on context."""
    context._timing_start = time.monotonic()


def record_end(context, scenario):
    """Call in after_scenario to append a JSONL line.

    Returns elapsed seconds (float).
    """
    start = getattr(context, "_timing_start", None)
    if start is None:
        return None
    elapsed = time.monotonic() - start
    os.makedirs(RESULTS_DIR, exist_ok=True)
    entry = {
        "scenario": scenario.name,
        "feature": getattr(getattr(scenario, "feature", None), "name", "unknown"),
        "status": scenario.status.name,
        "elapsed_s": round(elapsed, 3),
        "sla_s": SLA_SCENARIO_DEFAULT,
        "sla_violated": elapsed > SLA_SCENARIO_DEFAULT,
    }
    try:
        with open(TIMINGS_FILE, "a", encoding="utf-8") as file_obj:
            file_obj.write(json.dumps(entry) + "\n")
    except OSError:
        pass
    return elapsed
