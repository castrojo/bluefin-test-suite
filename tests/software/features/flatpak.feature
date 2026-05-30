@software_suite
Feature: gnome-software (Bazaar) smoke tests
  Validates Bazaar launches and core UI elements are accessible.
  Regression coverage for bluefin#4062 and #4471.

  Background:
    * Start application "software" via "command"
    * Wait until "Software" "frame" appears in "software"

  @software @launch
  Scenario: Bazaar launches and main window is visible
    * Application "software" is running
    * Item "Software" "frame" is "showing" in "software"

  @software @navigation
  Scenario: Explore tab is present and accessible
    * Item "Explore" "toggle button" is "showing" in "software"

  @software @navigation
  Scenario: Installed tab is present and accessible
    * Item "Installed" "toggle button" is "showing" in "software"

  @software @navigation
  Scenario: Clicking Installed tab shows installed apps list
    * Left click "Installed" "toggle button" in "software"
    * Wait until "Installed" "page tab" appears in "software"

  @software @search
  Scenario: Search bar accepts input and returns results
    * Left click "Search" "toggle button" in "software"
    * Type text: "Firefox" with uinput
    * Wait until "Firefox" "label" appears in "software"

  @software @regression @bluefin_4062
  Scenario: Flatpak updates section is reachable without crash (bluefin#4062)
    * Left click "Installed" "toggle button" in "software"
    * No journal entries match "gnome-software.*segfault|gnome-software.*abort"

  @software @regression @bluefin_4471
  Scenario: No gnome-software coredump on Explore page load (bluefin#4471)
    * Left click "Explore" "toggle button" in "software"
    * Wait 2 seconds before action
    * No coredump entries exist for "gnome-software"

  @software @close
  Scenario: Bazaar closes cleanly via shortcut
    * Close application "software" via "shortcut"
    * Application "software" is no longer running

  # ── Flatpak CLI ───────────────────────────────────────────────────────────
  # These scenarios bypass the Bazaar GUI and test the flatpak subsystem
  # directly. Background still opens Bazaar; that's acceptable overhead.

  @software @flatpak_cli
  Scenario: Flathub remote is configured and reachable
    * Flatpak remote "flathub" is configured

  @software @flatpak_cli @nightly
  Scenario: flatpak install and uninstall round-trip succeeds
    # Apostrophe (~5 MB) is a small, stable Flatpak with no heavy runtimes.
    # Marked @nightly to avoid slow network I/O on every PR run.
    * Run and save command output: "flatpak install --noninteractive flathub org.gnome.Apostrophe 2>&1; echo rc:$?"
    * Last command output contains "rc:0"
    * Flatpak app "org.gnome.Apostrophe" is installed
    * Run and save command output: "flatpak uninstall --noninteractive org.gnome.Apostrophe 2>&1; echo rc:$?"
    * Last command output contains "rc:0"
    * Flatpak app "org.gnome.Apostrophe" is not installed
