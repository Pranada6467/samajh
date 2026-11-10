# P8 contract: the right-party check as a lender setting (DRAFT, 2026-11-10)

Status: **draft, nothing built**. P8 was paused on 2026-11-10 before any code was written (see `P8-report.md`).
Stage A is new files only. Stage B (the call, the server, the phone, the case file) waits for P2 round 4 and is
adjusted to what round 4 lands. Where this file and the code differ, the code wins.

Evidence for every choice: `identity-check-research.md` and claims ledger rows I1 to I8, IX1 to IX10. Coordinator
decisions of 2026-11-10 are marked **(decided)**.

## 1. The setting

`samajh.identity.IdentityPolicy` (frozen). No field holds free text, so no deployment can make the bot ask a
question the code does not already contain.

| Field | Values | Default | Meaning |
|---|---|---|---|
| `second_check` | `None` ("none"), `CheckKind.year_of_birth` | `None` **(decided)** | The one question asked after the name, or none |
| `attempts` | 1, 2 | 1 **(decided)** | Answers the second check will judge. Ignored with no second check |
| `prior_notice` | true, false | true **(decided)** | A written message before the call. Mocked in the browser demo |
| `call_back_line` | true, false | true **(decided)** | The spoken line "hang up and call the customer-care number on your papers" |

- The menu is `CheckKind`, an enum in code. It has one member. **Not built (decided):** a PIN-code check and a
  second item. No source shows either as practice in India (ledger I4).
- The menu can never hold a credential (OTP, PIN, password, CVV, account or card number, Aadhaar, PAN, a full
  date of birth, mother's maiden name) or a record value under test (kind, premium, payment source, cover, term,
  cancel window, consent, provider choice). Tests enforce both (section 5).
- The honest description is part of the setting (`describe(policy)`), is shown on the phone's demo page and is
  written into the case file:
  - none: "No second check. A person who answers yes to the name question and yes to 'are you <first name>
    yourself?' is treated as the borrower. This is a right-party check, not identity verification."
  - year of birth: "The call asks for the year of birth after the name (N attempt/s). A family member or anyone
    holding the borrower's details can answer it. This is a right-party check, not identity verification."

## 2. The record

The expected answer comes from the loan record and from nothing else: `year_of_birth` reads
`record.borrower.dob.year`. The three packaged records and the loan book already carry a synthetic date of birth.
The expected answer is never sent to the extraction model or the classifier, never put in a bot line, and never
written to the case file, a reviewer page or the case summary.

## 3. The call (stage B; adjusted to round 4)

**No second check (default).**
1. `right_party.ask`: "are you <first name>?"
2. A yes (round 4's ordinary confirmation) leads to the direct question, `right_party.reask`: "are you <first
   name> yourself?" A yes to that question passes **(decided: no first-person sentence is required)**. An explicit
   first-person claim at step 1 ("yes, speaking") already answers the direct question and passes.
3. Any relation word, other name, hedge or question at either step is not a pass: `wrong_party`, or the who-check,
   exactly as round 4 builds them.
4. Nothing names the lender, the loan or a product before the pass. After it: `disclosure.who`,
   `disclosure.not_sales`, `disclosure.recording`, `disclosure.never_ask`, [`verify.short` when `call_back_line`],
   `disclosure.go_ahead`; on yes, `context.loan`, `disclosure.rights`, `open_recall.ask`.
5. `speaker_confirmed` becomes true at the pass. The case file says on what basis (section 4).

**Year of birth (the lender's opt-in).** The round 4 call, unchanged, with `attempts` 1: tolerant of near-spellings
of the SAME year, one re-ask for a reply with no year, a wrong year or a guess ends the call. With `attempts` 2 a
wrong year or a guess uses one attempt and `second_check.reask` is asked once more; the reply-with-no-year re-ask
stays single; the second wrong answer ends the call as `second_check_failed`.

Outcomes are unchanged. No new outcome name.

## 4. What is recorded

`samajh.identity.IdentityRecord` in the case file: the policy in force, which check was used, attempts allowed and
used, whether it passed, whether the prior notice was shown (and that it was mocked), and one fixed sentence built
from templates. It has no field that can hold the expected answer or the words of a reply.

## 5. Tests that enforce the rules (stage A, `tests/identity/`)

1. No `CheckKind` name or value contains a credential word or the name of a record value under test.
2. For each kind, the expected answer does not change when every product and loan value under test changes, does
   not change when the day and month of birth change, and does change with the year.
3. `IdentityPolicy` has no text field; the parser refuses unknown keys, unknown kinds and free text.
4. Every line key a check names exists in each language's prompt file and passes the bot-line lint.
5. `IdentityRecord` has no field for an answer; its sentence holds no digit.
6. The prior-notice text passes the bans (a secret word only where it is denied), names no product and no record
   value, and holds no digit except the literal 1600.

## 6. The prior notice (mocked)

`samajh.identity.notice` renders a short written message per language from `data/notices/<lang>.toml`: who will
call, that the voice is automated, that it is a short feedback call and not sales, that the number starts with
1600, that the caller never asks for an OTP, PIN or password, and that the customer can check by calling the
customer-care number printed on their papers. It names the lender. It does not name the loan or a product (a
message can be read on a locked screen by someone else).

**Mocked:** the browser demo shows the message as a card ("SMS, mocked: not sent"). No message is sent. The 1600
series is named in the text and cannot be shown by a browser. Tamil and Kannada texts are `not human-reviewed`.

## 7. Server and phone (stage B)

- `samajh/server/settings.toml` gains `[identity]` with the four fields; `parse_policy` reads it.
- A session request may carry `identity` (the demo picker); the server validates it with `parse_policy` and
  answers 422 on anything outside the menu.
- `GET /api/identity/menu` lists the options with their descriptions; `GET /api/identity/notice` returns the
  rendered notice for a record and language. Both live in `samajh/server/identity_routes.py`.
- The phone's demo page: a picker for the second check with the description under it, and the notice card before
  the call when `prior_notice` is on.
