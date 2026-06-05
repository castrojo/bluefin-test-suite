@software_suite
Feature: Bazaar (GNOME Software) smoke tests
  Validates Bazaar (`io.github.kolunmi.Bazaar`) launches and core UI elements are accessible.
  Regression coverage for bluefin#4062 and #4471.

  Background:
    * Start application "software" via "command"
    * Wait until "Software" "frame" appears in "software"

  @software @launch
  Scenario: Bazaar launches and main window is visible
    * Application "software" is running
    * Item "Software" "frame" is "showing" in "software"

  # Quarantined on gnomeos/GNOME 50 pending re-validation of Bazaar's
  # AT-SPI roles and names after /org/a11y/atspi/cache errors tracked in #176.
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

  @software @search
  Scenario: Search bar accepts input and returns results
    * Left click "Search" "toggle button" in "software"
    * Type text: "Firefox" with uinput
    * Wait until "Firefox" "label" appears in "software"

  # These crash/close checks depend on the same GNOME 50 navigation widgets,
  # so keep them quarantined until the UI structure is re-verified on gnomeos.
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

  # ── Flatpak CLI checks moved to flatpak_cli.feature ─────────────────────
  # flatpak_permissions and flatpak_cli scenarios are now in flatpak_cli.feature
  # which has no Background dependency, so they run cleanly on all images.

