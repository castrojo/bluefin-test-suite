@smoke_suite @printing
Feature: Printing stack smoke checks
  Validates CUPS is installed, socket-activated, reachable, exposes a working
  GNOME Settings Printers panel, and can accept a job through a virtual raw
  socket queue.

  @printing @cups @systemd @sla_10s
  Scenario: CUPS socket is enabled and active
    * cups.socket is enabled and active

  @printing @cups @scheduler @sla_15s
  Scenario: CUPS scheduler is running
    * CUPS scheduler is running

  @printing @cups @gnome @settings @sla_20s
  Scenario: GNOME Settings Printers panel is accessible
    * Launch Settings via command
    * Settings window is accessible
    * Navigate to Settings panel "Printers"
    * Settings panel "Printers" is visible

  @printing @cups @plumbing @sla_30s
  Scenario: Virtual raw socket printer queue accepts and completes a job
    * virtual raw printer queue "smokeprint" accepts a test job and is removed
