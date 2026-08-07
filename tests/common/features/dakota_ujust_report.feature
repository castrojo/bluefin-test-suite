@common @dakota_only @regression
Feature: Dakota ujust report
  Regression coverage for projectbluefin/dakota#913 (local summary/journal
  copy missing) and projectbluefin/dakota#940 (successful report exits 1).

  Background:
    * Bluefin VM is booted and reachable over SSH

  # @pending blocker: the success path of `ujust report` (bonedigger-report in
  # projectbluefin/common) only reaches persist_local_copy after the full
  # interactive flow — intent chooser, smart-log profile chooser, queue
  # preference chooser, consent confirm, `gh gist create` and `gh issue create`.
  # The mocks below drive that flow, but the scenario has never been validated
  # against a real Dakota image in the lab, so keeping it active would claim
  # coverage the suite does not have. Unblocked by #706 (lab image coverage for
  # @dakota_only scenarios); re-activate once a Dakota lab run is green.
  @pending
  Scenario: ujust report with mocked upload persists local summary and journal
    * ujust report runs with safe mocks and exits cleanly
    * SSH command return code is "0"
    * SSH command output contains "MOCK_GH_GIST_OK=1"
    * SSH command output contains "MOCK_GH_ISSUE_OK=1"
    * SSH command output contains "MOCK_REPORT_SUMMARY_OK=1"
    * SSH command output contains "MOCK_REPORT_JOURNAL_OK=1"
