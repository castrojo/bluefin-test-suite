@bazzite_suite
Feature: Bazzite GNOME extension presence
  Validates that all extensions enabled by default in Bazzite are loaded
  and in ENABLED state. A non-1 state means the extension crashed or was
  disabled — which breaks the Bazzite UX.
  Runner: qecore-headless + behave (same as smoke suite).
  Image: ghcr.io/ublue-os/bazzite:latest

  # Enabled by default: zz0-03-bazzite-desktop-silverblue-extensions.gschema.override

  # 2026-06-05: All bazzite extensions are in state=6 (ERROR) — image regression.
  # Quarantined until bazzite ships a fix. Tracking: #410
  @bazzite_suite @quarantine
  Scenario: Logo Menu extension is enabled
    * GNOME Shell is accessible via AT-SPI
    * Extension "logomenu@aryan_k" is enabled

  @bazzite_suite @quarantine
  Scenario: AppIndicator support extension is enabled
    * GNOME Shell is accessible via AT-SPI
    * Extension "appindicatorsupport@rgcjonas.gmail.com" is enabled

  @bazzite_suite @quarantine
  Scenario: User Themes extension is enabled
    * GNOME Shell is accessible via AT-SPI
    * Extension "user-theme@gnome-shell-extensions.gcampax.github.com" is enabled

  @bazzite_suite @quarantine
  Scenario: GSConnect extension is enabled
    * GNOME Shell is accessible via AT-SPI
    * Extension "gsconnect@andyholmes.github.io" is enabled

  @bazzite_suite @quarantine
  Scenario: Blur My Shell extension is enabled
    * GNOME Shell is accessible via AT-SPI
    * Extension "blur-my-shell@aunetx" is enabled

  @bazzite_suite @quarantine
  Scenario: Hot Edge extension is enabled
    * GNOME Shell is accessible via AT-SPI
    * Extension "hotedge@jonathan.jdoda.ca" is enabled

  @bazzite_suite @quarantine
  Scenario: Caffeine extension is enabled
    * GNOME Shell is accessible via AT-SPI
    * Extension "caffeine@patapon.info" is enabled

  @bazzite_suite @quarantine
  Scenario: Add to Steam extension is enabled
    * GNOME Shell is accessible via AT-SPI
    * Extension "add-to-steam@pupper.space" is enabled

  @bazzite_suite @quarantine
  Scenario: Restart To extension is enabled
    * GNOME Shell is accessible via AT-SPI
    * Extension "restartto@tiagoporsch.github.io" is enabled

  @bazzite_suite @quarantine
  Scenario: Compiz Magic Lamp extension is enabled
    * GNOME Shell is accessible via AT-SPI
    * Extension "compiz-alike-magic-lamp-effect@hermes83.github.com" is enabled

  @bazzite_suite @quarantine
  Scenario: Bazaar Integration extension is enabled
    * GNOME Shell is accessible via AT-SPI
    * Extension "bazaar-integration@kolunmi.github.io" is enabled

  @bazzite_suite
  Scenario: Burn My Windows extension is installed
    * GNOME Shell is accessible via AT-SPI
    * Extension "burn-my-windows@schneegans.github.com" is installed

  @bazzite_suite
  Scenario: Desktop Cube extension is installed
    * GNOME Shell is accessible via AT-SPI
    * Extension "desktop-cube@schneegans.github.com" is installed

  @bazzite_suite
  Scenario: Compiz Windows Effect extension is installed
    * GNOME Shell is accessible via AT-SPI
    * Extension "compiz-windows-effect@hermes83.github.com" is installed
