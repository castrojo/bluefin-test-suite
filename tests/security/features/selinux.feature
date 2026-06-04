@security @selinux @bluefin
Feature: SELinux enforcing mode validation
  Validates that Bluefin runs correctly with SELinux enforcing and
  that no AVC denials are generated during normal desktop operation.
  Runner: plain SSH behave (runs inside the VM after boot).

  # AVC denials that are expected and explicitly allowed are listed in
  # tests/security/features/selinux_allowlist.yaml.

  Background:
    * Bluefin VM is booted and reachable over SSH

  @selinux @mode
  Scenario: SELinux is in enforcing mode
    * Run SSH command: "getenforce"
    * SSH command output "is" "Enforcing"

  @selinux @no_denials
  Scenario: No AVC denials in system journal since boot
    # Guard: if ausearch is absent or SELinux is not enforcing, emit sentinel so the
    # test fails visibly rather than passing trivially with a spurious "0".
    * Run SSH command: "command -v ausearch >/dev/null && getenforce | grep -q Enforcing && sudo ausearch -m avc -ts boot --raw 2>/dev/null | grep -c '^' || echo selinux-not-enforcing"
    * SSH command output does not contain "selinux-not-enforcing"
    * SSH command output "is" "0"

  @selinux @context_labels
  Scenario: Key files have correct SELinux context labels
    * Run SSH command: "ls -Z /etc/passwd | grep -c system_u:object_r:passwd_file_t"
    * SSH command output "is" "1"
    * Run SSH command: "ls -Z /usr/bin/gnome-shell | grep -c system_u:object_r:bin_t"
    * SSH command return code is "0"

  @selinux @ostree_unlock
  Scenario: ostree admin unlock does not create mislabeled files
    * Run SSH command: "sudo ostree admin unlock 2>/dev/null || true"
    * Run SSH command: "sudo touch /usr/local/bin/test-labeled"
    * Run SSH command: "ls -Z /usr/local/bin/test-labeled | grep -c bin_t"
    * SSH command return code is "0"

  @selinux @user_session
  Scenario: No AVC denials during GNOME session startup
    # Guard: emit sentinel if ausearch absent or SELinux not enforcing.
    * Run SSH command: "command -v ausearch >/dev/null && getenforce | grep -q Enforcing && sudo ausearch -m avc -ts boot -c gnome-shell --raw 2>/dev/null | grep -c '^' || echo selinux-not-enforcing"
    * SSH command output does not contain "selinux-not-enforcing"
    * SSH command output "is" "0"
    * Run SSH command: "command -v ausearch >/dev/null && getenforce | grep -q Enforcing && sudo ausearch -m avc -ts boot -c gdm --raw 2>/dev/null | grep -c '^' || echo selinux-not-enforcing"
    * SSH command output does not contain "selinux-not-enforcing"
    * SSH command output "is" "0"
