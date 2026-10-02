# Vietnamese pilot: chapter 01

## Scope and state

Vietnamese (`vi`) is registered as `publication: pilot`. It is not a completed translation. The source chapter currently has 36 items. Only intro 00 and items 01–03 were translated by local Hy-MT2 Q8, then reviewed against Chinese and edited.

- Readable pilot: [vi-ch01-pilot.md](vi-ch01-pilot.md).
- Front matter: [README.vi.md](../../README.vi.md).
- Published chapters: none; `book/vi/` is intentionally empty.
- Manifest: `translations.json`, chapter 01 `in_progress`, `verified: null`.
- Local workdir: `translate/runs/active/vi/01/` (gitignored).
- Original model output: `raw-units/`; edited units: `units/`.

## LLM configuration

The server at `127.0.0.1:8080` runs the official Hy-MT2-30B-A3B Q8 GGUF. It was restarted with **one slot and 16384 tokens of context**, verified using `/props`. Previously two slots shared a 10240-token budget, leaving 5120 per slot.

`.env` contains the exact model ID returned by `/v1/models`, the local `/v1` URL, API key placeholder `local`, and temperature `0.2`. No cloud model was used.

The startup script supports both `~/llama.cpp/build/bin/llama-server` and the installed `llama server` launcher. To apply `.env` startup settings after stopping the current server:

```bash
set -a
. ./.env
set +a
bash translate/steps/translate/start-llama-server.sh
```

Do not start another listener on 8080 while the server is running.

## Reproduce the pilot

```bash
make digest CH=01

# This overwrites the unit output; preserve reviewed units first if rerunning.
for unit in 00 01 02 03; do
  PYTHONPATH=. .venv/bin/python3 \
    translate/steps/translate/translate_unit.py \
    --nn 01 --unit "$unit" --lang vi \
    --out-dir translate/runs/active/vi/01 || break
done

# Human review and fixes happen in units/, not the Chinese source.
PYTHONPATH=. .venv/bin/python3 translate/steps/assemble/assemble.py \
  01 translate/runs/active/vi/01 \
  translate/runs/active/vi/01/assembled.md vi --items 1,2,3

PYTHONPATH=. .venv/bin/python3 translate/steps/verify/verify.py \
  01 --lang vi --file translate/runs/active/vi/01/assembled.md \
  --items 1,2,3 --json
```

The checked-in readable pilot has relative links adjusted for `docs/pipeline/` and an explicit partial-chapter banner. The local assembly retains chapter-oriented links intended for eventual `book/vi/` output.

`--items` verification compares with the same selected Chinese items plus the intro. It never produces a completion stamp; partial assembly into `book/` is rejected. Without `--items`, full-chapter verify correctly fails because 33 items are missing.

## Quality review

The first model draft was fluent but **not publication-ready**. Important corrections:

1. Item 1: `下降 45%` means risk decreases **by** 45%, not **to** 45%.
2. Item 1: the 50% seat-belt statistic applies only where belt status was known; the model dropped that condition in two fields.
3. Item 3: restored the omitted final plain-terms sentence about Chinese CO deaths and deaths at home during winter.
4. Item 3: corrected the denominator of the monthly percentages. 72.59%, 67.42% and 66.48% are the proportions of deaths occurring **at home within each month**, not each month’s share of annual deaths.
5. Item 3: corrected “40% of fires” to the original’s “40% of people were asleep”.
6. Fixed the intro back-link and added the unofficial-translation status; normalized decimal punctuation and thousands formatting for numeric checks.

Item 2 retains the mortality/head-injury figures and the limitation that motorcycle findings are extrapolated to electric bicycles. No Vietnamese prices, laws or emergency numbers were substituted.

Result after editing: selected-item integrity verify passes; 3 headings, 3 original tags and 3 original source lines are preserved. Style check reports zero configured warnings. Numeric warnings remain because Chinese phrases such as 六成/四成/七成 are rendered as 60%/40%/70%, and the pilot banner adds scope numbers. These are explained transformations, not new research facts.

This is an assistant source-comparison review, **not an independent native-editor or medical review**. The tiny style pack is not a complete Vietnamese quality model.

## Gates and limits

- Pilot integrity verification is not full-chapter verification.
- LanguageTool has no configured `vi` mapping. Its CLI now fails explicitly for unsupported locales rather than silently reporting zero checks.
- Readability is not calibrated for Vietnamese and returns exit 2; no English/Spanish formula is substituted.
- Laya polish was not run or validated for Vietnamese. These remaining gates must be resolved before publication.
- Content gates still check all locale filenames/CJK/empty fields. Full-corpus parity and corpus badges do not apply to explicit unpublished pilots; a pilot with chapter files or manifest completion claims is rejected.
- The `/vi/` page is generated as a preview with an explicit in-progress notice, not a completed book. No Vietnamese OG image or ebook was generated.

## Validation results

- `make ci`: passed (tests, integration, lint, links, content, Pages build and artifact).
- Unit suite: 392 passed, 2 skipped, 2 expected failures; 3 subtests passed.
- Ebook manifest tests: 10 passed; unpublished pilots are excluded.
- Selected-item verify: passed; full-chapter verify: exit 1 as expected.
- Style: zero configured warnings. LanguageTool and readability: exit 2, explicitly unsupported.
- Default bulk waves/quality and ebook builds skip pilot locales; explicit `vi` commands remain available for development.

## Next step

Review the sample with the user/native editor. If approved, translate the remaining 33 items sequentially, review every number/condition, assemble without `--items`, and run the full verify gate. Before publication resolve Vietnamese grammar/clarity validation, remove `publication: pilot`, complete the README/chapter corpus and pass the ordinary publication gates. Do not mark `complete` or commit without user approval.
