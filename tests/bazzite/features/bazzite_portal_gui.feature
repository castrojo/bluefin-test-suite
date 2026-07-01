@bazzite_suite @portal_gui
Feature: Bazzite Portal and ujust GUI testing
  Validates that the Bazzite Portal post-install wizard launches and is
  accessible via AT-SPI, exposing appropriate control elements for system maintenance
  and correctly triggering the ujust backend terminals.

  Background:
    * The Bazzite Portal application is running

  Scenario: Bazzite Portal launches and is accessible
    Then the "Bazzite Portal" window is visible
    And the update button "Update System" is present

  Scenario: Triggering system update from Bazzite Portal
    When I click the button "Update System" in "Bazzite Portal"
    Then a terminal execution window with title "Ptyxis" or "Konsole" is visible
    And the update command is executing in the terminal
