@bazzite_suite @steam_gamepad
Feature: Steam Gamepad UI automation in Gamescope
  Validates that Steam Big Picture (Gamepad UI) starts up inside gamescope with
  remote debugging enabled, and allows inspecting and interacting with DOM elements.

  Scenario: Verify Remote Debugging and Quick Access menu interaction
    Given Steam Gamepad UI is running in gamescope
    Then the Quick Access menu can be opened
