from __future__ import annotations

import sys
from types import SimpleNamespace

from tests.shared import behave_retry
from tests.shared.quarantine import skip_quarantine


class DummyScenario:
    def __init__(self, tags):
        self.tags = set(tags)
        self.effective_tags = set(tags)
        self.skip_calls = []

    def skip(self, reason=None):
        self.skip_calls.append(reason)


def test_skip_quarantine_marks_scenario_skipped():
    scenario = DummyScenario({"quarantine"})

    assert skip_quarantine(scenario) is True
    assert scenario.skip_calls == ["@quarantine — known flaky, skipping"]


def test_retry_reruns_failed_scenarios_until_success(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    rerun_path = tmp_path / behave_retry.RERUN_FILENAME
    commands = []
    returncodes = [1, 0]
    rerun_outputs = [
        "features/demo.feature:12\nfeatures/other.feature:7\n",
        "",
    ]

    def fake_run(command, check=False):
        commands.append(command)
        rerun_path.write_text(rerun_outputs.pop(0), encoding="utf-8")
        return SimpleNamespace(returncode=returncodes.pop(0))

    monkeypatch.setattr(behave_retry.subprocess, "run", fake_run)

    rc = behave_retry.main(
        [
            "tests/smoke/features",
            "--format",
            "pretty",
            "--outfile",
            "results/results.txt",
            "--retries",
            "1",
        ]
    )

    assert rc == 0
    assert commands[0][:3] == [sys.executable, "-m", "behave"]
    assert commands[0][-4:] == ["--format", "rerun", "--outfile", str(rerun_path)]
    assert commands[0][3:-4] == [
        "tests/smoke/features",
        "--format",
        "pretty",
        "--outfile",
        "results/results.txt",
        "--tags",
        "~@quarantine",
    ]
    assert commands[1][:3] == [sys.executable, "-m", "behave"]
    assert "tests/smoke/features" not in commands[1]
    assert commands[1][3:-4] == [
        "--tags",
        "~@quarantine",
        "features/demo.feature:12",
        "features/other.feature:7",
    ]
