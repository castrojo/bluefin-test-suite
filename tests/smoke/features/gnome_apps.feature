@smoke_suite
Feature: GNOME app launch smoke tests
  Validates core Bluefin desktop apps launch, show a visible window, and exit cleanly.

  @apps @terminal
  Scenario: Ptyxis terminal launches successfully
    * the Ptyxis terminal launches successfully

  @apps @files
  Scenario: Files file manager launches successfully
    * the Files file manager launches successfully
