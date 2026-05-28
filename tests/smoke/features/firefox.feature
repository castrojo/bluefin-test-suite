@smoke_suite
Feature: Firefox smoke tests
  Validates Firefox launches and core browser UI elements are accessible.
  Covers startup, navigation, tab management, and coredump regressions.

  Background:
    * Launch Firefox via command
    * Firefox main window is accessible

  @firefox @launch
  Scenario: Firefox launches and main window is accessible
    * Firefox main window is accessible

  @firefox @address_bar
  Scenario: Address bar is present and focusable
    * Address bar is present in Firefox

  @firefox @navigation
  Scenario: Navigating to about:blank loads successfully
    * Navigate Firefox to "about:blank"
    * Address bar is present in Firefox

  @firefox @new_tab
  Scenario: New tab opens via Ctrl+T and tab count increases
    * Firefox tab count increases after Ctrl+T

  @firefox @close_tab
  Scenario: Closing tab via Ctrl+W reduces tab count
    * Firefox tab count increases after Ctrl+T
    * Firefox tab count decreases after Ctrl+W

  @firefox @navigation @url
  Scenario: Navigating to a real URL loads the page
    * Navigate Firefox to "https://projectbluefin.io"
    * Address bar is present in Firefox

  @firefox @close
  Scenario: Firefox closes cleanly via Ctrl+Q
    * Key combo: "<Ctrl><Q>" with uinput
    * Firefox is no longer running

  @firefox @regression @bluefin
  Scenario: No Firefox coredump after session start
    * Run and save command output: "sh -c 'coredumpctl list firefox --no-pager --lines=10 2>/dev/null | grep -c firefox; true'"
    * Last command output stripped "is" "0"
