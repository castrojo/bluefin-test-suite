@smoke_suite
Feature: GNOME Files smoke tests
  Validates GNOME Files (Nautilus) is functional on a fresh Bluefin boot.
  All shared steps come from qecore common_steps; Nautilus-specific checks live in
  gnome_files_steps.py.

  Background:
    * Start application "nautilus" via "command"
    * Wait until "Files" "frame" appears in "nautilus"

  @files @launch
  Scenario: Files launches and window is accessible
    * Application "nautilus" is running
    * Item "Files" "frame" is "showing" in "nautilus"

  @files @sidebar
  Scenario: Home folder is in the sidebar
    * Home folder is in the sidebar

  @files @navigation
  Scenario: Navigating to home folder shows contents
    * Left click "Home" "list item" in "nautilus"
    * Navigating to home folder shows file listing

  @files @navigation
  Scenario: Back button returns to previous location after navigating to Downloads
    * Left click "Downloads" "list item" in "nautilus"
    * Item "Downloads" "toggle button" is "showing" in "nautilus"
    * Key combo: "<Alt>Left" with uinput
    * Item "Home" "toggle button" is "showing" in "nautilus"

  @files @new_folder
  Scenario: New folder dialog opens via keyboard shortcut Ctrl+Shift+N
    * Key combo: "<Control><Shift>n" with uinput
    * New folder dialog is open

  @files @close
  Scenario: Files closes cleanly via Ctrl+W
    * Close application "nautilus" via "shortcut"
    * Application "nautilus" is no longer running

  @regression @bluefin
  Scenario: No Nautilus coredump after session start
    * Run and save command output: "sh -c 'coredumpctl list nautilus --no-pager --lines=10 2>/dev/null | grep -c nautilus; true'"
    * Last command output stripped "is" "0"
