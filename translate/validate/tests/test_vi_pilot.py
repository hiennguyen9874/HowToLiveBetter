"""Vietnamese configuration and non-publishable pilot integrity checks."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from translate.lib.config import default_root, translation_langs, unit_dir
from translate.lib.labels import field_labels, source_label
from translate.lib.pilot import parse_items, select_source
from translate.shelf.lt_check import check_text
from translate.steps.translate.translate_unit import build_messages, validate_unit

ROOT = Path(default_root())
PILOT = ROOT / "docs/pipeline/vi-ch01-pilot.md"


def test_vi_pack():
    assert "vi" in translation_langs()
    assert "vi" not in translation_langs(include_pilots=False)
    assert source_label("vi") == "Nguồn"
    assert field_labels("vi")[1] == "Nói dễ hiểu"
    assert unit_dir(str(ROOT), "vi", 1).endswith("active/vi/01/units")
    messages = build_messages("vi", "### 1. 示例", None, "Translate", uu="01")
    assert "Vietnamese" in messages[1]["content"]
    unit = (
        "### 1. Ví dụ\n§TAG§\n"
        + "\n".join(f"- {label}: test" for label in field_labels("vi"))
        + "\n§SRC§\n"
    )
    assert not validate_unit(unit, "01", "vi")


@pytest.mark.parametrize("value", ["", "0", "1,1", "3,1", "1-3", "1,x"])
def test_invalid_selection(value):
    with pytest.raises(ValueError, match="--items"):
        parse_items(value)


def test_select_intro_and_items():
    lines = ["# Intro", "### 1. First", "one", "### 2. Second", "two", "### 3. Third", "three"]
    assert select_source(lines, parse_items("1,3")) == [
        "# Intro",
        "### 1. First",
        "one",
        "### 3. Third",
        "three",
    ]
    with pytest.raises(ValueError, match="unknown source items"):
        select_source(lines, [4])


def verify(*options):
    return subprocess.run(
        [sys.executable, "-m", "translate.steps.verify.verify", "01", "--lang", "vi", *options],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_pilot_passes_but_full_chapter_fails():
    partial = verify("--file", str(PILOT), "--items", "1,2,3", "--json")
    assert partial.returncode == 0, partial.stdout + partial.stderr
    report = next(json.loads(line) for line in partial.stdout.splitlines() if line.startswith("{"))
    assert report["ok"]
    assert report["scope"] == "pilot"
    assert report["selected_items"] == [1, 2, 3]
    assert "stamp skipped" in partial.stdout
    full = verify("--file", str(PILOT), "--json")
    assert full.returncode == 1
    assert "headings 36 != 3" in full.stdout


def test_pilot_requires_explicit_file():
    result = verify("--items", "1,2,3")
    assert result.returncode == 2
    assert "requires --file" in result.stderr


def test_partial_assembly_cannot_publish():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "translate.steps.assemble.assemble",
            "01",
            "unused-workdir",
            "book/vi/01-Dung-Chet-Som.md",
            "vi",
            "--items",
            "1,2,3",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "outside book/" in result.stderr


def test_unsupported_lt_is_not_silent_success():
    with pytest.raises(ValueError, match="unknown language"):
        check_text("- Nói dễ hiểu: Ví dụ.", "vi")


def test_pilot_wrong_item_id_fails(tmp_path):
    candidate = tmp_path / "pilot.md"
    candidate.write_text(PILOT.read_text().replace("### 3.", "### 4."))
    result = verify("--file", str(candidate), "--items", "1,2,3")
    assert result.returncode == 1
    assert "pilot item IDs" in result.stdout


@pytest.mark.parametrize("claim", [{"status": "complete"}, {"file": "01.md"}, {"verified": True}])
def test_pilot_cannot_claim_completion(tmp_path, monkeypatch, claim):
    from forge.ops import check_content

    (tmp_path / "translations.json").write_text(json.dumps({"vi": {"01": claim}}))
    (tmp_path / "README.vi.md").write_text("Pilot only")
    entry = {
        "code": "vi",
        "publication": "pilot",
        "contentRoot": "book/vi",
        "readme": "README.vi.md",
    }
    monkeypatch.setattr(check_content, "ROOT", str(tmp_path))
    monkeypatch.setattr(check_content, "load_langs", lambda _root: [entry])
    issues = []
    assert check_content.publication_entries(issues) == []
    assert any("completion claim" in issue for issue in issues)


def test_pilot_cannot_contain_published_chapter(tmp_path, monkeypatch):
    from forge.ops import check_content

    (tmp_path / "translations.json").write_text("{}")
    (tmp_path / "README.vi.md").write_text("Pilot only")
    chapter_dir = tmp_path / "book/vi"
    chapter_dir.mkdir(parents=True)
    (chapter_dir / "01-Example.md").write_text("# Incomplete")
    entry = {
        "code": "vi",
        "publication": "pilot",
        "contentRoot": "book/vi",
        "readme": "README.vi.md",
    }
    monkeypatch.setattr(check_content, "ROOT", str(tmp_path))
    monkeypatch.setattr(check_content, "load_langs", lambda _root: [entry])
    issues = []
    check_content.publication_entries(issues)
    assert any("published content" in issue for issue in issues)
