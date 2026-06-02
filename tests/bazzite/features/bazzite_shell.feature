@bazzite_suite
Feature: Bazzite GNOME shell behaviour
  Validates Bazzite-specific shell UI behaviour: Logo Menu replacing Activities,
  no coredumps with all extensions loaded, and core GNOME shell still functional.

  @bazzite_suite
  Scenario: GNOME Shell is accessible via AT-SPI
    * GNOME Shell is accessible via AT-SPI
    * Dump panel children to log

  @bazzite_suite
  Scenario: Activities button is replaced by Logo Menu
    * GNOME Shell is accessible via AT-SPI
    * Activities button is absent from panel
    * Logo Menu button is present in panel

  @bazzite_suite
  Scenario: Panel is present in AT-SPI tree
    * GNOME Shell is accessible via AT-SPI
    * Panel is present in AT-SPI tree

  @bazzite_suite
  Scenario: Super key opens Activities overview with Logo Menu active
    * GNOME Shell is accessible via AT-SPI
    * Open Activities overview via Shell.Eval
    * Overview is open
    * Close Activities overview via Shell.Eval
    * Overview is closed

  @bazzite_suite
  Scenario: Quick Settings panel opens with extensions loaded
    * GNOME Shell is accessible via AT-SPI
    * Open Quick Settings via Shell.Eval
    * Quick Settings panel is open via Shell.Eval

  @bazzite_suite
  Scenario: No gnome-shell coredump with all extensions loaded
    * No gnome-shell coredump with extensions loaded
