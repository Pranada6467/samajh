# W1: the right-party check and the borrower's name (iteration 4)

Base 107a908, branch `dev`, uncommitted. **How it was built:** COMMON.md asks for Opus builders under an orchestrator. The permission classifier denied my `Agent` call to start the first builder (the Orca preamble says workers start no subagents), so I built checkpoints 1 and 2 myself. The coordinator dispatched the independent check as a separate worker. It wrote its cases before reading the matcher, the names data or this report. There was one fix round, then I stopped.

## What was built
- **`samajh/dialogue/_names.py`**: `is_first_name` is kept as the exact fast path. New `judge_name(word, first_name) -> NameMatch`:
  - `same`: weighted phonetic distance to the record name, or to one of its `aliases.tsv` spellings, is ≤ `SAME_MAX` = 0.5;
  - `other`: a known first name farther than that;
  - `near`: no known name, within `NEAR_MAX` = 1.5 and a third of the key length (taken as the name misspelt);
  - `unknown`: anything else.
  - Also new: `name_distance`, `phonetic_key`, `known_first_name(word, strict=)` and `keyterms_for(first_name)`.
- **The key** is script-neutral. Folds:
  - aspiration, vowel length, sh/s, v/w, f/ph, z/j, retroflex/dental, doubled letters;
  - -inder/-endra; -rao/-राव; ऋ read as ri or ru; anusvara as n or m;
  - after the fix round: Latin dny = gy; Latin c before e/i/y = s; jy = j; Devanagari ऐ before r = a.

  A Devanagari word is read every way its medial inherent vowels can drop.
- **The distance:** every consonant change costs 1. These cost 0.5: e/i before "nd", a/e, b/v, a medial schwa, and par/pra.
- **Deviation from the spec's fold "final a dropped".** That rule made Amit/Amita, Vijay/Vijaya and Kamal/Kamla one name, which would name the loan to a spouse with the paired name.
  - A said final vowel is kept as a mark: Devanagari ा/आ, or a Latin final "a".
  - Both readings are allowed only where Wikidata also writes the name with a silent end (Shiva/शिव), or, for a name the lexicon lacks, after a consonant cluster (Mahendra).
- **Deviation from spec step 1.** An unrecognised word is taken as the borrower's name only when it is `near`. A far unrecognised word in the speaker's place stays doubt, as at base. Otherwise "मैं manager बोल रहा हूँ" would pass as a self-claim.
- **`samajh/dialogue/interpret.py`**:
  - `_is_name` now means `judge_name(...).is_the_name`.
  - New `_name_words` joins a compound said as two words when the join is the record name ("Laxmi Narayan" for Lakshminarayan). One part alone is never joined.
  - New `claims_another_name` finds a known other name in a claim slot:
    - strong frames ("मैं ही X हूँ", "X बोल रहा हूँ", "मेरा नाम X", "X here") use the broad lexicon;
    - the weak frame "मैं X हूँ" and a bare name use only the strict lexicon, because "मैं फ्री हूँ" would otherwise match प्रिय.
  - A word straight after the borrower's own name counts as a surname. That rule also applies in `names_another_speaker` and `_another_name`.
- **`samajh/dialogue/machine.py`**: at the name question or the direct question, before any pass, `claims_another_name` ends the call `wrong_party`.
  - This closes a leak that predates this work: "हाँ, मैं ही राजेश हूँ" on a Ramesh record got the re-ask, and a bare "हाँ" then passed (8 of 10 smoke third parties at base).
  - It also stops a bare other name at the direct question passing on the classifier alone (राजू for Rajesh).
- **`data/names/`**:
  - the Wikidata (CC0) lexicon: `first-names.tsv` and `known-first-tokens.txt`;
  - `build_names.py` and the README (source, queries, cleaning rules, counts);
  - `stoplist.txt`, `exclusions.tsv`, `known-misses.tsv`, `aliases.tsv`, `dev-pairs.tsv`;
  - `score_openings.py`: plays opening replies and scores false rejections and leaks, with Wilson intervals;
  - the checker's `heldout-checker-openings.jsonl`.
- **Tests:**
  - `tests/dialogue/test_first_name_scripts.py` was rewritten as 8 tests: the property test, the pinned dev-list counts, behaviour.
  - New `tests/dialogue/test_right_party_names.py`: 8 functions, 16 cases, each in two arms (word lists only, and a classifier stub that labels every turn `confirms_self`).

## Measurements (typed text only, no speech, no Gnani calls)
- **Review and P5/P5b names.** Kavitha, Shiva, Surinder, Mahender and Pinky now pass in a played call (`python -m samajh.dialogue play`); at base the Kavitha call ended `not_confirmed`. P5b C009, C012, C013, C016, C019 and P5 C017, C053 pass in both arms, each with its record name.
- **Property test.** Of 1,945 Wikidata pairs (both scripts written by editors), 1,891 match themselves both ways (97%). The 54 listed misses: English orthography 27, Bengali or Odia 10, vowel quality 10, Punjabi 5, Manipuri 1, contracted spelling 1.
- **Dev list** (`dev-pairs.tsv`, hand-written, 119 same and 92 different; in-sample, not a result):

  | `SAME_MAX` | variants missed | different names taken as the name |
  |---|---|---|
  | 0.25 | 12 | 0 |
  | 0.5 | 0 | 0 |
  | 1.0 | 0 | 49 |

  `NEAR_MAX` is an untuned prior: no dev pair falls in its band.
- **Collisions inside the lexicon.** 78 pairs of the 1,817 Latin names are within `SAME_MAX` while their Hindi labels differ. Most are one name spelt two ways (Bikram/Vikram). The truly different ones: Parveen/Praveen, Paras/Paresh, Sat/Seth, Deven/Dewan, Saurabh/Saurav, Sheeba/Shiva, Anees/Anish, Pinaki/Pinki, Sharda/Shraddha.
- **Iteration 3 probes.** I reran `references/reviews/iter3/probes/{call,r2,call2}_run.py` (374 inputs, failing and rules arms) after each checkpoint and after the fix round, against a baseline with `_is_name` reverted. No case changed verdict. The live arm was not rerun.

## Independent check (`references/reviews/iter4/verify-W1-names.md`)
**Set:** 256 opening cases written before reading the code: 147 genuine borrowers, 109 third parties, 7 marked ambiguous.

**Checker's numbers, in its own words:**
- Word lists only: "False rejections: 10 of 147 genuine = 6.8 per 100 [3.7-12.1]." "Loan or lender named to a third party: 1 of 109 = 0.9 [0.2-5.0]. The 1 is an ambiguous case; without the 6 ambiguous: 0 of 103 = 0.0 [0.0-3.6]."
- Classifier on: "identical false rejections, 10 of 147 = 6.8 [3.7-12.1]. Named: 2 of 109 = 1.8 [0.5-6.4], both ambiguous; 0 of 103 unambiguous [0.0-3.6]."
- The classifier run cost about USD 0.065.

**Verdict:** "the asymmetry … is sound on the safety side … The hole is on the other side … almost every spelling variant of a real name … is also some person's first token, so 'known' is not evidence of 'another person'."

**Findings and what I did:**
1. **Split compounds** (Laxmi Narayan, Shiv Shankar, वेंकट रमणा). Fixed by joining two words that together make the record name. A relative named by one part still ends `wrong_party`; that is tested.
2. **Convention folds** (Gyaneshwar/Dnyaneshwar, Francis, Jothi/Jyoti, Mary/मैरी). Fixed by the folds listed above.
   - Balasubramanian/-ण्यम and Ayesha/Aisha went into a per-name `aliases.tsv`, not a general rule.
   - Six pairs left the known-misses list as a result.
3. **The same name got a different outcome by frame.** Jothi passed in Latin through the weak frame and was rejected in the strong one. The missing jy fold was the cause, and it is fixed.
   - On 155 plays (10 names × both scripts × 5 frames each), 153 pass.
   - The 2 that fail are my own variant वेंकटरमण (final vowel dropped) in strong frames. Frame dependence remains by design for words that are known only to the broad lexicon.
4. **A bare name at the direct question.** It is now judged too: राजू for Rajesh ends `wrong_party`.
5. **Not fixed, as instructed.** Nicknames and short forms (Bala for Balasubramanian still ends `wrong_party`), and the yes-twice default (t-094: a man saying yes twice to a Kavitha record passes).
6. **Kept as the checker advised.** `SAME_MAX` is not raised, and there is no re-ask on an `other` name.

**Post-fix rerun of a set already seen** (the checker's 256 cases; not a held-out result):

| | false rejections, genuine | named, third parties | named, unambiguous third parties |
|---|---|---|---|
| Word lists, before (checker) | 10 of 147 = 6.8 [3.7-12.1] | 1 of 109 | 0 of 103 [0.0-3.6] |
| Word lists, after | 1 of 147 = 0.7 [0.1-3.8] (Bala, ambiguous) | 1 of 109 = 0.9 [0.2-5.0] (t-094) | 0 of 103 |
| Classifier, before (checker) | 10 of 147 = 6.8 [3.7-12.1] | 2 of 109 = 1.8 [0.5-6.4] | 0 of 103 [0.0-3.6] |
| Classifier, after | 1 of 147 = 0.7 [0.1-3.8] | 1 of 109 = 0.9 [0.2-5.0] (t-094) | 0 of 103 |

Unambiguous genuine borrowers: 0 of 146 rejected after the fix, in both arms. My classifier rerun cost at most USD 0.08: the shared ledger read 4.536 after the checker's runs and 4.616 after mine, and other workers write to it too.

## Left open
- **Role words.** A role word with no relation-list entry ("मैं manager बोल रहा हूँ", then "हाँ") still passes, as at base. Ending on any unrecognised word in that slot would also end "मैं बिज़ी हूँ".
- **Missing name parts.** A borrower known by a middle name or surname loses the call: the plan keeps only the first name ("मैं ही रफ़ीक़ हूँ" for Mohammed Rafiq).
- **Nicknames and short forms** (Bala, Ravi, Raju) end `wrong_party`. This is accepted.
- **Known misses and collisions:** the 54 listed misses and the collisions above.
- **Frame dependence.** A known-only-broad name gets different outcomes in strong and weak frames.
- **After the pass,** a different-name claim gets the who-check, not an end.

## Needed from others
- **Server worker:** pass `keyterms_for(first_name)` as Prisma `keyterms` on the identity turns. For Kavitha that is Kavitha, Kavita, कविता. Not measured.
- **Wave 2 classifier worker:** give the classifier the first name. `judge_name` can tell it whether a spoken name is the borrower's.
- **Documentation worker:**
  - `CLAUDE.md` still calls `_names.py` "partial Devanagari first-name matching".
  - The P8 line should say that a known other name ends the call at the identity questions.

## Test command
`uv run pytest tests/dialogue -q` gives **3,750 passed** (2026-11-14, after the fix round). `uv run ruff check` on the changed files is clean.
