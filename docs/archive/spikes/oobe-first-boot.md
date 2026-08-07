> **Archived design spike** — Investigation completed in 2026-08 for issue
> #502. This records a recommendation; it does not approve new test
> infrastructure.

# Spike: GNOME Initial Setup first-boot coverage

> Issue: #502 | Priority: Low | Decision owner: `projectbluefin/lab` maintainers

## Outcome

Do not add a blocking first-boot lane to the current suites. `qecore-headless`
assumes an existing autologin user and a normal desktop session, so it cannot
drive the production GDM to GNOME Initial Setup (GIS) handoff.

A bounded mock-mode probe in a normal session is the lowest-cost next step. It
can establish whether dogtail sees useful GIS accessibility nodes, but it would
cover only wizard UI regressions. A true OOBE integration test still needs a
separate, explicitly approved QEMU boot path with no pre-created user and a
pre-login input mechanism.

## Investigation answers

### 1. Can pages be skipped or preconfigured?

GIS has a supported vendor configuration file:

1. `/etc/gnome-initial-setup/vendor.conf`
2. `/usr/share/gnome-initial-setup/vendor.conf`

The first file found wins. Its `[pages]` group supports `skip`,
`new_user_only`, and `existing_user_only` lists. For example:

```ini
[pages]
skip=network;software
```

The page IDs are defined by GIS and currently include `welcome`, `language`,
`keyboard`, `network`, `privacy`, `timezone`, `software`, `account`,
`password`, `parental_controls`, `parent_password`, and `summary`. The exact
set is build-dependent.

dconf or GSettings defaults can seed values used by a page, but they do not
suppress the page. There is no supported per-page command-line or environment
override. A test should therefore install a temporary vendor file rather than
infer page visibility from seeded settings.

Upstream existing-user mode has exited without showing the wizard since GIS
40. It cannot substitute for testing the new-user flow.

### 2. Can AT-SPI run in the initial-setup session?

Possibly, but this is not a supported qecore configuration and has not been
demonstrated on Bluefin.

AT-SPI uses a dedicated accessibility bus. `org.a11y.Bus.GetAddress` on the
session bus starts or discovers that bus. The GIS new-user flow runs in a
dedicated GNOME kiosk session, not in the normal user's session and not in the
GDM greeter session. That creates three unresolved requirements:

- discover and enter the kiosk user's D-Bus environment before a regular user
  exists;
- ensure the AT-SPI bus launcher starts in the reduced kiosk session; and
- provide Wayland input injection, which dogtail alone cannot do.

The current harness solves these requirements only after autologin by sourcing
`/tmp/session.env`, enabling `toolkit-accessibility`, and using
`gnome-ponytail-daemon`. Reusing those steps pre-login would be a new,
empirically validated harness rather than a qecore option.

### 3. Is a separate QEMU boot sequence required?

Yes, for true OOBE coverage.

The reusable workflow creates a new disk, but then deliberately makes it
unsuitable for GIS before boot:

- writes the `bluefin-test` account directly into passwd, shadow, and group;
- enables GDM autologin for that account;
- also suppresses systemd-firstboot with `systemd.firstboot=no`; and
- waits for that user's SSH and graphical session before starting qecore.

GIS new-user mode is selected by GDM when no regular user exists. GDM also
supports the `gnome.initial-setup=1` kernel argument for debugging, but forcing
GIS while retaining the existing autologin contract would not validate the
real no-user handoff.

GIS records completion in
`$XDG_CONFIG_HOME/gnome-initial-setup-done`. A repeatable integration test must
start from a writable disk without the created user or completion stamp, run
the wizard, then verify the account and handoff state. This should be a
separate opt-in job so it cannot change the existing suite contract.

### 4. Does qecore-headless support pre-login tests?

No. qecore describes `qecore-headless` as a session configuration tool for an
SSH-connected machine. It configures GDM autologin, waits for a user session,
and then runs AT-SPI/dogtail automation. It does not expose a GDM/GIS driver,
QMP or VNC control, framebuffer matching, or a pre-login session hook.

The testsuite QEMU process already exposes a human-monitor socket and
`qemu_screendump.py` captures its framebuffer. That is observation only; the
repository has no corresponding pre-login input or image-recognition layer.

## Options

| Option | Coverage | Cost and risk | Recommendation |
|---|---|---|---|
| GIS mock mode in the normal qecore session | Page presence, accessibility tree, navigation | Low cost; does not test GDM, account creation, or session handoff; `UNDER_JHBUILD` is a development hook rather than a stable API | Run only as a bounded feasibility probe |
| AT-SPI inside the true GIS kiosk session | Real page semantics and accessibility | High risk; requires custom session-bus discovery and Wayland input before login | Stop if the probe cannot prove this reliably |
| QEMU monitor input plus framebuffer checkpoints | Full GDM to GIS to user-session path | High maintenance; keyboard/input sequencing and visual assertions are brittle | Preferred mechanism only if maintainers fund true integration coverage |
| Nested GIS or existing-user mode | Partial simulation | Does not reproduce the production new-user session; existing-user mode is disabled upstream | No-go |

## Proposed feasibility gate

Before creating a suite, workflow input, or lab resource:

1. On a disposable Bluefin VM, inspect the shipped `vendor.conf` and record the
   actual page sequence.
2. Run `UNDER_JHBUILD=1 gnome-initial-setup` in the existing qecore session.
3. Prove dogtail can identify the GIS application plus meaningful controls on
   at least the language and privacy pages.
4. Prove keyboard navigation can reach the summary page without writing
   `~/.config/gnome-initial-setup-done`.
5. Record the AT-SPI tree and screenshots as spike artifacts.

Fail the probe if GIS does not launch, the accessibility tree is empty, input
cannot be injected, the completion stamp is written, or the flow exceeds two
minutes. Failure means no qecore-based OOBE work should proceed.

Passing the probe authorizes discussion of UI-only coverage, not a claim of
first-boot coverage.

## Acceptance criteria for true OOBE coverage

A future implementation proposal must demonstrate all of the following before
it becomes a required gate:

- a fresh writable disk has no regular user or GIS completion stamp;
- GDM selects the GIS new-user kiosk session without autologin;
- the test asserts the expected vendor-controlled page sequence;
- deterministic input completes the selected pages and creates a non-root
  user;
- the created user reaches a normal GNOME session after GIS exits;
- locale, keyboard, privacy, and account results are verified outside the UI;
- serial logs and framebuffer screenshots are retained on failure; and
- runtime and flake rate are acceptable across at least three consecutive
  manual lab runs.

Any VM or orchestration work belongs in `projectbluefin/lab`; test content and
reusable workflow code belong in this repository. The design and merge gates
still apply before either implementation starts.

## Maintainer decision requested

Choose one scope:

1. Approve the bounded mock-mode probe for UI-only coverage.
2. Fund a separate true-OOBE QEMU/QMP spike and its lab resources.
3. Defer both and retain OOBE as a documented low-priority gap.

## Sources

- [GIS vendor configuration and operating modes](https://gitlab.gnome.org/GNOME/gnome-initial-setup/-/blob/main/README.md)
- [GIS page table, skip logic, existing-user exit, mock mode, and completion stamp](https://gitlab.gnome.org/GNOME/gnome-initial-setup/-/blob/main/gnome-initial-setup/gnome-initial-setup.c)
- [GIS new-user systemd service](https://gitlab.gnome.org/GNOME/gnome-initial-setup/-/blob/main/data/gnome-initial-setup.service.in)
- [GIS first-login systemd service](https://gitlab.gnome.org/GNOME/gnome-initial-setup/-/blob/main/data/gnome-initial-setup-first-login.service.in)
- [Forcing Initial Setup from the kernel command line](https://gitlab.gnome.org/GNOME/gnome-initial-setup/-/blob/main/DEBUGGING.md)
- [AT-SPI accessibility bus architecture](https://gitlab.gnome.org/GNOME/at-spi2-core/-/blob/main/bus/README.md)
- [qecore package documentation](https://pypi.org/project/qecore/)
- [qecore source](https://gitlab.com/dogtail/qecore)
