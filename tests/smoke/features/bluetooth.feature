@smoke_suite @bluetooth
Feature: Bluetooth stack coverage via virtual HCI
  Validates that the BlueZ stack is installed and configured, that a
  virtual HCI controller can be created with hci_vhci, and that GNOME
  Settings exposes the Bluetooth panel when the adapter is present.

  @bluetooth @presence @sla_10s
  Scenario: BlueZ daemon and service unit are present
    * the bluetoothd binary is present
    * the bluetooth.service unit file is present

  @bluetooth @vhci @sla_30s @retry
  Scenario: hci_vhci virtual adapter appears and powers on
    * bluetooth.service is started if inactive
    * the hci_vhci kernel module is loaded
    * a Bluetooth controller appears within 10 seconds
    * the Bluetooth controller is powered on

  @bluetooth @gnome @settings @sla_30s @retry
  Scenario: GNOME Settings Bluetooth panel opens with virtual adapter
    * bluetooth.service is started if inactive
    * the hci_vhci kernel module is loaded
    * a Bluetooth controller appears within 10 seconds
    * Launch Settings via command
    * Settings window is accessible
    * Navigate to Settings panel "Bluetooth"
    * Settings panel "Bluetooth" is visible

  @bluetooth @vhci @cleanup @sla_15s
  Scenario: virtual Bluetooth adapter is removed
    * the Bluetooth controller is powered off if present
    * the hci_vhci kernel module is removed if possible
