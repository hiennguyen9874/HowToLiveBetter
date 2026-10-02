# Vietnamese draft review checkpoint

Vietnamese remains an unpublished pilot. This checkpoint is **not** publication
approval or a complete semantic review. See [Gemma workflow](gemma-vi.md) and
[pilot scope](vi-pilot.md). The approved chapter 01 sample covers only intro and
items 1–3; it is not the full chapter.

## Drafts and recovery

The full-book draft set inspected is `translate/runs/gemma/vi/`, not the partial
`translate/runs/active/vi/01/` pilot. These paths are gitignored. No translation
API calls, `--overwrite`, source changes, resume-hash rewrites, manifest changes,
publication, commits or pushes were performed during this checkpoint.

Local backups, gzip-tested, outside the repository:

- Before assembly/edits: `~/translation-backups/gemma-vi-20261002T044104Z.tar.gz`
  SHA-256: `9f6603f63f649f4efb09bf37ebc85b9918467cbc1ca3d371f31559081d71ed91`.
- After repairs: `~/translation-backups/gemma-vi-reviewed-20261002T044503Z.tar.gz`
  SHA-256: `ad4ebf04c18e191e8eedfd28356da0096a722e24c28cc28a04963b6a00d7cc1b`.

These are local recovery copies, not off-host backups. Pushing a Git branch does
not preserve them. Manually edited units no longer match old resume stamps;
do not bypass that protection by rewriting `resume.json`.

## Integrity inventory

The old `batch-report.json` said 18/34 passed. Reassembling all 34 chapters from
the current `units/` and verifying with explicit `--lang vi --file` gave 33/34:
only chapter 01 failed, for absent `95.2`. Unit hashes were unchanged by this
initial assembly/verification. Original batch report and logs were preserved;
new checks have separate reports.

After the repairs below, **34/34 pass assemble and integrity verify**. Warnings
about added/less-frequent numbers remain unreviewed; a pass is not proof of
meaning, completeness, grammar, medical safety or legal accuracy.

Local audit evidence (gitignored):

- Before edits: `translate/runs/gemma/vi/review/20261002T044129Z/`.
- After edits: `translate/runs/gemma/vi/review/20261002T044351Z/`;
  `inventory.json` includes per-unit SHA-256 hashes, and per-chapter logs and
  structured verify results. Chapter 26 was refreshed after lexical corrections.

## Source-grounded repairs

### Chapter 26, unit 04

Edited `26/units/04.md`, then reassembled and verified, not just `assembled.md`.
Both plain-language and benefit fields now state: order to correct within the
specified period **and** a 10000 yuan fine; closure **if correction is refused**.
The homepage ICP-number penalty also now preserves an order to correct **and**
a 5000–50000 yuan fine, without introducing a failure-to-correct condition.
The nationwide scope explicitly means China. Licence and data-centre colocation
terminology were tightened against the Chinese unit.

A second assistant compared this unit to the Chinese and found the penalty
sequence and amounts preserved. This is not native-editor approval, legal advice
or independent validation of current Chinese statutes.

### Chapter 01, unit 22

The Chinese `95.2% CI 21.8–62.5` is **not an error**. The cited Bonten et al.
2015 abstract explicitly reports `45.6%; 95.2% confidence interval [CI], 21.8 to
62.5`, separately from the invasive-disease result `75.0%; 95% CI, 41.4 to 90.8`.

- DOI: <https://doi.org/10.1056/NEJMoa1408544>
- PMID: <https://pubmed.ncbi.nlm.nih.gov/25785969/>
- Retrieved abstract: Europe PMC core record for PMID 25785969; local evidence:
  `review/20261002T044129Z/ch01-unit22-source.json` under the draft root.

Restored the Vietnamese CI level from 95% to 95.2%, and corrected the age
threshold from over 65 to **65 or older**. No Chinese edits or invented numbers;
no source-error translator note is warranted.

## Remaining review and proposed Vietnamese quality process

**Pending user/native-editor agreement**, use this human-review process rather
than claiming unsupported automated checks passed:

1. Compare every unit with Chinese. Record omissions, unsupported advice,
   numbers/units, denominators, eligible populations, conditions, uncertainty,
   and reduction **by** versus **to**. Classify and explain every numeric warning.
2. Have an independent proficient Vietnamese reader review the complete text
   for grammar, terminology, clarity and naturalness; track chapter/unit,
   finding, proposed correction, source evidence, reviewer and decision.
3. Flag medical and legal units for appropriately qualified review, especially
   dosage, contraindications, age thresholds, jurisdiction and penalty triggers.
   Source inaccuracies must be researched and transparently annotated in the
   translation, never silently repaired in Chinese or padded to satisfy verify.
4. Apply accepted corrections to `units/`, reassemble, reverify and retain a
   reviewed snapshot plus issue/approval ledger. Unresolved substantive findings
   block publication.

LanguageTool has no configured Vietnamese mapping; readability is uncalibrated;
Laya polish is unvalidated for Vietnamese. These checks are **unsupported or
pending**, not passed. No Russian/English substitute was used. Any proposed
Vietnamese automated tool must first be evaluated on reviewed Vietnamese samples,
including deliberately seeded meaning/grammar errors and false-positive checks.
Starting a service is not validation. Assistant review does not satisfy the
independent Vietnamese-reader or domain-expert requirement above.

Keep a tooling PR separate from publication. CI and explicit user permission are
still required before any tooling push/PR. Publishing `book/vi/`, completing the
manifest, removing pilot status and finishing README/site require content and
quality-process approval followed by the ordinary publication gates.
