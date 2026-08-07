@software_suite
Feature: Flatpak per-app permission management
  Flatseal (com.github.tchx84.Flatseal) ships by default on these images, but it is
  only a GUI front end over `flatpak override` and the portal permission store.
  These scenarios assert the same state Flatseal manipulates using the flatpak CLI
  alone, so they need no desktop session and no AT-SPI.

  Every scenario here is deliberately independent of which Flatpaks are installed:
  `flatpak override --user` accepts an application ID that is not installed, and the
  installed-app sweep passes trivially on an empty install set. That is what keeps
  this feature runnable in CI, where `flatpak-preinstall.service` is masked via kernel
  args and `/var/lib/flatpak` is not seeded from the OCI build (the reason the 39
  scenarios in tests/smoke/features/flatpak_permissions.feature are quarantined).

  Scenarios carry @flatpak_cli so environment.py treats them as image-agnostic and
  does not gate them behind Bazaar being installed.

  # org.projectbluefin.TestsuitePermissionProbe is a synthetic application ID that is
  # never installed, so overriding and resetting it cannot clobber real user state.

  @software @flatpak_cli @flatpak_permissions_mgmt
  Scenario: Filesystem permission override round-trips through the user override store
    * Set flatpak user override "--filesystem=xdg-download:ro" for "org.projectbluefin.TestsuitePermissionProbe"
    * Flatpak user override for "org.projectbluefin.TestsuitePermissionProbe" grants "filesystems" value "xdg-download:ro"
    * Reset flatpak user overrides for "org.projectbluefin.TestsuitePermissionProbe"
    * No flatpak user overrides exist for "org.projectbluefin.TestsuitePermissionProbe"

  @software @flatpak_cli @flatpak_permissions_mgmt
  Scenario: Overrides across sockets, devices and environment are stored verbatim
    # These are the four toggle classes Flatseal exposes most prominently.
    * Set flatpak user override "--nosocket=wayland --device=all --share=network --env=BLUEFIN_TESTSUITE=1" for "org.projectbluefin.TestsuitePermissionProbe"
    * Flatpak user override for "org.projectbluefin.TestsuitePermissionProbe" grants "devices" value "all"
    * Flatpak user override for "org.projectbluefin.TestsuitePermissionProbe" grants "shared" value "network"
    * Flatpak user override for "org.projectbluefin.TestsuitePermissionProbe" grants "sockets" value "!wayland"
    * Flatpak user override for "org.projectbluefin.TestsuitePermissionProbe" section "Environment" sets "BLUEFIN_TESTSUITE" to "1"
    * Reset flatpak user overrides for "org.projectbluefin.TestsuitePermissionProbe"

  @software @flatpak_cli @flatpak_permissions_mgmt
  Scenario: Resetting an override clears every recorded permission key
    * Set flatpak user override "--filesystem=home --nosocket=wayland" for "org.projectbluefin.TestsuitePermissionProbe"
    * Flatpak user override for "org.projectbluefin.TestsuitePermissionProbe" records at least "2" permission keys
    * Reset flatpak user overrides for "org.projectbluefin.TestsuitePermissionProbe"
    * Flatpak user override for "org.projectbluefin.TestsuitePermissionProbe" records no permission keys

  @software @flatpak_cli @flatpak_permissions_mgmt
  Scenario: Every installed application exposes a parsable permission set
    # Passes trivially when no Flatpaks are installed, which is the CI case.
    * Every installed flatpak app exposes a parsable permission set

  @software @flatpak_cli @flatpak_permissions_mgmt
  Scenario: Portal permission store backing Flatseal is queryable
    * Flatpak portal permission store is queryable
    * Flatpak permissions table "documents" is queryable
