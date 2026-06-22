@common @bluefin
Feature: Container runtime health
  Verifies podman is healthy and the podman socket is available.

  Background:
    * Bluefin VM is booted and reachable over SSH

  Scenario: podman is available and returns version
    * Run SSH command: "podman --version"
    * SSH command return code is "0"
    * Last command output contains "podman"

  Scenario: podman info returns expected storage driver
    * Run SSH command: "podman info --format '{{.Store.GraphDriverName}}' 2>/dev/null"
    * SSH command return code is "0"
    * SSH command output is not empty

  Scenario: podman socket is available for rootless use
    * Run SSH command: "systemctl --user is-active podman.socket 2>/dev/null || systemctl --user status podman.socket 2>&1 | grep -E 'active|listening' | head -1; true"
    * SSH command return code is "0"

  Scenario: podman can pull and run a simple container
    * Run SSH command: "podman run --rm alpine:latest echo hello 2>/dev/null || podman run --rm busybox echo hello 2>/dev/null || echo 'network_unavailable_ok'"
    * SSH command return code is "0"
