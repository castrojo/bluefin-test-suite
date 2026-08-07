@common @dakota_only @regression
Feature: Dakota ujust report
  Regression coverage for projectbluefin/dakota#913 (local summary/journal
  copy missing) and projectbluefin/dakota#940 (successful report exits 1).

  Background:
    * Bluefin VM is booted and reachable over SSH

  Scenario: ujust report with mocked upload persists local summary and journal
    * ujust report runs with safe mocks and exits cleanly
    * SSH command return code is "0"
    * SSH command output contains "MOCK_REPORT_SUMMARY_OK=1"
    * SSH command output contains "MOCK_REPORT_JOURNAL_OK=1"
