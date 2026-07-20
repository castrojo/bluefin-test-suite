@native_app @smoke_suite
Feature: Nautilus drag-and-drop file transfer spike
  Investigates AT-SPI driven drag-and-drop between two Files windows.
  The raw DnD scenario is quarantined while reliability is validated.

  Background:
    * Source and destination directories are created with a marker file

  @quarantine @files @dnd @sla_30s
  Scenario: Drag a file from one Files window into another
    * Files window is open for the source directory
    * A second Files window is open for the destination directory
    * Drag the marker file from the source Files window to the destination Files window
    * The marker file is absent from the source directory
    * The marker file is present in the destination directory
    * Files windows are closed

  @files @clipboard @sla_30s
  Scenario: Move a file between Files windows via clipboard cut and paste
    * Files window is open for the source directory
    * A second Files window is open for the destination directory
    * Select the marker file in the source Files window
    * Key combo: "<Ctrl>x" with uinput
    * Focus the destination Files window
    * Key combo: "<Ctrl>v" with uinput
    * The marker file is absent from the source directory
    * The marker file is present in the destination directory
    * Files windows are closed
