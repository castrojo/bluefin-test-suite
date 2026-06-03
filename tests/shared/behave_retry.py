#!/usr/bin/env python3
"""Retry wrapper for behave with quarantine-tag filtering."""

from __future__ import annotations

import os
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


def with_quarantine_filter(args: list[str]) -> list[str]:
    return [*args, "--tags", "~@quarantine"]


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
    lines = [
        line.strip()
        for line in rerun_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    deduped: list[str] = []
    for line in lines:
        if line not in deduped:
            deduped.append(line)
    return deduped


def run_behave(args: list[str], rerun_path: Path) -> tuple[int, list[str]]:
    if rerun_path.exists():
        rerun_path.unlink()
    # sys.executable can be empty inside podman containers with --pid=host because
    # the kernel path seen via /proc/self/exe doesn't exist in the container FS.
    # Fall back to PATH lookup so behave can always be launched.
    python = sys.executable or shutil.which("python3") or "python3"
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
    base_args = with_quarantine_filter(behave_args)
    rerun_path = Path("/tmp") / RERUN_FILENAME

    rc, failed_entries = run_behave(base_args, rerun_path)
    if rc == 0:
        return 0

    retry_args = strip_reporter_args(extract_option_args(base_args))
    last_rc = rc
    for attempt in range(1, retries + 1):
        if not failed_entries:
            print("Retry data unavailable; cannot re-run failed scenarios.", flush=True)
            break
        print(
            f"Retry {attempt}/{retries}: re-running {len(failed_entries)} failed scenarios",
            flush=True,
        )
        last_rc, failed_entries = run_behave([*retry_args, *failed_entries], rerun_path)
        if last_rc == 0:
            return 0

    return last_rc


if __name__ == "__main__":
    raise SystemExit(main())
