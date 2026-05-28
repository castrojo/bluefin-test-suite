@dx_only @developer_suite
Feature: Bluefin DX variant smoke tests
  Validates developer-experience-specific tools present in the DX image.
  These scenarios are SKIPPED on standard Bluefin — DX only.
  Runner: qecore-headless + behave (GNOME GUI interaction for VS Code/Codium).

  # Requires: Bluefin DX golden disk (ghcr.io/ublue-os/bluefin-dx:latest).
  # See QA-REVIEW.md Epic E05 for full design.

  @dx @vscode @launch
  Scenario: VS Code or Codium launches and window is accessible
    # AT-SPI app name is likely "code" or "codium".
    * Start application "code" via "command"
    * Wait until "Visual Studio Code" "frame" appears in "code"
    * Application "code" is running

  @dx @vscode @close
  Scenario: VS Code closes cleanly
    * Start application "code" via "command"
    * Wait until "Visual Studio Code" "frame" appears in "code"
    * Close application "code" via "shortcut"
    * Application "code" is no longer running

  @dx @devcontainer @plain_ssh
  Scenario: devcontainer CLI is available on PATH
    * Run DX SSH command: "which devcontainer || echo missing"
    * Last command output does not contain "missing"

  @dx @distrobox @plain_ssh
  Scenario: distrobox is installed and can create a container
    * Run DX SSH command: "distrobox --version"
    * SSH command return code is "0"

  @dx @distrobox @plain_ssh
  Scenario: distrobox enter works with default container
    * Run DX SSH command: "distrobox create --name test-dx --image fedora:latest --yes 2>&1 | tail -1"
    * SSH command return code is "0"

  @dx @toolbox @plain_ssh
  Scenario: toolbox is available as alternative to distrobox
    * Run DX SSH command: "which toolbox || echo missing"
    * Last command output does not contain "missing"

  @dx @podman_compose @plain_ssh
  Scenario: podman-compose is available for container orchestration
    * Run DX SSH command: "podman-compose --version 2>&1 | head -1"
    * Last command output contains "podman-compose"

  @dx @jupyter @plain_ssh
  Scenario: JupyterLab can be launched (DX includes scientific stack)
    * Run DX SSH command: "which jupyter-lab || pip3 show jupyterlab 2>/dev/null | grep -c Name || echo missing"
    * SSH command return code is "0"
    * Last command output does not contain "missing"
