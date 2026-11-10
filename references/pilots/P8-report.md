# P8 report: the right-party check as a lender setting (paused 2026-11-10)

**State: research done; the build is not started.** The coordinator paused the package to save usage. No code,
test, prompt line or page exists for P8, and no existing file outside `references/claims/` was changed. No Gnani
credits and no LLM calls were used. Nothing was verified, because there is nothing to verify.

## The norm, in five lines (sources: `identity-check-research.md`, `references/claims/findings-F.md`)

1. No RBI, TRAI or IRDAI text we found says how to confirm who is on an outbound call (ledger I1; F1.1, F1.9).
2. No Indian lender or insurer publishes the data points, their count or the attempts it uses on an outbound call (F2.1, F2.6).
3. Firm, from primary texts: loan matters only with the borrower (E5.4); never ask for a credential (F1.3); the customer checks the caller by the 1600 number series or by calling a number they already hold (E1.8, F1.4, F4.10).
4. Soft, from vendor pages only: confirm the name, then at most one low-sensitivity item, usually date of birth; no retry limit is stated anywhere (I4; F3.1 to F3.7). Four institutions tell customers not to give a date of birth on a call (I3; F2.5).
5. A spoken knowledge answer is weak: family knows it, a leaked record holds it, and a blind guess at a birth year is about 2% to 5% (our arithmetic) (I5, I8; F4.1, F4.7). So there is no single norm, and none is claimed.

## Decisions in force (coordinator, 2026-11-10)

- Default: no second check, with the prior-notice message and the call-back line on. The default treats a person
  who affirms being the borrower as the borrower; the setting, the case file and every report must say so (ledger
  I1, I4, IX1).
- With no second check: a yes to the name question leads to the direct question ("are you <name> yourself?") and a
  yes to that passes. No first-person sentence is required. A relation word, another name, a hedge or a question at
  either step is not a pass. Third parties learn nothing before the pass.
- `year_of_birth` is the lender's opt-in: one attempt by default, settable to two. Keep round 4's tolerance of
  near-spellings of the same year and of a reply with no year; do not loosen it.
- Not built: a PIN-code check, a second item.
- Verification, when the build exists: one narrow Opus-high check by a subagent that wrote none of the code (about
  15 new inputs per group for the default, about 10 per group for `year_of_birth`; classifier live and classifier
  failing; the menu-guard test; a read of the new lines). No recheck round.

## What exists

- `references/pilots/identity-check-research.md`: the two-page research note.
- `references/claims/findings-F.md`, `references/claims/sources/F/` (local only) with `INDEX.md`: 47 findings; 208
  quoted spans pass `check_quotes.py F`.
- `references/claims/claims-ledger.md`: Part 1 rows I1 to I8 and IX1 to IX10; Part 2 group F. `check_quotes.py`
  and `build_ledger.py` know group F. (Run over all groups, the quote check also reports three older group D
  quotes that no longer match `DESIGN.md`; P8 did not touch them.)
- `references/pilots/P8-contract.md`: the draft specification for the build.

## What remains, and the next step

Everything in `P8-contract.md`. **Next step:** start one Opus-medium builder on contract sections 1, 2, 4, 5 and 6
plus the two routes of section 7, in new files only (`samajh/identity/`, `data/notices/`,
`samajh/server/identity_routes.py`, `web/notice.js`, `web/notice.css`, `tests/identity/`). When P2 round 4 has
landed, integrate section 3 and the rest of section 7 on top of it, list every new or changed bot line (key, hi,
hi-en) for the user's wording review, voice any new fixed line (at most 20 estimated credits), run the whole test
suite, then the one narrow verification, saved unchanged as `references/reviews/iter2/verify-P8.md`.
