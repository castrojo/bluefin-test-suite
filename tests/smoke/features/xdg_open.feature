@smoke_suite @bluefin
Feature: xdg-open MIME type handler registration
  Verifies Bluefin's MIME handler assignments so file types resolve to the
  expected desktop applications via the shared MIME database.
  Runner: qecore-headless (local to VM).

  @mime @firefox
  Scenario: HTML files open in Firefox
    * xdg-mime query default for "text/html" returns "org.mozilla.firefox.desktop"

  # Pending: Fedora's system mimeapps.list sets Firefox as the default handler and
  # Flatpak apps do not override defaults at the system level (#529).
  @mime @pdf @pending
  Scenario: PDF files open in Papers (GNOME Papers)
    * xdg-mime query default for "application/pdf" returns a document viewer

  # Pending: system mimeapps.list default, see #529.
  @mime @image @pending
  Scenario: PNG images open in Loupe or GNOME image viewer
    * xdg-mime query default for "image/png" returns an image viewer

  @mime @text_editor
  Scenario: Plain text opens in GNOME Text Editor
    * xdg-mime query default for "text/plain" returns a text editor

  # Pending: system mimeapps.list default, see #529.
  @mime @video @pending
  Scenario: Video files open in a video player
    * xdg-mime query default for "video/mp4" returns a video player
