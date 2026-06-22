@native_app @smoke_suite
Feature: GNOME app launch smoke tests
  Validates core Bluefin desktop apps launch, show a visible window, and exit cleanly.

  @retry @apps @ptyxis @terminal @sla_15s
  Scenario: Ptyxis terminal launches successfully
    * the Ptyxis terminal launches successfully

  @retry @apps @files @sla_15s
  Scenario: Files file manager launches successfully
    * the Files file manager launches successfully

  @bluefin @retry @apps @flatpak @sla_15s
  Scenario: Mission Center launches successfully
    * the Mission Center app launches successfully

  @bluefin @retry @apps @flatpak @sla_15s
  Scenario: Extension Manager launches successfully
    * the Extension Manager app launches successfully

  @bluefin @retry @apps @flatpak @sla_15s
  Scenario: Warehouse launches successfully
    * the Warehouse app launches successfully

  @bluefin @retry @apps @flatpak @sla_15s
  Scenario: Impression launches successfully
    * the Impression app launches successfully
