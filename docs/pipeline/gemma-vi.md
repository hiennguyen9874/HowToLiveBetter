# Gemma: translate the whole book into Vietnamese drafts

Use an already-running llama.cpp server. The source is **Chinese**, one digest
unit per call, processed sequentially. Vietnamese remains an unpublished pilot.
This runner never writes into `book/`, changes `translations.json`, or stamps
chapters complete. Passing integrity verify does not guarantee correct meaning.

## Configuration

From the repository root, Python >=3.11 is required. Make defaults to
`.venv/bin/python3`; use `make ... PY=python3` if using another Python environment.
No additional Python packages are needed by the HTTP client or batch runner.
The runner uses `fcntl` locking (Linux/macOS).

Set these keys in the gitignored `.env`:

```dotenv
HTLB_LLM_BASE_URL=http://127.0.0.1:8080/v1
HTLB_LLM_MODEL=gemma-4-31b-qat
HTLB_LLM_API_KEY=local
HTLB_LLM_TEMPERATURE=0.2
HTLB_LLM_MAX_TOKENS=4096
HTLB_LLM_TIMEOUT=300
```

The model must match an ID returned by `/v1/models`. An existing exported
`HTLB_LLM_*` variable takes precedence over `.env`; remove stale shell exports
if the preflight prints an unexpected configuration. Do not start the Hy-MT2
startup script or another listener on port 8080 while Gemma is running.

The client saves `message.content` only, not separate `reasoning_content`.
Reasoning can still consume the completion budget. Truncated responses are
rejected, never saved as successful units. If necessary, raise the token budget
and check the server's per-slot context capacity; input + reasoning + translation
must fit. Do not change model/template/settings halfway through a resumable run
without explicitly choosing a new run directory.

## Commands

```bash
# Preflight: server health, advertised model and configured token budget.
make translate-book ARGS='--check'

# List all Chinese chapters and draft destinations; no API calls or writes.
make translate-book ARGS='--dry-run'

# Optional first full chapter. Default stops on any chapter failure.
make translate-book ARGS='--chapters 01'

# Translate all chapters; keep going after chapter failures, then exit nonzero
# if any failed. Does not ignore or mark failed chapters successful.
make translate-book ARGS='--keep-going'
```

Alternatively, without Make:

```bash
PYTHONPATH=. python3 -m translate.ops.translate_book --keep-going
```

Default output:

```text
translate/runs/gemma/vi/
  batch-report.json
  01/
    units/00.md, 01.md, ...
    resume.json
    assembled.md
    digest.log
    unit-00.log, unit-01.log, ...
    assemble.log
    verify.log
  02/...
```

Logs and drafts are local/gitignored. Preserve or back them up before deleting
run directories. Run in a persistent terminal/tmux for a long book translation.
Do not concurrently regenerate digests or run another translation/repair process
against the same workdir. Batch runners serialize each other with a shared lock,
but legacy single-unit/digest commands do not participate in that lock.

## Resume and rerun

To explicitly keep completed units after changing token budget, timeout, client
or prompt, use:

```bash
make translate-book ARGS='--resume-changed --keep-going'
```

This translates **missing units only** and leaves tracked completed unit files
unchanged. Hash/structure checks still reject edited or untracked files. Each
unit retains its original configuration fingerprint; new units get the current
fingerprint. This deliberately creates mixed-configuration drafts and requires
human review: legacy state cannot prove the source/glossary remained unchanged.
Do not use this option after source changes unless you have independently checked
compatibility. Assemble/verify rerun, so assembled files and logs are regenerated.
It does not repair existing translations that fail numeric/CJK verification.


Press Ctrl+C to interrupt, then rerun the **same command**. Valid completed units
with matching fingerprints are skipped. Assemble/verify are rerun, including for
chapters whose previous verify failed. Source, prompt, glossary, rules, client,
translation code and settings are fingerprinted; changed inputs cause an explicit
error rather than mixing translations made under different configurations.

Untracked or manually edited unit files are not silently overwritten. A crash
between writing a unit and recording its resume stamp may leave an untracked
unit; preserve it and use a new run root, or explicitly retranslate that chapter.

```bash
# Retranslate one entire chapter (overwrites all its units, including edits).
make translate-book ARGS='--chapters 03 --overwrite'

# Preserve an old run while testing different settings/prompts.
make translate-book ARGS='--run-root translate/runs/gemma-v2/vi --keep-going'
```

Do not use `--overwrite` for a reviewed chapter unless you intend to discard its
unit edits. To reassemble and verify manually reviewed units without resume:

```bash
PYTHONPATH=. python3 translate/steps/assemble/assemble.py \
  01 translate/runs/gemma/vi/01 translate/runs/gemma/vi/01/assembled.md vi
PYTHONPATH=. python3 translate/steps/verify/verify.py \
  01 --lang vi --file translate/runs/gemma/vi/01/assembled.md --json
```

## Troubleshooting: observed 4096-token run

The saved `translate/runs/gemma/vi/batch-report.json` contained 34 chapters:
10 passed integrity, 18 stopped at truncated units, and 6 failed chapter verify.
A stopped chapter has unattempted later units; this is not a complete quality
scan of the entire book. Logs contain only the latest attempt, not API token
usage or partial responses from that run.

Truncated chapter/unit pairs:
`01/28 02/05 03/23 05/10 06/06 07/02 08/12 09/06 11/02
12/11 13/02 16/09 17/05 24/12 28/04 29/06 31/01 33/16`.
All report `finish_reason=length`, not HTTP errors or timeouts. The client
correctly refuses to save incomplete translations. The run requested 4096
completion tokens; the live server inspected afterward advertised one slot and
`n_ctx=65536`. This supports trying a larger completion budget, but old logs
cannot distinguish completion-budget exhaustion, context exhaustion, or runaway
output/reasoning. New truncation errors include API usage when available.

Verification failures:

| Chapter | Cause | Recovery |
|---|---|---|
| 10, unit 07 | Source formula `351.3 / 610.6` becomes `3513000 / 6106000`. This ratio is mathematically equivalent, but the gate requires the original bare operands too. | Retain the source formula with both operands explicitly in units of 10000 couples; keep correctly converted prose counts. Do not insert unrelated numbers. |
| 23, units 11 and 13 | Chinese terms remain in ordinary prose. | Translate the remaining terms; parenthetical originals and link targets are treated differently by the gate. |
| 25, intro 00 | `30.03.2026` is tokenized as decimal `30.03`, so day `30` appears absent. | Use `ngày 30 tháng 3 năm 2026`. |
| 26, unit 04 | Untranslated `备案` is attached to Vietnamese throughout five lines. | Translate it as ICP registration, keeping the Chinese jurisdiction. |
| 30, unit 13 | Source `一两百` folds to bounds `100` and `200`; Vietnamese spells these out as `một hai trăm`. | Fixed in verify: `lang=vi` now folds `một hai trăm` → 100 200, `hàng trăm nghìn` → 100000 and the scale words `nghìn`/`triệu`/`tỷ`/`nghìn tỷ` (`tỷ` = 10⁹, while 亿 = 10⁸). |
| 32, unit 10 | `28.10.2025` is tokenized as decimal `28.1`, so day `28` appears absent. | Use `2025-10-28` or separate day/month/year words. |

`number_added` and `number_less_frequent` messages are review warnings, not the
cause of these failures. Many additions are headings or spelled-out numbers
converted to digits, but each needs review. `no banned_calques` is informational:
Vietnamese has no configured calque check. Passing verify is not semantic proof.
For example, review chapter 26/unit 04's penalty conditions: the draft makes
fines conditional on failure to correct, whereas the source describes an order
to correct **and** a fine, then closure for refusal to correct.

### Safe recovery after code/prompt/settings changes

Back up the old run. Set a larger budget in `.env`, initially:

```dotenv
HTLB_LLM_MAX_TOKENS=8192
HTLB_LLM_TIMEOUT=600
```

Remove any stale shell exports overriding these values. Check server capacity
(input plus output must fit) and try the previously failing chapter first:

```bash
make translate-book ARGS='--check'
make translate-book ARGS='--run-root translate/runs/gemma-v2/vi --chapters 01'
# After inspecting that result, continue in the same new run root:
make translate-book ARGS='--run-root translate/runs/gemma-v2/vi --keep-going'
```

8192 is a starting point, not a guarantee. If truncation persists, inspect the
new usage diagnostics and server logs before increasing again. A larger budget
cannot fix a looping model. Do not silently accept partial output or disable
numeric/CJK checks. Existing resume fingerprints include client, prompt and
settings, so a changed budget or these fixes will intentionally reject the old
run without explicit recovery. The new root preserves all old drafts. To avoid
retranslating completed units instead, use `--resume-changed --keep-going` as
documented above; this accepts mixed-configuration drafts, not equivalent runs. `--overwrite` is an alternative only
when intentionally discarding the selected chapters' work.

For manual repairs, edit the relevant **unit** files in a backed-up draft,
then run the documented assemble/verify commands. Editing only `assembled.md`
is temporary: assembly replaces it. Edited units cannot be batch-resumed under
the old hashes; do not bypass this by manually rewriting `resume.json`.

## Review before publication

Read `batch-report.json` and each failed chapter's logs. Numeric integrity,
original tags and source preservation are checked against Chinese. Do not
mechanically insert missing numbers just to pass a gate.

For every chapter, compare Chinese and Vietnamese for omissions, denominator
changes, conditional populations, reduction BY versus TO, uncertainty, and
unsupported advice. The Vietnamese prompt locks currency/terminology and forbids
extra headings, but prompt instructions are not proof of factual accuracy.
Vietnamese LanguageTool/readability and Laya polish remain unvalidated; do not
claim those gates passed or run Russian/English substitutes.

Publication into `book/vi/`, manifest changes, removing `publication: pilot`,
site/README updates and independent review are separate work following the
ordinary publication checklist, with user approval. No automatic publication is
part of this command.
