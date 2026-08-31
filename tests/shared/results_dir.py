"""Single source of truth for the testsuite results-directory contract.

Every artifact writer in ``tests/shared`` (scenario timings, screenshots,
KDE failure bundles) must resolve its output directory through
``resolve_results_dir`` so the resolution order stays identical everywhere:

1. Behave userdata key ``results_dir`` (``-D results_dir=...``), when a
   context with a ``config.userdata`` mapping is supplied.
2. Environment variable ``TESTSUITE_RESULTS_DIR``.
3. ``DEFAULT_RESULTS_DIR`` — the runner container layout.
"""

import os
from typing import Any

DEFAULT_RESULTS_DIR = "/tmp/results"


def resolve_results_dir(context: Any | None = None) -> str:
    """Resolve output dir: userdata > env var > default /tmp/results."""
    if context is not None:
        config = getattr(context, "config", None)
        if config and hasattr(config, "userdata"):
            value = config.userdata.get("results_dir")
            if value:
                return value
    return os.environ.get("TESTSUITE_RESULTS_DIR", DEFAULT_RESULTS_DIR)
