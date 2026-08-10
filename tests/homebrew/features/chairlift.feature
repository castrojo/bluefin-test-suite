@homebrew @bluefin
Feature: Managed Homebrew and ChairLift integration

  # No feature-level Background: the packaging scenarios assert the cask state,
  # the system-wide desktop files, and the bootc PolicyKit contract without
  # ever launching the app, so a UI launch failure cannot mask a packaging
  # regression. Only @chairlift_ui scenarios start ChairLift. The AT-SPI
  # application root is the binary name "chairlift"; "ChairLift" is the frame
  # title.

  @chairlift @chairlift_cask
  Scenario: managed Homebrew state includes ChairLift
    * The brew-preinstall user service completed successfully
    * The managed Homebrew state lists cask "chairlift"
    * Homebrew reports cask "chairlift" installed

  @chairlift @chairlift_desktop
  Scenario: ChairLift desktop integration is installed for every user
    * The ChairLift command is available
    * The ChairLift desktop entry launches the Homebrew wrapper
    * The ChairLift scalable and symbolic icons exist

  @chairlift @chairlift_config @chairlift_ui
  Scenario: ChairLift uses Bluefin maintainer configuration
    * Start application "chairlift" via "command"
    * Wait until "ChairLift" "frame" appears in "chairlift"
    * ChairLift has no configuration error toast
    * ChairLift shows page "Applications"
    * ChairLift shows page "Updates"
    * ChairLift shows page "Maintenance"
    * ChairLift shows page "System"
    * ChairLift hides page "Features"

  @chairlift @chairlift_config @chairlift_ui
  Scenario: ChairLift exposes Brew and Flatpak management
    * Start application "chairlift" via "command"
    * Wait until "ChairLift" "frame" appears in "chairlift"
    * ChairLift shows group "Homebrew"
    * ChairLift shows group "System Flatpak Applications"

  @chairlift @chairlift_bootc
  Scenario: bootc staging remains authenticated and never applies on its own
    * The ChairLift bootc PolicyKit action requires administrator authentication
    * The ChairLift bootc helper stages the update without applying it
