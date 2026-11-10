# How these pages were rendered

Rendered 2026-11-10 21:19 IST by the P3b sub-orchestrator, from the working tree, not from a clean commit.

- **Commit:** `993edf4` (HEAD), plus uncommitted edits: 90 modified tracked files and 105 untracked paths in the checkout.
- **Edited paths the pages depend on:** `data/loanbook`, `samajh/amounts`, `samajh/extract`, `samajh/ops`, `samajh/rules`, `samajh/types.py`, `web/review`. New files not in the commit: `samajh/ops/chain.py`.
- **sha256 of `git diff HEAD` over those paths:** `7762c068d1e0a89039634b1b9ec7269868f0d15c133fac59df0a0dfe09c06045`. The same commit with the same diff gives the same pages, apart from the time each decision was recorded.
- **`samajh/rules` was being edited by another package (P3a) at the time. These pages must be rendered once more after the P3a work lands**; until then a count here may differ from what the code gives.

## What was run

1. `uv run python -m samajh.ops demo --state STATE` (the loan book in `data/loanbook`, seed 85; nine weekly draws; every call simulated text).
2. The 41 phone session folders of this machine were copied (case file, session log and recording only; the originals were not touched) into `STATE/sessions`, then `uv run python -m samajh.ops ingest --state STATE`: 0 session(s) on drawn loans, 7 outside the sample, 34 skipped. None of them was opened as a call on the loan book, so no phone call is an attempt in the sample on these pages.
3. Six reviewer decisions were recorded through the review API, with the same notes as in the earlier render (reviewer "Asha Reviewer (synthetic)"; every decision is a made-up example).
4. A review-only server (the review API and `web/review`, no phone routes, no Gnani key) on port 8097, then `node tests/ops/page_shots.mjs` twice: once for the first case in the queue (`case-*`), once for the phone call `20261110T103108-9f2e34f8dfdf` (`phone-case-*`).

## What the pages show

- Sold 200, sampled 80, completed within 30 days 64, referred 7, understanding gap 33; most common gap: Cover amount (20).
- 32 renders (four pages and the phone case, at 390 and 1280 px, light and dark): 0 with horizontal overflow, a console error, a banned word or a written-out undefined, NaN or null.
- The loan book, the customers and the simulated calls are synthetic. No share on these pages describes a real lender. No phone call is with a lender's customer.

## Files

`queue`, `case`, `attempts`, `report`, `phone-case`: `.html` (the rendered page), `-390-`/`-1280-` `light`/`dark` `.png`; `report.pdf`, `report-print.png`. `queue.json`, `attempts.json`, `report.json`, `draws.json`, `phone-case.json`: the API's answers. `dispositions.jsonl`, `outside.jsonl`: the store's files after the run.

The earlier render (committed at 4180556) showed 11 referrals of 64; `data/loanbook/README.md`, "The rendered pages", says what differs and why.
