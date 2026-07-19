@common @bluefin
Feature: XDG desktop portal Screenshot interface
  The Screenshot portal lets sandboxed Flatpak applications request a
  screenshot without direct display access. Bluefin's portal broker must
  expose the interface, accept non-interactive requests, and return a valid
  image. These scenarios focus on the org.freedesktop.portal.Screenshot call
  path; the broader portal health checks live in portal_integration.feature.

  Background:
    * Bluefin VM is booted and reachable over SSH

  Scenario: Screenshot portal exposes version property
    * Run SSH command: "gdbus call --session --dest org.freedesktop.portal.Desktop --object-path /org/freedesktop/portal/desktop --method org.freedesktop.DBus.Properties.Get 'org.freedesktop.portal.Screenshot' 'version' 2>/dev/null | grep -qE 'uint32|int32'"
    * SSH command return code is "0"

  Scenario: Screenshot portal accepts a non-interactive request
    * Screenshot portal accepts a non-interactive request

  @quarantine
  Scenario: Screenshot portal request produces a valid PNG
    # Quarantine reason: the Screenshot portal backend in the non-interactive
    # headless CI session does not emit a usable Request::Response with a
    # file:// URI. The broker accepts the request (scenario above), but the
    # backend needs a real compositor/display session to produce an image.
    # Other portal backends in this session show the same limitation.
    * Screenshot portal request produces a valid PNG
