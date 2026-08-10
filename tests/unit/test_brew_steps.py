"""Unit tests for tests/homebrew/features/steps/brew_steps.py."""

import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock, PropertyMock, patch

import pytest


def _import_brew_steps():
    """Import the module under test with lightweight behave/dogtail/qecore stubs."""
    behave_stub = types.ModuleType("behave")
    behave_stub.step = lambda *a, **kw: (lambda f: f)

    dogtail_stub = types.ModuleType("dogtail")
    rawinput_stub = types.ModuleType("dogtail.rawinput")
    rawinput_stub.pressKey = lambda *a, **kw: None
    rawinput_stub.typeText = lambda *a, **kw: None
    dogtail_stub.rawinput = rawinput_stub

    qecore_stub = types.ModuleType("qecore")
    common_steps_stub = types.ModuleType("qecore.common_steps")
    common_steps_stub.__all__ = []
    qecore_stub.common_steps = common_steps_stub

    sys.modules["behave"] = behave_stub
    sys.modules["dogtail"] = dogtail_stub
    sys.modules["dogtail.rawinput"] = rawinput_stub
    sys.modules["qecore"] = qecore_stub
    sys.modules["qecore.common_steps"] = common_steps_stub
    sys.modules.pop("tests.homebrew.features.steps.brew_steps", None)

    import tests.homebrew.features.steps.brew_steps as module

    return module


@pytest.mark.parametrize(
    ("previous_text", "current_text", "expected"),
    [
        ("prompt$ ", "prompt$ brew install", "brew install"),
        ("older output", "new output", "new output"),
        ("", "brew doctor", "brew doctor"),
        ("same text", "same text", ""),
        ("much longer previous text", "short", "short"),
    ],
)
def test_terminal_delta(previous_text, current_text, expected):
    module = _import_brew_steps()

    assert module._terminal_delta(previous_text, current_text) == expected


def test_wait_for_command_result_returns_output_and_exit_code():
    module = _import_brew_steps()
    marker = "__BREW_EXIT_[1].+?__"
    terminal = MagicMock()
    type(terminal).text = PropertyMock(
        side_effect=[
            "prompt$ still running",
            f"""prompt$ brew install wget
Downloading...
{marker}:17""",
        ]
    )
    context = SimpleNamespace()

    with patch.object(module, "_terminal_widget", return_value=terminal), patch.object(
        module, "monotonic", side_effect=[0, 0, 1]
    ), patch.object(module, "sleep"):
        output, exit_code = module._wait_for_command_result(context, marker, "prompt$ ")

    assert output == "brew install wget\nDownloading..."
    assert exit_code == 17


def test_wait_for_command_result_raises_on_timeout():
    module = _import_brew_steps()
    terminal = MagicMock()
    type(terminal).text = PropertyMock(side_effect=["prompt$ still running"])
    context = SimpleNamespace()

    with patch.object(module, "COMMAND_TIMEOUT_SECONDS", 2), patch.object(
        module, "_terminal_widget", return_value=terminal
    ), patch.object(module, "monotonic", side_effect=[0, 0, 3]), patch.object(module, "sleep"):
        with pytest.raises(AssertionError, match="Timed out waiting for terminal output marker"):
            module._wait_for_command_result(context, "__BREW_EXIT__", "prompt$ ")
