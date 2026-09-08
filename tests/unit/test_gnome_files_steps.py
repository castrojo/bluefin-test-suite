"""Unit tests for tests/smoke/features/steps/gnome_files_steps.py."""

import sys
import types
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Import helper
# ---------------------------------------------------------------------------

def _import_files_steps(tree_available: bool = True):
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
    app_support_stub.launch_background = MagicMock(return_value="desktop")
    app_support_stub._IN_CONTAINER = False
    app_support_stub._ssh_args = MagicMock(return_value=[])
    app_support_stub._ssh_run = MagicMock()
    app_support_stub.atspi_click = MagicMock()
    sys.modules["app_support"] = app_support_stub

    for key in list(sys.modules):
        if "gnome_files_steps" in key:
            del sys.modules[key]

    import tests.smoke.features.steps.gnome_files_steps as m  # noqa: PLC0415
    m.sleep = MagicMock()
    return m


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestFilesConstants:
    def setup_method(self):
        self.m = _import_files_steps()

    def test_files_app_names_is_tuple(self):
        assert isinstance(self.m.FILES_APP_NAMES, tuple)

    def test_files_app_names_contains_nautilus(self):
        assert "nautilus" in self.m.FILES_APP_NAMES

    def test_files_app_names_contains_gnome_nautilus_dbus(self):
        assert "org.gnome.Nautilus" in self.m.FILES_APP_NAMES

    def test_files_launch_targets_is_tuple(self):
        assert isinstance(self.m.FILES_LAUNCH_TARGETS, tuple)

    def test_files_launch_targets_contains_desktop_entry(self):
        assert any("org.gnome.Nautilus.desktop" in t for t in self.m.FILES_LAUNCH_TARGETS)

    def test_files_sidebar_uris_is_dict(self):
        assert isinstance(self.m.FILES_SIDEBAR_URIS, dict)

    def test_files_sidebar_uris_contains_home(self):
        assert "Home" in self.m.FILES_SIDEBAR_URIS

    def test_files_sidebar_uris_contains_trash(self):
        assert "Trash" in self.m.FILES_SIDEBAR_URIS

    def test_files_sidebar_uris_home_is_uri(self):
        assert self.m.FILES_SIDEBAR_URIS["Home"].startswith("home://")

    def test_files_sidebar_uris_trash_is_uri(self):
        assert self.m.FILES_SIDEBAR_URIS["Trash"].startswith("trash://")


# ---------------------------------------------------------------------------
# _skip_if_no_atspi
# ---------------------------------------------------------------------------

class TestSkipIfNoAtspi:
    def setup_method(self):
        self.m = _import_files_steps()

    def test_returns_true_and_skips_when_tree_is_none(self):
        context = MagicMock()
        with patch.object(self.m, "tree", None):
            result = self.m._skip_if_no_atspi(context)
        assert result is True
        context.scenario.skip.assert_called_once_with(
            "AT-SPI unavailable: dogtail not imported in this environment"
        )

    def test_returns_false_when_tree_is_available(self):
        context = MagicMock()
        with patch.object(self.m, "tree", MagicMock()):
            result = self.m._skip_if_no_atspi(context)
        assert result is False
        context.scenario.skip.assert_not_called()

    def test_does_not_raise_when_skip_raises(self):
        context = MagicMock()
        context.scenario.skip.side_effect = RuntimeError("skip not available")
        with patch.object(self.m, "tree", None):
            result = self.m._skip_if_no_atspi(context)
        assert result is True


# ---------------------------------------------------------------------------
# _nautilus_app
# ---------------------------------------------------------------------------

class TestNautilusApp:
    def setup_method(self):
        self.m = _import_files_steps()

    def test_returns_first_matching_app(self):
        mock_app = MagicMock()
        tree_mock = MagicMock()
        tree_mock.root.application.return_value = mock_app
        with patch.object(self.m, "tree", tree_mock):
            result = self.m._nautilus_app()
        assert result is mock_app

    def test_tries_next_name_when_first_raises(self):
        mock_app = MagicMock()
        call_count = {"n": 0}

        def side_effect(name):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("not found")
            return mock_app

        tree_mock = MagicMock()
        tree_mock.root.application.side_effect = side_effect
        with patch.object(self.m, "tree", tree_mock):
            result = self.m._nautilus_app()
        assert result is mock_app
        assert call_count["n"] == 2

    def test_finds_nautilus_via_applications_list(self):
        mock_app = MagicMock()
        mock_app.name = "org.gnome.Nautilus"
        tree_mock = MagicMock()
        tree_mock.root.applications.return_value = [mock_app]
        with patch.object(self.m, "tree", tree_mock):
            result = self.m._nautilus_app(timeout=1)
        assert result is mock_app

    def test_raises_assertion_error_when_all_names_fail(self):
        tree_mock = MagicMock()
        tree_mock.root.applications.return_value = []
        tree_mock.root.application.side_effect = RuntimeError("not found")
        with patch.object(self.m, "tree", tree_mock):
            with pytest.raises(AssertionError, match="GNOME Files application was not found"):
                self.m._nautilus_app(timeout=0)


# ---------------------------------------------------------------------------
# _nautilus_window
# ---------------------------------------------------------------------------

class TestNautilusWindow:
    def setup_method(self):
        self.m = _import_files_steps()

    def _make_frame(self, role="frame", name="Files", showing=True):
        node = MagicMock()
        node.roleName = role
        node.name = name
        node.showing = showing
        return node

    def test_returns_first_visible_frame(self):
        frame = self._make_frame()
        app_mock = MagicMock()
        app_mock.findChildren.return_value = [frame]
        tree_mock = MagicMock()
        tree_mock.root.application.return_value = app_mock
        with patch.object(self.m, "tree", tree_mock), \
             patch("time.sleep"):
            result = self.m._nautilus_window(timeout=1)
        assert result is frame

    def test_raises_assertion_error_when_no_window_found(self):
        app_mock = MagicMock()
        app_mock.findChildren.return_value = []
        app_mock.children = []
        tree_mock = MagicMock()
        tree_mock.root.application.return_value = app_mock
        with patch.object(self.m, "tree", tree_mock), \
             patch("time.sleep"):
            with pytest.raises(AssertionError, match="Visible Files window not found"):
                self.m._nautilus_window(timeout=1)


# ---------------------------------------------------------------------------
# launch_files_via_command
# ---------------------------------------------------------------------------

class TestLaunchFilesViaCommand:
    def setup_method(self):
        self.m = _import_files_steps()

    def test_sets_launch_target_on_context(self):
        context = MagicMock()
        app_support = sys.modules["app_support"]
        app_support.launch_background.return_value = "desktop"
        with patch.object(self.m, "tree", MagicMock()), \
             patch("time.sleep"):
            self.m.launch_files_via_command(context)
        assert context.files_launch_target == "desktop"

    def test_skips_when_tree_unavailable(self):
        context = MagicMock()
        with patch.object(self.m, "tree", None):
            self.m.launch_files_via_command(context)
        context.scenario.skip.assert_called_once()


# ---------------------------------------------------------------------------
# home_folder_is_in_the_sidebar
# ---------------------------------------------------------------------------

class TestHomeFolderIsInTheSidebar:
    def setup_method(self):
        self.m = _import_files_steps()

    def _make_window_with_sidebar(self, item_role="list item", item_name="Home"):
        home_item = MagicMock()
        home_item.roleName = item_role
        home_item.showing = True
        home_item.name = item_name

        sidebar_tree = MagicMock()
        sidebar_tree.roleName = "tree"
        sidebar_tree.showing = True
        sidebar_tree.name = "Sidebar"

        def sidebar_find(pred):
            return [home_item] if pred(home_item) else []

        sidebar_tree.findChildren.side_effect = sidebar_find

        window = MagicMock()

        def window_find(pred):
            return [sidebar_tree] if pred(sidebar_tree) else []

        window.findChildren.side_effect = window_find
        return window

    def test_passes_when_home_is_in_sidebar(self):
        window = self._make_window_with_sidebar()
        with patch.object(self.m, "_nautilus_window", return_value=window):
            self.m.home_folder_is_in_the_sidebar(MagicMock())

    def test_passes_when_item_is_labelled_personal_folder(self):
        window = self._make_window_with_sidebar(item_name="Personal Folder")
        with patch.object(self.m, "_nautilus_window", return_value=window):
            self.m.home_folder_is_in_the_sidebar(MagicMock())

    def test_passes_for_gnome50_button_role(self):
        window = self._make_window_with_sidebar(item_role="button")
        with patch.object(self.m, "_nautilus_window", return_value=window):
            self.m.home_folder_is_in_the_sidebar(MagicMock())

    def test_raises_when_no_sidebar_found(self):
        window = MagicMock()
        window.findChildren.return_value = []
        with patch.object(self.m, "_nautilus_window", return_value=window):
            with pytest.raises(AssertionError, match="Sidebar tree not found"):
                self.m.home_folder_is_in_the_sidebar(MagicMock())


# ---------------------------------------------------------------------------
# nautilus_location_shows
# ---------------------------------------------------------------------------

class TestNautilusLocationShows:
    def setup_method(self):
        self.m = _import_files_steps()

    def test_passes_when_location_is_visible(self):
        node = MagicMock()
        node.showing = True
        node.name = "Home"
        app_mock = MagicMock()
        app_mock.findChildren.return_value = [node]
        tree_mock = MagicMock()
        tree_mock.root.application.return_value = app_mock
        with patch.object(self.m, "tree", tree_mock), \
             patch("time.sleep"):
            self.m.nautilus_location_shows(MagicMock(), "Home")

    def test_raises_when_location_not_visible(self):
        app_mock = MagicMock()
        app_mock.findChildren.return_value = []
        tree_mock = MagicMock()
        tree_mock.root.application.return_value = app_mock
        with patch.object(self.m, "tree", tree_mock), \
             patch("time.sleep"):
            with pytest.raises(AssertionError, match="does not show"):
                self.m.nautilus_location_shows(MagicMock(), "Downloads")

    def test_location_check_is_case_insensitive(self):
        node = MagicMock()
        node.showing = True
        node.name = "HOME"
        app_mock = MagicMock()

        def find_children(pred):
            return [node] if pred(node) else []

        app_mock.findChildren.side_effect = find_children
        tree_mock = MagicMock()
        tree_mock.root.application.return_value = app_mock
        with patch.object(self.m, "tree", tree_mock), \
             patch("time.sleep"):
            self.m.nautilus_location_shows(MagicMock(), "home")


# ---------------------------------------------------------------------------
# navigating_to_home_folder_shows_file_listing
# ---------------------------------------------------------------------------

class TestNavigatingToHomeFolderShowsFileListing:
    def setup_method(self):
        self.m = _import_files_steps()

    def _make_window_with_list(self, child_count=3):
        child = MagicMock()
        content_list = MagicMock()
        content_list.roleName = "list"
        content_list.showing = True
        content_list.children = [child] * child_count
        window = MagicMock()

        def find(pred):
            return [content_list] if pred(content_list) else []

        window.findChildren.side_effect = find
        return window

    def test_passes_when_file_listing_is_visible(self):
        window = self._make_window_with_list(child_count=2)
        with patch.object(self.m, "_nautilus_window", return_value=window), \
             patch("time.sleep"):
            self.m.navigating_to_home_folder_shows_file_listing(MagicMock())

    def test_raises_when_listing_is_empty(self):
        window = self._make_window_with_list(child_count=0)
        with patch.object(self.m, "_nautilus_window", return_value=window), \
             patch("time.sleep"):
            with pytest.raises(AssertionError, match="Visible file listing"):
                self.m.navigating_to_home_folder_shows_file_listing(MagicMock())


# ---------------------------------------------------------------------------
# new_folder_dialog_is_open
# ---------------------------------------------------------------------------

class TestNewFolderDialogIsOpen:
    def setup_method(self):
        self.m = _import_files_steps()

    def test_passes_when_text_entry_is_found(self):
        entry = MagicMock()
        entry.roleName = "entry"
        entry.showing = True
        app_mock = MagicMock()

        def find(pred):
            return [entry] if pred(entry) else []

        app_mock.findChildren.side_effect = find
        tree_mock = MagicMock()
        tree_mock.root.application.return_value = app_mock
        with patch.object(self.m, "tree", tree_mock), \
             patch("time.sleep"):
            self.m.new_folder_dialog_is_open(MagicMock())

    def test_soft_passes_when_no_entry_found(self, capsys):
        app_mock = MagicMock()
        app_mock.findChildren.return_value = []
        tree_mock = MagicMock()
        tree_mock.root.application.return_value = app_mock
        with patch.object(self.m, "tree", tree_mock), \
             patch("time.sleep"):
            self.m.new_folder_dialog_is_open(MagicMock())
        captured = capsys.readouterr()
        assert "WARNING" in captured.out


# ---------------------------------------------------------------------------
# file_search_bar_is_open_in_files
# ---------------------------------------------------------------------------

class TestFileSearchBarIsOpenInFiles:
    def setup_method(self):
        self.m = _import_files_steps()

    def test_sets_context_search_bar_when_found(self):
        entry = MagicMock()
        entry.roleName = "text"
        entry.showing = True
        context = MagicMock()
        app_mock = MagicMock()

        def find(pred):
            return [entry] if pred(entry) else []

        app_mock.findChildren.side_effect = find
        tree_mock = MagicMock()
        tree_mock.root.application.return_value = app_mock
        with patch.object(self.m, "tree", tree_mock), \
             patch("time.sleep"):
            self.m.file_search_bar_is_open_in_files(context)
        assert context.search_bar is entry

    def test_soft_passes_when_no_search_bar_found(self, capsys):
        app_mock = MagicMock()
        app_mock.findChildren.return_value = []
        tree_mock = MagicMock()
        tree_mock.root.application.return_value = app_mock
        with patch.object(self.m, "tree", tree_mock), \
             patch("time.sleep"):
            self.m.file_search_bar_is_open_in_files(MagicMock())
        captured = capsys.readouterr()
        assert "WARNING" in captured.out


# ---------------------------------------------------------------------------
# files_is_no_longer_running
# ---------------------------------------------------------------------------

class TestFilesIsNoLongerRunning:
    def setup_method(self):
        self.m = _import_files_steps()

    def test_passes_immediately_when_app_not_found(self):
        tree_mock = MagicMock()
        tree_mock.root.application.side_effect = RuntimeError("not found")
        with patch.object(self.m, "tree", tree_mock), \
             patch("time.sleep"):
            self.m.files_is_no_longer_running(MagicMock())

    def test_passes_when_app_exists_but_has_no_visible_frames(self):
        app_mock = MagicMock()
        app_mock.findChildren.return_value = []
        tree_mock = MagicMock()
        tree_mock.root.application.return_value = app_mock
        with patch.object(self.m, "tree", tree_mock), \
             patch("time.sleep"):
            self.m.files_is_no_longer_running(MagicMock())

    def test_raises_when_app_stays_visible(self):
        frame = MagicMock()
        frame.roleName = "frame"
        frame.showing = True
        app_mock = MagicMock()

        def find(pred):
            return [frame] if pred(frame) else []

        app_mock.findChildren.side_effect = find
        tree_mock = MagicMock()
        tree_mock.root.application.return_value = app_mock
        with patch.object(self.m, "tree", tree_mock), \
             patch("time.sleep"), \
             patch("subprocess.run"):
            with pytest.raises(AssertionError, match="GNOME Files is still visible"):
                self.m.files_is_no_longer_running(MagicMock())
