#!/usr/bin/env python3
"""Sequential, resumable ZH → locale draft runner. Never publishes into book/."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from translate.lib.config import default_root, translation_langs, unit_dir
from translate.lib.paths import cn_chapter_path
from translate.llm.client import LLMError, _positive_env, _require_env, load_dotenv
from translate.steps.translate.translate_unit import atomic_write, translation_prompt, validate_unit


class BatchError(Exception):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def chapters_available(root: Path) -> list[str]:
    chapters = sorted({p.name[:2] for p in (root / "book").glob("[0-9][0-9]-*.md")})
    for nn in chapters:
        cn_chapter_path(str(root), nn)  # Reject duplicate sources.
    return chapters


def select_chapters(available: list[str], requested: list[str] | None) -> list[str]:
    if requested and any(not re.fullmatch(r"\d{1,2}", ch) for ch in requested):
        raise BatchError("Chapter IDs must be 1–2 digits")
    selected = sorted({f"{int(ch):02d}" for ch in requested}) if requested else available
    if not selected or any(nn not in available for nn in selected):
        raise BatchError(f"Unknown/empty chapter selection; available: {available}")
    return selected


def safe_run_root(root: Path, output: Path) -> Path:
    output = output.resolve()
    runs = (root / "translate" / "runs").resolve()
    if not output.is_relative_to(runs) or output == runs:
        raise BatchError("--run-root must be a subdirectory of translate/runs/, never book/")
    return output


def preflight() -> dict:
    load_dotenv()
    base = _require_env("HTLB_LLM_BASE_URL").rstrip("/")
    if not base.endswith("/v1"):
        raise LLMError("Batch runner requires HTLB_LLM_BASE_URL ending in /v1")
    model = _require_env("HTLB_LLM_MODEL")
    key = _require_env("HTLB_LLM_API_KEY")
    headers = {"Authorization": f"Bearer {key}"}
    for url in (base.removesuffix("/v1") + "/health", base + "/models"):
        req = urllib.request.Request(url, headers=headers)  # noqa: S310
        try:
            with urllib.request.urlopen(req, timeout=15) as response:  # noqa: S310
                data = json.load(response)
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise LLMError(f"Server preflight failed at {url}: {exc}") from exc
        if url.endswith("/health") and data.get("status") != "ok":
            raise LLMError("llama.cpp server is not healthy")
        if url.endswith("/models"):
            ids = [entry.get("id") for entry in data.get("data", [])]
            if model not in ids:
                raise LLMError(f"Configured model {model!r} not in server model IDs: {ids}")
    return {
        "base_url": base,
        "model": model,
        "temperature": os.environ.get("HTLB_LLM_TEMPERATURE", "0.2"),
        "max_tokens": _positive_env("HTLB_LLM_MAX_TOKENS", 4096),
        "timeout": _positive_env("HTLB_LLM_TIMEOUT", 300),
    }


def fingerprint(root: Path, nn: str, lang: str, settings: dict) -> str:
    paths = [
        Path(cn_chapter_path(str(root), nn)),
        translation_prompt(root, lang),
        root / "translate" / "glossary.json",
        root / "translate" / "rules" / f"{lang}.json",
        root / "translate" / "steps" / "translate" / "translate_unit.py",
        root / "translate" / "llm" / "client.py",
    ]
    data = {
        "schema": 1,
        "lang": lang,
        "settings": settings,
        "files": {str(p.relative_to(root)): sha256(p) for p in paths},
    }
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def cached_unit(
    path: Path, uid: str, lang: str, state: dict, *, chapter: str | None = None
) -> bool:
    if not path.exists():
        return False
    record = state.get("units", {}).get(uid)
    if record != sha256(path):
        raise BatchError(
            f"Untracked or edited unit {path}; preserve it or use --overwrite explicitly"
        )
    errors = validate_unit(path.read_text(encoding="utf-8"), uid, lang, chapter=chapter)
    if errors:
        raise BatchError(f"Cached unit is structurally invalid: {path}: {errors}")
    return True


def run_command(root: Path, arguments: list[str], log: Path) -> int:
    env = dict(os.environ, PYTHONPATH=str(root))
    result = subprocess.run(  # noqa: PLW1510
        [sys.executable, *arguments],
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    atomic_write(log, result.stdout)
    if result.returncode:
        print(result.stdout[-3000:], flush=True)
    return result.returncode


def translate_chapter(
    root: Path,
    nn: str,
    lang: str,
    work: Path,
    settings: dict,
    *,
    overwrite: bool,
    resume_changed: bool = False,
) -> dict:
    work.mkdir(parents=True, exist_ok=True)
    state_path = work / "resume.json"
    current = fingerprint(root, nn, lang, settings)
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    if state and state.get("fingerprint") != current and not overwrite:
        if not resume_changed:
            raise BatchError(
                f"Inputs/model changed for {nn}; choose a new --run-root, "
                "--resume-changed (preserves completed units), or --overwrite"
            )
        # Explicit mixed-configuration draft recovery. Keep provenance for every
        # existing unit; never claim it was generated with the new settings.
        for uid in state.get("units", {}):
            state.setdefault("unit_fingerprints", {}).setdefault(uid, state["fingerprint"])
        print(
            f"[{nn}] WARNING: accepting changed inputs/settings for missing units only; "
            "cached units retain old provenance. Source compatibility requires human review.",
            flush=True,
        )
        state["fingerprint"] = current
    if overwrite or not state:
        state = {"fingerprint": current, "units": {}}
    # Check all existing files before accepting a changed configuration on disk.
    if not overwrite:
        for output in sorted((work / "units").glob("*.md")):
            cached_unit(output, output.stem, lang, state, chapter=nn)
    atomic_write(state_path, json.dumps(state, indent=2) + "\n")
    if run_command(root, ["translate/steps/digest/make_digest.py", nn], work / "digest.log"):
        raise BatchError(f"Digest failed for {nn}")
    digest = Path(unit_dir(str(root), "cn", nn))
    meta = json.loads((digest.parent / "blocks.json").read_text())
    unit_ids = [f"{i:02d}" for i in range(meta["items"] + 1)]
    translated = skipped = 0
    for uid in unit_ids:
        output = work / "units" / f"{uid}.md"
        if not overwrite and cached_unit(output, uid, lang, state, chapter=nn):
            skipped += 1
            print(f"[{nn}/{uid}] resume: skip", flush=True)
            continue
        print(f"[{nn}/{uid}] translate → {lang}", flush=True)
        args = [
            "translate/steps/translate/translate_unit.py",
            "--nn",
            nn,
            "--unit",
            uid,
            "--lang",
            lang,
            "--out-dir",
            str(work),
        ]
        if run_command(root, args, work / f"unit-{uid}.log"):
            raise BatchError(f"Translation failed at {nn}/{uid}; see {work / f'unit-{uid}.log'}")
        errors = validate_unit(output.read_text(encoding="utf-8"), uid, lang, chapter=nn)
        if errors:
            raise BatchError(f"Invalid translated unit {nn}/{uid}: {errors}")
        state["units"][uid] = sha256(output)
        state.setdefault("unit_fingerprints", {})[uid] = current
        atomic_write(state_path, json.dumps(state, indent=2) + "\n")
        translated += 1
    assembled = work / "assembled.md"
    assemble_code = run_command(
        root,
        ["translate/steps/assemble/assemble.py", nn, str(work), str(assembled), lang],
        work / "assemble.log",
    )
    verify_code = (
        run_command(
            root,
            [
                "translate/steps/verify/verify.py",
                nn,
                "--lang",
                lang,
                "--file",
                str(assembled),
                "--json",
            ],
            work / "verify.log",
        )
        if not assemble_code
        else None
    )
    ok = assemble_code == 0 and verify_code == 0
    return {
        "chapter": nn,
        "ok": ok,
        "translated": translated,
        "skipped": skipped,
        "assemble_exit": assemble_code,
        "verify_exit": verify_code,
        "draft": str(assembled),
        "human_review_required": True,
    }


def main(argv: list[str] | None = None) -> int:
    root = Path(default_root())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lang", choices=translation_langs(), default="vi")
    parser.add_argument("--chapters", nargs="+", help="Chapter IDs; default: all Chinese chapters")
    parser.add_argument("--run-root", type=Path, help="Default: translate/runs/gemma/<lang>")
    parser.add_argument(
        "--dry-run", action="store_true", help="List sources/output; no API calls or writes"
    )
    parser.add_argument(
        "--check", action="store_true", help="Check server/config only; no translations"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Explicitly retranslate selected chapters, including edited units",
    )
    parser.add_argument(
        "--keep-going",
        action="store_true",
        help="Continue other chapters after a failure; final exit remains nonzero",
    )
    parser.add_argument(
        "--resume-changed",
        action="store_true",
        help="Explicitly accept mixed configurations: preserve tracked completed units, "
        "translate missing units with current settings; source compatibility needs review",
    )
    args = parser.parse_args(argv)
    if args.resume_changed and args.overwrite:
        parser.error("--resume-changed cannot be combined with --overwrite")
    try:
        output = safe_run_root(root, args.run_root or root / "translate/runs/gemma" / args.lang)
        selected = select_chapters(chapters_available(root), args.chapters)
        if args.dry_run:
            for nn in selected:
                print(f"{nn}: {cn_chapter_path(str(root), nn)} → {output / nn / 'assembled.md'}")
            print(f"{len(selected)} chapters; ZH → {args.lang}; sequential; draft only")
            return 0
        settings = preflight()
        print(json.dumps(settings, ensure_ascii=False), flush=True)
        if args.check:
            return 0
        output.mkdir(parents=True, exist_ok=True)
        # Shared digest is mutable: serialize all instances of this batch runner.
        with (root / "translate/runs/.translate-book.lock").open("w") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise BatchError("Another translate-book runner is active") from exc
            reports = []
            for nn in selected:
                try:
                    options = {"overwrite": args.overwrite}
                    if args.resume_changed:
                        options["resume_changed"] = True
                    report = translate_chapter(
                        root, nn, args.lang, output / nn, settings, **options
                    )
                except (BatchError, OSError, ValueError) as exc:
                    report = {"chapter": nn, "ok": False, "error": str(exc)}
                reports.append(report)
                atomic_write(
                    output / "batch-report.json",
                    json.dumps(
                        {
                            "lang": args.lang,
                            "source": "zh",
                            "settings": settings,
                            "publication": False,
                            "chapters": reports,
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                )
                print(json.dumps(report, ensure_ascii=False), flush=True)
                if not report["ok"] and not args.keep_going:
                    break
        return 0 if all(report["ok"] for report in reports) else 1
    except (BatchError, LLMError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted; rerun the same command to resume.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
