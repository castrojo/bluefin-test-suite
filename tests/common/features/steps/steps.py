"""Common suite step definitions."""

import base64
import shlex

from behave import step

from tests.shared.ssh_steps import *  # noqa: F401,F403
from tests.shared.ssh_steps import run_ssh


def _run_vm_python(context, script: str) -> tuple[str, str, int]:
    """Run a Python script on the VM via SSH, avoiding shell quoting issues.

    The script is base64-encoded and executed with python3 -c so that complex
    GVariant dicts and D-Bus signal handling do not need to be expressed in a
    single shell-quoted line.
    """
    encoded = base64.b64encode(script.encode("utf-8")).decode("utf-8")
    one_liner = f"import base64; exec(base64.b64decode({encoded!r}))"
    cmd = f"python3 -c {shlex.quote(one_liner)}"
    stdout, rc = run_ssh(context, cmd)
    stderr = getattr(context.last_ssh_result, "stderr", "") if context.last_ssh_result else ""
    return stdout, stderr, rc


@step("Last command exits with non-zero status")
def last_command_exits_with_non_zero_status(context) -> None:
    actual = getattr(context, "ssh_rc", None)
    last_result = getattr(context, "last_ssh_result", None)
    stderr = getattr(last_result, "stderr", "") if last_result else ""
    stdout = getattr(last_result, "stdout", "") if last_result else ""
    assert actual not in (None, 0), (
        "Expected SSH command to exit non-zero\n"
        f"stdout: {stdout}\n"
        f"stderr: {stderr}"
    )


@step("Screenshot portal accepts a non-interactive request")
def screenshot_portal_accepts_noninteractive_request(context) -> None:
    """Call org.freedesktop.portal.Screenshot.Screenshot with interactive=false."""
    script = """
import subprocess
import sys
# Tokens must be valid D-Bus object path elements: [A-Za-z0-9_]
dict_arg = "{'handle_token': <'bluefin_portal_ss_test'>, 'interactive': <false>}"
result = subprocess.run(
    ['gdbus', 'call', '--session', '--dest', 'org.freedesktop.portal.Desktop',
     '--object-path', '/org/freedesktop/portal/desktop',
     '--method', 'org.freedesktop.portal.Screenshot.Screenshot', '', dict_arg],
    capture_output=True, text=True,
)
print(result.stdout, end='')
ok = result.returncode == 0 and 'objectpath' in result.stdout
if not ok:
    print(f"rc={result.returncode} stderr={result.stderr!r}")
sys.exit(0 if ok else 1)
"""
    stdout, stderr, rc = _run_vm_python(context, script)
    context.command_stdout = stdout
    context.ssh_rc = rc
    assert rc == 0, (
        "Screenshot portal did not return a Request handle:\n"
        f"stdout: {stdout}\nstderr: {stderr}"
    )


@step("Screenshot portal request produces a valid PNG")
def screenshot_portal_produces_valid_png(context) -> None:
    """Subscribe to Request::Response, call Screenshot, and verify the PNG file.

    Uses dbus-monitor when available so the Response signal is matched by
    interface/member rather than exact object path; falls back to gdbus monitor
    on the request subtree if dbus-monitor is missing.
    """
    script = """
import os
import re
import shutil
import subprocess
import sys
import time

# Tokens must be valid D-Bus object path elements: [A-Za-z0-9_]
token = f"bluefin_portal_ss_png_{int(time.time())}"
dict_arg = f"{{'handle_token': <'{token}'>, 'interactive': <false>}}"
runtime = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
log = os.path.join(runtime, "portal-screenshot-response.log")
out = os.path.join(runtime, "portal-screenshot-test.png")

for p in (log, out):
    try:
        os.remove(p)
    except FileNotFoundError:
        pass

# Prefer dbus-monitor because it can match the Response signal by
# interface/member regardless of the dynamic request object path.
has_dbus_monitor = shutil.which("dbus-monitor") is not None

with open(log, "w") as log_f:
    if has_dbus_monitor:
        mon = subprocess.Popen(
            ["dbus-monitor", "--session",
             "type='signal',interface='org.freedesktop.portal.Request',member='Response'"],
            stdout=log_f, stderr=subprocess.STDOUT,
        )
    else:
        mon = subprocess.Popen(
            ["gdbus", "monitor", "--session", "--dest", "org.freedesktop.portal.Desktop",
             "--object-path", "/org/freedesktop/portal/desktop/request"],
            stdout=log_f, stderr=subprocess.STDOUT,
        )
    try:
        time.sleep(0.5)
        result = subprocess.run(
            ["gdbus", "call", "--session", "--dest", "org.freedesktop.portal.Desktop",
             "--object-path", "/org/freedesktop/portal/desktop",
             "--method", "org.freedesktop.portal.Screenshot.Screenshot", "", dict_arg],
            capture_output=True, text=True,
        )
        print(f"CALL rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}")
        if result.returncode != 0:
            sys.exit(1)
        time.sleep(4)
    finally:
        mon.terminate()
        try:
            mon.wait(timeout=2)
        except subprocess.TimeoutExpired:
            mon.kill()

with open(log) as f:
    text = f.read()
print("MONITOR OUTPUT:")
print(text)

m = re.search("file://\\\\S+", text)
if not m:
    print("ERROR: no uri in Request::Response")
    sys.exit(1)

uri = m.group(0)
src = uri[len("file://"):]
if not os.path.isfile(src):
    print(f"ERROR: screenshot source missing: {src}")
    sys.exit(1)

shutil.copy(src, out)
with open(out, "rb") as f:
    header = f.read(8)
if header != b"\\x89PNG\\r\\n\\x1a\\n":
    print(f"ERROR: not a PNG: {header!r}")
    sys.exit(1)

print(f"OK: {out}")
"""
    stdout, stderr, rc = _run_vm_python(context, script)
    context.command_stdout = stdout
    context.ssh_rc = rc
    assert rc == 0, (
        "Portal screenshot PNG check failed:\n"
        f"stdout: {stdout}\nstderr: {stderr}"
    )
