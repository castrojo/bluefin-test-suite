@smoke_suite
Feature: Display fractional scaling smoke tests
  Validates Mutter DisplayConfig can apply fractional and integer scaling
  on Wayland and that GNOME Shell remains stable after each change.
  Scale is restored to 1.0 after every scenario.

  Background:
    * GNOME Shell is accessible via AT-SPI
    * Fractional scaling experimental feature is enabled if required

  @retry @display_scaling @fractional_scale @scale_1_5 @sla_15s
  Scenario: Fractional scale 1.5 applies via Mutter DisplayConfig
    * Set display scale to the nearest supported value of "1.5" via Mutter DisplayConfig
    * Current display scale matches the applied scale
    * GNOME Shell process is running
    * GNOME Shell is accessible via AT-SPI

  @retry @display_scaling @integer_scale @scale_2_0 @sla_15s
  Scenario: Integer scale 2.0 applies via Mutter DisplayConfig
    * Set display scale to the nearest supported value of "2.0" via Mutter DisplayConfig
    * Current display scale matches the applied scale
    * GNOME Shell process is running
    * GNOME Shell is accessible via AT-SPI
