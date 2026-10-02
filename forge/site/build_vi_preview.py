#!/usr/bin/env python3
"""Build a static, unreviewed Vietnamese preview from Git-tracked snapshots.

Input:  preview/vi/NN.md  (exactly chapters 01..34, plus optionally README.md)
Output: site/vi/preview/NN.html + site/vi/preview/index.html

Snapshots are read-only here: the builder never looks at translate/runs/, never
calls an API and never rewrites a snapshot. It only renders basic escaped HTML
(headings, paragraphs, lists, quotes, comments as metadata, safe links) with an
inline stylesheet, no JavaScript and no CDN. Every page and the index carry the
same prominent warning: these are machine-translated drafts that no independent
Vietnamese reader has reviewed; integrity-pass is not quality approval.

Usage (repo root):
  PYTHONPATH=. python3 forge/site/build_vi_preview.py [--root DIR] [--out-dir DIR]
"""

from __future__ import annotations

import argparse
import html
import os
import re
import sys
from urllib.parse import quote

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

SNAPSHOT_SUBDIR = os.path.join("preview", "vi")
OUTPUT_SUBDIR = os.path.join("site", "vi", "preview")

# Fork pages artifacts live here; Chinese/research references that have no
# offline copy in the published HTML directory point back at this repo.
SOURCE_REPO = "https://github.com/hiennguyen9874/HowToLiveBetter"
SOURCE_BLOB = SOURCE_REPO + "/blob/main"
SOURCE_TREE = SOURCE_REPO + "/tree/main"

CHAPTER_IDS: tuple[str, ...] = tuple(f"{number:02d}" for number in range(1, 35))

WARNING_TITLE = "Cảnh báo: bản dịch máy chưa được kiểm duyệt"
WARNING_POINTS: tuple[str, ...] = (
    "Đây là bản nháp dịch bằng máy từ tiếng Trung, chưa được người đọc độc lập kiểm tra.",
    "Nội dung có thể sai nghĩa, thiếu sót, dùng sai thuật ngữ hoặc tối nghĩa.",
    "Các phần y tế và pháp lý chỉ để tham khảo, không thay thế tư vấn của chuyên gia có chuyên môn.",
    "Bản dịch giữ bối cảnh nguồn tiếng Trung; số liệu, ghi chú và nguồn gốc cần được kiểm chứng.",
    "Vượt qua kiểm tra toàn vẹn số liệu là kiểm tra kỹ thuật, không xác nhận chất lượng nội dung.",
    "Đây không phải bản hoàn chỉnh; nội dung có thể được sửa đổi hoặc ẩn đi bất cứ lúc nào.",
)


class PreviewError(ValueError):
    """Invalid preview input (missing/extra snapshots, bad directory)."""


HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
LIST_RE = re.compile(r"^(\s*)([-*+]|\d+\.)\s+(.*)$")
ORDERED_RE = re.compile(r"^\s*\d+\.\s")
HR_RE = re.compile(r"^\s*([-*_])(?:\s*\1){2,}\s*$")
BQ_RE = re.compile(r"^>\s?(.*)$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
COMMENT_START_RE = re.compile(r"^\s*<!--")
COMMENT_RE = re.compile(r"<!--(.*?)-->", re.DOTALL)
PAGE_BLOCK_RES = (HEADING_RE, LIST_RE, COMMENT_START_RE, BQ_RE, HR_RE, FENCE_RE)

READMES_RE = re.compile(r"README(?:\.[A-Za-z0-9]{2,8})?\.md", re.IGNORECASE)
TOKEN_RE = re.compile(
    r"\[(?P<link>[^\]]+)\]\((?P<href>[^)\s]+)(?:\s+\"[^\"]*\")?\)"
    r"|<(?P<url>(?:https?|mailto):[^<>\s]+)>"
)
BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
CODE_RE = re.compile(r"`([^`]+)`")

STYLE = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body { margin: 0; background: #fff; color: #1b1b1b;
  font-family: Georgia, "Times New Roman", serif; line-height: 1.65; }
.wrap { max-width: 46rem; margin: 0 auto; padding: 1rem 1.1rem 4rem; }
a { color: #0b5cad; }
nav.chapter-nav { display: flex; flex-wrap: wrap; gap: .75rem;
  padding: .55rem 0; border-bottom: 1px solid #ddd; font-size: .95rem; }
.warning { border: 2px solid #b00020; background: #fff2f3; border-radius: .5rem;
  padding: .9rem 1rem; margin: 1rem 0 1.4rem; }
.warning h2 { margin: .1rem 0 .5rem; font-size: 1.05rem; color: #8a0018; }
.warning ul { margin: .4rem 0 0; padding-left: 1.2rem; }
.warning li { margin: .3rem 0; }
main.content h1 { font-size: 1.7rem; line-height: 1.25; }
main.content h2 { font-size: 1.35rem; margin-top: 1.9rem; }
main.content h3 { font-size: 1.12rem; margin-top: 1.6rem; }
main.content h4, main.content h5, main.content h6 { margin-top: 1.4rem; }
main.content p { margin: .65rem 0; }
main.content ul, main.content ol { margin: .45rem 0 .9rem; padding-left: 1.3rem; }
main.content li { margin: .25rem 0; }
p.cost-tag { font-size: .85rem; color: #555; background: #f6f6f6;
  border-left: 3px solid #bbb; padding: .3rem .6rem; }
blockquote { border-left: 3px solid #bbb; margin: .7rem 0; padding: .1rem .9rem; color: #444; }
pre { background: #f6f6f6; padding: .6rem; overflow-x: auto; }
code { background: #f0f0f0; padding: .05rem .2rem; }
.chapter-list { list-style: none; padding: 0; }
.chapter-list li { margin: .35rem 0; }
footer { margin-top: 2.5rem; border-top: 1px solid #ddd; padding-top: .8rem;
  font-size: .9rem; color: #555; }
@media (max-width: 520px) { .wrap { padding: .8rem; } }
""".strip()


def _is_readme(basename: str) -> bool:
    return READMES_RE.fullmatch(basename) is not None


def _preview_chapter_target(path: str) -> str | None:
    """Return NN.html when a relative link points at a generated chapter."""
    parts = [part for part in path.split("/") if part not in ("", ".")]
    if "docs" in parts or "research" in parts:
        return None
    if "book" in parts:
        index = parts.index("book")
        if index + 1 < len(parts) and parts[index + 1] != "vi":
            return None
    basename = parts[-1] if parts else ""
    match = re.fullmatch(r"(\d{2})(?:[-_][^/]*)?\.md", basename)
    if match and match.group(1) in CHAPTER_IDS:
        return f"{match.group(1)}.html"
    match = re.fullmatch(r"(\d{2})\.html", basename)
    if match and match.group(1) in CHAPTER_IDS:
        return f"{match.group(1)}.html"
    return None


def _external_target(path: str) -> str:
    """Normalise a relative path to a repo-root path for GitHub blob links."""
    for anchor in ("docs/", "book/", "translate/", "forge/", "preview/"):
        index = path.find(anchor)
        if index != -1:
            return path[index:]
    parts = [part for part in path.split("/") if part not in ("", ".")]
    while parts and parts[0] == "..":
        parts.pop(0)
    return "/".join(parts)


def map_href(href: str) -> str | None:
    """Map an input href to a safe output href, or None if disallowed.

    Safe schemes only; raw/relative targets never pass through. README vi links
    (the back-to-contents line) go to the generated index; other README/docs
    files go to the external GitHub main URL because the standalone artifact
    only ships the HTML directory.
    """
    href = href.strip()
    if not href:
        return None
    if href.startswith("#"):
        return href
    lowered = href.lower()
    if lowered.startswith(("javascript:", "data:", "vbscript:", "file:")):
        return None
    if lowered.startswith(("http://", "https://", "mailto:")):
        return href
    if href.startswith("//") or "://" in href:
        return None
    path, _, fragment = href.partition("#")
    suffix = f"#{fragment}" if fragment else ""
    basename = path.rstrip("/").rsplit("/", 1)[-1]
    if _is_readme(basename):
        if basename.lower() == "readme.vi.md":
            return "index.html" + suffix
        return f"{SOURCE_BLOB}/{quote(basename, safe='')}{suffix}"
    target = _preview_chapter_target(path)
    if target:
        return target + suffix
    external = _external_target(path)
    if not external:
        return None
    return f"{SOURCE_BLOB}/{quote(external, safe='/')}{suffix}"


def _inline_text(text: str) -> str:
    escaped = html.escape(text, quote=False)
    escaped = BOLD_RE.sub(r"<strong>\1</strong>", escaped)
    return CODE_RE.sub(r"<code>\1</code>", escaped)


def render_inline(text: str) -> str:
    """Escape inline text and turn markdown/autolinks into safe anchors."""
    out: list[str] = []
    position = 0
    for match in TOKEN_RE.finditer(text):
        if match.start() > position:
            out.append(_inline_text(text[position : match.start()]))
        label = match.group("link")
        if label is not None:
            target = map_href(match.group("href"))
            label_html = _inline_text(label)
            if target is None:
                out.append(label_html)
            else:
                out.append(f'<a href="{html.escape(target, quote=True)}">{label_html}</a>')
        else:
            url = match.group("url")
            safe = html.escape(url, quote=True)
            out.append(f'<a href="{safe}">{safe}</a>')
        position = match.end()
    out.append(_inline_text(text[position:]))
    return "".join(out)


def _is_block_start(line: str) -> bool:
    return any(pattern.match(line) for pattern in PAGE_BLOCK_RES)


def render_markdown(text: str) -> str:
    """Render snapshot markdown to escaped HTML without dropping content."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks: list[str] = []
    index = 0
    total = len(lines)
    while index < total:
        line = lines[index]
        if not line.strip():
            index += 1
            continue

        fence = FENCE_RE.match(line)
        if fence:
            marker = fence.group(1)
            index += 1
            buffer: list[str] = []
            while index < total and not lines[index].strip().startswith(marker):
                buffer.append(lines[index])
                index += 1
            index += 1
            blocks.append("<pre><code>" + html.escape("\n".join(buffer)) + "</code></pre>")
            continue

        heading = HEADING_RE.match(line)
        if heading:
            level = len(heading.group(1))
            blocks.append(f"<h{level}>{render_inline(heading.group(2))}</h{level}>")
            index += 1
            continue

        if HR_RE.match(line):
            blocks.append("<hr>")
            index += 1
            continue

        if COMMENT_START_RE.match(line):
            buffer = [line]
            while "-->" not in "\n".join(buffer) and index + 1 < total:
                index += 1
                buffer.append(lines[index])
            inner = COMMENT_RE.sub(r"\1", "\n".join(buffer), count=1)
            blocks.append('<p class="cost-tag">' + html.escape(inner.strip()) + "</p>")
            index += 1
            continue

        quote_match = BQ_RE.match(line)
        if quote_match:
            quoted: list[str] = []
            while index < total:
                current = BQ_RE.match(lines[index])
                if current is None:
                    break
                quoted.append(current.group(1))
                index += 1
            blocks.append("<blockquote>" + render_inline(" ".join(quoted)) + "</blockquote>")
            continue

        list_match = LIST_RE.match(line)
        if list_match:
            ordered = ORDERED_RE.match(line) is not None
            tag = "ol" if ordered else "ul"
            items: list[str] = []
            while index < total:
                item = LIST_RE.match(lines[index])
                if item is None or (ORDERED_RE.match(lines[index]) is not None) != ordered:
                    break
                items.append("<li>" + render_inline(item.group(3)) + "</li>")
                index += 1
            blocks.append(f"<{tag}>" + "".join(items) + f"</{tag}>")
            continue

        paragraph = [line]
        index += 1
        while index < total and lines[index].strip() and not _is_block_start(lines[index]):
            paragraph.append(lines[index])
            index += 1
        blocks.append("<p>" + render_inline("\n".join(paragraph)) + "</p>")

    return "\n".join(blocks)


def extract_title(text: str) -> str | None:
    match = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
    if match is None:
        return None
    return match.group(1).strip()


def warning_html() -> str:
    items = "".join(f"<li>{html.escape(point)}</li>" for point in WARNING_POINTS)
    return (
        '<div class="warning" role="alert">'
        f"<h2>{html.escape(WARNING_TITLE)}</h2>"
        f"<ul>{items}</ul>"
        "</div>"
    )


def render_nav(prev_id: str | None, next_id: str | None) -> str:
    parts: list[str] = []
    if prev_id:
        parts.append(f'<a rel="prev" href="{prev_id}.html">← Chương {prev_id}</a>')
    parts.append('<a href="index.html">Mục lục</a>')
    if next_id:
        parts.append(f'<a rel="next" href="{next_id}.html">Chương {next_id} →</a>')
    return '<nav class="chapter-nav">' + " ".join(parts) + "</nav>"


def render_shell(*, title: str, body: str, nav: str) -> str:
    footer = (
        f'<p>Nguồn tiếng Trung: <a href="{SOURCE_TREE}/book">book/</a>. '
        "Bản xem trước chỉ để rà soát, không phải bản hoàn chỉnh.</p>"
    )
    return (
        "<!DOCTYPE html>\n"
        '<html lang="vi">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<meta name="robots" content="noindex, nofollow">\n'
        f"<title>{html.escape(title)}</title>\n"
        f"<style>\n{STYLE}\n</style>\n"
        '</head>\n<body>\n<div class="wrap">\n'
        f"{nav}\n{warning_html()}\n"
        f'<main class="content">\n{body}\n</main>\n'
        f"<footer>\n{footer}\n</footer>\n"
        "</div>\n</body>\n</html>\n"
    )


def render_index(chapters: list[tuple[str, str, str]]) -> str:
    items = "\n".join(
        f'<li><a href="{chapter}.html">{chapter}. {html.escape(title)}</a></li>'
        for chapter, title, _body in chapters
    )
    body = (
        "<h1>Bản xem trước tiếng Việt chưa kiểm duyệt</h1>\n"
        "<p>34 chương nháp dịch bằng máy từ tiếng Trung. Danh sách đủ 01–34 "
        "nhưng không xác nhận chất lượng và không phải bản hoàn chỉnh.</p>\n"
        f'<ul class="chapter-list">\n{items}\n</ul>'
    )
    return render_shell(
        title="Bản xem trước tiếng Việt chưa kiểm duyệt",
        body=body,
        nav="",
    )


def snapshot_entries(root: str | os.PathLike[str]) -> list[tuple[str, str]]:
    """Return [(chapter, path), ...] for 01..34, or raise PreviewError.

    Non-numeric markdown (for example README.md) is ignored; a numeric extra
    such as 99.md or a missing chapter fails so the preview cannot silently
    claim a complete 01..34 set.
    """
    root_str = os.fspath(root)
    snapshot_dir = os.path.join(root_str, SNAPSHOT_SUBDIR)
    if not os.path.isdir(snapshot_dir):
        raise PreviewError(f"missing snapshot directory: {snapshot_dir}")
    found: dict[str, str] = {}
    extras: list[str] = []
    for name in sorted(os.listdir(snapshot_dir)):
        path = os.path.join(snapshot_dir, name)
        if not os.path.isfile(path) or not name.endswith(".md"):
            continue
        chapter = name[: -len(".md")]
        if chapter in CHAPTER_IDS:
            found[chapter] = path
        elif chapter.isdigit():
            extras.append(name)
    missing = [chapter for chapter in CHAPTER_IDS if chapter not in found]
    if missing or extras:
        problems: list[str] = []
        if missing:
            problems.append("missing IDs: " + ", ".join(missing))
        if extras:
            problems.append("extra IDs: " + ", ".join(sorted(extras)))
        raise PreviewError(
            "preview/vi snapshots must cover exactly 01..34 (" + "; ".join(problems) + ")"
        )
    return [(chapter, found[chapter]) for chapter in CHAPTER_IDS]


def _write(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def build(root: str | os.PathLike[str] = ROOT, *, out_dir: str | None = None) -> list[str]:
    """Render the tracked snapshots under ``root`` and return written paths."""
    root_str = os.fspath(root)
    entries = snapshot_entries(root_str)
    destination = os.fspath(out_dir) if out_dir else os.path.join(root_str, OUTPUT_SUBDIR)
    os.makedirs(destination, exist_ok=True)

    chapters: list[tuple[str, str, str]] = []
    written: list[str] = []
    for chapter, path in entries:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        title = extract_title(text) or f"Chương {chapter}"
        chapters.append((chapter, title, render_markdown(text)))

    for index, (chapter, title, body) in enumerate(chapters):
        prev_id = chapters[index - 1][0] if index > 0 else None
        next_id = chapters[index + 1][0] if index + 1 < len(chapters) else None
        page = render_shell(
            title=f"{title} — bản dịch máy chưa duyệt",
            body=body,
            nav=render_nav(prev_id, next_id),
        )
        out_path = os.path.join(destination, f"{chapter}.html")
        _write(out_path, page)
        written.append(out_path)

    index_path = os.path.join(destination, "index.html")
    _write(index_path, render_index(chapters))
    written.append(index_path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=None, help="repo root (default: auto-detected)")
    parser.add_argument("--out-dir", default=None, help="override site/vi/preview output dir")
    args = parser.parse_args(argv)
    root = args.root or ROOT
    try:
        written = build(root, out_dir=args.out_dir)
    except PreviewError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    for path in written:
        print("wrote", os.path.relpath(path))
    print(f"wrote {len(written)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
