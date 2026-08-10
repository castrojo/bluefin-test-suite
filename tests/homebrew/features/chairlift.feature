@homebrew @bluefin
Feature: Managed Homebrew and ChairLift integration

  Background:
    * Start application "chairlift" via "command"
    * Wait until "ChairLift" "frame" appears in "chairlift"

  @chairlift @chairlift_cask
  Scenario: managed Homebrew state includes ChairLift
    * The brew-preinstall user service completed successfully
    * The managed Homebrew state lists cask "chairlift"
    * Homebrew reports cask "chairlift" installed

  @chairlift @chairlift_desktop
  Scenario: ChairLift desktop integration is installed for the user
    * The ChairLift command is available
    * The ChairLift desktop entry launches the Homebrew wrapper
    * The ChairLift scalable and symbolic icons exist

  @chairlift @chairlift_config
  Scenario: ChairLift uses Bluefin maintainer configuration
    * ChairLift has no configuration error toast
    * ChairLift shows page "Applications"
    * ChairLift shows page "Updates"
    * ChairLift shows page "Maintenance"
    * ChairLift shows page "System"
    * ChairLift hides page "Features"

  @chairlift @chairlift_config
  Scenario: ChairLift exposes Brew and Flatpak management
    * ChairLift shows group "Homebrew"
    * ChairLift shows group "System Flatpak Applications"

  @chairlift @chairlift_bootc
  Scenario: bootc staging remains authenticated and download-only
    * The ChairLift bootc PolicyKit action requires administrator authentication
    * The ChairLift bootc helper executes only download-only staging
