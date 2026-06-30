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

  @bluefin @retry @apps @flatpak @sla_15s
  Scenario: Clocks launches successfully
    * the Clocks app launches successfully

  @bluefin @retry @apps @flatpak @sla_15s
  Scenario: Weather launches successfully
    * the Weather app launches successfully

  @bluefin @retry @apps @flatpak @sla_15s
  Scenario: Calendar launches successfully
    * the Calendar app launches successfully

  @bluefin @retry @apps @flatpak @sla_15s
  Scenario: Decibels launches successfully
    * the Decibels app launches successfully

  @bluefin @retry @apps @flatpak @sla_15s
  Scenario: Loupe image viewer launches successfully
    * the Loupe image viewer launches successfully

  @bluefin @retry @apps @flatpak @sla_15s
  Scenario: Papers PDF viewer launches successfully
    * the Papers PDF viewer launches successfully

  @bluefin @retry @apps @flatpak @sla_15s
  Scenario: Showtime video player launches successfully
    * the Showtime video player launches successfully

  @bluefin @retry @apps @flatpak @sla_15s
  Scenario: Baobab disk usage analyzer launches successfully
    * the Baobab disk usage analyzer launches successfully

  @bluefin @retry @apps @flatpak @sla_15s
  Scenario: Characters launches successfully
    * the Characters app launches successfully

  @bluefin @retry @apps @flatpak @sla_15s
  Scenario: Logs launches successfully
    * the Logs app launches successfully

  @bluefin @retry @apps @flatpak @sla_15s
  Scenario: File Roller archive manager launches successfully
    * the File Roller archive manager launches successfully
