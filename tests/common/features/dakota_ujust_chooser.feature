@common @dakota_only
Feature: Dakota ujust chooser
  Validates that the ujust recipe chooser can be exercised non-interactively
  on Dakota images by mocking fzf to return a benign recipe.

  Scenario: ujust --choose runs a benign recipe with mocked fzf
    # logs-this-boot is `sudo journalctl --no-hostname -b 0` in
    # projectbluefin/dakota files/just-overrides/default.just, so a real run
    # emits journal lines. A bare `ujust --choose` recipe listing does not, and
    # neither does a run where fzf was never consulted.
    * ujust --choose runs mocked fzf recipe "logs-this-boot"
    * SSH command return code is "0"
    * SSH command output contains "FZF_INVOKED=1"
    * SSH command output contains "CHOOSE_RC=0"
    * SSH command output contains "systemd[1]:"
