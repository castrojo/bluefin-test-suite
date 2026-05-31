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

  @quarantine @software @navigation
  Scenario: Explore tab is present and accessible
    * Item "Explore" "toggle button" is "showing" in "software"

  @quarantine @software @navigation
  Scenario: Installed tab is present and accessible
    * Item "Installed" "toggle button" is "showing" in "software"

  @quarantine @software @navigation
  Scenario: Clicking Installed tab shows installed apps list
    * Left click "Installed" "toggle button" in "software"
    * Wait until "Installed" "page tab" appears in "software"

  @quarantine @software @search
  Scenario: Search bar accepts input and returns results
    # Quarantined: uinput (python-uinput) not available on gnomeos — no gcc in image.
    * Left click "Search" "toggle button" in "software"
    * Type text: "Firefox" with uinput
    * Wait until "Firefox" "label" appears in "software"

  @quarantine @software @regression @bluefin_4062
  Scenario: Flatpak updates section is reachable without crash (bluefin#4062)
    * Left click "Installed" "toggle button" in "software"
    * No journal entries match "gnome-software.*segfault|gnome-software.*abort"

  @quarantine @software @regression @bluefin_4471
  Scenario: No gnome-software coredump on Explore page load (bluefin#4471)
    * Left click "Explore" "toggle button" in "software"
    * Wait 2 seconds before action
    * No coredump entries exist for "gnome-software"

  @quarantine @software @close
  Scenario: Bazaar closes cleanly via shortcut
    * Close application "software" via "shortcut"
    * Application "software" is no longer running

  # ── Flatpak permissions ──────────────────────────────────────────────────
  # Verify the XDG portal permissions database is queryable and that
  # per-app overrides can be set and reset without corrupting the DB.

  @software @flatpak_permissions
  Scenario: Flatpak permissions database is queryable
    * Flatpak permissions table "notifications" is queryable

  @quarantine @software @flatpak_permissions @nightly
  Scenario: flatpak user override round-trip succeeds
    # Calculator is always present; override doesn't require the app to be installed.
    * Set flatpak user override "--filesystem=home" for "org.gnome.Calculator"
    * Flatpak user override "filesystem=home" is active for "org.gnome.Calculator"
    * Reset flatpak user overrides for "org.gnome.Calculator"
    * No flatpak user overrides exist for "org.gnome.Calculator"

  @software @flatpak_cli
  Scenario: Flathub remote is configured and reachable
    * Flatpak remote "flathub" is configured

  @quarantine @software @flatpak_cli @nightly
  Scenario: flatpak install and uninstall round-trip succeeds
    # Apostrophe (~5 MB) is a small, stable Flatpak with no heavy runtimes.
    # Marked @nightly to avoid slow network I/O on every PR run.
    * Run and save command output: "flatpak install --noninteractive flathub org.gnome.Apostrophe 2>&1; echo rc:$?"
    * Last command output contains "rc:0"
    * Flatpak app "org.gnome.Apostrophe" is installed
    * Run and save command output: "flatpak uninstall --noninteractive org.gnome.Apostrophe 2>&1; echo rc:$?"
    * Last command output contains "rc:0"
    * Flatpak app "org.gnome.Apostrophe" is not installed
