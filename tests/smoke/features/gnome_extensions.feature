@smoke_suite
Feature: GNOME Extensions smoke tests
  Validates installed Bluefin GNOME Shell extensions are present, enabled,
  manageable via the Extensions app, and do not trigger shell load errors.

  @extensions
  Scenario: At least one GNOME extension is installed
    * At least one GNOME extension is installed

  @extensions
  Scenario: At least one GNOME extension is enabled
    * At least one GNOME extension is enabled

  @extensions
  Scenario: GNOME Extensions preferences app launches
    * Launch Extensions preferences via command
    * Extensions window is accessible
    * Key combo: "<Alt><F4>" with uinput
    * Extensions is no longer running

  @extensions @regression
  Scenario: No gnome-shell crash on extension load
    * No gnome-shell extension load journal errors exist
