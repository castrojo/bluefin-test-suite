@smoke_suite
Feature: GNOME Text Editor smoke tests
  Validates GNOME Text Editor launches, accepts input, opens core dialogs,
  and exits cleanly on a fresh Bluefin session.

  Background:
    * Launch Text Editor via command

  @text_editor @launch
  Scenario: Text Editor launches and window is accessible
    * Text Editor window has an editable text area

  @text_editor @input
  Scenario: Text Editor accepts keyboard input
    * Text Editor window has an editable text area
    * Type text: "Bluefin smoke test" with uinput
    * Text Editor buffer contains "Bluefin smoke test"

  @text_editor @new_document
  Scenario: New document via Ctrl+N
    * Text Editor window has an editable text area
    * Type text: "Previous document content" with uinput
    * Text Editor buffer contains "Previous document content"
    * Key combo: "<Ctrl><N>" with uinput
    * Text Editor creates a new empty document buffer

  @text_editor @save_dialog
  Scenario: Save dialog via Ctrl+S
    * Text Editor window has an editable text area
    * Type text: "Save dialog smoke test" with uinput
    * Text Editor buffer contains "Save dialog smoke test"
    * Key combo: "<Ctrl><S>" with uinput
    * Text Editor save dialog is open

  @text_editor @discard
  Scenario: Closing with unsaved changes shows discard dialog
    * Text Editor window has an editable text area
    * Type text: "Unsaved content for discard test" with uinput
    * Text Editor buffer contains "Unsaved content for discard test"
    * Key combo: "<Ctrl><Q>" with uinput
    * Text Editor discard dialog is open

  @text_editor @close
  Scenario: Text Editor closes cleanly via Ctrl+Q
    * Text Editor window has an editable text area
    * Key combo: "<Ctrl><Q>" with uinput
    * Text Editor is no longer running

  @text_editor @coredump @regression @bluefin
  Scenario: No gnome-text-editor coredump after session start
    * Run and save command output: "sh -c 'coredumpctl list gnome-text-editor --no-pager --lines=10 2>/dev/null | grep -c gnome-text-editor; true'"
    * Last command output stripped "is" "0"
