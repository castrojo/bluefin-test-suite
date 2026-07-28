"""Regression tests for kde-smoke environment helper imports.

These tests assert that the kde-smoke environment module imports the REAL
shared helper API without any try/except swallow.  If a helper is renamed
or removed, these tests FAIL loudly — preventing a silent CI pass where
zero scenarios actually run.
"""

import importlib

import pytest


# ---------------------------------------------------------------------------
# 1. The kde-smoke environment imports helpers at module scope (no swallow)
# ---------------------------------------------------------------------------


def test_environment_imports_successfully():
    """The kde-smoke environment module must import without error."""
    mod = importlib.import_module("tests.kde-smoke.features.environment")
    assert mod is not None


# ---------------------------------------------------------------------------
# 2. Assert specific names exist and are callable on the shared modules
# ---------------------------------------------------------------------------


class TestKdePreconditionsAPI:
    """The shared kde_preconditions module must expose the real public API."""

    @pytest.fixture(autouse=True)
    def _load_module(self):
        self.mod = importlib.import_module("tests.shared.kde_preconditions")

    def test_is_kde_session_exists_and_callable(self):
        assert hasattr(self.mod, "is_kde_session")
        assert callable(self.mod.is_kde_session)

    def test_apply_kde_session_preconditions_exists_and_callable(self):
        assert hasattr(self.mod, "apply_kde_session_preconditions")
        assert callable(self.mod.apply_kde_session_preconditions)

    def test_has_sddm_exists_and_callable(self):
        assert hasattr(self.mod, "has_sddm")
        assert callable(self.mod.has_sddm)

    def test_wait_for_plasma_session_exists_and_callable(self):
        assert hasattr(self.mod, "wait_for_plasma_session")
        assert callable(self.mod.wait_for_plasma_session)

    def test_no_is_kde_image_function(self):
        """is_kde_image was a phantom name that never existed; ensure it stays gone."""
        assert not hasattr(self.mod, "is_kde_image")

    def test_no_ensure_kde_session_function(self):
        """ensure_kde_session was a phantom name that never existed; ensure it stays gone."""
        assert not hasattr(self.mod, "ensure_kde_session")


class TestKdeWebdriverAPI:
    """The shared kde_webdriver module must expose the real public API."""

    @pytest.fixture(autouse=True)
    def _load_module(self):
        self.mod = importlib.import_module("tests.shared.kde_webdriver")

    def test_new_session_exists_and_callable(self):
        assert hasattr(self.mod, "new_session")
        assert callable(self.mod.new_session)

    def test_quit_session_exists_and_callable(self):
        assert hasattr(self.mod, "quit_session")
        assert callable(self.mod.quit_session)

    def test_find_exists_and_callable(self):
        assert hasattr(self.mod, "find")
        assert callable(self.mod.find)

    def test_find_all_exists_and_callable(self):
        assert hasattr(self.mod, "find_all")
        assert callable(self.mod.find_all)

    def test_wait_for_exists_and_callable(self):
        assert hasattr(self.mod, "wait_for")
        assert callable(self.mod.wait_for)

    def test_retry_atspi_action_exists_and_callable(self):
        assert hasattr(self.mod, "retry_atspi_action")
        assert callable(self.mod.retry_atspi_action)

    def test_save_screenshot_exists_and_callable(self):
        assert hasattr(self.mod, "save_screenshot")
        assert callable(self.mod.save_screenshot)

    def test_no_start_driver_function(self):
        """start_driver was a phantom name that never existed; ensure it stays gone."""
        assert not hasattr(self.mod, "start_driver")

    def test_no_press_key_function(self):
        """press_key never existed — the dead code branch has been removed."""
        assert not hasattr(self.mod, "press_key")


class TestKdeShellStepsAPI:
    """The shared kde_shell_steps module must expose wait_until."""

    @pytest.fixture(autouse=True)
    def _load_module(self):
        self.mod = importlib.import_module("tests.shared.kde_shell_steps")

    def test_wait_until_exists_and_callable(self):
        assert hasattr(self.mod, "wait_until")
        assert callable(self.mod.wait_until)


# ---------------------------------------------------------------------------
# 3. The environment module references the CORRECT names from shared modules
# ---------------------------------------------------------------------------


def test_environment_uses_correct_precondition_names():
    """environment.py must import is_kde_session (not is_kde_image)
    and apply_kde_session_preconditions (not ensure_kde_session)."""
    mod = importlib.import_module("tests.kde-smoke.features.environment")
    # These are imported at module scope; verify they resolve to the real functions.
    from tests.shared.kde_preconditions import (
        apply_kde_session_preconditions,
        is_kde_session,
    )

    assert mod.is_kde_session is is_kde_session
    assert mod.apply_kde_session_preconditions is apply_kde_session_preconditions


def test_environment_uses_correct_webdriver_module():
    """environment.py must import kde_webdriver with new_session (not start_driver)."""
    mod = importlib.import_module("tests.kde-smoke.features.environment")
    assert hasattr(mod.kde_webdriver, "new_session")
    assert not hasattr(mod.kde_webdriver, "start_driver")
