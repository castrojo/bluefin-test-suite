@notifications @smoke_suite
Feature: GNOME notification smoke tests
  Validates desktop notifications can be delivered without GNOME Shell regressions.

  @notifications @smoke_suite
  Scenario: Desktop notification can be sent and acknowledged
    * A test desktop notification is sent via gdbus
    * Notification request returns a positive notification ID

  @notifications @smoke_suite
  Scenario: Notification history is accessible from Quick Settings
    * A test desktop notification is sent via gdbus
    * Open date menu via Shell.Eval
    * Date menu panel is open via Shell.Eval
    * Close date menu via Shell.Eval

  @notifications @regression @smoke_suite
  Scenario: No gnome-shell journal errors after notification
    * A test desktop notification is sent via gdbus
    * No gnome-shell notification journal errors are present
