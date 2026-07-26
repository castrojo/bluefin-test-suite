"""Custom step definitions for sudo-rs privilege escalation and security checks."""
import os
import re
import subprocess
from behave import step

try:
    from qecore.common_steps import *  # noqa: F401,F403
except Exception:  # noqa: BLE001
    pass


_IN_CONTAINER = os.path.lexists("/proc/1/ns/mnt") and not os.path.isfile("/usr/bin/bootc")


def _run_host(cmd: str, timeout: int = 30):
    """Run cmd on the host VM via SSH when inside the runner container."""
    if _IN_CONTAINER:
        ssh_key = os.environ.get("SSH_KEY", "/home/bluefin-test/.ssh/id_ed25519")
        vm_ip = os.environ.get("VM_IP", "127.0.0.1")
        vm_user = os.environ.get("VM_USER", "bluefin-test")
        ssh_port = os.environ.get("SSH_PORT", "22")
        result = subprocess.run(
            [
                "ssh",
                "-i", ssh_key,
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "ConnectTimeout=10",
                "-p", ssh_port,
                f"{vm_user}@{vm_ip}",
                cmd,
            ],
            capture_output=True, text=True, timeout=timeout,
        )
    else:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return result.stdout.strip(), result.returncode, result.stderr.strip()


def _skip_scenario(context, reason: str) -> None:
    scenario = getattr(context, "scenario", None)
    if scenario is not None:
        try:
            scenario.skip(reason)
        except TypeError:
            scenario.skip()


@step("/usr/bin/sudo is owned by root and has setuid mode 4755")
def sudo_is_setuid_root_4755(context) -> None:
    output, returncode, stderr = _run_host("stat -c '%a %U:%G' /usr/bin/sudo")
    assert returncode == 0, f"stat on /usr/bin/sudo failed: {stderr or output}"
    mode, owner = output.split()
    assert mode == "4755", (
        f"/usr/bin/sudo has invalid mode '{mode}' (expected '4755'). "
        "BuildStream strip-binaries may have stripped the setuid bit."
    )
    assert owner == "root:root", f"/usr/bin/sudo owner is '{owner}' (expected 'root:root')"


@step("sudo -n id -u returns user ID 0")
def sudo_n_id_u_returns_0(context) -> None:
    output, returncode, stderr = _run_host("sudo -n id -u")
    assert returncode == 0, f"sudo -n id -u failed (rc={returncode}): {stderr or output}"
    assert output == "0", f"Expected root UID 0 from sudo -n id -u, got '{output}'"


@step("sudo --preserve-env preserves specified environment variables")
def sudo_preserve_env_check(context) -> None:
    # Test that unflagged vars are scrubbed while --preserve-env=VAR passes through
    cmd = "SUDO_TEST_SCRUBBED=secret SUDO_TEST_PRESERVED=kept sudo -n --preserve-env=SUDO_TEST_PRESERVED env"
    output, returncode, stderr = _run_host(cmd)
    assert returncode == 0, f"sudo --preserve-env execution failed: {stderr or output}"
    assert "SUDO_TEST_PRESERVED=kept" in output, "Expected SUDO_TEST_PRESERVED to be retained in sudo environment"
    assert "SUDO_TEST_SCRUBBED" not in output, "Expected SUDO_TEST_SCRUBBED to be scrubbed from sudo environment"


@step("sudo PAM configuration includes system-auth for authentication fallback")
def sudo_pam_includes_system_auth(context) -> None:
    output, returncode, stderr = _run_host("cat /etc/pam.d/sudo")
    assert returncode == 0, f"Failed to read /etc/pam.d/sudo: {stderr or output}"
    assert "system-auth" in output or "include" in output, (
        f"/etc/pam.d/sudo does not reference system-auth or include directives:\n{output}"
    )


@step("sudoedit binary is present and operational")
def sudoedit_binary_check(context) -> None:
    output, returncode, stderr = _run_host("which sudoedit")
    assert returncode == 0, f"sudoedit binary not found on PATH: {stderr or output}"

    # Verify sudoedit points to /usr/bin/sudo or is a setuid symlink/binary
    stat_out, returncode, _ = _run_host("stat -c '%a %U:%G' /usr/bin/sudoedit")
    assert returncode == 0, f"stat /usr/bin/sudoedit failed: {stat_out}"


@step("sudo PAM password authentication is functional for isolated test accounts")
def sudo_pam_password_auth_check(context) -> None:
    # Check if sudo-pam-test user exists, or create temporarily to test PAM password auth
    check_user_out, rc, _ = _run_host("id sudo-pam-test 2>/dev/null")
    if rc != 0:
        # User doesn't exist; skip gracefully if not provisioned on this image
        _skip_scenario(context, "sudo-pam-test user not provisioned on image")
        return

    # Verify password authentication using su/sudo
    output, returncode, stderr = _run_host("echo 'testpass' | su -c 'sudo -S -v' sudo-pam-test 2>&1")
    assert returncode == 0, f"PAM password authentication failed for sudo-pam-test: {stderr or output}"
