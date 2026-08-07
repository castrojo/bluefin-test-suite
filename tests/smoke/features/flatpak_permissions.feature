@smoke_suite @bluefin
Feature: OOTB Flatpak sandbox permission auditing
  Verify that OOTB Flatpaks are installed and do not hold excessive
  host filesystem access.

  # Pending: e2e.yml masks flatpak-preinstall.service and never seeds
  # /var/lib/flatpak, so no system-wide Flatpaks exist in CI and every scenario
  # below has nothing to audit. Coverage is real and planned; it becomes runnable
  # once CI seeds system Flatpaks. Unmasking the service is a CI-interface change
  # requiring human sign-off.

  @permissions @pending
  Scenario: be.alexandervanhee.gradia is installed system-wide
    * Flatpak "be.alexandervanhee.gradia" is installed system-wide

  @permissions @pending
  Scenario: com.github.PintaProject.Pinta is installed system-wide
    * Flatpak "com.github.PintaProject.Pinta" is installed system-wide

  @permissions @pending
  Scenario: com.github.tchx84.Flatseal is installed system-wide
    * Flatpak "com.github.tchx84.Flatseal" is installed system-wide

  @permissions @pending
  Scenario: com.mattjakeman.ExtensionManager is installed system-wide
    * Flatpak "com.mattjakeman.ExtensionManager" is installed system-wide

  @permissions @pending
  Scenario: com.ranfdev.DistroShelf is installed system-wide
    * Flatpak "com.ranfdev.DistroShelf" is installed system-wide

  @permissions @pending
  Scenario: io.github.flattool.Ignition is installed system-wide
    * Flatpak "io.github.flattool.Ignition" is installed system-wide

  @permissions @pending
  Scenario: io.github.flattool.Warehouse is installed system-wide
    * Flatpak "io.github.flattool.Warehouse" is installed system-wide

  @permissions @pending
  Scenario: io.github.kolunmi.Bazaar is installed system-wide
    * Flatpak "io.github.kolunmi.Bazaar" is installed system-wide

  @permissions @pending
  Scenario: io.gitlab.adhami3310.Impression is installed system-wide
    * Flatpak "io.gitlab.adhami3310.Impression" is installed system-wide

  @permissions @pending
  Scenario: io.missioncenter.MissionCenter is installed system-wide
    * Flatpak "io.missioncenter.MissionCenter" is installed system-wide

  @permissions @pending
  Scenario: it.mijorus.smile is installed system-wide
    * Flatpak "it.mijorus.smile" is installed system-wide

  @permissions @pending
  Scenario: org.gnome.Calculator is installed system-wide
    * Flatpak "org.gnome.Calculator" is installed system-wide

  @permissions @pending
  Scenario: org.gnome.Calendar is installed system-wide
    * Flatpak "org.gnome.Calendar" is installed system-wide

  @permissions @pending
  Scenario: org.gnome.Characters is installed system-wide
    * Flatpak "org.gnome.Characters" is installed system-wide

  @permissions @pending
  Scenario: org.gnome.Connections is installed system-wide
    * Flatpak "org.gnome.Connections" is installed system-wide

  @permissions @pending
  Scenario: org.gnome.Contacts is installed system-wide
    * Flatpak "org.gnome.Contacts" is installed system-wide

  @permissions @pending
  Scenario: org.gnome.Decibels is installed system-wide
    * Flatpak "org.gnome.Decibels" is installed system-wide

  @permissions @pending
  Scenario: org.gnome.DejaDup is installed system-wide
    * Flatpak "org.gnome.DejaDup" is installed system-wide

  @permissions @pending
  Scenario: org.gnome.FileRoller is installed system-wide
    * Flatpak "org.gnome.FileRoller" is installed system-wide

  @permissions @pending
  Scenario: org.gnome.Firmware is installed system-wide
    * Flatpak "org.gnome.Firmware" is installed system-wide

  @permissions @pending
  Scenario: org.gnome.Logs is installed system-wide
    * Flatpak "org.gnome.Logs" is installed system-wide

  @permissions @pending
  Scenario: org.gnome.Loupe is installed system-wide
    * Flatpak "org.gnome.Loupe" is installed system-wide

  @permissions @pending
  Scenario: org.gnome.Maps is installed system-wide
    * Flatpak "org.gnome.Maps" is installed system-wide

  @permissions @pending
  Scenario: org.gnome.NautilusPreviewer is installed system-wide
    * Flatpak "org.gnome.NautilusPreviewer" is installed system-wide

  @permissions @pending
  Scenario: org.gnome.Papers is installed system-wide
    * Flatpak "org.gnome.Papers" is installed system-wide

  @permissions @pending
  Scenario: org.gnome.Showtime is installed system-wide
    * Flatpak "org.gnome.Showtime" is installed system-wide

  @permissions @pending
  Scenario: org.gnome.SimpleScan is installed system-wide
    * Flatpak "org.gnome.SimpleScan" is installed system-wide

  @permissions @pending
  Scenario: org.gnome.Snapshot is installed system-wide
    * Flatpak "org.gnome.Snapshot" is installed system-wide

  @permissions @pending
  Scenario: org.gnome.TextEditor is installed system-wide
    * Flatpak "org.gnome.TextEditor" is installed system-wide

  @permissions @pending
  Scenario: org.gnome.Weather is installed system-wide
    * Flatpak "org.gnome.Weather" is installed system-wide

  @permissions @pending
  Scenario: org.gnome.baobab is installed system-wide
    * Flatpak "org.gnome.baobab" is installed system-wide

  @permissions @pending
  Scenario: org.gnome.clocks is installed system-wide
    * Flatpak "org.gnome.clocks" is installed system-wide

  @permissions @pending
  Scenario: org.gnome.font-viewer is installed system-wide
    * Flatpak "org.gnome.font-viewer" is installed system-wide

  @permissions @pending
  Scenario: org.mozilla.Thunderbird is installed system-wide
    * Flatpak "org.mozilla.Thunderbird" is installed system-wide

  @permissions @pending
  Scenario: org.mozilla.firefox is installed system-wide
    * Flatpak "org.mozilla.firefox" is installed system-wide

  @permissions @pending
  Scenario: page.tesk.Refine is installed system-wide
    * Flatpak "page.tesk.Refine" is installed system-wide

  @permissions @pending
  Scenario: Calculator Flatpak has no host filesystem access
    * Flatpak "org.gnome.Calculator" sandbox does not have excessive filesystem permissions

  @permissions @pending
  Scenario: Loupe Flatpak has no host filesystem access
    * Flatpak "org.gnome.Loupe" sandbox does not have excessive filesystem permissions

  @permissions @pending
  Scenario: Firefox Flatpak has no host filesystem access
    * Flatpak "org.mozilla.firefox" sandbox does not have excessive filesystem permissions
