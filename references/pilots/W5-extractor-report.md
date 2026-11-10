# W5 report: extractor and text-path evaluation

Date: 2026-11-10. Worker: W5b. The first W5 worker built most of the code and stopped on a usage limit without a report. W5b established the state, reviewed the code as an independent reviewer (it wrote none of the original), fixed what it proved, ran the frozen measurement once and wrote this report.

Goal as I understood it: the extractor is the one step of Samajh that can be wrong without anyone noticing, so its numbers have to be trustworthy. That means a boundary that cannot keep words the customer did not say, a model that never sees the lender's answer, scoring that does not flatter, and one measurement on a set nobody tuned on.

## 1. What was built

Built by the first W5 worker, unchanged in design:

- `samajh/extract/`: `extract(transcript, record, llm) -> RawExtraction` and `extract_traced` (the same, plus cost and span counts per LLM call).
  - `_extract.py`: pairs each customer reply with the bot turn before it, makes two small LLM calls per reply (the answer to the question asked, then a screen for claims and concerns said in passing), and assembles the result in code.
  - `_wire.py`: the strict schema of each call. The model returns enums, clause numbers and spans. No turn ids, no product ids, no rupee figures, no verdicts.
  - `_ground.py`: resolves clause numbers and spans against the reply. Every string kept is a slice of the reply, never model output.
  - `_prompt.py`: one prompt per question. The builders take the bot's question and the customer's reply and nothing else.
- `samajh/pipeline.py`: `run_text_case(transcript, record) -> CaseResult` and `run_text` (every stage, for the evaluation).
- `tests/extract/`: 176 tests with a fake LLM that replays recorded model outputs.
- `eval/text_path/`: `devset.py` (20 hand-written calls, 5 per language), `run.py` (the rerunnable evaluation), `scoring.py`, `scenario.py`, `scenario_sets.py`, and `runs/` (the reports).

Data shape, as the first worker designed it and as it stands: one LLM call sees one question and one reply. Code decides which question a reply answers, which turn a quote comes from and which product an answer belongs to. A field whose clause number or span is not in the reply becomes `Unclear(quote_not_grounded)`.

Added or changed by W5b (section 2.5 gives the reason for each):

- `samajh/extract/_extract.py`: an answer now quotes the customer's whole reply; a recall item, a claim or a concern quotes the whole clauses around its span; the two identity checks are never sent to the model; the output token limit is 4000 instead of 800.
- `samajh/pipeline.py`: `default_llm()`, which leaves out `temperature` for a model that rejects it. `WithoutTemperature` and `takes_temperature` moved here from `eval/text_path/run.py`.
- `eval/text_path/e1.py`: experiment E1 by stratum.
- `eval/text_path/run.py`: the E1 section, counts per base case, the consent stratum, a check for record values in bot questions, and a count of replies shared with the development set.
- `eval/text_path/scoring.py`: a call the extractor failed on now counts every gold field as wrong.
- `eval/text_path/negation_probe.py`: 24 adversarial replies, rerunnable.
- `tests/extract/`: 14 new tests (162 before, 176 now). `test_text_path_report.py` is new.
- `eval/text_path/runs/before-review/`: the first worker's development-set reports, kept for comparison.

The prompt (`_prompt.py`), the schema (`_wire.py`) and the grounding (`_ground.py`) are byte for byte the first worker's: `git diff HEAD` on them is empty.

## 2. Evidence

### 2.1 Checks

```
$ uv run pytest tests/extract -q
........................................................................ [ 81%]
................................                                         [100%]
176 passed in 0.42s
pytest exit: 0

$ uv run ruff check samajh/extract samajh/pipeline.py tests/extract eval/text_path
All checks passed!
ruff check exit: 0

$ uv run ruff format --check samajh/extract samajh/pipeline.py tests/extract eval/text_path
34 files already formatted
ruff format exit: 0

$ uv run pytest tests/core tests/scenarios -q
1350 passed in 10.69s
```

State when W5b started: `uv run pytest tests/extract -q` gave 162 passed and ruff was clean. `samajh.amounts` changed on the same day (ambiguous shapes refused, new `cross_check`). The pipeline needed no change for it: the 20 development calls, replayed from recorded model output, still give their expected verdicts and flags (`test_recorded_outputs_give_the_expected_verdict_and_flags`, 20 cases).

Missing from the original spec when W5b started: the report, the independent review, the frozen-set run and the E1 comparison. Everything else in the spec was present.

### 2.2 The frozen measurement

Run once, on the code hashed below, after every change in section 2.5 and before any look at its results. Nothing was changed afterwards.

```
$ uv run python -m samajh.scenarios verify
OK: files on disk and the generator match FROZEN.json

$ shasum -a 256 data/scenarios/gold.jsonl data/scenarios/calls.jsonl
14e49b58929c368e710709c8a93cc88e8852cead5ac89bbcde72c62be422e5dc  data/scenarios/gold.jsonl
b10111dfc64e5dd74061f553cdbf666db916491f9ce3ef647ae3d0778fad29f5  data/scenarios/calls.jsonl
FROZEN.json: version 3, 144 rows in each file

$ uv run python eval/text_path/run.py --set frozen --model openai/gpt-6-luna --usd-cap 1.5 --workers 8
exit: 0
```

Extractor code at the time of the run (sha256, first 16 hex digits): `_extract.py` 5412a809cbfe2b60, `_ground.py` a3bec802d8a121f1, `_prompt.py` 243120350b143945, `_wire.py` 5a441c039aa1f890, `pipeline.py` 3269515ae587349c.

Headline, for the recommended default model `openai/gpt-6-luna`:

- False clear: 1 of 108 calls whose gold is not clear (0.9%; 95% Wilson interval 0.2% to 5.1% over calls). It is B03 in Tamil. Counted by base case, 1 of 27 not-clear base cases has a false clear in some language (interval 0.7% to 18.3%).
- False alarm: 0 of 36 gold-clear calls, which are 9 base cases (interval 0% to 29.9% over base cases).
- Call verdict: 143 of 144. Product verdict: 143 of 144 (one product per record).
- Fields: 2,163 of 2,180.
- Flags over all rules: precision 282 of 284, recall 282 of 284.
- Extractor errors: 0. Spans not in the reply: 0 of 802. Clause numbers out of range: 0 of 1,195.

What the number is and what limits it:

- **Gold.** Verdicts and flags are scored against the hand-written gold of version 3. Fields are scored against the set's perfect extraction, passed through the same `to_beliefs`. The rule engine on that perfect extraction agrees with gold on 144 of 144, so every miss below is the extractor's.
- **Text, not speech.** The calls are scripted text. No speech-to-text ran. `data/scenarios/README.md` calls results on this set an upper bound for the text path, and I agree.
- **Templated speech.** The 144 calls made 3,391 LLM requests, and only 1,224 of them are distinct: the same question and reply recur across scenarios. 2,149 requests came from the cache inside this run and 1,242 were paid for (18 identical requests were in flight at the same time). The measurement rests on 1,224 distinct model readings, and one reading repeats in every scenario that uses the same line.
- **36 base cases.** The four languages share gold. Only 9 base cases are gold-clear.
- **In-sample replies.** 70 of the 1,604 replies to a checked question are word for word a reply of the development set, 28 of them longer than three words. The first worker's docstring said the two sets shared no text. I corrected the docstring and the report now counts the overlap. I do not know whether the first worker read the phrase bank or wrote the same Hindi lines independently.
- **Tamil and Kannada** text is not human-reviewed. All 17 wrong fields but 4 are in Tamil or Kannada (ta 8, kn 5, hi 2, hi-en 2).
- **One run.** The model rejects the `temperature` parameter, so it is not pinned to 0. A second uncached run could differ. Reruns of the script are identical because every call is cached.
- **What I saw before the run.** For the record-value check I read the bot lines of three Hindi base cases. A dry run of the report code with no LLM printed one customer reply of U01-hi. The overlap check printed the four shared replies, which are development-set text. No extractor or prompt change followed any of these.

The full report of the run is `eval/text_path/runs/frozen__openai-gpt-6-luna.md`. Everything from its headline to its last failure is pasted here unedited. Only the heading levels are lowered.

#### Headline

| group | calls | false clear | false alarm | call verdict | product verdict | fields |
|---|---|---|---|---|---|---|
| all | 144 | 0.9% (1/108) | 0.0% (0/36) | 99.3% (143/144) | 99.3% (143/144) | 99.2% (2163/2180) |
| hi | 36 | 0.0% (0/27) | 0.0% (0/9) | 100.0% (36/36) | 100.0% (36/36) | 99.6% (543/545) |
| hi-en | 36 | 0.0% (0/27) | 0.0% (0/9) | 100.0% (36/36) | 100.0% (36/36) | 99.6% (543/545) |
| ta | 36 | 3.7% (1/27) | 0.0% (0/9) | 97.2% (35/36) | 97.2% (35/36) | 98.5% (537/545) |
| kn | 36 | 0.0% (0/27) | 0.0% (0/9) | 100.0% (36/36) | 100.0% (36/36) | 99.1% (540/545) |
| gold extraction, no LLM | 144 | 0.0% (0/108) | 0.0% (0/36) | 100.0% (144/144) | 100.0% (144/144) | - |

False clear: gold is flag_for_review or unclear_needs_human and the pipeline says clear (n = calls whose gold is not clear). False alarm: gold is clear and the pipeline does not say clear (n = calls whose gold is clear). Extractor errors: 0. Last row: the rule engine on the set's gold extraction, so any miss there is not the extractor's.

#### Verdicts, gold against pipeline (all calls)

| gold | pipeline | calls |
|---|---|---|
| clear | clear | 36 |
| flag_for_review | clear | 1 |
| flag_for_review | flag_for_review | 99 |
| unclear_needs_human | unclear_needs_human | 8 |

#### Extraction accuracy per field

| field | all | hi | hi-en | ta | kn |
|---|---|---|---|---|---|
| kind | 100.0% (144/144) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) |
| premium_inr | 99.3% (143/144) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) | 97.2% (35/36) |
| premium_readback | 100.0% (132/132) | 100.0% (33/33) | 100.0% (33/33) | 100.0% (33/33) | 100.0% (33/33) |
| payment_source | 100.0% (144/144) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) |
| required_for_loan | 100.0% (144/144) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) |
| provider_choice_offered | 100.0% (32/32) | 100.0% (8/8) | 100.0% (8/8) | 100.0% (8/8) | 100.0% (8/8) |
| cover_inr | 100.0% (144/144) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) |
| term_months | 100.0% (144/144) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) |
| cancel_allowed | 99.3% (143/144) | 100.0% (36/36) | 100.0% (36/36) | 97.2% (35/36) | 100.0% (36/36) |
| cancel_window_days | 100.0% (144/144) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) |
| feature_probe | 98.6% (142/144) | 100.0% (36/36) | 100.0% (36/36) | 97.2% (35/36) | 97.2% (35/36) |
| consent_given | 99.3% (143/144) | 100.0% (36/36) | 100.0% (36/36) | 97.2% (35/36) | 100.0% (36/36) |
| consent_method | 93.8% (135/144) | 94.4% (34/36) | 94.4% (34/36) | 91.7% (33/36) | 94.4% (34/36) |
| recall_items | 98.6% (142/144) | 100.0% (36/36) | 100.0% (36/36) | 97.2% (35/36) | 97.2% (35/36) |
| volunteered_claims | 99.3% (143/144) | 100.0% (36/36) | 100.0% (36/36) | 97.2% (35/36) | 100.0% (36/36) |
| sale_concerns | 100.0% (144/144) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) | 100.0% (36/36) |

#### Flags per rule: precision and recall

| rule | all P | hi P | hi-en P | ta P | kn P | all R | hi R | hi-en R | ta R | kn R |
|---|---|---|---|---|---|---|---|---|---|---|
| kind | 100.0% (28/28) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (28/28) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (7/7) |
| premium | 100.0% (16/16) | 100.0% (4/4) | 100.0% (4/4) | 100.0% (4/4) | 100.0% (4/4) | 100.0% (16/16) | 100.0% (4/4) | 100.0% (4/4) | 100.0% (4/4) | 100.0% (4/4) |
| cover | 100.0% (36/36) | 100.0% (9/9) | 100.0% (9/9) | 100.0% (9/9) | 100.0% (9/9) | 100.0% (36/36) | 100.0% (9/9) | 100.0% (9/9) | 100.0% (9/9) | 100.0% (9/9) |
| term | 100.0% (24/24) | 100.0% (6/6) | 100.0% (6/6) | 100.0% (6/6) | 100.0% (6/6) | 100.0% (24/24) | 100.0% (6/6) | 100.0% (6/6) | 100.0% (6/6) | 100.0% (6/6) |
| cancel_window | 100.0% (31/31) | 100.0% (8/8) | 100.0% (8/8) | 100.0% (7/7) | 100.0% (8/8) | 96.9% (31/32) | 100.0% (8/8) | 100.0% (8/8) | 87.5% (7/8) | 100.0% (8/8) |
| recall | 85.7% (12/14) | 100.0% (3/3) | 100.0% (3/3) | 75.0% (3/4) | 75.0% (3/4) | 100.0% (12/12) | 100.0% (3/3) | 100.0% (3/3) | 100.0% (3/3) | 100.0% (3/3) |
| consent | 100.0% (28/28) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (28/28) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (7/7) |
| loan_funded | 100.0% (24/24) | 100.0% (6/6) | 100.0% (6/6) | 100.0% (6/6) | 100.0% (6/6) | 100.0% (24/24) | 100.0% (6/6) | 100.0% (6/6) | 100.0% (6/6) | 100.0% (6/6) |
| bundling | 100.0% (28/28) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (28/28) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (7/7) | 100.0% (7/7) |
| belief_mismatch | 100.0% (43/43) | 100.0% (11/11) | 100.0% (11/11) | 100.0% (10/10) | 100.0% (11/11) | 97.7% (43/44) | 100.0% (11/11) | 100.0% (11/11) | 90.9% (10/11) | 100.0% (11/11) |
| sale_conduct | 100.0% (12/12) | 100.0% (3/3) | 100.0% (3/3) | 100.0% (3/3) | 100.0% (3/3) | 100.0% (12/12) | 100.0% (3/3) | 100.0% (3/3) | 100.0% (3/3) | 100.0% (3/3) |
| all rules | 99.3% (282/284) | 100.0% (71/71) | 100.0% (71/71) | 98.6% (69/70) | 98.6% (71/72) | 99.3% (282/284) | 100.0% (71/71) | 100.0% (71/71) | 97.2% (69/71) | 100.0% (71/71) |

#### Spans and grounding

- Spans the model copied (amounts, durations, recall items, claims, concerns) that were not in the reply: 0 of 802 (0.00%). By field: none.
- Answers whose clause numbers were missing or out of range: 0 of 1195 (0.00%). By field: none.
- Both kinds are dropped to `unclear` (answers) or left for the rule engine to record as an evidence gap (recall items, claims, concerns). None is kept as an answer.
- Answers marked stated with no value or no span, kept as unclear: 0. By field: none.
- Gaps the rule engine raised with reason `quote_not_grounded`: 0 (with the gold extraction: 0).
- Gaps with reason `value_not_parsed`: 0 (with the gold extraction: 0).
- Record values found in bot turns shown to the model: premium in a `readback` question: 120. A lexical check of the premium, cover, sanctioned and disbursed amounts (digits and spoken form) and the provider name. A read-back repeats the amount the customer said, so it shows the record's premium whenever the customer's amount equals it. The two identity checks are never sent.

#### Cost and latency

- LLM calls: 3391 for 144 calls (2149 served from the cache in this run).
- Spent in this run: $0.09482.
- Cost of these calls with nothing cached: $0.24589 ($0.00171 per transcript, $0.00007 per LLM call).
- Latency per LLM call when first made: median 1.88 s, p90 3.38 s (wall time of the client call, retries included, one network).

#### By base case

- False clears: 1 calls in 1 of 36 base cases (B03).
- False alarms: 0 calls in 0 of 36 base cases; gold-clear base cases: 9.
- Any wrong call verdict: 1 calls in 1 of 36 base cases (B03).
- Any wrong field: 16 calls in 7 of 36 base cases (B01, B03, G01, G02, G05, U08, U10).
- `consent_given` where the customer agreed to a misdescribed product (C02, U08, V04, V06; the set expects true and calls false a defensible reading): 16/16 match the set. All other calls: 127/128.
- Replies to a checked question that are word for word a reply of the development set: 70 of 1604 (4.36%); 28 of them longer than three words. The prompt was iterated on the development set, so the model's reading of these replies is in-sample.

#### E1: teach-back call against the yes/no call, by stratum

| stratum | gold | calls (base cases) | yes/no call caught | teach-back caught | teach-back flagged the target rule | teach-back caught, gold extraction |
|---|---|---|---|---|---|---|
| coached | flag or unclear | 12 (3) | 0/12 calls (0/3 base cases in every language) | 12/12 calls (3/3 base cases in every language) | 12/12 calls (3/3 base cases in every language) | 12/12 calls (3/3 base cases in every language) |
| acquiescent | flag or unclear | 4 (1) | 0/4 calls (0/1 base cases in every language) | 4/4 calls (1/1 base cases in every language) | 4/4 calls (1/1 base cases in every language) | 4/4 calls (1/1 base cases in every language) |
| never_asked | flag or unclear | 20 (5) | 0/20 calls (0/5 base cases in every language) | 19/20 calls (4/5 base cases in every language) | 19/20 calls (4/5 base cases in every language) | 20/20 calls (5/5 base cases in every language) |
| asked | flag or unclear | 40 (10) | 40/40 calls (10/10 base cases in every language) | 40/40 calls (10/10 base cases in every language) | 36/40 calls (9/10 base cases in every language) | 40/40 calls (10/10 base cases in every language) |
| informed | flag or unclear | 32 (8) | 4/32 calls (1/8 base cases in every language) | 32/32 calls (8/8 base cases in every language) | 28/32 calls (7/8 base cases in every language) | 32/32 calls (8/8 base cases in every language) |
| informed | clear | 36 (9) | 0/36 calls (0/9 base cases in every language) | 0/36 calls (0/9 base cases in every language) | 0/36 calls (0/9 base cases in every language) | 0/36 calls (0/9 base cases in every language) |

Caught: the call did not end as a pass (yes/no: not confirmed; teach-back: verdict not clear, which includes unclear and an extractor error). The yes/no arm is the set's scripted outcome with no LLM; coached and acquiescent customers say yes to it by assumption, and never_asked is the coverage of a five-question script. The strata are the set author's mix, so no pooled rate is given. For a clear-gold row, caught is a false alarm.

#### Failures

##### U08-ta (ta): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Customer believes the cover is an investment plan that grows [violating, target rule kind]
- field `recall_items`: gold `((('P1', <KindClaim.investment: 'investment'>), 1),)`, pipeline `(((None, None), 1),)`
  - turn 10 [recall] bot: "லோனுடன் நீங்கள் என்னென்ன எடுத்தீர்கள், எவ்வளவுக்கு?" customer: "லோனோட ஒரு பிளான்ல பணம் போட்டேன், இருபத்தையாயிரம் ரூபாய்."
  - pipeline kept: None:"லோனோட ஒரு பிளான்ல பணம் போட்டேன்"->None
- flag not in gold: `recall` on P1: customer did not name this product unprompted | quote: "லோனோட ஒரு பிளான்ல பணம் போட்டேன், இருபத்தையாயிரம் ரூபாய்."

##### U08-kn (kn): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Customer believes the cover is an investment plan that grows [violating, target rule kind]
- field `recall_items`: gold `((('P1', <KindClaim.investment: 'investment'>), 1),)`, pipeline `(((None, None), 1),)`
  - turn 10 [recall] bot: "ಲೋನ್ ಜೊತೆ ನೀವು ಏನೇನು ತೆಗೆದುಕೊಂಡಿರಿ, ಎಷ್ಟಕ್ಕೆ?" customer: "ಲೋನ್ ಜೊತೆ ಒಂದು ಪ್ಲಾನಲ್ಲಿ ದುಡ್ಡು ಹಾಕಿದೆ, ಇಪ್ಪತ್ತೈದು ಸಾವಿರ ರೂಪಾಯಿ."
  - pipeline kept: None:"ಲೋನ್ ಜೊತೆ ಒಂದು ಪ್ಲಾನಲ್ಲಿ ದುಡ್ಡು ಹಾಕಿದೆ"->None
- flag not in gold: `recall` on P1: customer did not name this product unprompted | quote: "ಲೋನ್ ಜೊತೆ ಒಂದು ಪ್ಲಾನಲ್ಲಿ ದುಡ್ಡು ಹಾಕಿದೆ, ಇಪ್ಪತ್ತೈದು ಸಾವಿರ ರೂಪಾಯಿ."

##### U10-hi (hi): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Customer who answers 'I don't know' to almost everything [violating, target rule cover]
- field `consent_method`: gold `('dont_know', None)`, pipeline `('unclear', None)`
  - turn 28 [consent] bot: "लोन लेते समय आपने क्या-क्या लेने के लिए हामी भरी थी, और हामी कैसे दी थी?" customer: "ये मुझे नहीं पता कि किस-किस चीज़ के लिए हाँ हुई थी।"
  - pipeline kept: "ये मुझे नहीं पता कि किस-किस चीज़ के लिए हाँ हुई थी।" (turn 28)

##### U10-hi-en (hi-en): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Customer who answers 'I don't know' to almost everything [violating, target rule cover]
- field `consent_method`: gold `('dont_know', None)`, pipeline `('unclear', None)`
  - turn 28 [consent] bot: "Loan लेते समय आपने क्या-क्या लेने के लिए हाँ की थी, और हाँ कैसे की थी?" customer: "ये मुझे नहीं पता कि किस-किस चीज़ के लिए agree किया था।"
  - pipeline kept: "ये मुझे नहीं पता कि किस-किस चीज़ के लिए agree किया था।" (turn 28)

##### U10-ta (ta): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Customer who answers 'I don't know' to almost everything [violating, target rule cover]
- field `cancel_allowed`: gold `('dont_know', None)`, pipeline `('unclear', None)`
  - turn 24 [cancel_window] bot: "அதை ரத்து செய்ய முடியுமா முடியாதா, எத்தனை நாளுக்குள் என்று உங்களிடம் சொன்னார்களா?" customer: "கேன்சல் பண்ண முடியுமா முடியாதான்னு தெரியல."
  - pipeline kept: "கேன்சல் பண்ண முடியுமா முடியாதான்னு தெரியல." (turn 24)
- field `consent_method`: gold `('dont_know', None)`, pipeline `('unclear', None)`
  - turn 28 [consent] bot: "லோன் வாங்கும்போது நீங்கள் என்னென்ன எடுக்க ஒப்புக்கொண்டீர்கள், எப்படி ஒப்புதல் கொடுத்தீர்கள்?" customer: "எது எதுக்கு ஒத்துக்கிட்டேன்னு எனக்கு தெரியலங்க."
  - pipeline kept: "எது எதுக்கு ஒத்துக்கிட்டேன்னு எனக்கு தெரியலங்க." (turn 28)
- missed flag: `cancel_window` on P1

##### U10-kn (kn): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Customer who answers 'I don't know' to almost everything [violating, target rule cover]
- field `consent_method`: gold `('dont_know', None)`, pipeline `('unclear', None)`
  - turn 28 [consent] bot: "ಲೋನ್ ತೆಗೆದುಕೊಳ್ಳುವಾಗ ನೀವು ಏನೇನು ತೆಗೆದುಕೊಳ್ಳಲು ಒಪ್ಪಿದ್ದಿರಿ, ಒಪ್ಪಿಗೆ ಹೇಗೆ ಕೊಟ್ಟಿರಿ?" customer: "ಯಾವುದಕ್ಕೆಲ್ಲ ಒಪ್ಪಿದ್ದೆ ಅಂತ ನನಗೆ ಗೊತ್ತಿಲ್ಲ."
  - pipeline kept: "ಯಾವುದಕ್ಕೆಲ್ಲ ಒಪ್ಪಿದ್ದೆ ಅಂತ ನನಗೆ ಗೊತ್ತಿಲ್ಲ." (turn 28)

##### G01-ta (ta): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Two lakh debited from the borrower's account for a policy, no consent on record [violating, target rule consent]
- field `consent_method`: gold `('unclear', None)`, pipeline `('stated', <ConsentMethod.verbal: 'verbal'>)`
  - turn 28 [consent] bot: "லோன் வாங்கும்போது நீங்கள் என்னென்ன எடுக்க ஒப்புக்கொண்டீர்கள், எப்படி ஒப்புதல் கொடுத்தீர்கள்?" customer: "நான் லோனுக்கு மட்டும்தான் சரின்னு சொன்னேன். இன்ஷூரன்ஸ் பத்தி என்கிட்ட யாரும் கேக்கல. எனக்கு அப்புறம்தான் தெரிஞ்சுது, அக்கவுண்ட்ல இருந்து பணம் போனப்ப."
  - pipeline kept: "நான் லோனுக்கு மட்டும்தான் சரின்னு சொன்னேன். இன்ஷூரன்ஸ் பத்தி என்கிட்ட யாரும் கேக்கல. எனக்கு அப்புறம்தான் தெரிஞ்சுது, அக்கவுண்ட்ல இருந்து பணம் போனப்ப." (turn 28)

##### G01-kn (kn): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Two lakh debited from the borrower's account for a policy, no consent on record [violating, target rule consent]
- field `premium_inr`: gold `('stated', 200000)`, pipeline `('unclear', None)`
  - turn 14 [premium] bot: "ಅದಕ್ಕೆ ನೀವು ಎಷ್ಟು ರೂಪಾಯಿ ಕೊಟ್ಟಿರಿ?" customer: "ಎರಡು ಲಕ್ಷ ರೂಪಾಯಿ ತಗೊಂಡಿದ್ದಾರೆ."
  - turn 30 [readback] bot: "ಎರಡು ಲಕ್ಷ, ಅಂದರೆ 2,00,000 ರೂಪಾಯಿ, ಸರಿಯೇ?" customer: "ಹೌದು, ಸರಿ."
  - pipeline kept: "ಎರಡು ಲಕ್ಷ ರೂಪಾಯಿ ತಗೊಂಡಿದ್ದಾರೆ." (turn 14)

##### G02-hi (hi): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Signed consent on file; the customer says they agreed only to the loan [violating, target rule consent]
- field `consent_method`: gold `('unclear', None)`, pipeline `('stated', <ConsentMethod.signed_form: 'signed_form'>)`
  - turn 28 [consent] bot: "लोन लेते समय आपने क्या-क्या लेने के लिए हामी भरी थी, और हामी कैसे दी थी?" customer: "मैंने तो बस लोन के लिए हाँ बोली थी। बीमे के लिए मुझसे किसी ने नहीं पूछा। बहुत सारे काग़ज़ों पर साइन करवाए थे, किसी ने बताया नहीं कौन सा किस चीज़ का है।"
  - pipeline kept: "मैंने तो बस लोन के लिए हाँ बोली थी। बीमे के लिए मुझसे किसी ने नहीं पूछा। बहुत सारे काग़ज़ों पर साइन करवाए थे, किसी ने बताया नहीं कौन सा किस चीज़ का है।" (turn 28)

##### G02-hi-en (hi-en): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Signed consent on file; the customer says they agreed only to the loan [violating, target rule consent]
- field `consent_method`: gold `('unclear', None)`, pipeline `('stated', <ConsentMethod.signed_form: 'signed_form'>)`
  - turn 28 [consent] bot: "Loan लेते समय आपने क्या-क्या लेने के लिए हाँ की थी, और हाँ कैसे की थी?" customer: "सिर्फ़ loan। Insurance लेने की हामी मैंने कभी नहीं भरी। बहुत सारे papers पर sign करवाए थे, किसी ने बताया नहीं कौन सा किस चीज़ का है।"
  - pipeline kept: "सिर्फ़ loan। Insurance लेने की हामी मैंने कभी नहीं भरी। बहुत सारे papers पर sign करवाए थे, किसी ने बताया नहीं कौन सा किस चीज़ का है।" (turn 28)

##### G02-ta (ta): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Signed consent on file; the customer says they agreed only to the loan [violating, target rule consent]
- field `consent_method`: gold `('unclear', None)`, pipeline `('stated', <ConsentMethod.signed_form: 'signed_form'>)`
  - turn 28 [consent] bot: "லோன் வாங்கும்போது நீங்கள் என்னென்ன எடுக்க ஒப்புக்கொண்டீர்கள், எப்படி ஒப்புதல் கொடுத்தீர்கள்?" customer: "லோன் மட்டும்தான். இன்ஷூரன்ஸ் எடுக்க நான் ஒருநாளும் ஒத்துக்கல. நிறைய பேப்பர்ல கையெழுத்து வாங்கினாங்க, எது எதுக்குன்னு யாரும் சொல்லல."
  - pipeline kept: "லோன் மட்டும்தான். இன்ஷூரன்ஸ் எடுக்க நான் ஒருநாளும் ஒத்துக்கல. நிறைய பேப்பர்ல கையெழுத்து வாங்கினாங்க, எது எதுக்குன்னு யாரும் சொல்லல." (turn 28)

##### G02-kn (kn): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Signed consent on file; the customer says they agreed only to the loan [violating, target rule consent]
- field `consent_method`: gold `('unclear', None)`, pipeline `('stated', <ConsentMethod.signed_form: 'signed_form'>)`
  - turn 28 [consent] bot: "ಲೋನ್ ತೆಗೆದುಕೊಳ್ಳುವಾಗ ನೀವು ಏನೇನು ತೆಗೆದುಕೊಳ್ಳಲು ಒಪ್ಪಿದ್ದಿರಿ, ಒಪ್ಪಿಗೆ ಹೇಗೆ ಕೊಟ್ಟಿರಿ?" customer: "ಲೋನ್ ಮಾತ್ರ. ಇನ್ಶೂರೆನ್ಸ್ ತಗೊಳ್ಳೋಕೆ ನಾನು ಯಾವತ್ತೂ ಒಪ್ಪಿಲ್ಲ. ತುಂಬಾ ಪೇಪರಿಗೆ ಸಹಿ ಹಾಕಿಸ್ಕೊಂಡ್ರು, ಯಾವುದು ಯಾವುದಕ್ಕೆ ಅಂತ ಯಾರೂ ಹೇಳಿಲ್ಲ."
  - pipeline kept: "ಲೋನ್ ಮಾತ್ರ. ಇನ್ಶೂರೆನ್ಸ್ ತಗೊಳ್ಳೋಕೆ ನಾನು ಯಾವತ್ತೂ ಒಪ್ಪಿಲ್ಲ. ತುಂಬಾ ಪೇಪರಿಗೆ ಸಹಿ ಹಾಕಿಸ್ಕೊಂಡ್ರು, ಯಾವುದು ಯಾವುದಕ್ಕೆ ಅಂತ ಯಾರೂ ಹೇಳಿಲ್ಲ." (turn 28)

##### G05-ta (ta): gold `unclear_needs_human`, pipeline `unclear_needs_human`
Scenario: Customer agreed to the insurance but cannot say how [near_miss, target rule consent]
- field `consent_given`: gold `('stated', True)`, pipeline `('unclear', None)`
  - turn 28 [consent] bot: "லோன் வாங்கும்போது நீங்கள் என்னென்ன எடுக்க ஒப்புக்கொண்டீர்கள், எப்படி ஒப்புதல் கொடுத்தீர்கள்?" customer: "ரெண்டுக்கும் ஒத்துக்கிட்டேன். ஆனா எப்படி ஒத்துக்கிட்டேன்னு ஞாபகம் வரல."
  - pipeline kept: "ரெண்டுக்கும் ஒத்துக்கிட்டேன். ஆனா எப்படி ஒத்துக்கிட்டேன்னு ஞாபகம் வரல." (turn 28)

##### B01-ta (ta): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Knows it is a policy; believes the money can be withdrawn after one year [violating, target rule belief_mismatch]
- field `feature_probe`: gold `('stated', (<FeatureClaim.withdrawable_after_period: 'withdrawable_after_period'>,))`, pipeline `('stated', (<FeatureClaim.refundable_anytime: 'refundable_anytime'>, <FeatureClaim.withdrawable_after_period: 'withdrawable_after_period'>))`
  - turn 26 [features] bot: "அந்தப் பணத்தை நீங்கள் திரும்பக் கேட்டால் கிடைக்குமா, எப்போது?" customer: "ஆமா, ஒரு வருஷம் கழிச்சு எப்ப வேணும்னாலும் எடுத்துக்கலாம்னு சொன்னாங்க."
  - pipeline kept: "ஆமா, ஒரு வருஷம் கழிச்சு எப்ப வேணும்னாலும் எடுத்துக்கலாம்னு சொன்னாங்க." (turn 26)

##### B01-kn (kn): gold `flag_for_review`, pipeline `flag_for_review`
Scenario: Knows it is a policy; believes the money can be withdrawn after one year [violating, target rule belief_mismatch]
- field `feature_probe`: gold `('stated', (<FeatureClaim.withdrawable_after_period: 'withdrawable_after_period'>,))`, pipeline `('stated', (<FeatureClaim.refundable_anytime: 'refundable_anytime'>, <FeatureClaim.withdrawable_after_period: 'withdrawable_after_period'>))`
  - turn 26 [features] bot: "ಆ ಹಣವನ್ನು ನೀವು ವಾಪಸ್ ಕೇಳಿದರೆ ಸಿಗುತ್ತದೆಯೇ, ಯಾವಾಗ?" customer: "ಹೌದು, ಒಂದು ವರ್ಷ ಆದ್ಮೇಲೆ ಯಾವಾಗ ಬೇಕಾದ್ರೂ ತಗೋಬಹುದು ಅಂತ ಹೇಳಿದ್ರು."
  - pipeline kept: "ಹೌದು, ಒಂದು ವರ್ಷ ಆದ್ಮೇಲೆ ಯಾವಾಗ ಬೇಕಾದ್ರೂ ತಗೋಬಹುದು ಅಂತ ಹೇಳಿದ್ರು." (turn 26)

##### B03-ta (ta): gold `flag_for_review`, pipeline `clear` **FALSE CLEAR**
Scenario: Believes the premium is paid only once; the record shows a regular-premium product [violating, target rule belief_mismatch]
- field `volunteered_claims`: gold `(('P1', <FeatureClaim.one_time_payment: 'one_time_payment'>),)`, pipeline `()`
  - pipeline kept: -
  - gold has: one_time_payment:"ஒரே தடவைதான், ஐம்பத்திரண்டாயிரம் ரூபாய்."
- missed flag: `belief_mismatch` on P1

Reading of the failures, kept apart from the unedited list above:

- **B03-ta, the one false clear.** The customer says "ஒரே தடவைதான், ஐம்பத்திரண்டாயிரம் ரூபாய்." in reply to the premium question. Gold reads "only once" as a volunteered `one_time_payment` claim. The screening call returned no claim. The same case is caught in Hindi, Hinglish and Kannada. Not fixed: the frozen set is not for tuning.
- **G02, all four languages, and G01-ta.** The customer says they agreed only to the loan and adds that they were made to sign many papers. The model records `consent_method: signed_form` (or `verbal`); the set expects `unclear`. No verdict or flag changes.
- **U10, all four languages.** "I do not know what I agreed to" is read as `consent_method: unclear`; the set expects `dont_know`. No verdict or flag changes. U10-ta also reads a "do not know whether it can be cancelled" as `unclear`, which loses the `cancel_window` flag.
- **U08-ta and U08-kn.** "I put money in a plan" is given no kind in open recall, so the item is not matched to the product and an extra low `recall` flag appears. These are the two false-positive flags.
- **B01-ta and B01-kn.** "After one year, whenever I want" is read as two beliefs, `withdrawable_after_period` and `refundable_anytime`. The set expects the first only. The flag is the same.
- **G01-kn.** "They took two lakh rupees" is not read as the premium. **G05-ta.** "I agreed to both" is read as `unclear`.

### 2.3 E1, by stratum

The table is in the pasted report above ("E1: teach-back call against the yes/no call, by stratum"). In words, with no pooled figure:

- **Coached** (3 base cases, 12 calls): the yes/no call catches 0 of 12, the teach-back pipeline 12 of 12. The yes/no miss is an assumption of the set: these customers say yes to everything on that call.
- **Acquiescent** (1 base case, 4 calls; the hero case U02): 0 of 4 against 4 of 4. Also an assumption. `data/scenarios/README.md` says a truthful U02 would be caught by the first yes/no question.
- **Never asked** (5 base cases, 20 calls): 0 of 20 against 19 of 20. The miss is B03-ta. This stratum measures what a five-question closed script covers, not open against closed questions.
- **Asked** (10 base cases, 40 calls): 40 of 40 for both calls. Where the closed script asks about the wrong belief and the customer is truthful, the yes/no call does as well as the teach-back call.
- **Informed, gold flag or unclear** (8 base cases, 32 calls): yes/no 4 of 32, teach-back 32 of 32. These are flags on customers whose beliefs match the record: a fault on the lender's side (no consent on record, no choice of provider), a consent method that differs from the record, a rounded or forgotten premium, a product not named unprompted (G03, G05, R01, U05, U09, V02, V03, W01).
- **Informed, gold clear** (9 base cases, 36 calls): neither call raises a false alarm (0 of 36 each).

What E1 does not show: the yes/no arm is the set's scripted outcome, read perfectly, with no LLM and no speech. Disposition applies to the yes/no call only, which favours the teach-back call. The column "flagged the target rule" is below "caught" in two rows because the gold of one base case in each row is unclear for its target rule, not a flag (W06 and G05).

### 2.4 Model comparison and recommendation

Development set, 20 hand-written calls (5 per language), run on the final code. In-sample for the prompt: the first worker iterated the prompt on this set.

```
$ uv run python eval/text_path/run.py --set dev --model mistralai/mistral-small-3.2-24b-instruct --model google/gemini-2.5-flash-lite --model openai/gpt-6-luna --model anthropic/claude-haiku-5.5 --usd-cap 0.4
```

| model | false clear | false alarm | call verdict | fields | flag P | flag R | errors | $ / transcript | $ / LLM call | median s / LLM call |
|---|---|---|---|---|---|---|---|---|---|---|
| `mistralai/mistral-small-3.2-24b-instruct` | 0.0% (0/13) | 42.9% (3/7) | 85.0% (17/20) | 98.0% (298/304) | 93.8% (60/64) | 100.0% (60/60) | 0 | $0.00081 | $0.00004 | 0.82 s |
| `google/gemini-2.5-flash-lite` | 0.0% (0/13) | 100.0% (7/7) | 65.0% (13/20) | 93.8% (285/304) | 81.1% (60/74) | 100.0% (60/60) | 0 | $0.00135 | $0.00007 | 1.01 s |
| `openai/gpt-6-luna` | 0.0% (0/13) | 0.0% (0/7) | 100.0% (20/20) | 100.0% (304/304) | 100.0% (60/60) | 100.0% (60/60) | 0 | $0.00153 | $0.00008 | 1.87 s |
| `anthropic/claude-haiku-5.5` | 0.0% (0/13) | 0.0% (0/7) | 100.0% (20/20) | 99.7% (303/304) | 98.4% (60/61) | 100.0% (60/60) | 0 | $0.00502 | $0.00025 | 1.04 s |

Negation probe: 24 Hindi and Hinglish replies I wrote so that the first clause, read alone, gives the opposite answer. It shows a failure pattern and is not a rate. No Tamil or Kannada: I cannot write negation in them reliably.

```
$ uv run python eval/text_path/negation_probe.py --model mistralai/mistral-small-3.2-24b-instruct --model google/gemini-2.5-flash-lite --model openai/gpt-6-luna --model anthropic/claude-haiku-5.5
mistralai/mistral-small-3.2-24b-instruct: 20 of 24 read correctly
google/gemini-2.5-flash-lite: 18 of 24 read correctly
openai/gpt-6-luna: 24 of 24 read correctly
anthropic/claude-haiku-5.5: 24 of 24 read correctly
```

Every miss is listed in `eval/text_path/runs/negation_probe.md`. Two of Mistral's four are in the false-clear direction: "बीमा के लिए हामी भरी थी, ऐसा मुझे याद नहीं, …" and "Policy के लिए agree किया, ये गलत है, …" are both read as consent given.

**Recommendation: `openai/gpt-6-luna` as the default for extraction.**

| | gpt-6-luna | mistral-small-3.2 (today's default) | claude-haiku-5.5 | gemini-2.5-flash-lite |
|---|---|---|---|---|
| Dev call verdicts (n=20) | 20 | 17 | 20 | 13 |
| Dev false alarms (n=7 clear calls) | 0 | 3 | 0 | 7 |
| Dev fields (n=304) | 304 | 298 | 303 | 285 |
| Negation probe (n=24) | 24 | 20 | 24 | 18 |
| Cost per transcript, dev | $0.00153 | $0.00081 | $0.00502 | $0.00135 |
| Median latency per LLM call | 1.87 s | 0.82 s | 1.04 s | 1.01 s |
| p90 latency per LLM call | 3.37 s | 1.25 s | 1.89 s | 1.22 s |

- **Why not the cheap default.** Mistral and Gemini show a real failure pattern on two independent checks: false alarms from reading a plain "I signed" or "I gave the OTP" as a sale concern, and misread negations. The spec allows a stronger model only on such a pattern, and it is there.
- **Cost.** $0.00153 per transcript on the development set (20 LLM calls per transcript) and $0.00171 on the frozen set (23.5 calls per transcript). About twice Mistral and a third of Haiku.
- **Latency.** A transcript is 20 to 24 calls made one after another. At the median that is about 40 s per transcript. This is inferred from the per-call median and not measured end to end. It is fine after a call and too slow inside one.
- **Two caveats.** The model rejects `temperature`; OpenRouter answers 404 if it is sent, so `default_llm()` leaves it out. It is a reasoning model and needs room: at 800 output tokens one hard reply came back cut off and empty, which fails the whole call. The same request used 863 completion tokens and 10.5 s when allowed 4000.
- **Run-to-run variation.** Mistral gave 18 of 20 verdicts in the first worker's run and 17 of 20 in mine with the same prompts, and 19 then 20 of 24 on the probe. Haiku gave 23 then 24. The two probe runs differ in the token limit (800, then 4000), which does not bind for either model. A difference of one or two on these sets is noise. The gap between the two groups of models is not.
- **Alternative.** `anthropic/claude-haiku-5.5` matches luna on the probe, is one field behind on the development set, costs 3.3 times as much and is faster per call.
- **Not selected on the frozen set.** `references/pilots/W2-clients-report.md` line 232 asked for the selection to be rerun on the frozen gold set. I did not: the W5 spec keeps that set for one final measurement. Only the recommended model was run on it.

The default path with this model was run end to end (every call came from the cache, so it cost nothing):

```
$ SAMAJH_LLM_MODEL=openai/gpt-6-luna uv run python -c "... run_text_case(dev hi-02 transcript, record, default_llm()) ..."
WithoutTemperature wraps openai/gpt-6-luna
flag_for_review ['belief_mismatch', 'bundling', 'cancel_window', 'consent', 'cover', 'kind', 'loan_funded']
gold: flag_for_review
```

### 2.5 Independent review

I reviewed as the reviewer the spec asks for: I wrote none of the original code, ran the tests, and attacked with scripts. Each proven finding has a test that failed first, except finding 4.

| # | Finding | Proof | Fix |
|---|---|---|---|
| 1 | An answer kept a quote that stops short of a "not" in the next clause. With the model pointing at clause 1 of "रद्द करवा सकते हैं, ऐसा किसी ने नहीं बताया, तीस दिन की बात सुनी थी।" the evidence was "रद्द करवा सकते हैं" and the call came out `clear` | Script with the fake LLM; `test_an_answer_quotes_the_whole_reply_so_a_later_negation_is_never_cut_off` failed | Every answer now quotes the customer's whole reply. The model still has to point at a real clause, but it no longer chooses the words kept as evidence |
| 2 | A claim, a concern or a recall item kept a quote cut inside a clause: "हर बात पर हाँ कहना" from "किसी ने नहीं कहा कि हर बात पर हाँ कहना" raised a `sale_conduct` flag with the "not" removed | Three tests failed | The quote is widened to the whole clauses around the span |
| 3 | The borrower's name reached the LLM. The right-party question names the borrower and was sent in the screening call. A birth-year reply of three words or more was sent too | `test_the_identity_checks_are_never_sent_to_the_model` failed. The existing leak test could not see it: it swaps the record after the bot's lines were written from the old one | The right-party check and the second check are never sent to the model. The 20 development transcripts now take 403 LLM calls instead of 417 |
| 4 | An output cut off at 800 tokens fails the whole call (`ExtractionFailed`) | The negation probe on gpt-6-luna: `finish_reason=length, empty content` | Limit raised to 4000. No unit test: it is a constant, and the evidence is the probe |
| 5 | A call the extractor failed on dropped out of the field accuracy, which flatters the number | `test_an_extractor_error_counts_every_gold_field_as_wrong` failed | Every gold field of such a call counts as wrong. No error occurred in any run, so no reported number moved |
| 6 | The development set's docstring said it shares no text with the frozen set. 70 of 1,604 frozen replies are identical to a development reply | Counted with a script | Docstring corrected. The frozen report prints the count |
| 7 | `run_text_case` with its default client could not call a model that rejects `temperature` | OpenRouter 404 on gpt-6-luna | `default_llm()` in `samajh/pipeline.py`; two tests |

Attacks that found no defect:

- **Fabricated spans.** A rewritten, translated, reordered or digits-for-words amount is dropped to `quote_not_grounded` (tests existed and pass). A span that matches only after punctuation is removed ("15 lakh" against "1.5 lakh") comes back as the reply's own text, so the value is always read from what the customer said.
- **Record leakage.** The prompt builders take a question and a reply; a test pins their signatures and the module's source has no access to the record. On all 144 frozen teach-back calls the only record value found in a bot turn shown to the model is the premium in a read-back (120), which repeats the amount the customer just said. The 120 counts read-back turns. The check is lexical (amounts as digits and in spoken form, provider name) and cannot see a kind or a payment source put into a question in words. I read the bot questions for kind, payment source, required, provider choice, cancel, money back and consent in Hindi: all are open or list neutral options.
- **Prompt examples.** 0 of 49 prompt examples are a frozen reply. A test already pins that none is a development reply.
- **Scoring.** A stated answer to a question that was never asked cannot hide in the skipped `not_asked` fields: `to_beliefs` turns it into `unclear` first. Gold on the frozen set never passes through the rule engine.

What validation cannot do, and I did not try to fake: a wrong value on a real and complete reply. If the model reads "…, ऐसा किसी ने नहीं बताया" as yes, the quote is now honest but the answer is still wrong, and the call can still come out clear. That error is measured, not prevented: 24 of 24 on the probe and 1 false clear in 108 on the frozen set for the recommended model.

Scoring choices a reader should know. I left them as they were:

- A volunteered "it is a deposit" claim is ignored on both sides when the gold already has the customer calling the product a deposit.
- Flags are compared as sets of (product, rule). Severity and the number of flags under one rule are not scored.
- Gaps are not scored per rule. A wrong `unclear` shows in the field table and in the verdict.

## 3. Claims

Verified, with the source:

- `openai/gpt-6-luna` rejects `temperature` on OpenRouter: a live call returned HTTP 404 "No endpoints found that can handle the requested parameters", and the same request without it succeeded.
- The frozen set is version 3 and matches its hashes: `uv run python -m samajh.scenarios verify`, and `shasum` on both files, at the time of the run.
- The strata of E1 match `data/scenarios/README.md`: 3 coached, 1 acquiescent, 5 never asked and 10 asked base cases, counted from the loaded set.
- Cost and latency come from the client's ledger values per call (`usage.cost` and wall time), kept in `eval/text_path/runs/calls.jsonl`.

Not verified:

- Tamil and Kannada text in the development set, the prompt examples and the frozen set: `not human-reviewed`.
- Hindi and Hinglish text is model-written and model-reviewed only.
- Per-transcript latency (about 40 s) is inferred from per-call medians.
- The yes/no arm of E1 is a scripted model of a confirmation call, not a real lender's script.

## 4. Failures, known gaps and changes from the spec

Failures:

- One false clear on the frozen set (B03-ta) and 17 wrong fields in 16 calls. All are listed in section 2.2. None was fixed, by the rule that nothing is tuned on the frozen set.

Known gaps:

- **Nothing here is speech.** No STT output and no human voice. Real replies have no punctuation, so a whole reply is one clause.
- **No Tamil or Kannada negation probe.** 13 of the 17 wrong frozen fields are in those two languages.
- **The frozen set does not cover** two products on one record, a premium corrected at read-back, a re-asked question or a customer who names something off the record. The development set covers them with 20 calls, in-sample.
- **One invalid output fails the whole call.** That is the first worker's design and I kept it. It happened 0 times in the runs reported here.
- **LLM calls for one transcript run one after another.**
- **`default_llm()` reads the client's private `_model`** and fetches OpenRouter's model list once per call. If the list cannot be read it sends `temperature`.
- **The fixes of section 2.5 have had no independent review.** I wrote them and I was the reviewer of the original code.

Changes from the spec, and why:

- **No reviewer subagent.** The W5b task made me the reviewer and allowed at most one subagent. I used none.
- **No builder subagents and no architect pass.** The code existed. I loaded `pstack-poteto-mode` and worked inline.
- **Answer quotes are the whole reply**, not the clause the model points at. Coordinator decision 4 asks for whole clauses never cut short of a negation; the whole reply is the one form that guarantees it across clauses.
- **Spec item 5 said one stronger model only if needed.** The first worker ran two (gpt-6-luna and claude-haiku-5.5). I reran both so the table is on the final code.

## 5. Spend

- Gnani credits: 0. No Gnani call was made.
- OpenRouter, by the shared ledger (`.samajh/ledger.jsonl`): 0.5205 USD in total for the whole project when this report was written. 0.2231 USD was there when W5b started and 0.2974 USD is W5b's. The ledger has no worker field, so the 0.2231 cannot be split exactly between the first W5 worker, W2 (0.0023 by its report) and W9.
- W5b's 0.2974 USD: the frozen run 0.0948, the development rerun on four models about 0.17, the negation probe twice about 0.03.
- By model, whole ledger: claude-haiku-5.5 0.2138, gpt-6-luna 0.1649, mistral-small-3.2 0.0773, gemini-2.5-flash-lite 0.0636, gpt-4.1-nano 0.0009.
- The budget was 3 USD including the first worker's spend. The whole project's ledger is under a fifth of it.

## 6. Next iteration

1. Decide the default model (section 7, `defaults.toml`). Until then `run_text_case` with no `llm` argument runs Mistral.
2. Run the text path on STT output of the same scenarios (E2 and E5 need it). Unpunctuated replies change what a clause is.
3. Get a fluent Tamil and Kannada reader for the 13 wrong fields in those languages, and write a negation probe in both.
4. Look at the Tamil "only once" miss (B03-ta) on new development replies, not on the frozen set.
5. Decide whether one invalid model output should fail the call or leave that one field `unclear`.
6. An independent review of the section 2.5 fixes.
7. If per-transcript time matters, run the calls of one transcript in parallel.

## 7. Document lines this work makes stale

- `ORCHESTRATION.md:79`: the W5 row says "Replacement W5b in progress". It is done; the report is this file.
- `CLAUDE.md:57`: "the extractor and dialogue are in progress (replacement workers W5b and W9b …)". The extractor is done. The Files section has no entry for `samajh/extract/`, `samajh/pipeline.py`, `tests/extract/` (176 tests) or `eval/text_path/`.
- `README.md:17` and `README.md:18`: W5b is listed as in progress.
- `README.md:23`: "the extractor and call-flow evaluations (E1, E2) have not been run on it". The text path has now been run on it once: scripted text, one model, no speech.
- `samajh/clients/defaults.toml:15` to `:19`: the comment and the default model. This report recommends `openai/gpt-6-luna` for extraction. Changing the line alone would break any caller that sends `temperature` to that model. `samajh.pipeline.default_llm()` handles it for the text path; I did not check the dialogue's LLM fallback (`samajh/dialogue/`), which is W9's. The choices are a separate model setting for extraction, or an `LlmClient` that leaves `temperature` out for models that reject it.
- `references/pilots/W2-clients-report.md:176`: the default-model paragraph. `:232`: "rerun … selection on the frozen gold set" was not done, on purpose (section 2.4).
- `DESIGN.md:230` and `:231` (E1 and E2 rows): text-path results now exist for both and can be cited from section 2.2 and 2.3 with their limits.
- `DESIGN.md:253` (demo step 4): the X, Y and Z of "Open questions flagged X of Y …" can be filled per stratum from section 2.3, for text only.
- `eval/text_path/devset.py`: its docstring claimed no shared text with the frozen set. Already corrected by this work.
