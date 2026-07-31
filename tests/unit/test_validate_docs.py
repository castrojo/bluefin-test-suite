"""Unit tests for scripts/validate_docs.py."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts import validate_docs as vd  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_globals():
    """Clear module-level ERRORS / WARNINGS between tests."""
    vd.ERRORS.clear()
    vd.WARNINGS.clear()
    yield
    vd.ERRORS.clear()
    vd.WARNINGS.clear()


# ── parse_frontmatter ─────────────────────────────────────────────────────────


class TestParseFrontmatter:
    def test_valid_frontmatter_returns_dict_and_body(self):
        text = "---\nname: foo\ndescription: bar\n---\nBody text"
        fm, body = vd.parse_frontmatter(text)
        assert fm == {"name": "foo", "description": "bar"}
        assert "Body text" in body

    def test_no_frontmatter_returns_none_and_full_text(self):
        text = "# Title\nNo frontmatter here"
        fm, body = vd.parse_frontmatter(text)
        assert fm is None
        assert body == text

    def test_incomplete_delimiter_returns_none(self):
        text = "---\nname: foo\n"
        fm, body = vd.parse_frontmatter(text)
        assert fm is None

    def test_non_dict_yaml_returns_none(self):
        text = "---\n- item1\n- item2\n---\nBody"
        fm, body = vd.parse_frontmatter(text)
        assert fm is None

    def test_malformed_yaml_returns_none(self):
        text = "---\nkey: [unclosed\n---\nBody"
        fm, body = vd.parse_frontmatter(text)
        assert fm is None


# ── heading_level ─────────────────────────────────────────────────────────────


class TestHeadingLevel:
    @pytest.mark.parametrize(
        "line,expected",
        [
            ("# H1 title", 1),
            ("## H2 section", 2),
            ("### H3 sub", 3),
            ("#### H4 deep", 4),
            ("##### H5 too-deep", 5),
            ("###### H6 too-deep", 6),
        ],
    )
    def test_detects_heading_levels(self, line, expected):
        assert vd.heading_level(line) == expected

    def test_plain_text_is_not_a_heading(self):
        assert vd.heading_level("regular paragraph") is None

    def test_hash_without_space_is_not_a_heading(self):
        assert vd.heading_level("#nospace") is None

    def test_empty_line_is_not_a_heading(self):
        assert vd.heading_level("") is None

    def test_mid_line_hash_is_not_a_heading(self):
        assert vd.heading_level("some # text") is None


# ── validate_general ──────────────────────────────────────────────────────────


class TestValidateGeneral:
    def test_valid_single_h1_passes(self, tmp_path):
        p = tmp_path / "doc.md"
        vd.validate_general(p, "# Title\n\n## Section\n\nContent.\n")
        assert vd.ERRORS == []

    def test_missing_h1_raises_error(self, tmp_path):
        p = tmp_path / "doc.md"
        vd.validate_general(p, "## Section only\n\nContent.\n")
        assert any("missing H1" in e for e in vd.ERRORS)

    def test_multiple_h1_raises_error(self, tmp_path):
        p = tmp_path / "doc.md"
        vd.validate_general(p, "# First\n\n# Second\n\n## Sub\n")
        assert any("multiple H1" in e for e in vd.ERRORS)

    def test_h5_heading_is_error(self, tmp_path):
        p = tmp_path / "doc.md"
        vd.validate_general(p, "# Title\n\n##### Too deep\n")
        assert any("H5" in e for e in vd.ERRORS)

    def test_h6_heading_is_error(self, tmp_path):
        p = tmp_path / "doc.md"
        vd.validate_general(p, "# Title\n\n###### Too deep\n")
        assert any("H6" in e for e in vd.ERRORS)

    def test_h4_is_allowed(self, tmp_path):
        p = tmp_path / "doc.md"
        vd.validate_general(p, "# Title\n\n#### H4 fine\n")
        assert vd.ERRORS == []

    def test_headings_inside_backtick_fence_ignored(self, tmp_path):
        p = tmp_path / "doc.md"
        vd.validate_general(p, "# Title\n\n```\n##### not real\n```\n")
        assert vd.ERRORS == []

    def test_headings_inside_tilde_fence_ignored(self, tmp_path):
        p = tmp_path / "doc.md"
        vd.validate_general(p, "# Title\n\n~~~\n##### not real\n~~~\n")
        assert vd.ERRORS == []


# ── validate_links ────────────────────────────────────────────────────────────


class TestValidateLinks:
    def test_external_https_link_skipped(self, tmp_path):
        p = tmp_path / "doc.md"
        vd.validate_links(p, "[GitHub](https://github.com)")
        assert vd.ERRORS == []

    def test_mailto_link_skipped(self, tmp_path):
        p = tmp_path / "doc.md"
        vd.validate_links(p, "[email](mailto:x@y.z)")
        assert vd.ERRORS == []

    def test_tel_link_skipped(self, tmp_path):
        p = tmp_path / "doc.md"
        vd.validate_links(p, "[call](tel:555-1234)")
        assert vd.ERRORS == []

    def test_anchor_only_link_skipped(self, tmp_path):
        p = tmp_path / "doc.md"
        vd.validate_links(p, "[section](#my-section)")
        assert vd.ERRORS == []

    def test_broken_relative_link_is_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vd, "ROOT", tmp_path)
        p = tmp_path / "doc.md"
        vd.validate_links(p, "[missing](./nonexistent.md)")
        assert any("broken relative link" in e for e in vd.ERRORS)

    def test_valid_relative_link_passes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vd, "ROOT", tmp_path)
        (tmp_path / "other.md").write_text("# Other\n")
        p = tmp_path / "doc.md"
        vd.validate_links(p, "[other](./other.md)")
        assert vd.ERRORS == []

    def test_relative_link_with_anchor_stripped(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vd, "ROOT", tmp_path)
        (tmp_path / "other.md").write_text("# Other\n")
        p = tmp_path / "doc.md"
        vd.validate_links(p, "[sec](other.md#section)")
        assert vd.ERRORS == []

    def test_relative_link_with_query_stripped(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vd, "ROOT", tmp_path)
        (tmp_path / "other.md").write_text("# Other\n")
        p = tmp_path / "doc.md"
        vd.validate_links(p, "[sec](other.md?v=2)")
        assert vd.ERRORS == []


# ── validate_skill ────────────────────────────────────────────────────────────


class TestValidateSkill:
    def _skill(self, tmp_path, name, body="# Title\n", desc="A skill"):
        skill_dir = tmp_path / "docs" / "skills" / name
        skill_dir.mkdir(parents=True)
        p = skill_dir / "SKILL.md"
        p.write_text(f"---\nname: {name}\ndescription: {desc}\n---\n{body}")
        return p

    def test_valid_skill_passes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vd, "ROOT", tmp_path)
        p = self._skill(tmp_path, "my-skill")
        vd.validate_skill(p)
        assert vd.ERRORS == []

    def test_missing_frontmatter_is_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vd, "ROOT", tmp_path)
        skill_dir = tmp_path / "docs" / "skills" / "test"
        skill_dir.mkdir(parents=True)
        p = skill_dir / "SKILL.md"
        p.write_text("# Title\nNo frontmatter")
        vd.validate_skill(p)
        assert any("missing YAML frontmatter" in e for e in vd.ERRORS)

    def test_missing_name_is_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vd, "ROOT", tmp_path)
        skill_dir = tmp_path / "docs" / "skills" / "test"
        skill_dir.mkdir(parents=True)
        p = skill_dir / "SKILL.md"
        p.write_text("---\ndescription: desc\n---\n# Title\n")
        vd.validate_skill(p)
        assert any("missing 'name'" in e for e in vd.ERRORS)

    def test_missing_description_is_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vd, "ROOT", tmp_path)
        skill_dir = tmp_path / "docs" / "skills" / "test"
        skill_dir.mkdir(parents=True)
        p = skill_dir / "SKILL.md"
        p.write_text("---\nname: test\n---\n# Title\n")
        vd.validate_skill(p)
        assert any("missing 'description'" in e for e in vd.ERRORS)

    def test_name_mismatch_with_directory_is_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vd, "ROOT", tmp_path)
        p = self._skill(tmp_path, "my-skill")
        # Overwrite with mismatching name
        p.write_text("---\nname: wrong-name\ndescription: desc\n---\n# Title\n")
        vd.validate_skill(p)
        assert any("does not match directory" in e for e in vd.ERRORS)

    def test_skill_md_over_500_lines_is_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vd, "ROOT", tmp_path)
        p = self._skill(tmp_path, "big-skill", body="# Title\n" + "line\n" * 500)
        vd.validate_skill(p)
        assert any("exceeds 500 lines" in e for e in vd.ERRORS)

    def test_reference_over_200_lines_is_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vd, "ROOT", tmp_path)
        ref_dir = tmp_path / "docs" / "skills" / "my-skill" / "references"
        ref_dir.mkdir(parents=True)
        p = ref_dir / "api.md"
        p.write_text("---\nname: api\ndescription: ref\n---\n# Title\n" + "line\n" * 200)
        vd.validate_skill(p)
        assert any("exceeds 200 lines" in e for e in vd.ERRORS)


# ── main() ────────────────────────────────────────────────────────────────────


class TestMain:
    def test_returns_0_on_clean_docs(self, tmp_path, monkeypatch):
        doc = tmp_path / "README.md"
        doc.write_text("# Title\n\nContent.\n")
        monkeypatch.setattr(vd, "collect_md_files", lambda: [doc])
        monkeypatch.setattr(vd, "ROOT", tmp_path)
        assert vd.main() == 0

    def test_returns_1_on_missing_h1(self, tmp_path, monkeypatch):
        doc = tmp_path / "bad.md"
        doc.write_text("## No H1 here\n")
        monkeypatch.setattr(vd, "collect_md_files", lambda: [doc])
        monkeypatch.setattr(vd, "ROOT", tmp_path)
        assert vd.main() == 1

    def test_returns_1_on_broken_link(self, tmp_path, monkeypatch):
        doc = tmp_path / "broken.md"
        doc.write_text("# Title\n\n[missing](./nope.md)\n")
        monkeypatch.setattr(vd, "collect_md_files", lambda: [doc])
        monkeypatch.setattr(vd, "ROOT", tmp_path)
        assert vd.main() == 1

    def test_non_skill_docs_validated_as_general(self, tmp_path, monkeypatch):
        """Files outside docs/skills/ go through validate_other (no frontmatter required)."""
        doc = tmp_path / "CONTRIBUTING.md"
        doc.write_text("# Contributing\n\nContent.\n")
        monkeypatch.setattr(vd, "collect_md_files", lambda: [doc])
        monkeypatch.setattr(vd, "ROOT", tmp_path)
        assert vd.main() == 0

    def test_skill_docs_require_frontmatter(self, tmp_path, monkeypatch):
        skill_dir = tmp_path / "docs" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        p = skill_dir / "SKILL.md"
        p.write_text("# Title\nNo frontmatter")
        monkeypatch.setattr(vd, "collect_md_files", lambda: [p])
        monkeypatch.setattr(vd, "ROOT", tmp_path)
        assert vd.main() == 1

    def test_empty_file_list_returns_0(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vd, "collect_md_files", lambda: [])
        monkeypatch.setattr(vd, "ROOT", tmp_path)
        assert vd.main() == 0
