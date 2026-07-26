@smoke_suite
Feature: sudo-rs execution and privilege escalation
  Validates that sudo-rs binary permissions, setuid bits, non-interactive execution,
  environment preservation, PAM configuration, and sudoedit behave correctly on Dakota.

  @sudo_rs @setuid @security @sla_10s
  Scenario: sudo binary is setuid root with 4755 permissions
    * /usr/bin/sudo is owned by root and has setuid mode 4755

  @sudo_rs @escalation @sla_10s
  Scenario: sudo -n escalates privileges non-interactively for wheel users
    * sudo -n id -u returns user ID 0

  @sudo_rs @env @security @sla_10s
  Scenario: sudo-rs scrubs unflagged environment variables and preserves explicit flags
    * sudo --preserve-env preserves specified environment variables

  @sudo_rs @pam @sla_10s
  Scenario: sudo PAM configuration integrates system-auth
    * sudo PAM configuration includes system-auth for authentication fallback

  @sudo_rs @sudoedit @sla_10s
  Scenario: sudoedit binary exists and resolves to setuid binary
    * sudoedit binary is present and operational

  @sudo_rs @pam_auth @isolation
  Scenario: sudo PAM password authentication functions for non-wheel user
    * sudo PAM password authentication is functional for isolated test accounts
