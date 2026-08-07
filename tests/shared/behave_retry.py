#!/usr/bin/env python3
"""Retry wrapper for behave with non-runnable scenario filtering."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_RETRIES = int(os.environ.get("BEHAVE_RETRIES", "2"))
RERUN_FILENAME = ".behave-rerun.txt"
OPTION_FLAGS_WITH_VALUES = {
    "-D",
    "--define",
    "-e",
    "--exclude",
    "-f",
    "--format",
    "-i",
    "--include",
    "--junit-directory",
    "-j",
    "--jobs",
    "--parallel",
    "--lang",
    "--logging-datefmt",
    "--logging-filter",
    "--logging-format",
    "--logging-level",
    "-n",
    "--name",
    "-o",
    "--outfile",
    "-r",
    "--runner",
    "--stage",
    "-t",
    "--tags",
}
REPORTER_FLAGS = {"-f", "--format", "-o", "--outfile", "--junit", "--junit-directory"}
RERUN_ENTRY_RE = re.compile(r".+\.feature(?::\d+)?$")
TAG_RE = re.compile(r"@([A-Za-z0-9_.-]+)")
NON_RUNNABLE_TAGS = ("quarantine", "pending", "future")


def parse_cli_args(argv: list[str]) -> tuple[int, list[str]]:
    retries = DEFAULT_RETRIES
    behave_args: list[str] = []
    idx = 0
    while idx < len(argv):
        arg = argv[idx]
        if arg == "--retries":
            retries = int(argv[idx + 1])
            idx += 2
            continue
        if arg.startswith("--retries="):
            retries = int(arg.split("=", 1)[1])
            idx += 1
            continue
        behave_args.append(arg)
        idx += 1
    return retries, behave_args


def with_skip_filters(args: list[str]) -> list[str]:
    filtered = [*args]
    for tag in NON_RUNNABLE_TAGS:
        filtered.extend(("--tags", f"~@{tag}"))
    return filtered


def _split_long_option(arg: str) -> str:
    return arg.split("=", 1)[0] if arg.startswith("--") and "=" in arg else arg


def extract_option_args(args: list[str]) -> list[str]:
    option_args: list[str] = []
    expects_value = False
    for arg in args:
        if expects_value:
            option_args.append(arg)
            expects_value = False
            continue
        flag = _split_long_option(arg)
        if arg.startswith("-") and arg != "-":
            option_args.append(arg)
            if flag in OPTION_FLAGS_WITH_VALUES and "=" not in arg:
                expects_value = True
            continue
    return option_args


def strip_reporter_args(args: list[str]) -> list[str]:
    cleaned: list[str] = []
    expects_value = False
    for arg in args:
        if expects_value:
            expects_value = False
            continue
        flag = _split_long_option(arg)
        if flag in REPORTER_FLAGS:
            if flag in OPTION_FLAGS_WITH_VALUES and "=" not in arg:
                expects_value = True
            continue
        cleaned.append(arg)
    return cleaned


def read_rerun_entries(rerun_path: Path) -> list[str]:
    if not rerun_path.exists():
        return []
    # behave 1.3.x adds "# -- RERUN: N failing scenarios..." header comments.
    # Strip them so they are not passed as feature file paths on retry.
    # Also ignore any non-feature noise to avoid ConfigError when behave changes
    # rerun formatting again.
    lines = [
        line.strip()
        for line in rerun_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
        and not line.strip().startswith("#")
        and RERUN_ENTRY_RE.fullmatch(line.strip())
    ]
    deduped: list[str] = []
    for line in lines:
        if line not in deduped:
            deduped.append(line)
    return deduped


def parse_rerun_entry(entry: str) -> tuple[Path, int | None]:
    feature_path, sep, line = entry.rpartition(":")
    if sep and line.isdigit() and feature_path.endswith(".feature"):
        return Path(feature_path), int(line)
    return Path(entry), None


def retry_tags_for_entry(entry: str) -> set[str]:
    feature_path, target_line = parse_rerun_entry(entry)
    if not feature_path.exists():
        return set()

    feature_tags: set[str] = set()
    pending_tags: list[str] = []
    scenario_start: int | None = None
    scenario_tags: set[str] = set()

    for line_number, raw_line in enumerate(feature_path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lowered = stripped.lower()
        if stripped.startswith("@"):
            pending_tags.extend(TAG_RE.findall(stripped))
            continue
        if lowered.startswith("feature:"):
            feature_tags.update(pending_tags)
            pending_tags = []
            continue
        if lowered.startswith("scenario:") or lowered.startswith("scenario outline:"):
            if target_line is not None and scenario_start is not None and target_line < line_number:
                return scenario_tags
            scenario_start = line_number
            scenario_tags = feature_tags | set(pending_tags)
            pending_tags = []
            if target_line == line_number:
                return scenario_tags
            continue
        pending_tags = []

    if target_line is None:
        return feature_tags
    if scenario_start is not None and target_line >= scenario_start:
        return scenario_tags
    return feature_tags


def should_retry_entry(entry: str) -> bool:
    return "retry" in retry_tags_for_entry(entry)


def _find_python() -> str:
    """Return a usable Python interpreter path.

    sys.executable is '' inside podman --pid=host containers on Python 3.14
    (the kernel /proc/self/exe path doesn't exist in the container FS).
    Validate each candidate before using it so subprocess.run never receives ''.
    """
    for candidate in filter(None, [
        sys.executable,
        shutil.which("python3"),
        shutil.which("python"),
        "/usr/bin/python3",
        "/usr/local/bin/python3",
        "/usr/bin/python",
    ]):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return "python3"


def run_behave(args: list[str], rerun_path: Path) -> tuple[int, list[str]]:
    if rerun_path.exists():
        rerun_path.unlink()
    python = _find_python()
    command = [
        python,
        "-m",
        "behave",
        *args,
        "--format",
        "rerun",
        "--outfile",
        str(rerun_path),
    ]
    result = subprocess.run(command, check=False)
    return result.returncode, read_rerun_entries(rerun_path)


def main(argv: list[str] | None = None) -> int:
    retries, behave_args = parse_cli_args(list(sys.argv[1:] if argv is None else argv))
    base_args = with_skip_filters(behave_args)
    rerun_path = Path.cwd() / RERUN_FILENAME

    rc, failed_entries = run_behave(base_args, rerun_path)
    if rc == 0:
        return 0

    retry_args = strip_reporter_args(extract_option_args(base_args))
    retryable_entries = [entry for entry in failed_entries if should_retry_entry(entry)]
    non_retryable_entries = [entry for entry in failed_entries if entry not in retryable_entries]
    last_rc = rc

    if non_retryable_entries:
        print(
            f"Not retrying {len(non_retryable_entries)} untagged failures; "
            "add @retry only to infrastructure-flaky scenarios.",
            flush=True,
        )

    for attempt in range(1, retries + 1):
        if not retryable_entries:
            print("No @retry-tagged failed scenarios remain to re-run.", flush=True)
            break
        print(
            f"Retry {attempt}/{retries}: re-running {len(retryable_entries)} @retry scenarios",
            flush=True,
        )
        last_rc, failed_entries = run_behave([*retry_args, *retryable_entries], rerun_path)
        if last_rc == 0:
            return 0 if not non_retryable_entries else rc
        retryable_entries = [entry for entry in failed_entries if should_retry_entry(entry)]

    return rc if non_retryable_entries else last_rc


if __name__ == "__main__":
    raise SystemExit(main())
