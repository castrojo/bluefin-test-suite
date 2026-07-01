@aurora_suite @plasma_settings
Feature: Aurora Custom Settings and KCM accessibility
  Validates that Aurora's KDE Plasma desktop-related customization modules (KCMs)
  are accessible, allowing settings manipulation (such as changing the SDDM Login theme).

  Scenario: Launch and verify the SDDM Vapor Login Screen setting
    Given the KCM module "kcm_sddm" is running under kcmshell6
    Then the "Login Screen (SDDM)" window is visible
    And the "Bazzite Vapor" theme entry is present in the list
    When I click the list item "Bazzite Vapor"
    Then the "Apply" button is enabled
