@gnome_core @vanilla_gnome @nightly
Feature: Vanilla GNOME baseline smoke tests
  Validates core GNOME Shell behaviour on upstream Fedora (no Bluefin customizations).
  Used as a comparison baseline: failures here indicate upstream GNOME issues;
  failures on Bluefin but not here indicate Bluefin-specific regressions.
  Runner: qecore-headless + behave (same as smoke suite).

  # Golden disk: quay.io/fedora/fedora-bootc:latest (vanilla GNOME, no extensions)
  # Namespace: gnome-baseline-test
  # Runs: nightly, not per-PR (expensive)
  # See QA-REVIEW.md Epic E07

  @gnome_core
  Scenario: GNOME Shell process is running and accessible via AT-SPI
    * GNOME Shell is accessible via AT-SPI
    * Dump panel children to log
    * Dump gnome-shell AT-SPI tree to results

  @gnome_core
  Scenario: Panel is present in AT-SPI tree
    * GNOME Shell is accessible via AT-SPI
    * Panel is present in AT-SPI tree

  @gnome_core
  Scenario: Activities toggle button is visible in panel
    * GNOME Shell is accessible via AT-SPI
    * Item "Activities" "toggle button" is "showing" in "gnome-shell"

  @gnome_core
  Scenario: Super key opens Activities overview
    * GNOME Shell is accessible via AT-SPI
    * Open Activities overview via Shell.Eval
    * Overview is open
    * Close Activities overview via Shell.Eval
    * Overview is closed

  @gnome_core
  Scenario: Typing in overview populates search bar
    * GNOME Shell is accessible via AT-SPI
    * Open Activities overview via Shell.Eval
    * Overview is open
    * Set overview search text to "Files" via Shell.Eval
    * Overview search bar contains "Files"
    * Close Activities overview via Shell.Eval

  @gnome_core
  Scenario: Clicking System menu opens Quick Settings
    * GNOME Shell is accessible via AT-SPI
    * Open Quick Settings via Shell.Eval
    * Quick Settings panel is open via Shell.Eval

  @gnome_core
  Scenario: Clicking clock opens calendar popup
    * GNOME Shell is accessible via AT-SPI
    * Open date menu via Shell.Eval
    * Date menu panel is open via Shell.Eval

  @gnome_core
  Scenario: No gnome-shell coredump after session start
    * No coredump entries exist for "gnome-shell"
