@native_app @smoke_suite @bluefin
Feature: GNOME regression checks
  Regression guard scenarios that do not require a running app session.
  These run without any Background app-open precondition.

  @regression @bluefin
  Scenario: No gnome-control-center coredump after session start
    * No coredump entries exist for "gnome-control-center"
