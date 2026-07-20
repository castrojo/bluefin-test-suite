@common @bluefin @screencast
Feature: XDG ScreenCast portal plumbing
  The ScreenCast portal lets sandboxed apps request screen capture streams.
  These scenarios assert that the portal D-Bus plumbing, PipeWire socket,
  and session services are present and functional on a headless image;
  they do not capture or inspect pixels.

  Background:
    * Bluefin VM is booted and reachable over SSH

  Scenario: ScreenCast portal interface is exposed
    * Run SSH command: "busctl introspect --user org.freedesktop.portal.Desktop /org/freedesktop/portal/desktop 2>/dev/null | grep -q 'ScreenCast'"
    * SSH command return code is "0"

  Scenario: ScreenCast portal exposes version and available source types
    * Run SSH command: "busctl get-property --user org.freedesktop.portal.Desktop /org/freedesktop/portal/desktop org.freedesktop.portal.ScreenCast version 2>/dev/null"
    * SSH command output contains "u "
    * Run SSH command: "busctl get-property --user org.freedesktop.portal.Desktop /org/freedesktop/portal/desktop org.freedesktop.portal.ScreenCast AvailableSourceTypes 2>/dev/null"
    * SSH command output contains "u "

  Scenario: ScreenCast portal accepts a CreateSession request
    * Run SSH command: "busctl call --user org.freedesktop.portal.Desktop /org/freedesktop/portal/desktop org.freedesktop.portal.ScreenCast CreateSession 'a{sv}' 2 handle_token s bluefin_screencast_test_01 session_handle_token s bluefin_screencast_session_01"
    * SSH command return code is "0"
    * SSH command output contains "/org/freedesktop/portal/desktop/request/"

  Scenario: PipeWire socket is present in the user session
    * Run SSH command: "test -S ${XDG_RUNTIME_DIR}/pipewire-0 && echo present || echo missing"
    * SSH command output contains "present"

  Scenario: PipeWire and WirePlumber user services are active
    * Run SSH command: "systemctl --user is-active pipewire.service wireplumber.service"
    * SSH command return code is "0"
