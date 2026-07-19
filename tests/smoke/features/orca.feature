@orca @accessibility @smoke_suite
Feature: Orca screen reader
  Verify the Orca screen reader stack is installed, the screen-reader
  gsettings toggle starts and stops Orca, and speech-dispatcher responds.

  @orca @binary @a11y
  Scenario: Orca and speech-dispatcher binaries are installed
    * Run and save command output: "command -v orca && rpm -q orca speech-dispatcher"
    * Return code of last command output "is" "0"
    * Last command output "contains" "orca-"
    * Last command output "contains" "speech-dispatcher-"

  @orca @a11y @bus
  Scenario: AT-SPI accessibility bus name is registered
    * Run and save command output: "busctl --user list | grep -q org.a11y.Bus"
    * Return code of last command output "is" "0"

  @orca @a11y @screen_reader @retry
  Scenario: Screen reader toggle starts and stops Orca
    * Screen reader enabled state toggles Orca on and off

  @orca @speech @retry
  Scenario: Speech Dispatcher responds to a module list request
    * Run and save command output: "spd-say -O"
    * Return code of last command output "is" "0"
