"""Unit tests for gnome_apps_steps.py pure helper functions."""
import os
import sys
import types
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Import helper
# ---------------------------------------------------------------------------

def _import_gnome_apps(tree_available: bool = True, in_container: bool = False):
    behave_stub = types.ModuleType("behave")
    behave_stub.step = lambda *a, **kw: (lambda f: f)
    sys.modules["behave"] = behave_stub

    dogtail_stub = types.ModuleType("dogtail")
    tree_stub = types.ModuleType("dogtail.tree")
    if tree_available:
        tree_stub.root = MagicMock()
    sys.modules["dogtail"] = dogtail_stub
    sys.modules["dogtail.tree"] = tree_stub

    qecore_stub = types.ModuleType("qecore")
    qecore_common_stub = types.ModuleType("qecore.common_steps")
    sys.modules["qecore"] = qecore_stub
    sys.modules["qecore.common_steps"] = qecore_common_stub

    app_support_stub = types.ModuleType("app_support")
    app_support_stub.launch_background = MagicMock()
    app_support_stub.launch_target_available = MagicMock(return_value=True)
    sys.modules["app_support"] = app_support_stub

    for key in list(sys.modules):
        if "gnome_apps_steps" in key:
            del sys.modules[key]

    with patch("os.path.lexists", return_value=in_container), \
         patch("os.path.isfile", return_value=not in_container):
        import tests.smoke.features.steps.gnome_apps_steps as m  # noqa: PLC0415
    return m


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestGnomeAppsConstants:
    def test_frame_roles_is_set(self):
        m = _import_gnome_apps()
        assert isinstance(m.FRAME_ROLES, set)
        assert "frame" in m.FRAME_ROLES
        assert "filler" in m.FRAME_ROLES

    def test_ptyxis_app_names_is_tuple(self):
        m = _import_gnome_apps()
        assert isinstance(m.PTYXIS_APP_NAMES, tuple)
        assert "ptyxis" in m.PTYXIS_APP_NAMES

    def test_files_app_names_is_tuple(self):
        m = _import_gnome_apps()
        assert isinstance(m.FILES_APP_NAMES, tuple)
        assert "nautilus" in m.FILES_APP_NAMES

    def test_app_wm_class_hints_has_ptyxis(self):
        m = _import_gnome_apps()
        assert "ptyxis" in m._APP_WM_CLASS_HINTS
        assert m._APP_WM_CLASS_HINTS["ptyxis"] == "ptyxis"

    def test_app_wm_class_hints_has_nautilus(self):
        m = _import_gnome_apps()
        assert "nautilus" in m._APP_WM_CLASS_HINTS


# ---------------------------------------------------------------------------
# _in_container
# ---------------------------------------------------------------------------

class TestInContainer:
    def test_false_outside(self):
        m = _import_gnome_apps(in_container=False)
        assert m._IN_CONTAINER is False

    def test_true_inside(self):
        m = _import_gnome_apps(in_container=True)
        assert m._IN_CONTAINER is True


# ---------------------------------------------------------------------------
# _skip_if_no_atspi
# ---------------------------------------------------------------------------

class TestSkipIfNoAtspi:
    def test_returns_false_when_tree_available(self):
        m = _import_gnome_apps(tree_available=True)
        context = MagicMock()
        assert m._skip_if_no_atspi(context) is False

    def test_returns_true_when_tree_none(self):
        m = _import_gnome_apps(tree_available=False)
        m.tree = None
        context = MagicMock()
        assert m._skip_if_no_atspi(context) is True

    def test_calls_scenario_skip_when_tree_none(self):
        m = _import_gnome_apps(tree_available=False)
        m.tree = None
        context = MagicMock()
        m._skip_if_no_atspi(context)
        context.scenario.skip.assert_called_once()

    def test_skip_message_mentions_at_spi(self):
        m = _import_gnome_apps(tree_available=False)
        m.tree = None
        context = MagicMock()
        m._skip_if_no_atspi(context)
        msg = context.scenario.skip.call_args[0][0]
        assert "AT-SPI" in msg


# ---------------------------------------------------------------------------
# _ssh_args
# ---------------------------------------------------------------------------

class TestSshArgs:
    def test_returns_list_starting_with_ssh(self):
        m = _import_gnome_apps()
        args = m._ssh_args()
        assert isinstance(args, list)
        assert args[0] == "ssh"

    def test_uses_env_ssh_key(self):
        m = _import_gnome_apps()
        with patch.dict(os.environ, {"SSH_KEY": "/tmp/testkey"}):
            args = m._ssh_args()
        assert "/tmp/testkey" in args

    def test_uses_env_vm_user_and_ip(self):
        m = _import_gnome_apps()
        with patch.dict(os.environ, {"VM_USER": "testuser", "VM_IP": "10.0.0.1"}):
            args = m._ssh_args()
        assert "testuser@10.0.0.1" in args

    def test_uses_default_ip_when_not_set(self):
        m = _import_gnome_apps()
        env = {k: v for k, v in os.environ.items() if k not in ("VM_IP", "VM_USER")}
        with patch.dict(os.environ, env, clear=True):
            args = m._ssh_args()
        assert "bluefin-test@127.0.0.1" in args

    def test_includes_strict_host_key_checking_no(self):
        m = _import_gnome_apps()
        args = m._ssh_args()
        assert "StrictHostKeyChecking=no" in args

    def test_includes_port_argument(self):
        m = _import_gnome_apps()
        with patch.dict(os.environ, {"SSH_PORT": "2222"}):
            args = m._ssh_args()
        assert "-p" in args
        idx = args.index("-p")
        assert args[idx + 1] == "2222"


# ---------------------------------------------------------------------------
# _shell_eval_force_close — WM hint resolution
# ---------------------------------------------------------------------------

class TestShellEvalForceClose:
    def test_noop_when_no_matching_hint(self):
        m = _import_gnome_apps()
        with patch("subprocess.run") as mock_run:
            m._shell_eval_force_close(("com.example.unknown",))
        mock_run.assert_not_called()

    def test_calls_subprocess_for_known_app(self):
        m = _import_gnome_apps(in_container=False)
        m._IN_CONTAINER = False
        with patch("subprocess.run") as mock_run, patch("time.sleep"):
            mock_run.return_value = MagicMock(returncode=0)
            m._shell_eval_force_close(("ptyxis",))
        mock_run.assert_called_once()

    def test_includes_wm_class_hint_in_js(self):
        m = _import_gnome_apps(in_container=False)
        m._IN_CONTAINER = False
        captured_js = []
        def capture_run(cmd, **kwargs):
            if isinstance(cmd, list):
                captured_js.extend(cmd)
            return MagicMock(returncode=0)
        with patch("subprocess.run", side_effect=capture_run), patch("time.sleep"):
            m._shell_eval_force_close(("ptyxis",))
        full_cmd = " ".join(str(a) for a in captured_js)
        assert "ptyxis" in full_cmd

    def test_routes_via_ssh_in_container(self):
        m = _import_gnome_apps(in_container=True)
        m._IN_CONTAINER = True
        captured = []
        def capture_run(cmd, **kwargs):
            captured.append(cmd)
            return MagicMock(returncode=0)
        with patch("subprocess.run", side_effect=capture_run), patch("time.sleep"):
            m._shell_eval_force_close(("ptyxis",))
        assert any("ssh" in str(c) for c in captured)
