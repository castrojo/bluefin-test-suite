---
name: mocking-interactive-cli
description: "Mocking interactive CLI tools (gum, fzf, gh) in ujust coverage."
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Mocking Interactive Cli

Dakota's `ujust` recipes shell out to interactive tools. Covering them means
shadowing those tools on `PATH` inside a throwaway directory. Three rules keep
such scenarios honest.

## A mock that answers every prompt the same way exercises nothing

`bonedigger-report` (projectbluefin/common
`system_files/bluefin/usr/libexec/bonedigger-report`) drives several `gum choose`
prompts: the intent chooser, a `--no-limit` smart-log profile chooser, and the
queue-preference chooser. A mock that prints `Skip` for all of them makes
`main()` fall through its `case` without running any flow, so the scenario proves
only that `ujust report` exits 0. Branch on the prompt text and return a valid
answer per prompt, and make the mock `exit 1` for prompts it does not recognise —
a silent default is how the flow drifts away from the test unnoticed.

## Assert on the invocation, not just that the tool was called

`gh` must never reach the network from a test. Shadowing it is necessary but not
sufficient: a mock that accepts every `gh gist` invocation cannot tell a correct
upload from `gh gist list`. The mock should validate the subcommand, reject
unknown flags, require `--desc`, require at least one file argument, and verify
each file argument actually exists, then log a marker (`MOCK_GH_GIST_OK=1`) that
the step asserts on. Unit-test the mock by extracting its heredoc body and running
it under `sh` with a table of argv vectors and expected exit codes — that is what
`tests/unit/test_common_steps.py::TestUjustReportMocks` does.

Export the mock directory onto `PATH` **before** the recipe runs, and assert that
ordering in a unit test so no future edit can let the real `gh` through.

## Prove the recipe ran, not that some output appeared

`ujust --choose` with a mocked `fzf` returns 0 and prints a recipe listing even
when the chooser was never consulted, so `return code is 0` plus `output is not
empty` is a vacuous pass. Have the mock touch a marker file, echo
`FZF_INVOKED=1`/`0` and `CHOOSE_RC=$rc`, propagate the real return code with
`exit $rc`, and assert on output that only the chosen recipe can produce —
`logs-this-boot` is `sudo journalctl --no-hostname -b 0`, so `systemd[1]:` in the
output is unique to a real run.
