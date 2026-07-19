@smoke_suite
Feature: XWayland smoke tests
  Validates XWayland is present and usable when a native X11 client connects
  and runs without crashing.  Uses glxgears from glx-utils because it is a
  pure X11 GLX client (links libX11, calls XOpenDisplay) that ships on stock
  Fedora/GNOME images.

  Background:
    * X11 client glxgears is available
    * Terminate any running glxgears

  @xwayland @on_demand
  Scenario: XWayland process appears when an X11 client connects
    * Launch glxgears via command
    * XWayland process appears within 10 seconds
    * Terminate glxgears

  @xwayland @client
  Scenario: X11 client can use the XWayland display
    * Launch glxgears via command
    * XWayland process appears within 10 seconds
    * xprop can query the X root window
    * Terminate glxgears

  @xwayland @clean_exit
  Scenario: XWayland incurs no coredump after the X11 client closes
    * Launch glxgears via command
    * XWayland process appears within 10 seconds
    * Terminate glxgears
    * Wait 2 seconds
    * No coredump entries exist for "Xwayland"
