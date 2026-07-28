@kde_smoke @informational
Feature: KDE Plasma smoke tests
  First KDE Plasma harness validation for Project Bluefin.
  Aurora-only, deliberately tiny (≤15 scenarios), all @informational.
  No golden snapshots; assertions are invariants over process state, D-Bus
  service presence, roles, and regex-matched window names.

  evaluateScript is reserved for diagnostics and session reset.  Every user
  action asserted here (app launch, Kickoff open) uses a real activation path.

  @session @processes
  Scenario: Plasma session processes are running
    * the Plasma session processes "kwin_wayland,plasmashell" are running

  @session @wayland
  Scenario: Session is Wayland
    * the session type is "wayland"

  @a11y @dbus
  Scenario: AT-SPI accessibility bus is reachable
    * the D-Bus service "org.a11y.Bus" is present on the session bus

  @plasma @dbus
  Scenario: org.kde.plasmashell D-Bus service is present
    * the D-Bus service "org.kde.plasmashell" is present on the session bus

  @kwin @dbus
  Scenario: org.kde.KWin D-Bus service is present
    * the D-Bus service "org.kde.KWin" is present on the session bus

  @systemd @health
  Scenario: No failed systemd units
    * No failed systemd units at boot

  @coredump @session
  Scenario: No coredumps from Plasma session processes
    * No coredump entries exist for any of "kwin_wayland,plasmashell,ksmserver"

  @kwin @outputs
  Scenario: KWin reports at least one output
    * KWin reports at least "1" output

  @apps @kcm
  Scenario: A known KCM opens and its window appears
    * Launch "kcmshell6 kcm_autostart" and wait for its window
    * Window whose name matches "Autostart|Session" is present
    * Close the active KCM window

  @apps @dolphin
  Scenario: Dolphin launches and its window appears
    * Launch "dolphin" and wait for its window
    * Window whose name matches "Dolphin" is present
    * Close the active application window

  @apps @konsole
  Scenario: Konsole launches and its window appears
    * Launch "konsole" and wait for its window
    * Window whose name matches "Konsole" is present
    * Close the active application window

  @panel @a11y
  Scenario: System tray panel exists in the AT-SPI tree
    * the Plasma panel exists in the AT-SPI tree

  @kickoff @a11y
  Scenario: Kickoff application launcher opens
    * Open Kickoff via the Plasma launcher D-Bus action
    * the Kickoff window is present in the AT-SPI tree
    * Close the Kickoff window
