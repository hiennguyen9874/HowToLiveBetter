from __future__ import annotations

import io
import json
import urllib.error
from unittest.mock import patch

import pytest
from translate.llm import client
from translate.ops import translate_book as batch
from translate.steps.translate import translate_unit as tu


def vi_item(uid="01"):
    text = f"### {int(uid)}. Tiêu đề\n" + "\n".join(
        f"{label} Nội dung" for label in tu.REQUIRED_FIELDS["vi"]
    )
    return tu.inject_mechanical_markers(text, uid)


@pytest.mark.parametrize("extra", ["# Chương 2\n", "## Ghi chú\n", "### 99. Khác\n"])
def test_extra_headings_rejected(extra):
    assert tu.validate_unit(extra + vi_item(), "01", "vi")


def test_duplicate_empty_unknown_and_reordered_fields():
    good = vi_item()
    assert not tu.validate_unit(good, "01", "vi")
    assert tu.validate_unit(good + "- Chi phí: Thêm\n", "01", "vi")
    assert tu.validate_unit(good.replace("- Chi phí: Nội dung", "- Chi phí:"), "01", "vi")
    assert tu.validate_unit(good + "- Khác: x\n", "01", "vi")
    assert tu.validate_unit(good.replace("- Chi phí:", "- Sai:"), "01", "vi")


def test_unnumbered_heading_and_preamble_rejected():
    assert tu.validate_unit(vi_item().replace("### 1.", "###"), "01", "vi")
    assert tu.validate_unit("Đây là bản dịch\n" + vi_item(), "01", "vi")


def test_intro_extra_title_rejected():
    assert tu.validate_unit("# 1. Tiêu đề\n# Thêm\nVăn bản\n", "00", "vi")
    assert not tu.validate_unit("# 1. Tiêu đề\nVăn bản\n", "00", "vi")


def test_intro_chapter_number_preserved():
    assert tu.validate_unit("# Tiêu đề\nVăn bản\n", "00", "vi", chapter="01")
    assert tu.validate_unit("# 2. Tiêu đề\nVăn bản\n", "00", "vi", chapter="01")
    assert not tu.validate_unit("# 1. Tiêu đề\nVăn bản\n", "00", "vi", chapter="01")


def test_vi_prompt_selected():
    from pathlib import Path

    assert tu.translation_prompt(Path("."), "vi").name == "translate-unit-vi.md"
    assert tu.translation_prompt(Path("."), "en").name == "translate-unit.md"


class Response(io.BytesIO):
    def getcode(self):
        return 200


@pytest.mark.parametrize("finish", ["length", "content_filter", "tool_calls"])
def test_incomplete_api_output_rejected(monkeypatch, finish):
    monkeypatch.setattr(client, "load_dotenv", lambda: None)
    data = {"choices": [{"finish_reason": finish, "message": {"content": "Partial"}}]}
    with (
        patch.object(
            client.urllib.request, "urlopen", return_value=Response(json.dumps(data).encode())
        ),
        pytest.raises(client.LLMError),
    ):
        client.chat([], base_url="http://localhost/v1", model="gemma")


def test_truncation_diagnostics(monkeypatch):
    monkeypatch.setattr(client, "load_dotenv", lambda: None)
    data = {
        "usage": {"prompt_tokens": 1200, "completion_tokens": 4096},
        "choices": [
            {
                "finish_reason": "length",
                "message": {"content": "Partial", "reasoning_content": "Think"},
            }
        ],
    }
    with (
        patch.object(
            client.urllib.request, "urlopen", return_value=Response(json.dumps(data).encode())
        ),
        pytest.raises(client.LLMError) as error,
    ):
        client.chat([], max_tokens=4096, base_url="http://localhost/v1", model="gemma")
    for expected in (
        "requested_max_tokens=4096",
        "prompt_tokens=1200",
        "completion_tokens=4096",
        "reasoning_chars=5",
        "--run-root",
    ):
        assert expected in str(error.value)
    assert "Partial" not in str(error.value)


def test_env_budget_and_content_only(monkeypatch):
    monkeypatch.setattr(client, "load_dotenv", lambda: None)
    monkeypatch.setenv("HTLB_LLM_MAX_TOKENS", "8192")
    monkeypatch.setenv("HTLB_LLM_TIMEOUT", "600")
    data = {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"content": "Translation", "reasoning_content": "Do not save me"},
            }
        ]
    }
    with patch.object(
        client.urllib.request, "urlopen", return_value=Response(json.dumps(data).encode())
    ) as call:
        assert client.chat([], base_url="http://localhost/v1", model="gemma") == "Translation"
    request = call.call_args.args[0]
    assert json.loads(request.data)["max_tokens"] == 8192
    assert call.call_args.kwargs["timeout"] == 600


def test_http_errors_not_retried(monkeypatch):
    monkeypatch.setattr(client, "load_dotenv", lambda: None)
    error = urllib.error.HTTPError(
        "http://localhost", 400, "Bad request", {}, io.BytesIO(b"context full")
    )
    with (
        patch.object(client.urllib.request, "urlopen", side_effect=error) as call,
        pytest.raises(client.LLMError, match="HTTP 400"),
    ):
        client.chat([], base_url="http://localhost/v1", model="gemma")
    assert call.call_count == 1


@pytest.mark.parametrize("raw", ["0", "-1", "abc"])
def test_bad_token_budget(monkeypatch, raw):
    monkeypatch.setattr(client, "load_dotenv", lambda: None)
    monkeypatch.setenv("HTLB_LLM_MAX_TOKENS", raw)
    with pytest.raises(client.LLMError, match="positive integer"):
        client.chat([], base_url="http://localhost/v1", model="gemma")


def test_chapter_selection():
    assert batch.select_chapters(["01", "02"], ["2", "01", "02"]) == ["01", "02"]
    for requested in (["99"], ["all"], ["../01"]):
        with pytest.raises(batch.BatchError):
            batch.select_chapters(["01"], requested)


def test_output_guard(tmp_path):
    valid = tmp_path / "translate/runs/gemma/vi"
    assert batch.safe_run_root(tmp_path, valid) == valid
    for invalid in (
        tmp_path / "book/vi",
        tmp_path / "translate/digest",
        tmp_path / "translate/runs",
    ):
        with pytest.raises(batch.BatchError):
            batch.safe_run_root(tmp_path, invalid)


def test_cache_preserves_untracked_or_edited_units(tmp_path):
    unit = tmp_path / "01.md"
    assert not batch.cached_unit(unit, "01", "vi", {})
    unit.write_text(vi_item())
    with pytest.raises(batch.BatchError, match="Untracked or edited"):
        batch.cached_unit(unit, "01", "vi", {})
    state = {"units": {"01": batch.sha256(unit)}}
    assert batch.cached_unit(unit, "01", "vi", state)
    unit.write_text(vi_item() + "Edit\n")
    with pytest.raises(batch.BatchError):
        batch.cached_unit(unit, "01", "vi", state)


def project(tmp_path):
    source = tmp_path / "book/01-source.md"
    source.parent.mkdir()
    source.write_text("# 1. Source\n### 1. Item\n")
    files = [
        "translate/prompts/translate-unit-vi.md",
        "translate/glossary.json",
        "translate/rules/vi.json",
        "translate/steps/translate/translate_unit.py",
        "translate/llm/client.py",
    ]
    for name in files:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}")
    (tmp_path / "translate/rules/project.json").write_text(
        json.dumps({"unit_dirs": {"cn": "translate/digest/{nn}/units"}})
    )
    return source


def test_fingerprint_changes_with_source_and_model(tmp_path):
    source = project(tmp_path)
    a = batch.fingerprint(tmp_path, "01", "vi", {"model": "a"})
    assert a != batch.fingerprint(tmp_path, "01", "vi", {"model": "b"})
    source.write_text("Changed")
    assert a != batch.fingerprint(tmp_path, "01", "vi", {"model": "a"})


def test_dry_run_no_network_or_writes(tmp_path, monkeypatch, capsys):
    project(tmp_path)
    monkeypatch.setattr(batch, "default_root", lambda: str(tmp_path))
    with patch.object(batch, "preflight", side_effect=AssertionError("network")):
        assert batch.main(["--dry-run"]) == 0
    assert "ZH → vi" in capsys.readouterr().out
    assert not (tmp_path / "translate/runs").exists()


def test_batch_resume_verify_failure_and_input_guard(tmp_path, monkeypatch):
    source = project(tmp_path)
    work = tmp_path / "translate/runs/gemma/vi/01"
    calls = []

    def fake_command(root, args, log):
        calls.append(args)
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("test log")
        if "make_digest.py" in args[0]:
            digest = root / "translate/digest/01"
            (digest / "units").mkdir(parents=True, exist_ok=True)
            (digest / "blocks.json").write_text(json.dumps({"items": 1}))
        elif "translate_unit.py" in args[0]:
            uid = args[args.index("--unit") + 1]
            (work / "units").mkdir(exist_ok=True)
            (work / "units" / f"{uid}.md").write_text(
                "# 1. Tiêu đề\nVăn bản\n" if uid == "00" else vi_item(uid)
            )
        elif "assemble.py" in args[0]:
            (work / "assembled.md").write_text("Draft")
        elif "verify.py" in args[0]:
            assert "--file" in args  # Never stamp a publication.
            return 1
        return 0

    monkeypatch.setattr(batch, "run_command", fake_command)
    first = batch.translate_chapter(tmp_path, "01", "vi", work, {}, overwrite=False)
    assert first["translated"] == 2
    assert not first["ok"]
    calls.clear()
    second = batch.translate_chapter(tmp_path, "01", "vi", work, {}, overwrite=False)
    assert second["skipped"] == 2
    assert not any("translate_unit.py" in args[0] for args in calls)
    source.write_text("New source")
    with pytest.raises(batch.BatchError, match="Inputs/model changed"):
        batch.translate_chapter(tmp_path, "01", "vi", work, {}, overwrite=False)
    original_state = json.loads((work / "resume.json").read_text())
    before = {p.name: p.read_bytes() for p in (work / "units").glob("*.md")}
    calls.clear()
    recovered = batch.translate_chapter(
        tmp_path, "01", "vi", work, {}, overwrite=False, resume_changed=True
    )
    assert recovered["skipped"] == 2
    assert not any("translate_unit.py" in args[0] for args in calls)
    assert before == {p.name: p.read_bytes() for p in (work / "units").glob("*.md")}
    state = json.loads((work / "resume.json").read_text())
    assert state["unit_fingerprints"] == dict.fromkeys(["00", "01"], original_state["fingerprint"])
    # Missing units are translated under the new configuration, not cached.
    (work / "units/01.md").unlink()
    calls.clear()
    recovered = batch.translate_chapter(tmp_path, "01", "vi", work, {}, overwrite=False)
    assert recovered["translated"] == 1
    assert recovered["skipped"] == 1
    state = json.loads((work / "resume.json").read_text())
    assert state["unit_fingerprints"]["01"] == state["fingerprint"]
    assert state["unit_fingerprints"]["00"] == original_state["fingerprint"]
    # Explicit recovery still refuses manually edited completed files.
    (work / "units/01.md").write_text(vi_item() + "Edit\n")
    saved_state = (work / "resume.json").read_bytes()
    with pytest.raises(batch.BatchError, match="Untracked or edited"):
        batch.translate_chapter(
            tmp_path,
            "01",
            "vi",
            work,
            {"max_tokens": 16384},
            overwrite=False,
            resume_changed=True,
        )
    assert (work / "resume.json").read_bytes() == saved_state


@pytest.mark.parametrize("keep_going", [False, True])
def test_main_reports_failures_and_keep_going(tmp_path, monkeypatch, keep_going):
    project(tmp_path)
    (tmp_path / "book/02-source.md").write_text("# 2. Source")
    monkeypatch.setattr(batch, "default_root", lambda: str(tmp_path))
    monkeypatch.setattr(batch, "preflight", lambda: {"model": "gemma"})
    calls = []

    def fake_chapter(root, nn, lang, work, settings, *, overwrite):
        assert root == tmp_path
        assert lang == "vi"
        assert work == tmp_path / "translate/runs/gemma/vi" / nn
        assert settings == {"model": "gemma"}
        assert not overwrite
        calls.append(nn)
        return {"chapter": nn, "ok": nn != "01"}

    monkeypatch.setattr(batch, "translate_chapter", fake_chapter)
    assert batch.main(["--keep-going"] if keep_going else []) == 1
    assert calls == (["01", "02"] if keep_going else ["01"])
    report = json.loads((tmp_path / "translate/runs/gemma/vi/batch-report.json").read_text())
    assert not report["publication"]
    assert not report["chapters"][0]["ok"]
