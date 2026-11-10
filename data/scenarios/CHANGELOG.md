# Changelog: scenario set

Every freeze of `gold.jsonl` and `calls.jsonl` is listed here with its hashes and the reason. A change to gold after the first freeze names the scenario, the old and new gold, and the evidence.

## Version 1, frozen 2026-11-10

- `gold.jsonl` sha256 `08b147008d07c0ec917bee3ee16f16e77fa9abd24a5defbee014b6b712264405`
- `calls.jsonl` sha256 `c41b56f65555e04e93f3f7dac3875db5aaded3ddc18b4cc6512a9c3533c4a198`
- 144 scenarios: 36 base cases in hi, hi-en, ta and kn.
- Gold was written by hand from DESIGN.md section 6 and the coordinator's decisions of 2026-11-10. The rule engine had not been run on any scenario when this version was frozen.

## Version 2, frozen 2026-11-10

- `gold.jsonl` sha256 `d002423a32eeb7c020526e01cf0b21083566ad2e593a67a30e1c9d7f0154f152`
- `calls.jsonl` sha256 `b10111dfc64e5dd74061f553cdbf666db916491f9ce3ef647ae3d0778fad29f5`
- 144 scenarios, as before. No audio and no LLM extraction had been run on version 1.

What happened between the versions, in order:

1. Version 1 was frozen.
2. An independent model reviewer (Fable, high effort, no access to the rule engine) wrote its own verdict for all 36 base cases with gold hidden, then compared. It agreed with the case verdict in 36 of 36 and with the full flag and unclear sets in 35 of 36. It also read 38 scripted calls in full across the four languages.
3. In parallel, version 1 was compared with the rule engine on perfect beliefs: 136 of 144 scenarios agreed on verdict and flag set. The 8 that differed were U09 and U10 in each language.
4. `DESIGN.md` section 6 was rewritten by another work package while version 1 was being written. Version 1 gold was written against the earlier text. The lines cited below are from the current text.

### Gold changes (2 base cases, 8 scenarios)

| Case | Rule | Version 1 | Version 2 | Evidence | Found by |
|---|---|---|---|---|---|
| U10 | `consent` | unclear | flag | `DESIGN.md` section 6, `consent`: "A customer who says they do not know what they agreed to buy → flag (medium)" | Reviewer; the engine comparison showed the same |
| U10 | `belief_mismatch` | unclear | flag | Section 6, `belief_mismatch`: "'I don't know' is a flag (low)" | Reviewer; the engine comparison showed the same |
| U10 | `kind` | unclear | flag | Section 6 is silent on a customer who does not know what the product is. Every other understanding rule in section 6 flags "unaware", "unsure" or "I don't know" (`cover`, `term`, `cancel_window`, `consent`, `belief_mismatch`). **Our reading**, for the coordinator to confirm | Engine comparison; the reviewer called it unsettled |
| G01 | `belief_mismatch` | not flagged (the customer said the money does not come back) | flag (the customer says they do not know whether it comes back) | The belief itself changed. The reviewer found the version 1 line implausible for a customer debited two lakh without consent. With "I don't know", section 6 flags (low) | Reviewer |

U10's case verdict is unchanged (`flag_for_review`). G01's case verdict is unchanged.

### Gold kept against the rule engine (2 base cases, 8 scenarios)

| Case | Rule | Gold | Engine | Evidence |
|---|---|---|---|---|
| U09, U10 | `premium` | unclear | flag (medium) | Section 6, `premium`: "not stated → `unclear`". A customer who says "I don't remember the amount" has not stated it. The reviewer read the line the same way. The engine treats a clear "I don't know" as a flag. Reported to the coordinator; the engine is not ours to edit |

### Script changes (no gold effect)

- U10 consent line named a method ("signed some papers") that contradicted the record, the `told` text and the extraction. Now: "I don't know what I said yes to." The yes/no "unsure" consent line changed the same way.
- C03 answered three questions a bare yes can answer (required, cancel, money back) with "yes, absolutely", which reads as an answer. Those slots now use deflections with no yes or no in them ("whatever the bank did"). The gold rationale for C03 was reworded to match.
- G02's story changed so the customer's lines agree with each other: the officer described the cover and never asked for agreement. On the yes/no call G02 now says yes to "the terms were explained"; the outcome is still `not_confirmed`.
- The guaranteed-return line no longer says "back after three years", which read as a second claim (U08, B02).
- G01 no longer says "I paid two lakh"; a customer who did not agree says the amount "was deducted" (G01, G02).
- A customer who forgot the amount (U09) and one who never knew it (U10) now use different lines.
- Customers of an NBFC no longer say "the bank people said".
- Tamil and Kannada wording fixes the reviewer was confident of: `req.no_soft`, `term.dont_know`, `consent.no_method`, the Tamil bot question on "required" (tense), a Kannada double dative.
- C03 `told`, B01 `yes_no_basis` and the G02 template text were corrected. U05 and R01 gained the tag `flag-on-informed-customer`.

### Reviewer findings not acted on

- A consent given to a misdescribed product (U08, V04, V06, C02) stays unflagged, and a product recalled under the wrong name stays matched to the record. Both are documented as our readings in `README.md`.
- U01-ta: the amount parser reads "ஒரே" ("only once") as the number 1 and refuses the turn. The sentence is natural and was not changed. Reported as a parser defect.
- V04, V06 and G01 give a mildly implausible yes to one closed question after a no to an earlier one. The outcome is `not_confirmed` either way.

## Version 3, frozen 2026-11-10

- `gold.jsonl` sha256 `14e49b58929c368e710709c8a93cc88e8852cead5ac89bbcde72c62be422e5dc`
- `calls.jsonl` sha256 `b10111dfc64e5dd74061f553cdbf666db916491f9ce3ef647ae3d0778fad29f5` (unchanged from version 2: no script, record or belief changed)
- 144 scenarios, as before.
- **This change was made before any audio or LLM extraction was run on the set.** Nothing had been scored against version 1 or version 2.
- **It resolves a disagreement between gold and the rule engine in the engine's favour.** Version 2 gold disagreed with the engine on 8 scenarios, and version 3 gold takes the engine's reading on all 8: U09-hi, U09-hi-en, U09-ta, U09-kn, U10-hi, U10-hi-en, U10-ta, U10-kn. A reader should know that agreement of 144 of 144 was reached by changing gold, on a coordinator decision, after the comparison was seen. The gold was still written by hand in `samajh/scenarios/cases.py`; the build does not call the engine.

### The decision (coordinator, 2026-11-10)

1. **Premium "I don't know" is a flag.** A customer who says they do not know what the product cost has stated a lack of understanding of a feature, which is what RBI paragraph 85Y (101Y for an NBFC) probes. Gold is a `premium` flag (medium), not unclear. Only silence, a question not asked, or an unusable answer is unclear. This replaces the version 2 reading of `DESIGN.md` section 6 ("not stated → `unclear`"), under which "I don't remember the amount" counted as not stated.
2. **Kind "I don't know" is a flag.** Confirmed. Gold has said so since version 2 (U10), where it was marked as our reading. No gold change.

### Gold changes (2 base cases, 8 scenarios)

| Case | Scenarios | Rule | Version 2 | Version 3 | Case verdict |
|---|---|---|---|---|---|
| U09 | U09-hi, U09-hi-en, U09-ta, U09-kn | `premium` | unclear | flag | `unclear_needs_human` → `flag_for_review` (product verdict the same) |
| U10 | U10-hi, U10-hi-en, U10-ta, U10-kn | `premium` | unclear | flag | `flag_for_review`, unchanged. `bundling` stays unclear |

Two fields follow from the U09 change and nothing else was touched:

- U09 `scenario_class` moved from `near_miss` to `violating`. The model requires the class to be `violating` exactly when gold flags the target rule, and U09's target rule is `premium`.
- The `rationale` text of U09 and U10 was rewritten to state the decision.

Not changed: U09's `customer_state` stays `informed` and its tags stay `("dont-know",)`. It is now a third informed customer whom the rules flag, next to U05 and R01, but it does not carry the tag `flag-on-informed-customer`. Left for the coordinator, because the instruction was to change nothing else.

### Rule engine agreement after the change

- `beliefs` path: 144 of 144 (version 2: 136 of 144).
- `extraction` path: 144 of 144 (version 2: 135 of 144). The ninth scenario was U01-ta: the amount parser read "ஒரே" ("only once") as the number 1. The parser was fixed by its owner; the scenario text did not change. The test that pinned the defect as a known exception now expects no disagreement on either path.
