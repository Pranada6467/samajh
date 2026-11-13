# P8 report: the right-party check as a lender setting (iteration 3, 2026-11-13)

**State: built and independently verified on typed text** (`references/reviews/iter3/verify-call.md`, parts 1 and 2).
Nothing here is tested on speech. The research behind the decisions is unchanged (`identity-check-research.md`,
ledger rows I1 to I8, IX1 to IX10). Where this file and the code differ, the code wins.

## What the setting is

A fixed menu in code (`samajh/identity/policy.py`). A lender picks from it; no field holds free text, so no
deployment can make the bot ask a question the code does not contain.

| Field | Values | Default |
|---|---|---|
| `second_check` | none, `year_of_birth` | none |
| `attempts` | 1, 2 (only with `year_of_birth`) | 1 |
| `prior_notice` | true, false (a written message before the call; **mocked** in the demo, never sent) | true |
| `call_back_line` | true, false (the "hang up and call the number on your papers" line) | true |

No PIN-code check, no second item, no two-check option. **The default treats a person who twice affirms being the
borrower as the borrower.** The setting's description, the case file and the demo page all say this, and say that
this is a right-party check, not identity verification.

- **none:** "are you <first name>?" → a yes → "क्या आप ख़ुद <first name> जी हैं?" → a yes passes. An explicit
  first-person claim at the first question passes at once. A relation word, another name, a hedge ("वही समझ लीजिए")
  or a question at either step is not a pass. No first-person sentence is required.
- **year_of_birth:** round 4's step, unchanged in tolerance: a near-spelling of the same year passes, a reply with no
  year gets one re-ask, a hedged year ("1984 के आसपास") is a guess and uses an attempt, a different year ends
  `second_check_failed`. With two attempts a second wrong answer ends the call.

**Where it is set.** `samajh/server/settings.toml` `[identity]`, read through `parse_policy` (anything outside the
menu fails at load). A phone session may carry a top-level `identity` object (422 outside the menu). The demo page
has a picker (None / Year of birth, attempts 1 or 2) with the description under it, and shows the mocked SMS card
("SMS, mocked: not sent") before the call. Routes: `GET /api/identity/menu`, `GET /api/identity/notice`.

**What is recorded.** The case file gains `identity` (which check, attempts allowed and used, passed, notice shown
and mocked, one fixed sentence; no field for an answer) and `identity_description`. If a takeover later ends the call
as a wrong party, the sentence says so.

**Where the year is kept.** The expected year never reaches a classifier prompt, a bot line, the case file, a
response or the extraction model (verifier: 95 + 176 logged classifier requests, 108 extraction messages). The
customer's reply to the year question is withheld in the case file, the responses and the Batch segments that
overlap it in time. **Not withheld:** the call audio, the on-disk dialogue state (`session.json`), and the demo
player's cheat sheet (`/api/records`, "born 1984"). Batch withholding is by time window, so a segment that drifts off
the turn on real audio would keep the words (not tested).

## Verified (verifier's wording, typed text only)

- With no second check, 16 of 16 genuine borrowers passed (classifier live), and 16 of 16 third parties at the
  opening did not pass in each arm, with nothing named before the pass.
- The default treats a person who says yes twice as the borrower: 5 of 5 such false claimants passed. A third party
  who knows the year passes the year check (3 of 3).
- With two attempts, 5 of 5 pairs of wrong years ended the call.
- 14 invalid `identity` forms (free text, `pin_code`, `mothers_maiden_name`, attempts 3, nested in params, …) got 422.
- Six mutants adding a credential or record-value check to the menu were caught by the menu tests.

## Built, not verified

The demo page was not opened in a browser by the verifier (the builder saw the idle page in headless Chrome only;
no call placed through the picker). Two attempts were not exercised live. The notice text has no fluent reader;
Tamil and Kannada notices are `not human-reviewed`.

## Known limits

- With `year_of_birth`, a customer who answers the name question with an explicit claim hears the lender named
  before the year, and `end.check_failed` names it again (verifier C-y08; not fixed).
- The bot-line lint still lets "अपनी माता जी का मायके वाला नाम बताइए" through: the lint is a word list, so a person
  must read any line change.

## Credits and spend (whole CALL package)

9.82 estimated Gnani credits (ledger 310.794 → 320.611): 10 + 6 new bot-line clips and 4 Batch jobs; replays from
the cache. OpenRouter about US$0.03 in all (builders and verifier).
