"""Unit tests for scripts/generate_skill_index.py.

Covers parse_frontmatter, collect, render_json, render_md and main() in both
generate and --check modes. The module resolves its paths at import time via
module-level constants, so every test repoints ROOT/SKILLS_DIR/INDEX_JSON/
INDEX_MD at a tmp_path tree.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts import generate_skill_index as gsi  # noqa: E402


def _frontmatter(**overrides) -> str:
    fields = {
        "id": "demo-skill",
        "name": "demo-skill",
        "one_line_purpose": "Do a demo thing.",
        "entry_point": "docs/skills/ci-ops/demo-skill/SKILL.md",
        "category": "ci-ops",
        "status": "active",
        "tags": ["demo"],
        "description": "A demo skill.",
        "version": "1.0",
        "last_updated": "2026-01-01",
    }
    fields.update(overrides)
    lines = ["---"]
    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, list):
            lines.append(f"{key}:")
            lines.extend(f"  - {item}" for item in value)
        elif isinstance(value, dict):
            lines.append(f"{key}:")
            lines.extend(f"  {k}: {v}" for k, v in value.items())
        else:
            lines.append(f'{key}: "{value}"')
    lines += ["---", "", "# Body", ""]
    return "\n".join(lines)


@pytest.fixture
def skill_tree(tmp_path, monkeypatch):
    """Repoint the module's path constants at an empty tmp docs/skills tree."""
    skills_dir = tmp_path / "docs" / "skills"
    skills_dir.mkdir(parents=True)
    monkeypatch.setattr(gsi, "ROOT", tmp_path)
    monkeypatch.setattr(gsi, "SKILLS_DIR", skills_dir)
    monkeypatch.setattr(gsi, "INDEX_JSON", skills_dir / "index.json")
    monkeypatch.setattr(gsi, "INDEX_MD", skills_dir / "index.md")
    return tmp_path


def _write_skill(root: Path, rel_dir: str, **overrides) -> Path:
    """Write a SKILL.md whose entry_point defaults to its own repo-relative path."""
    path = root / "docs" / "skills" / rel_dir / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    overrides.setdefault("entry_point", path.relative_to(root).as_posix())
    path.write_text(_frontmatter(**overrides), encoding="utf-8")
    return path


# ── parse_frontmatter ─────────────────────────────────────────────────────────


class TestParseFrontmatter:
    def test_returns_mapping(self, tmp_path):
        path = tmp_path / "SKILL.md"
        path.write_text(_frontmatter(), encoding="utf-8")
        data = gsi.parse_frontmatter(path)
        assert data["id"] == "demo-skill"
        assert data["tags"] == ["demo"]

    def test_missing_front_matter_exits(self, tmp_path):
        path = tmp_path / "SKILL.md"
        path.write_text("# No front matter\n", encoding="utf-8")
        with pytest.raises(SystemExit) as exc:
            gsi.parse_frontmatter(path)
        assert "missing YAML front matter" in str(exc.value)

    def test_non_mapping_front_matter_exits(self, tmp_path):
        path = tmp_path / "SKILL.md"
        path.write_text("---\n- a\n- b\n---\nbody\n", encoding="utf-8")
        with pytest.raises(SystemExit) as exc:
            gsi.parse_frontmatter(path)
        assert "not a mapping" in str(exc.value)


# ── collect ───────────────────────────────────────────────────────────────────


class TestCollect:
    def test_empty_tree_returns_empty_list(self, skill_tree):
        assert gsi.collect() == []

    def test_builds_entry_from_front_matter(self, skill_tree):
        _write_skill(skill_tree, "ci-ops/demo-skill")
        (entry,) = gsi.collect()
        assert entry == {
            "id": "demo-skill",
            "name": "demo-skill",
            "one_line_purpose": "Do a demo thing.",
            "entry_point": "docs/skills/ci-ops/demo-skill/SKILL.md",
            "category": "ci-ops",
            "status": "active",
            "tags": ["demo"],
            "description": "A demo skill.",
            "version": "1.0",
            "last_updated": "2026-01-01",
        }

    def test_results_sorted_by_id(self, skill_tree):
        _write_skill(skill_tree, "ci-ops/zebra", id="zebra", name="zebra")
        _write_skill(skill_tree, "meta/alpha", id="alpha", name="alpha", category="meta")
        assert [s["id"] for s in gsi.collect()] == ["alpha", "zebra"]

    def test_description_whitespace_is_collapsed(self, skill_tree):
        path = _write_skill(skill_tree, "ci-ops/demo-skill")
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                'description: "A demo skill."',
                "description: >-\n  A demo    skill\n  wrapped over lines.",
            ),
            encoding="utf-8",
        )
        (entry,) = gsi.collect()
        assert entry["description"] == "A demo skill wrapped over lines."

    def test_metadata_type_becomes_doc_type(self, skill_tree):
        _write_skill(skill_tree, "meta/demo-skill", category="meta",
                     metadata={"type": "manifest"})
        (entry,) = gsi.collect()
        assert entry["doc_type"] == "manifest"

    def test_absent_metadata_omits_doc_type(self, skill_tree):
        _write_skill(skill_tree, "ci-ops/demo-skill")
        (entry,) = gsi.collect()
        assert "doc_type" not in entry

    @pytest.mark.parametrize("field", ["id", "name", "one_line_purpose", "category",
                                       "status", "tags", "description", "version",
                                       "last_updated"])
    def test_missing_required_field_fails(self, skill_tree, capsys, field):
        _write_skill(skill_tree, "ci-ops/demo-skill", **{field: None})
        with pytest.raises(SystemExit) as exc:
            gsi.collect()
        assert exc.value.code == 1
        assert f"front matter missing {field}" in capsys.readouterr().err

    def test_unknown_category_fails(self, skill_tree, capsys):
        _write_skill(skill_tree, "ci-ops/demo-skill", category="not-a-category")
        with pytest.raises(SystemExit) as exc:
            gsi.collect()
        assert exc.value.code == 1
        assert "category 'not-a-category' not in" in capsys.readouterr().err

    def test_unknown_status_fails(self, skill_tree, capsys):
        _write_skill(skill_tree, "ci-ops/demo-skill", status="retired")
        with pytest.raises(SystemExit) as exc:
            gsi.collect()
        assert exc.value.code == 1
        assert "status 'retired' not in" in capsys.readouterr().err

    def test_entry_point_mismatch_fails(self, skill_tree, capsys):
        _write_skill(skill_tree, "ci-ops/demo-skill",
                     entry_point="docs/skills/ci-ops/wrong/SKILL.md")
        with pytest.raises(SystemExit) as exc:
            gsi.collect()
        assert exc.value.code == 1
        assert "does not match its own path" in capsys.readouterr().err

    def test_id_name_mismatch_fails(self, skill_tree, capsys):
        _write_skill(skill_tree, "ci-ops/demo-skill", id="other-id")
        with pytest.raises(SystemExit) as exc:
            gsi.collect()
        assert exc.value.code == 1
        assert "does not match name" in capsys.readouterr().err

    def test_all_errors_reported_together(self, skill_tree, capsys):
        _write_skill(skill_tree, "ci-ops/a", id="a", name="a", status="retired")
        _write_skill(skill_tree, "ci-ops/b", id="b", name="b", category="bogus")
        with pytest.raises(SystemExit):
            gsi.collect()
        err = capsys.readouterr().err
        assert "status 'retired' not in" in err
        assert "category 'bogus' not in" in err


# ── render_json / render_md ───────────────────────────────────────────────────


class TestRenderJson:
    def test_payload_shape_and_trailing_newline(self):
        out = gsi.render_json([{"id": "a"}], "2026-01-01")
        assert out.endswith("\n")
        payload = json.loads(out)
        assert payload == {
            "generated_at": "2026-01-01",
            "schema_version": gsi.SCHEMA_VERSION,
            "skills": [{"id": "a"}],
        }

    def test_unicode_is_not_escaped(self):
        out = gsi.render_json([{"id": "café"}], "2026-01-01")
        assert "café" in out


class TestRenderMd:
    @staticmethod
    def _skill(**over):
        base = {
            "id": "demo-skill",
            "entry_point": "docs/skills/ci-ops/demo-skill/SKILL.md",
            "category": "ci-ops",
            "status": "active",
            "one_line_purpose": "Do a demo thing.",
        }
        base.update(over)
        return base

    def test_row_href_is_relative_to_docs_skills(self):
        md = gsi.render_md([self._skill()], "2026-01-01")
        assert "| [demo-skill](ci-ops/demo-skill/SKILL.md) | ci-ops | active |" in md

    def test_header_reports_count_schema_and_date(self):
        md = gsi.render_md([self._skill()], "2026-01-01")
        assert f"Generated: 2026-01-01 · schema {gsi.SCHEMA_VERSION} · 1 skills" in md

    def test_empty_catalog_still_renders_table_header(self):
        md = gsi.render_md([], "2026-01-01")
        assert "| id | category | status | one-line purpose |" in md
        assert "· 0 skills" in md

    def test_front_matter_is_emitted(self):
        md = gsi.render_md([], "2026-01-01")
        assert md.startswith("---\nname: index\n")
        assert 'last_updated: "2026-01-01"' in md


# ── main ──────────────────────────────────────────────────────────────────────


class TestMainGenerate:
    def test_writes_both_catalog_files(self, skill_tree, monkeypatch, capsys):
        _write_skill(skill_tree, "ci-ops/demo-skill")
        monkeypatch.setattr(sys, "argv", ["generate_skill_index.py"])
        assert gsi.main() == 0
        payload = json.loads(gsi.INDEX_JSON.read_text(encoding="utf-8"))
        assert [s["id"] for s in payload["skills"]] == ["demo-skill"]
        assert "demo-skill" in gsi.INDEX_MD.read_text(encoding="utf-8")
        assert "Wrote 1 skills" in capsys.readouterr().out


class TestMainCheck:
    @staticmethod
    def _generate(monkeypatch):
        monkeypatch.setattr(sys, "argv", ["generate_skill_index.py"])
        assert gsi.main() == 0

    @staticmethod
    def _check(monkeypatch):
        monkeypatch.setattr(sys, "argv", ["generate_skill_index.py", "--check"])
        return gsi.main()

    def test_missing_index_json_fails(self, skill_tree, monkeypatch, capsys):
        _write_skill(skill_tree, "ci-ops/demo-skill")
        assert self._check(monkeypatch) == 1
        assert "index.json is missing" in capsys.readouterr().out

    def test_freshly_generated_catalog_is_in_sync(self, skill_tree, monkeypatch, capsys):
        _write_skill(skill_tree, "ci-ops/demo-skill")
        self._generate(monkeypatch)
        capsys.readouterr()
        assert self._check(monkeypatch) == 0
        assert "Skill catalog is in sync (1 skills)." in capsys.readouterr().out

    def test_new_skill_makes_json_stale(self, skill_tree, monkeypatch, capsys):
        _write_skill(skill_tree, "ci-ops/demo-skill")
        self._generate(monkeypatch)
        _write_skill(skill_tree, "meta/extra", id="extra", name="extra", category="meta")
        capsys.readouterr()
        assert self._check(monkeypatch) == 1
        assert "index.json is stale" in capsys.readouterr().out

    def test_hand_edited_md_makes_it_stale(self, skill_tree, monkeypatch, capsys):
        _write_skill(skill_tree, "ci-ops/demo-skill")
        self._generate(monkeypatch)
        gsi.INDEX_MD.write_text("hand edited\n", encoding="utf-8")
        capsys.readouterr()
        assert self._check(monkeypatch) == 1
        assert "index.md is stale" in capsys.readouterr().out

    def test_check_uses_committed_generated_at_not_today(self, skill_tree, monkeypatch):
        """The md comparison must reuse index.json's generated_at, otherwise the
        gate would fail every day after the catalog is committed."""
        _write_skill(skill_tree, "ci-ops/demo-skill")
        self._generate(monkeypatch)
        payload = json.loads(gsi.INDEX_JSON.read_text(encoding="utf-8"))
        payload["generated_at"] = "1999-12-31"
        gsi.INDEX_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        gsi.INDEX_MD.write_text(
            gsi.render_md(payload["skills"], "1999-12-31"), encoding="utf-8"
        )
        assert self._check(monkeypatch) == 0

    def test_check_does_not_write_files(self, skill_tree, monkeypatch):
        _write_skill(skill_tree, "ci-ops/demo-skill")
        self._generate(monkeypatch)
        _write_skill(skill_tree, "meta/extra", id="extra", name="extra", category="meta")
        before = gsi.INDEX_JSON.read_text(encoding="utf-8")
        assert self._check(monkeypatch) == 1
        assert gsi.INDEX_JSON.read_text(encoding="utf-8") == before
