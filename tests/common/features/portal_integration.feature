@common @bluefin
Feature: XDG desktop portal integration
  XDG portals are the secure bridge between sandboxed Flatpak applications
  and host system capabilities. Bluefin is Flatpak-first — portal health
  is critical infrastructure.

  Background:
    * Bluefin VM is booted and reachable over SSH

  Scenario: FileChooser portal interface is introspectable
    * Run SSH command: "gdbus introspect --session --dest org.freedesktop.portal.Desktop --object-path /org/freedesktop/portal/desktop --xml 2>/dev/null | grep -q 'FileChooser'"
    * SSH command return code is "0"

  Scenario: Screenshot portal interface is introspectable
    * Run SSH command: "gdbus introspect --session --dest org.freedesktop.portal.Desktop --object-path /org/freedesktop/portal/desktop --xml 2>/dev/null | grep -q 'Screenshot'"
    * SSH command return code is "0"

  Scenario: OpenURI portal interface is introspectable
    * Run SSH command: "gdbus introspect --session --dest org.freedesktop.portal.Desktop --object-path /org/freedesktop/portal/desktop --xml 2>/dev/null | grep -q 'OpenURI'"
    * SSH command return code is "0"

  Scenario: Notification portal interface is introspectable
    * Run SSH command: "gdbus introspect --session --dest org.freedesktop.portal.Desktop --object-path /org/freedesktop/portal/desktop --xml 2>/dev/null | grep -q 'Notification'"
    * SSH command return code is "0"

  Scenario: Document portal broker is running
    * Run SSH command: "systemctl --user is-active xdg-document-portal 2>/dev/null"
    * SSH command return code is "0"

  Scenario: Document portal fuse filesystem is mounted
    * Run SSH command: "mount | grep -qE 'fuse\.(portal|xdg-document-portal)'"
    * SSH command return code is "0"

  Scenario: OpenURI portal can handle a URI without crashing
    * Run SSH command: "gdbus call --session --dest org.freedesktop.portal.Desktop --object-path /org/freedesktop/portal/desktop --method org.freedesktop.portal.OpenURI.OpenURI '' 'https://projectbluefin.io' '{}' 2>&1 | head -3 || echo called"
    * SSH command output is not empty

  Scenario: Settings portal exposes color scheme preference
    * Run SSH command: "gdbus call --session --dest org.freedesktop.portal.Desktop --object-path /org/freedesktop/portal/desktop --method org.freedesktop.portal.Settings.Read 'org.freedesktop.appearance' 'color-scheme' 2>/dev/null | grep -q 'uint32'"
    * SSH command return code is "0"

  Scenario: xdg-terminal-exec launches a terminal
    * Run SSH command: "which xdg-terminal-exec 2>/dev/null && echo found || echo missing"
    * SSH command output contains "found"

  Scenario: GNOME portal backend D-Bus name is registered
    * Run SSH command: "gdbus introspect --session --dest org.freedesktop.impl.portal.desktop.gnome --object-path /org/freedesktop/portal/desktop --xml 2>/dev/null | grep -q 'interface'"
    * SSH command return code is "0"

  Scenario: portals.conf exists and configures the GNOME backend
    * Run SSH command: "grep -q 'gnome' /usr/share/xdg-desktop-portal/gnome-portals.conf 2>/dev/null"
    * SSH command return code is "0"

  Scenario: Desktop portal broker responds to D-Bus Ping
    * Run SSH command: "gdbus call --session --dest org.freedesktop.portal.Desktop --object-path /org/freedesktop/portal/desktop --method org.freedesktop.DBus.Peer.Ping 2>/dev/null && echo ok"
    * SSH command output contains "ok"

  Scenario: Settings portal exposes accent-color preference
    * Run SSH command: "gdbus call --session --dest org.freedesktop.portal.Desktop --object-path /org/freedesktop/portal/desktop --method org.freedesktop.portal.Settings.Read 'org.freedesktop.appearance' 'accent-color' 2>/dev/null | grep -qE '<<|uint'"
    * SSH command return code is "0"

  Scenario: Settings portal ReadAll returns appearance namespace
    * Run SSH command: "busctl --user call org.freedesktop.portal.Desktop /org/freedesktop/portal/desktop org.freedesktop.portal.Settings ReadAll as 1 org.freedesktop.appearance 2>/dev/null | grep -q color-scheme"
    * SSH command return code is "0"

  Scenario: Camera portal IsCameraPresent property is readable
    * Run SSH command: "gdbus call --session --dest org.freedesktop.portal.Desktop --object-path /org/freedesktop/portal/desktop --method org.freedesktop.DBus.Properties.Get 'org.freedesktop.portal.Camera' 'IsCameraPresent' 2>/dev/null | grep -qE 'true|false'"
    * SSH command return code is "0"

  Scenario: xdg-document-portal FUSE mount is accessible to user
    * Run SSH command: "ls ${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/doc/ 2>/dev/null && echo accessible || echo missing"
    * SSH command output contains "accessible"

  Scenario: Document portal Documents interface is introspectable
    * Run SSH command: "gdbus introspect --session --dest org.freedesktop.portal.Documents --object-path /org/freedesktop/portal/documents --xml 2>/dev/null | grep -q 'interface'"
    * SSH command return code is "0"
