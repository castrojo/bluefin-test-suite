@input_methods @smoke_suite
Feature: Input method and keyboard layout smoke tests
  Verify the GNOME input-method stack (IBus) is present, the default keyboard
  layout is readable, a second layout can be added and switched via gsettings,
  and localectl reports a console keymap. All checks are headless-safe and run
  inside the VM session via the in-VM execution helper used by other smoke steps.

  @ibus @session
  Scenario: IBus daemon is running in the user session
    * IBus daemon process is present
    * IBus owns org.freedesktop.IBus on the session bus

  @gsettings @layout @default
  Scenario: Default input sources contain a usable keyboard layout
    * Input sources list contains a keyboard layout

  @gsettings @layout @switch
  Scenario: A second keyboard layout can be added and switched via gsettings
    * Current input sources are saved
    * Input sources are set to include a second layout
    * Current input source is switched to index 1
    * Input sources list contains the second layout
    * Current input source index is 1
    * MRU sources contain the second layout
    * Original input sources are restored

  @localectl @keymap
  Scenario: localectl reports a virtual console keymap
    * localectl status reports a keymap
