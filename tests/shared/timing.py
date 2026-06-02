"""Scenario timing helpers — write JSONL lines to the configured results directory."""

import json
import os
import re
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


DEFAULT_SLA = {
    "app_launch": 10,
    "shell_eval": 5,
    "ssh_check": 15,
    "system_health": 8,
}

SLA_TAG_PATTERN = re.compile(r"sla_(\d+)s")
SLA_STRICT = os.environ.get("TIMING_SLA_STRICT", "").lower() in ("1", "true", "yes")


def _scenario_sla_seconds(scenario):
    """Return SLA threshold from the first matching scenario tag, if present."""
    tags = getattr(scenario, "effective_tags", None) or getattr(scenario, "tags", [])
    for tag in tags:
        match = SLA_TAG_PATTERN.fullmatch(tag.lstrip("@"))
        if match:
            return int(match.group(1))
    return None


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
    rounded_elapsed = round(elapsed, 3)
    sla_s = _scenario_sla_seconds(scenario)
    entry = {
        "scenario": scenario.name,
        "feature": getattr(getattr(scenario, "feature", None), "name", "unknown"),
        "status": scenario.status.name,
        "elapsed": rounded_elapsed,
        "elapsed_s": rounded_elapsed,
        "sla_s": sla_s,
        "sla_violated": bool(sla_s is not None and rounded_elapsed > sla_s),
    }
    try:
        with open(timings_file, "a", encoding="utf-8") as file_obj:
            file_obj.write(json.dumps(entry) + "\n")
    except OSError:
        pass
    return elapsed
