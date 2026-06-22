@smoke_suite @bluefin
Feature: xdg-open MIME type handler registration
  Verifies Bluefin's MIME handler assignments so file types resolve to the
  expected desktop applications via the shared MIME database.
  Runner: qecore-headless (local to VM).

  @mime @firefox
  Scenario: HTML files open in Firefox
    * xdg-mime query default for "text/html" returns "org.mozilla.firefox.desktop"

  @mime @pdf
  Scenario: PDF files open in Papers (GNOME Papers)
    * xdg-mime query default for "application/pdf" returns a document viewer

  @mime @image
  Scenario: PNG images open in Loupe or GNOME image viewer
    * xdg-mime query default for "image/png" returns an image viewer

  @mime @text_editor
  Scenario: Plain text opens in GNOME Text Editor
    * xdg-mime query default for "text/plain" returns a text editor

  @mime @video
  Scenario: Video files open in a video player
    * xdg-mime query default for "video/mp4" returns a video player
