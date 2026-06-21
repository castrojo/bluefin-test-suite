@native_app @smoke_suite
Feature: GNOME Files smoke tests
  Validates GNOME Files (Nautilus) is functional on a fresh Bluefin boot.
  All shared steps come from qecore common_steps; Nautilus-specific checks live in
  gnome_files_steps.py.

  Background:
    * Launch Files via command
    * Files window is accessible

  @retry @files @launch @sla_15s
  Scenario: Files launches and window is accessible
    * Files window is accessible

  @files @sidebar
  Scenario: Home folder is in the sidebar
    * Home folder is in the sidebar

  @files @navigation
  Scenario: Navigating to home folder shows contents
    * Navigate to "Home" in Files sidebar
    * Navigating to home folder shows file listing

  @files @navigation
  Scenario: Back button returns to previous location after navigating to Downloads
    * Navigate to "Downloads" in Files sidebar
    * Nautilus location shows "Downloads"
    * Key combo: "<Alt>Left" with uinput
    * Nautilus location shows "Home"

  @retry @files @new_folder
  Scenario: New folder dialog opens via keyboard shortcut Ctrl+Shift+N
    * Key combo: "<Control><Shift>n" with uinput
    * New folder dialog is open

  @retry @files @search
  Scenario: Search bar opens via Ctrl+F
    * Key combo: "<Control>f" with uinput
    * File search bar is open in Files

  @files @close
  Scenario: Files closes cleanly via Ctrl+W
    * Key combo: "<Ctrl><W>" with uinput
    * Files is no longer running

  @regression @bluefin
  Scenario: No Nautilus coredump after session start
    * No coredump entries exist for "nautilus"
