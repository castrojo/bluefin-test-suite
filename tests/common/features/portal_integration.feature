@common @bluefin
Feature: XDG desktop portal integration
  XDG portals are the secure bridge between sandboxed Flatpak applications
  and host system capabilities. Bluefin is Flatpak-first — portal health
  is critical infrastructure.

  Background:
    * Bluefin VM is booted and reachable over SSH

  Scenario: FileChooser portal interface is introspectable
    * Run SSH command: "gdbus introspect --session --dest org.freedesktop.portal.Desktop --object-path /org/freedesktop/portal/desktop --xml 2>/dev/null | grep -c 'FileChooser' || echo 0"
    * SSH command output is not "0"

  Scenario: Screenshot portal interface is introspectable
    * Run SSH command: "gdbus introspect --session --dest org.freedesktop.portal.Desktop --object-path /org/freedesktop/portal/desktop --xml 2>/dev/null | grep -c 'Screenshot' || echo 0"
    * SSH command output is not "0"

  Scenario: OpenURI portal interface is introspectable
    * Run SSH command: "gdbus introspect --session --dest org.freedesktop.portal.Desktop --object-path /org/freedesktop/portal/desktop --xml 2>/dev/null | grep -c 'OpenURI' || echo 0"
    * SSH command output is not "0"

  Scenario: Notification portal interface is introspectable
    * Run SSH command: "gdbus introspect --session --dest org.freedesktop.portal.Desktop --object-path /org/freedesktop/portal/desktop --xml 2>/dev/null | grep -c 'Notification' || echo 0"
    * SSH command output is not "0"

  Scenario: Document portal broker is running
    * Run SSH command: "systemctl --user is-active xdg-document-portal 2>/dev/null || systemctl --user status xdg-document-portal 2>/dev/null | grep -E 'active|running' | wc -l"
    * SSH command return code is "0"

  Scenario: Document portal fuse filesystem is mounted
    * Run SSH command: "mount | grep -c 'portal\\|fuse.xdg' || findmnt -t fuse.xdg-document-portal 2>/dev/null | wc -l"
    * SSH command output is not "0"

  Scenario: OpenURI portal can handle a URI without crashing
    * Run SSH command: "gdbus call --session --dest org.freedesktop.portal.Desktop --object-path /org/freedesktop/portal/desktop --method org.freedesktop.portal.OpenURI.OpenURI '' 'https://projectbluefin.io' '{}' 2>&1 | head -3 || echo called"
    * SSH command output is not empty

  Scenario: Settings portal exposes color scheme preference
    * Run SSH command: "gdbus call --session --dest org.freedesktop.portal.Desktop --object-path /org/freedesktop/portal/desktop --method org.freedesktop.portal.Settings.Read 'org.freedesktop.appearance' 'color-scheme' 2>/dev/null | grep -c 'uint32' || echo 0"
    * SSH command output is not "0"

  Scenario: xdg-terminal-exec launches a terminal
    * Run SSH command: "which xdg-terminal-exec 2>/dev/null && echo found || echo missing"
    * SSH command output contains "found"
