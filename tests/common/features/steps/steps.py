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


@step('ujust --choose runs mocked fzf recipe "{recipe}"')
def ujust_choose_mocked_fzf(context, recipe: str) -> None:
    """Run ``ujust --choose`` with a non-interactive fzf mock selecting recipe.

    Creates a fake fzf binary that ignores stdin and arguments, records that it
    was consulted, prints the chosen recipe name, and invokes ``ujust --choose``
    with it on PATH. ``FZF_INVOKED`` and ``CHOOSE_RC`` are echoed so callers can
    prove the chooser actually went through the mock instead of falling back to
    a plain recipe listing.
    """
    mock_dir = "/tmp/fake-fzf-bin"
    recipe_quoted = shlex.quote(recipe)
    script = (
        f"mkdir -p {mock_dir} && "
        f"rm -f {mock_dir}/invoked && "
        f"printf '#!/bin/sh\ncat >/dev/null\ntouch {mock_dir}/invoked\necho %s\n' "
        f"{recipe_quoted} > {mock_dir}/fzf && "
        f"chmod +x {mock_dir}/fzf && "
        f"rc=0; PATH={mock_dir}:$PATH ujust --choose || rc=$?; "
        f"if [ -e {mock_dir}/invoked ]; then echo FZF_INVOKED=1; "
        f"else echo FZF_INVOKED=0; fi; "
        f"echo CHOOSE_RC=$rc; exit $rc"
    )
    run_ssh(context, script)

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


@step("ujust report runs with safe mocks and exits cleanly")
def ujust_report_safe_mocks(context) -> None:
    """Run ``ujust report`` with mocked gum/gh/xdg-open/glow.

    Avoids interactive prompts and any real GitHub gist upload while still
    exercising the successful-upload code path, including the local copy
    persist step (regression guard for projectbluefin/dakota#913) and the
    final exit status (projectbluefin/dakota#940).
    """
    script = r"""
set -euo pipefail

mock_dir="$(mktemp -d)"
trap 'rm -rf "$mock_dir"' EXIT

# Mock gum: skip deep metrics, approve upload, no-op style/pager, exec spin.
cat > "$mock_dir/gum" <<'GUM_EOF'
#!/bin/sh
set -e
case "$1" in
  style) exit 0 ;;
  pager) cat >/dev/null; exit 0 ;;
  confirm)
    if printf '%s\n' "$*" | grep -qi "deep"; then
      exit 1  # skip deep hardware metrics
    fi
    exit 0  # approve upload
    ;;
  spin)
    shift
    while [ "$#" -gt 0 ] && [ "$1" != "--" ]; do
      shift
    done
    [ "$1" = "--" ] && shift
    exec "$@"
    ;;
  choose)
    shift
    # Drive the real bonedigger-report prompts instead of answering "Skip" to
    # every chooser, which silently short-circuits main() and exercises nothing.
    if printf '%s\n' "$*" | grep -q -- "--no-limit"; then
      echo "Update / boot"
    elif printf '%s\n' "$*" | grep -q "Bug report"; then
      echo "Bug report"
    elif printf '%s\n' "$*" | grep -q "queue preference"; then
      echo "No queue preference"
    else
      exit 1
    fi
    exit 0
    ;;
  *) exit 0 ;;
esac
GUM_EOF
chmod +x "$mock_dir/gum"

# Mock gh: active auth, fake gist URL.
cat > "$mock_dir/gh" <<'GH_EOF'
#!/bin/sh
set -e
log="$MOCK_GH_LOG"
printf '%s\n' "$*" >> "$log"
case "$1" in
  auth) exit 0 ;;
  gist)
    # Assert on the actual invocation: bonedigger-report calls
    # `gh gist create --public --desc <text> <file>...`. Accepting every
    # `gh gist` call proves nothing about what would be uploaded.
    [ "$2" = "create" ] || { echo "unexpected gist subcommand: $2" >&2; exit 1; }
    saw_desc=0
    files=0
    shift 2
    while [ "$#" -gt 0 ]; do
      case "$1" in
        --public|--public=*) ;;
        --desc) saw_desc=1; shift ;;
        --desc=*) saw_desc=1 ;;
        -*) echo "unexpected gist flag: $1" >&2; exit 1 ;;
        *)
          [ -f "$1" ] || { echo "gist file missing: $1" >&2; exit 1; }
          files=$((files + 1))
          ;;
      esac
      shift
    done
    [ "$saw_desc" = "1" ] || { echo "gist create without --desc" >&2; exit 1; }
    [ "$files" -gt 0 ] || { echo "gist create without files" >&2; exit 1; }
    echo "MOCK_GH_GIST_OK=1" >> "$log"
    echo "https://gist.github.com/ujust-test/dakota-report-913-940"
    exit 0
    ;;
  issue)
    # Never reach the network: assert the shape and return a fake URL.
    [ "$2" = "create" ] || { echo "unexpected issue subcommand: $2" >&2; exit 1; }
    echo "MOCK_GH_ISSUE_OK=1" >> "$log"
    echo "https://github.com/projectbluefin/dakota/issues/999999"
    exit 0
    ;;
  *) exit 1 ;;
esac
GH_EOF
chmod +x "$mock_dir/gh"

# Mock xdg-open and glow so the report never leaves the VM or blocks.
cat > "$mock_dir/xdg-open" <<'XDG_EOF'
#!/bin/sh
exit 0
XDG_EOF
chmod +x "$mock_dir/xdg-open"

cat > "$mock_dir/glow" <<'GLOW_EOF'
#!/bin/sh
cat >/dev/null
exit 0
GLOW_EOF
chmod +x "$mock_dir/glow"

export PATH="$mock_dir:$PATH"
MOCK_GH_LOG="$mock_dir/gh.log"
export MOCK_GH_LOG
: > "$MOCK_GH_LOG"
LOCAL_REPORT_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/ujust-report/last"
rm -rf "$LOCAL_REPORT_DIR"

rc=0
ujust report || rc=$?
printf 'MOCK_REPORT_RC=%d\n' "$rc"
if [ -f "$LOCAL_REPORT_DIR/summary.md" ]; then
    echo 'MOCK_REPORT_SUMMARY_OK=1'
else
    echo 'MOCK_REPORT_SUMMARY_OK=0'
fi
if [ -f "$LOCAL_REPORT_DIR/journal.txt" ]; then
    echo 'MOCK_REPORT_JOURNAL_OK=1'
else
    echo 'MOCK_REPORT_JOURNAL_OK=0'
fi
rm -rf "$LOCAL_REPORT_DIR"
if grep -qx 'MOCK_GH_GIST_OK=1' "$MOCK_GH_LOG"; then
    echo 'MOCK_GH_GIST_OK=1'
else
    echo 'MOCK_GH_GIST_OK=0'
fi
if grep -qx 'MOCK_GH_ISSUE_OK=1' "$MOCK_GH_LOG"; then
    echo 'MOCK_GH_ISSUE_OK=1'
else
    echo 'MOCK_GH_ISSUE_OK=0'
fi
echo '--- mocked gh invocations ---'
cat "$MOCK_GH_LOG"
exit "$rc"
"""
    run_ssh(context, script)
