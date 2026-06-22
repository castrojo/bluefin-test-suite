@smoke @bluefin
Feature: Bluefin GNOME extension presence
  Validates that all extensions enabled by default in Bluefin are loaded
  and in ENABLED state. A non-1 state means the extension crashed or was
  disabled — which breaks the Bluefin UX.
  Runner: qecore-headless + behave (same as smoke suite).

  Background:
    * GNOME Shell is accessible via AT-SPI

  @smoke @bluefin
  Scenario: Dash to Dock extension is enabled
    * GNOME extension "dash-to-dock@micxgx.gmail.com" is enabled

  @smoke @bluefin
  Scenario: AppIndicator extension is enabled
    * GNOME extension "appindicatorsupport@rgcjonas.gmail.com" is enabled

  @smoke @bluefin
  Scenario: Blur My Shell extension is enabled
    * GNOME extension "blur-my-shell@aunetx" is enabled

  @smoke @bluefin
  Scenario: GSConnect extension is enabled
    * GNOME extension "gsconnect@andyholmes.github.io" is enabled

  @smoke @bluefin
  Scenario: Search Light extension is enabled
    * GNOME extension "search-light@icedman.github.com" is enabled

  @smoke @bluefin
  Scenario: Custom Command Menu extension is enabled
    * GNOME extension "custom-command-list@storageb.github.com" is enabled

  @smoke @bluefin
  Scenario: Background Logo extension is enabled
    * GNOME extension "background-logo@fedorahosted.org" is enabled
