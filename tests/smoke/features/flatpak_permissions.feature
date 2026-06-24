@smoke_suite @bluefin
Feature: OOTB Flatpak sandbox permission auditing
  Verify that OOTB Flatpaks are installed and do not hold excessive
  host filesystem access.

  @permissions @quarantine
  Scenario: org.gnome.Calculator is installed system-wide
    * Flatpak "org.gnome.Calculator" is installed system-wide

  @permissions @quarantine
  Scenario: org.gnome.Loupe is installed system-wide
    * Flatpak "org.gnome.Loupe" is installed system-wide

  @permissions @quarantine
  Scenario: org.gnome.TextEditor is installed system-wide
    * Flatpak "org.gnome.TextEditor" is installed system-wide

  @permissions @quarantine
  Scenario: org.gnome.Papers is installed system-wide
    * Flatpak "org.gnome.Papers" is installed system-wide

  @permissions @quarantine
  Scenario: org.mozilla.firefox is installed system-wide
    * Flatpak "org.mozilla.firefox" is installed system-wide

  @permissions @quarantine
  Scenario: org.gnome.clocks is installed system-wide
    * Flatpak "org.gnome.clocks" is installed system-wide

  @permissions @quarantine
  Scenario: org.gnome.Calendar is installed system-wide
    * Flatpak "org.gnome.Calendar" is installed system-wide

  @permissions @quarantine
  Scenario: io.missioncenter.MissionCenter is installed system-wide
    * Flatpak "io.missioncenter.MissionCenter" is installed system-wide

  @permissions @quarantine
  Scenario: Calculator Flatpak has no host filesystem access
    * Flatpak "org.gnome.Calculator" sandbox does not have excessive filesystem permissions

  @permissions @quarantine
  Scenario: Loupe Flatpak has no host filesystem access
    * Flatpak "org.gnome.Loupe" sandbox does not have excessive filesystem permissions

  @permissions @quarantine
  Scenario: Firefox Flatpak has no host filesystem access
    * Flatpak "org.mozilla.firefox" sandbox does not have excessive filesystem permissions
