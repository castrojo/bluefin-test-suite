@smoke_suite
Feature: GNOME Settings smoke tests
  Validates GNOME Settings launches, exposes core navigation, and shows
  Bluefin system information without crashing.

  Background:
    * Start application "gnome-control-center" via "command"
    * Wait until "Settings" "frame" appears in "gnome-control-center"

  @settings @launch
  Scenario: GNOME Settings launches and window is accessible
    * Application "gnome-control-center" is running
    * Item "Settings" "frame" is "showing" in "gnome-control-center"

  @settings @navigation
  Scenario: Settings sidebar is present with navigation items
    * Settings sidebar is present

  @settings @about
  Scenario: About page is accessible
    * Navigate to Settings panel "About"
    * Settings panel "About" is visible

  @settings @about
  Scenario: About page shows OS information
    * Navigate to Settings panel "About"
    * Settings panel "About" is visible
    * About page shows system information

  @settings @displays
  Scenario: Displays settings panel is accessible
    * Navigate to Settings panel "Displays"
    * Settings panel "Displays" is visible

  @settings @close
  Scenario: Settings closes cleanly via Ctrl+Q
    * Key combo: "<Ctrl><Q>" with uinput
    * Application "gnome-control-center" is no longer running

  @regression @bluefin
  Scenario: No gnome-control-center coredump after session start
    * Run and save command output: "sh -c 'coredumpctl list gnome-control-center --no-pager --lines=10 2>/dev/null | grep -c gnome-control-center; true'"
    * Last command output stripped "is" "0"
