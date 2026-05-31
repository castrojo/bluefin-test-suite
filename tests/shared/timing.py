"""Scenario timing helpers — write JSONL lines to the configured results directory."""

import json
import os
import time


def _results_dir(context=None) -> str:
    """Resolve output dir: userdata > env var > default /tmp/results."""
    if context is not None:
        config = getattr(context, "config", None)
        if config and hasattr(config, "userdata"):
            value = config.userdata.get("results_dir")
            if value:
                return value
    return os.environ.get("TESTSUITE_RESULTS_DIR", "/tmp/results")

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
    results_dir = _results_dir(context)
    timings_file = os.path.join(results_dir, "timings.jsonl")
    os.makedirs(results_dir, exist_ok=True)
    entry = {
        "scenario": scenario.name,
        "feature": getattr(getattr(scenario, "feature", None), "name", "unknown"),
        "status": scenario.status.name,
        "elapsed_s": round(elapsed, 3),
        "sla_s": SLA_SCENARIO_DEFAULT,
        "sla_violated": elapsed > SLA_SCENARIO_DEFAULT,
    }
    try:
        with open(timings_file, "a", encoding="utf-8") as file_obj:
            file_obj.write(json.dumps(entry) + "\n")
    except OSError:
        pass
    return elapsed
