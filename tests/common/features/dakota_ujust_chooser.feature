@common @dakota_only
Feature: Dakota ujust chooser
  Validates that the ujust recipe chooser can be exercised non-interactively
  on Dakota images by mocking fzf to return a benign recipe.

  Scenario: ujust --choose runs a benign recipe with mocked fzf
    * ujust --choose runs mocked fzf recipe "logs-this-boot"
    * SSH command return code is "0"
    * SSH command output is not empty
