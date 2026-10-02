# Public Vietnamese preview (unreviewed)

The user explicitly accepted public **preview** distribution without the remaining
content reviews. This waives review only for an explicitly labelled draft; it
is not quality approval or permission to report unsupported gates as passed.
Vietnamese stays `publication: pilot`; `book/vi/`, the completion manifest and
Vietnamese ebook publication remain unchanged.

## Snapshot and build

Branch: `preview/vi-drafts`. The pilot/runner dependency was squash-merged
separately in the fork's PR #1 after GitHub CI passed. The preview-only commit
was then rebased onto the updated fork `main`, and PR #2 retargeted to `main`.
No PR targets the original author's repository.

- Tracked draft snapshots: `preview/vi/01.md` through `34.md`.
- Provenance: `preview/vi/snapshot.json` records assembled/snapshot hashes and
  pending review statuses. Warning insertion and relative-link corrections are
  the only transformations when taking this snapshot.
- Original units stay in gitignored `translate/runs/gemma/vi/`; the local backup
  archives described in [the review checkpoint](vi-draft-review.md) retain them.
- Generated static reader: `site/vi/preview/index.html` and `01.html`–`34.html`.
  It has a visible warning on every page, no JavaScript/CDN requirement and no
  search-engine indexing request. Public visibility does not imply approval.

Build from the repository root:

```bash
PYTHONPATH=. .venv/bin/python3 forge/site/build_vi_preview.py
make web-build
make check-content
make check-links
make ci
```

`make web-build` also builds the preview when snapshots exist. The Pages artifact
copies all of `site/` plus the separate `preview/vi/` Markdown snapshot directory,
so the reader will be available at `/vi/preview/` and raw snapshots at
`/preview/vi/` on a host serving that artifact. `make serve` allows local reading
at `http://127.0.0.1:8000/vi/preview/`.

For a separate static host, upload only the generated contents of
`site/vi/preview/` with its index at that host's root. This does not modify or
replace the main site. Preview content is intentionally not loaded into the
ordinary recommendation filters or counted as completed chapters.

## Selected deployment: main-site preview path

The user selected `/vi/preview/` on **their fork's** website, not a separate
host or a PR to the original author. Target repository:
`hiennguyen9874/HowToLiveBetter` (remote `origin`). Expected preview URL:
`https://hiennguyen9874.github.io/HowToLiveBetter/vi/preview/`.

The user approved commit/push/internal PR creation, enabled Actions for the
fork and requested continuation of the deployment using `gh`. Pages is
configured to build using GitHub Actions. Preparing/opening a PR **does not
deploy it**: publication follows branch → internal PR → green CI → squash merge
to the fork's `main`. The existing Pages workflow then deploys the tested
main-site artifact; verify the live preview after it succeeds.

The existing Pages workflow automatically deploys only after CI succeeds on
`main`. Its manual dispatch can deploy another ref, but it uses the **same
GitHub Pages environment** and can replace the whole live main site. It is not
an isolated branch-preview service. Do not dispatch it for this branch without
explicit approval of that replacement risk.

Deployment checklist:

1. Commit/push permission has been granted for the user's fork only. Never push
   to `upstream` or target its repository with a PR.
2. Keep the runner/tooling PR separate. Open the preview PR against the runner
   branch first; after the dependency is squash-merged, rebase the preview-only
   commit onto the fork's updated `main` and retarget its PR.
3. Open a PR adding the labelled `/vi/preview/` path to the main-site artifact.
4. Require green CI, review of tooling/scope and squash merge to `main`.
5. Confirm the Pages deployment succeeds and check the live index plus a direct
   chapter URL for warnings and working navigation.

Translation review remains waived for this preview only, not marked complete.
Do not use manual Pages dispatch to publish this feature branch.

No bypass of main branch protection or automatic ebook/full-publication promotion
is permitted. Run `make ci` before any push. Keep medical/legal risk notices
visible, including on direct chapter links; retain pending findings and accept
corrections in units before refreshing snapshots and integrity verification.
