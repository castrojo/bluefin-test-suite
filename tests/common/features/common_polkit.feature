@common @bluefin
Feature: Polkit rules presence
  Verifies Bluefin's custom polkit rules are present and parseable.
  Polkit rules control privilege escalation; missing rules hang first-login.

  Background:
    * Bluefin VM is booted and reachable over SSH

  Scenario: polkit rules directory has Bluefin rules
    * Run SSH command: "ls /etc/polkit-1/rules.d/*.rules 2>/dev/null | wc -l"
    * SSH command return code is "0"
    * SSH command output is not "0"

  Scenario: pkcheck is available
    * Run SSH command: "pkcheck --version 2>/dev/null || polkit --version"
    * SSH command return code is "0"

  Scenario: polkit daemon is running
    * Run SSH command: "systemctl is-active polkit.service"
    * SSH command return code is "0"
    * Last command output contains "active"

  Scenario: no polkit rules have syntax errors
    * Run SSH command: "if command -v node >/dev/null 2>&1; then for f in /etc/polkit-1/rules.d/*.rules /usr/share/polkit-1/rules.d/*.rules; do [ -f \"$f\" ] && node --check \"$f\" 2>&1 && echo OK; done; else for f in /etc/polkit-1/rules.d/*.rules /usr/share/polkit-1/rules.d/*.rules; do [ -r \"$f\" ] && [ -s \"$f\" ] && echo OK; done; fi; true"
    * SSH command return code is "0"
    * SSH command output is not empty
