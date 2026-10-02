"""Tests for the static unreviewed Vietnamese preview (preview/vi → site/vi/preview)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from forge.site.build_vi_preview import CHAPTER_IDS, WARNING_POINTS, build


def _fixture(root: Path, overrides: dict[str, str] | None = None) -> Path:
    snapshot_dir = root / "preview" / "vi"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    overrides = overrides or {}
    for chapter in CHAPTER_IDS:
        text = overrides.get(chapter, f"# Chương {chapter}\n\nĐoạn thử nghiệm {chapter}.\n")
        (snapshot_dir / f"{chapter}.md").write_text(text, encoding="utf-8")
    return snapshot_dir


def _page(root: Path, chapter: str) -> str:
    return (root / "site" / "vi" / "preview" / f"{chapter}.html").read_text(encoding="utf-8")


def _index(root: Path) -> str:
    return (root / "site" / "vi" / "preview" / "index.html").read_text(encoding="utf-8")


def test_builds_all_34_with_warning_on_every_page_and_index(tmp_path):
    _fixture(tmp_path)
    written = build(tmp_path)
    assert len(written) == 35
    index = _index(tmp_path)
    assert "noindex" in index
    for point in WARNING_POINTS:
        assert point in index
    for chapter in CHAPTER_IDS:
        page = _page(tmp_path, chapter)
        assert f"Chương {chapter}" in page
        assert "noindex" in page
        for point in WARNING_POINTS:
            assert point in page


def test_build_accepts_path_and_str(tmp_path):
    _fixture(tmp_path)
    build(str(tmp_path))
    build(tmp_path)
    assert _page(tmp_path, "01")


def test_non_numeric_markdown_is_ignored(tmp_path):
    snapshot_dir = _fixture(tmp_path)
    (snapshot_dir / "README.md").write_text("# Bản nháp\n", encoding="utf-8")
    build(tmp_path)
    assert not (tmp_path / "site" / "vi" / "preview" / "README.html").exists()
    assert _index(tmp_path)


def test_escaping_and_link_safety(tmp_path):
    override = (
        "# Tiêu đề\n\n"
        "Thẻ nguy hiểm: <script>alert('x')</script> & <b>bold</b>\n\n"
        "[xấu](javascript:alert(1)) [dữ liệu](data:text/html,x)\n\n"
        "[← Quay lại mục lục](../../README.vi.md) "
        "[bản gốc](../../README.zh.md) "
        "[tài liệu](../../docs/foo.md) [chương kề](02.md)\n\n"
        "<https://example.com/a?b=1&c=2>\n\n"
        "<!-- 成本标签: 钱=0 -->\n"
    )
    _fixture(tmp_path, {"01": override})
    build(tmp_path)
    page = _page(tmp_path, "01")
    assert "<script>alert" not in page
    assert "&lt;script&gt;alert" in page
    assert "javascript:" not in page
    assert "data:text/html" not in page
    assert "<!--" not in page
    assert "成本标签" in page


def test_readme_index_and_external_link_mapping(tmp_path):
    override = (
        "# Tiêu đề\n\n"
        "[← Quay lại mục lục](../../README.vi.md)\n\n"
        "[bản gốc](../../README.zh.md) [tài liệu](../../docs/foo.md) [chương kề](02.md)\n"
    )
    _fixture(tmp_path, {"01": override})
    build(tmp_path)
    page = _page(tmp_path, "01")
    assert '<a href="index.html">← Quay lại mục lục</a>' in page
    assert "https://github.com/hiennguyen9874/HowToLiveBetter/blob/main/README.zh.md" in page
    assert "https://github.com/hiennguyen9874/HowToLiveBetter/blob/main/docs/foo.md" in page
    assert 'href="02.html"' in page


def test_autolink_scheme_and_escaping(tmp_path):
    _fixture(tmp_path, {"01": "# T\n\n<https://example.com/a?b=1&c=2>\n"})
    build(tmp_path)
    page = _page(tmp_path, "01")
    assert 'href="https://example.com/a?b=1&amp;c=2"' in page


def test_navigation_previous_next_and_index(tmp_path):
    _fixture(tmp_path)
    build(tmp_path)
    page_01 = _page(tmp_path, "01")
    page_02 = _page(tmp_path, "02")
    page_34 = _page(tmp_path, "34")
    assert 'href="02.html"' in page_01
    assert 'href="01.html"' not in page_01
    assert 'href="index.html"' in page_01
    assert 'href="01.html"' in page_02
    assert 'href="03.html"' in page_02
    assert 'href="33.html"' in page_34
    assert 'href="35.html"' not in page_34
    index = _index(tmp_path)
    for chapter in CHAPTER_IDS:
        assert f'href="{chapter}.html"' in index


def test_missing_snapshot_fails_before_writing(tmp_path):
    snapshot_dir = tmp_path / "preview" / "vi"
    snapshot_dir.mkdir(parents=True)
    for chapter in CHAPTER_IDS[:-1]:
        (snapshot_dir / f"{chapter}.md").write_text(f"# {chapter}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing IDs: 34"):
        build(tmp_path)
    assert not (tmp_path / "site" / "vi" / "preview" / "01.html").exists()


@pytest.mark.parametrize("extra", ["99", "001"])
def test_extra_numeric_snapshot_fails(tmp_path, extra):
    snapshot_dir = _fixture(tmp_path)
    (snapshot_dir / f"{extra}.md").write_text("# Thừa\n", encoding="utf-8")
    with pytest.raises(ValueError, match=f"extra IDs: {extra}"):
        build(tmp_path)


def test_missing_snapshot_directory_fails(tmp_path):
    with pytest.raises(ValueError, match="missing snapshot directory"):
        build(tmp_path)


def test_pilot_files_and_snapshots_untouched(tmp_path):
    book_dir = tmp_path / "book" / "vi"
    book_dir.mkdir(parents=True)
    pilot = book_dir / "01-Dung-Chet-Som.md"
    pilot.write_text("# Pilot\n", encoding="utf-8")
    snapshot_dir = _fixture(tmp_path)
    snapshot = snapshot_dir / "01.md"
    snapshot_before = snapshot.read_bytes()
    pilot_before = pilot.read_bytes()
    build(tmp_path)
    assert snapshot.read_bytes() == snapshot_before
    assert pilot.read_bytes() == pilot_before
    assert not (book_dir / "01.html").exists()


def test_pages_artifact_includes_preview_without_publishing_pilot(tmp_path, monkeypatch):
    from forge.site import pages_artifact

    _fixture(tmp_path)
    build(tmp_path)
    (tmp_path / "site" / "index.html").write_text("landing", encoding="utf-8")
    (tmp_path / "book" / "vi").mkdir(parents=True)
    (tmp_path / "README.vi.md").write_text("pilot", encoding="utf-8")
    monkeypatch.setattr(pages_artifact, "ROOT", str(tmp_path))
    monkeypatch.setattr(pages_artifact, "SITE", str(tmp_path / "site"))
    monkeypatch.setattr(pages_artifact, "OUT", str(tmp_path / ".publish"))
    assert pages_artifact.main() == 0
    assert (tmp_path / ".publish" / "vi" / "preview" / "34.html").exists()
    assert (tmp_path / ".publish" / "preview" / "vi" / "34.md").exists()
    assert not list((tmp_path / ".publish" / "book" / "vi").glob("*.md"))


def test_tracked_snapshot_provenance():
    root = Path(__file__).resolve().parents[3]
    snapshots = root / "preview" / "vi"
    provenance = json.loads((snapshots / "snapshot.json").read_text(encoding="utf-8"))
    assert provenance["publication"] == "pilot"
    assert provenance["quality_approval"] is False
    assert [row["chapter"] for row in provenance["chapters"]] == list(CHAPTER_IDS)
    for row in provenance["chapters"]:
        data = (snapshots / f"{row['chapter']}.md").read_bytes()
        assert hashlib.sha256(data).hexdigest() == row["snapshot_sha256"]
        assert "BẢN XEM TRƯỚC CHƯA DUYỆT" in data.decode("utf-8")
        assert row["independent_vietnamese_review"] == "pending"


def test_paragraph_and_list_content_not_dropped(tmp_path):
    override = "# Chương 7\n\nĐoạn văn kiểm tra không bị mất nội dung.\n\n- Dòng một\n- Dòng hai\n"
    _fixture(tmp_path, {"07": override})
    build(tmp_path)
    page = _page(tmp_path, "07")
    assert "Đoạn văn kiểm tra không bị mất nội dung." in page
    assert "<li>Dòng một</li>" in page
    assert "<li>Dòng hai</li>" in page
