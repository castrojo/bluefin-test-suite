"""Unit tests for tests/security/features/steps/steps.py.

Tests _cosign_entries and _collect_values without loading the full behave stack.
"""

import sys
import types
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Import helper (avoids behave decorator side effects)
# ---------------------------------------------------------------------------


def _import_security_steps():
    behave_stub = types.ModuleType("behave")
    behave_stub.step = lambda *a, **kw: (lambda f: f)
    sys.modules["behave"] = behave_stub
    sys.modules.setdefault("behave.runner", MagicMock())

    sys.modules.pop("tests.shared.ssh_steps", None)
    sys.modules.pop("tests.security.features.steps.steps", None)

    import tests.security.features.steps.steps as m
    return m


# ---------------------------------------------------------------------------
# _cosign_entries
# ---------------------------------------------------------------------------


class TestCosignEntries:
    def setup_method(self):
        self.mod = _import_security_steps()

    def test_returns_list_payload_as_is(self):
        context = MagicMock()
        context.cosign_output = '[{"issuer": "one"}, {"issuer": "two"}]'

        assert self.mod._cosign_entries(context) == [
            {"issuer": "one"},
            {"issuer": "two"},
        ]

    def test_wraps_dict_payload_in_list(self):
        context = MagicMock()
        context.cosign_output = '{"issuer": "one"}'

        assert self.mod._cosign_entries(context) == [{"issuer": "one"}]

    def test_raises_for_empty_list_payload(self):
        context = MagicMock()
        context.cosign_output = '[]'

        with pytest.raises(AssertionError, match="cosign output JSON array is empty"):
            self.mod._cosign_entries(context)

    def test_raises_when_output_is_missing(self):
        context = MagicMock()
        context.cosign_output = None

        with pytest.raises(AssertionError, match="No cosign output available"):
            self.mod._cosign_entries(context)

    def test_raises_for_invalid_json(self):
        context = MagicMock()
        context.cosign_output = '{not-json}'

        with pytest.raises(AssertionError, match="Invalid cosign JSON output"):
            self.mod._cosign_entries(context)

    def test_raises_for_unexpected_payload_type(self):
        context = MagicMock()
        context.cosign_output = '42'

        with pytest.raises(
            AssertionError,
            match="Unexpected cosign JSON payload type: int",
        ):
            self.mod._cosign_entries(context)


# ---------------------------------------------------------------------------
# _collect_values
# ---------------------------------------------------------------------------


class TestCollectValues:
    def setup_method(self):
        self.mod = _import_security_steps()

    def test_collects_simple_dict_match(self):
        value = {"issuer": "https://issuer.example"}

        assert self.mod._collect_values(value, {"issuer"}) == ["https://issuer.example"]

    def test_collects_nested_dict_match(self):
        value = {"certificate": {"issuer": "nested-issuer"}}

        assert self.mod._collect_values(value, {"issuer"}) == ["nested-issuer"]

    def test_collects_values_from_list_of_dicts(self):
        value = {
            "entries": [
                {"issuer": "issuer-one"},
                {"issuer": "issuer-two"},
            ]
        }

        assert self.mod._collect_values(value, {"issuer"}) == [
            "issuer-one",
            "issuer-two",
        ]

    @pytest.mark.parametrize("value", [{}, []])
    def test_returns_empty_list_for_empty_inputs(self, value):
        assert self.mod._collect_values(value, {"issuer"}) == []

    def test_collects_multiple_keys(self):
        value = {
            "issuer": "issuer-one",
            "identity": "repo:projectbluefin/testsuite",
            "ignored": "nope",
        }

        assert self.mod._collect_values(value, {"issuer", "identity"}) == [
            "issuer-one",
            "repo:projectbluefin/testsuite",
        ]

    def test_skips_none_values(self):
        value = {
            "issuer": None,
            "nested": {
                "identity": None,
                "subjectAlternativeName": "signer@example.com",
            },
        }

        assert self.mod._collect_values(
            value,
            {"issuer", "identity", "subjectAlternativeName"},
        ) == ["signer@example.com"]

    def test_returns_empty_list_for_non_matching_keys(self):
        value = {"certificate": {"subject": "value"}, "entries": [{"name": "x"}]}

        assert self.mod._collect_values(value, {"issuer", "identity"}) == []

    def test_collects_deeply_nested_values(self):
        value = {
            "wrapper": [
                {"meta": {"issuer": "issuer-one"}},
                {"items": [{"nested": {"identity": "identity-one"}}]},
            ],
            "tail": {"subjectAlternativeName": "user@example.com"},
        }

        assert self.mod._collect_values(
            value,
            {"issuer", "identity", "subjectAlternativeName"},
        ) == [
            "issuer-one",
            "identity-one",
            "user@example.com",
        ]
