# W9 report: dialogue (call state machine and scripts)

Date: 2026-11-10. Worker: W9 execution manager.

Goal as I understood it: the bank's non-sales team needs a callback that tests what a borrower understood without telling them the answer. W9 is the conversation itself: a pure core that takes a loan record and the customer's words and decides the bot's next line, in the customer's language, following the v2 flow in DESIGN.md section 5. The experiment is void if the bot leaks a value it is testing, and the product is unsafe if it tells a stranger about the loan, never ends, or says something the design bans.

This file sits in `tests/dialogue/` because that is inside my lane. Move it to `references/pilots/` if you want it next to the other reports.

## 1. What I built (paths)

```
samajh/dialogue/
  machine.py       states, `start`, `step`, the transcript; pure
  interpret.py     `Expecting`, `Intent`, `Interpretation`, `RuleInterpreter`, `birth_year`
  _lexicon.py      word lists per language, one tokeniser, phrase matching
  llm_fallback.py  `LlmFallbackInterpreter` (the only module that imports a network client)
  prompts.py       `LINES` (step, question and slots of every line), `load_prompts`
  lint.py          banned wording; `load_prompts` refuses a file that fails it
  __main__.py      `play` and `eval-turns`
data/prompts/      hi.toml, hi-en.toml, ta.toml, kn.toml: 51 lines each, with the design paragraph
tests/dialogue/    9 test files, `dialogue_kit.py`, fixtures, `probes/gen_turns.py`
```

### Public surface

```python
from samajh.dialogue import start, step, CallState, BotUtterance, EndOfCall, Outcome, Limits

start(record: LoanRecord, language: Language, *, lender_name: str,
      call_id: str | None = None, limits: Limits | None = None) -> tuple[CallState, BotUtterance]
step(state: CallState, customer_text: str, *, interpreter: TurnInterpreter = RuleInterpreter())
      -> tuple[CallState, BotUtterance | EndOfCall]

BotUtterance(language, lines: tuple[Line, ...]); .text joins the lines
Line(key, slots, text, step: CallStep, asks: Question | None, product_id: ProductId | None)
EndOfCall(utterance: BotUtterance, outcome: Outcome, transcript: Transcript, unresolved: tuple[Unresolved, ...])
CallState: .transcript() -> samajh.types.Transcript; model_dump_json() / model_validate_json() to persist
Outcome: completed, wrong_party, not_confirmed, no_go_ahead, second_check_failed, declined,
         human_requested, turn_limit
Limits(max_bot_turns=60, max_read_backs=3)

class TurnInterpreter(Protocol):
    def interpret(self, text, *, language, expecting: Expecting, question: str) -> Interpretation
```

`step` raises `ValueError` on a call that has ended. `customer_text=""` means nothing was heard.

### How the states work

`CallState.position` says which reply the bot is waiting for. Each position is its own type:
`AtIdentity`, `AtGoAhead`, `AtBirthYear`, `AtRecall`, `AtTeachBack(product, question)`, `AtConsent`,
`AtReadBack(product, amount_inr, read_backs)`, `AtRestate`, `AtStopCheck(wish, resume)`, `Ended(outcome)`.
The interpreter turns the reply into an `Intent` (the event). `step` maps (position, intent) to the next position and the next lines.

Three decisions shape everything else.

1. **The state does not hold the record.** `start` keeps a `CallPlan`: loan id, first name, birth year and product ids. Nothing else from the record survives, so no line can depend on a tested value. The only figures the bot says are ones the customer said first. The question list is the same for every record (choice of provider is always asked, though the rules need it only when the product was required), because which questions are asked would otherwise reveal `required_for_loan`.
2. **Products are named by ordinal, never by kind.** One product: "the thing taken with the loan". Several: "the first / second thing on record with the loan". The words insurance, policy, premium, cover, FD and deposit are banned from every line by the lint, so the design's "Is this insurance, FD or something else?" became "आपकी समझ से वह चीज़ क्या है?" and "What does it cover?" became "what do you get from it, and up to what amount?".
3. **Only a plain refusal ends the call at once.** A weak signal (a short "रहने दो", or an LLM's guess) gets one question, "क्या आप यह कॉल यहीं रोकना चाहते हैं?". Yes ends the call; anything else goes back to the pending question as if its last reply had been unclear. Section 4 shows the measurement behind this.

One bot utterance can hold several lines (the disclosure is seven). Each line becomes its own bot `Turn`, and the last line is always the question, so the rules' "reply to the turn before it" linkage holds.

## 2. Evidence

```
$ uv run pytest tests/dialogue -q
PLACEHOLDER_PYTEST

$ uv run ruff check samajh/dialogue tests/dialogue
PLACEHOLDER_RUFF
```

What the tests cover, by file:

| File | What it holds the code to |
|---|---|
| `test_call_paths.py` | Scripted calls in all four languages: happy path; wrong party; no confirmation; decline and human request at each of 15 stages; unclear answers asked once more then recorded; "don't know" not re-asked; read-back of the customer's figure (record says 61,000, customer says 52,000, bot reads 52,000); correction and rejection at read-back; bounded read-back loop; two products; zero products; second check; weak stop signals; JSON round trip at every turn; turn budget |
| `test_no_leak_and_termination.py` | 200 random customers per language, each played against two records that differ in every tested value. Bot lines must be word-for-word identical, hold no record value, and the call must end inside its own bounds with the budget set to 10,000. The random pool includes the records' own values, format strings and out-of-range amounts. A self-test proves the scan fails on nine planted leaks |
| `test_prompts.py` | Every language defines every line with a design paragraph; slots are exactly the declared ones; no banned wording, no digit; every line at most 240 characters; a read-back line parses back to its amount (about 2,500 amounts per language and line); 30 bad lines the lint must reject; a prompt file with banned wording or a wrong slot does not load |
| `test_interpret.py` | 118 labelled turns, including answers that hold refusal-like words and must stay answers; amounts; birth years |
| `test_llm_fallback.py` | The LLM is not called when the rules settle a turn; it sees only the question and the reply; no label ends a call; a failed call leaves the rule reading |
| `test_rules_consume_the_call.py` | A finished Hindi call plus a faithful extraction goes through `to_beliefs` and `evaluate` with no `not_asked`, `quote_not_grounded` or `readback_mismatch` gap, and flags `kind`, `bundling` and `belief_mismatch`; a premium corrected at read-back is the one compared |
| `test_heldout_turns.py` | Pins the measurement in section 4 |
| `test_cli.py` | `play` in each language, with the transcript written and re-validated |

### One full Hindi call (typed into the CLI; one answer is unclear on purpose)

```
PLACEHOLDER_HI
```

### One full Hinglish call (the customer corrects the figure at read-back)

```
PLACEHOLDER_HI_EN
```

## 3. Claims

Verified, with source:
- The call steps, the content of the disclosure, the open consent and cancel questions: DESIGN.md section 5 and `references/claims/design-corrections.md` items 4, 5, 11 and 12, read on 2026-11-10. Each line in `data/prompts/*.toml` names the paragraph it implements.
- The transcript contract (tags, read-back turn, consent question without a product): `references/pilots/W1-core-report.md` section 3, and proven by `test_rules_consume_the_call.py` against the real rule engine.
- A read-back line parses back to its amount in all four languages for amounts from 100 to 50,000,000 (about 2,500 sampled amounts per language and line; `test_prompts.py`). The first Tamil and Kannada wording failed this for 37 and 4 of 4,745 sampled amounts, because `parse_amount` refuses an unknown word directly before a unit word. A colon before the amount fixed it.

Not verified:
- `[unverified]` The Tamil and Kannada lines, lexicons and scripted customers. All are `not human-reviewed` and labelled so in the data and in the CLI.
- `[unverified]` The Hindi and Hinglish lines were written by the build agent and have had no fluent second reader.
- `[unverified]` Nothing has been voiced. Whether Timbre reads the mixed-script Hinglish lines, "ए-आई", "ओ-टी-पी" and the 215-character Tamil recording line well is for the voice worker to check.
- `[unverified]` The reply set in section 4 is LLM-written. No human said or labelled any of it.

## 4. Turn interpretation: the measured gap and what it changed

**What was measured.** 408 customer replies: 17 behaviours × 4 languages × 6 replies, written by `google/gemini-2.5-flash-lite` from a behaviour description (`tests/dialogue/probes/gen_turns.py`). The gold label is the effect the reply should have on the call (answered, reask, decline, human, confirmed, ...). It is what the writer was told to write, not a human judgement, and some labels are wrong (a "confirmation" that states a different amount, for example). Each reply is played into the real machine at the right position and the effect is compared (`python -m samajh.dialogue eval-turns`). Rows are split into two folds by a hash. Fold 0 (n = 209) was used to tune the word lists and the fallback prompt. Fold 1 (n = 199) was not, with one exception stated below.

| Fold 1 (held out), n = 199 | Rules only | Rules + LLM fallback |
|---|---|---|
| All replies with the labelled effect | 155 (78%) | 188 (94%) |
| Hindi / Hinglish / Tamil / Kannada | 41/49, 45/52, 36/53, 33/45 | 49/49, 50/52, 47/53, 42/45 |
| Asked for a human (n = 13) | 5 | 12 (7 of them after the stop-check) |
| Unclear or off-topic (n = 36) | 18 | 35 |
| Declined (n = 22) | 17 | 21 (4 after the stop-check) |
| Answers (n = 72) | 66 | 70 |
| Calls ended on a reply that was not a refusal | 0 | 0 |

Fold 0 for comparison (in-sample after tuning): rules 191/209, with the fallback 202/209.

What limits these numbers: the replies are synthetic text, not speech and not STT output; one writer model; labels by construction; Tamil and Kannada unreviewed; n per cell is 3 to 9 in a fold. They show where the rules fail, not how the interpreter will do on real calls.

**What the measurement changed.**
- Before the fix, the rules ended 2 of the 72 fold-1 answers as declines. Both were a misled customer's sentence: "बाद में पता चला मुझे इसका" and its Tamil equivalent ("I found out about this later"). The cause was "later" as a short-turn decline word. I read those two fold-1 rows, so the 0 in the table is not strictly held out. Bare "later" words are gone and short stop phrases no longer end a call: they lead to the stop-check.
- On fold 0 the LLM took "நான் கிளை மேலாளர்ட்ட பேசிட்டேங்க" ("I spoke to the branch manager about it") for a request for a human, and "क्या काम है?" for a wrong number. So no LLM label ends a call: `decline` and `wants_human` lead to the stop-check, a "no" to "may we go on?" leads to the stop-check, and `wrong_person` is ignored.
- The fallback is justified for three things the rules miss on held-out replies: requests for a human (5 of 13), off-topic replies (the rules cannot detect these at all) and soft declines. It is off by default. `play --llm` and `eval-turns --llm` turn it on; the adapter chooses for live calls.
- Cost of the fallback: one call for each turn the rules leave as plain `said`, median 0.74 s and p95 1.87 s over 506 calls of `mistralai/mistral-small-3.2-24b-instruct` (from the shared ledger, identified by their shape). That is added silence on the line and the adapter must decide whether it is worth it.

**Failures left on fold 1 with the fallback (all 11):** three identity replies that mix a no or a yes with "who is this?" are re-asked instead of ended or confirmed; "That's not the figure I gave" is re-asked instead of read as a rejection; "எனக்கு ஒன்னும் புரியல" ("I understand none of this", meant as an answer) is re-asked; one Tamil request for "someone else to help" is taken as an answer; a colloquial Tamil amount ("இருபத்தி ஐயாயிரம்") is not parsed by `samajh.amounts`; two Kannada go-ahead replies are re-asked; one Kannada off-topic reply ("I have to leave right now") gets the stop-check, which is arguably right.

## 5. Independent review

PLACEHOLDER_REVIEW

## 6. Failures, known gaps, and what I changed from the spec

**Changed from the spec, and why.**
1. `start` takes a required `lender_name`. `LoanRecord` has no lender name and the disclosure must say one.
2. The year-of-birth check accepts two digits ("84"). A mismatch and an unclear reply get the same re-ask line, so the bot does not confirm a wrong guess as wrong. Two tries, then the call ends with no mention of a loan.
3. A go-ahead question follows the disclosure ("क्या हम आगे बढ़ें?"). The design says the customer can decline; this is where they are asked.
4. The disclosure says "the customer-care number printed on your papers from the lender", not "on the loan papers". DESIGN.md line 80 names the loan papers in step 2, and line 82 says the loan is first mentioned in step 4.
5. The close says "our team may call you again" only when the live call left something unresolved (an unclear answer, a rejected read-back, the turn budget). The machine cannot know about flags: they are computed after the call by the extractor and the rules. There is no "within N days".
6. The money-back probe (`asks=features`) is asked for every product, as the rule engine requires (W1 report section 7, decision 1).
7. Amounts below 100 or from 1,000,000,000 up are treated as no figure. `spoken_amount` raises outside 1 to 999,999,999, and read-back lines are only known to parse back from 100. Before this guard a customer saying "0 रुपये" or "5000000000" crashed `step`.
8. The stop-check (section 1, decision 3) is not in the design.
9. Process: I wrote the code myself and spawned one subagent, the reviewer. The planning pass was inline, not through `pstack-architect`. The Orca brief said to do the task myself and keep subagent use lean.

**Known gaps.**
- With several products of one family the customer cannot know which one "the first thing" is. Nothing that would tell them apart is safe to say. v1 has one product family and the demo record has one product.
- A customer who says in open recall that they took nothing is still asked nine questions about "the thing taken with the loan". They can say "don't know" to each (not re-asked), but it is a long call.
- The rule interpreter cannot tell an off-topic reply from an answer. Without the fallback such a reply is accepted and the call moves on; the extractor then finds no answer and the case goes to a human.
- Romanised Hindi amounts ("bavan hazaar") are refused by `samajh.amounts`, so a typed Hinglish call must use digits or English number words. Real Hinglish STT output with `format=transcribe` gives digits.
- Hedged amounts ("शायद बावन हज़ार") and two amounts in one reply are not read back. The premium question is asked once more, then left unresolved.
- A first-name "yes" from the wrong person followed by a correct birth year passes both checks. The design accepts this (section 5, "a first-name yes alone is a weak check").
- The 60-utterance budget ends a three-product call in which every answer is unclear before all questions are asked.
- `Turn.start_s` and `end_s` are left `None`. The transport knows the times; the adapter must fill them.
- The disclosure is one utterance of seven lines (about 700 characters in Hindi). W7's `BotUtterance.text` allows 600, so the adapter must send lines one by one.
- Lexicons are short lists. Section 4 shows what they miss.

## 7. Spend

Gnani credits: 0. OpenRouter: about USD 0.02 (0.0032 for writing the reply set, about 0.016 for 506 label calls; read from the shared ledger, so approximate). Subagents: one reviewer.

## 8. Documents this work makes stale

- `DESIGN.md` line 80 (step 2): "the customer-care number on the loan papers" names the loan before step 4. The line spoken says "papers from the lender". It also lacks the go-ahead question.
- `DESIGN.md` line 81 (step 3): does not say two tries, two-digit years accepted, or that failure ends the call with no mention of the loan.
- `DESIGN.md` line 84 (step 6): the quoted questions name insurance, FD, cover and "another company". The lines spoken name none of them, refer to the product by ordinal, and include the money-back probe. "from the loan amount, or separately?" is asked open.
- `DESIGN.md` line 86 (step 8): the read-back wording is "आपने बताया था बावन हज़ार, यानी 52,000। क्या यह सही है?", bounded at three read-backs per product, and only the premium is read back.
- `DESIGN.md` line 87 (step 9): "If anything was flagged: someone will call you within N days". The close says "may call again" and only on live signals; flags are not known during the call.
- `DESIGN.md` line 89: add the stop-check; "marked `unclear → human`" is `EndOfCall.unresolved` in code.
- `DESIGN.md` line 105 (diagram): "SCRIPT BUILDER" is `samajh/dialogue` plus `data/prompts/`; prompts are templates, and read-backs cannot be pre-generated because they carry the customer's figure.
- `DESIGN.md` line 213 (models table): "LLM ... Extraction only". There is now an optional LLM fallback for live turn reading (a label only, never a number, never ends a call).
- `DESIGN.md` line 319 (milestones): the call state machine exists.
- `ORCHESTRATION.md` line 82: W9 status.
- `CLAUDE.md` line 57 (files list): add `samajh/dialogue/` and `data/prompts/`.
- `CLAUDE.md` line 58: W7's `Dialogue` protocol still runs a `StubDialogue`; the adapter to `samajh.dialogue` is not written.
- `references/pilots/W1-core-report.md` section 3, script-builder contract item 2: the suggested read-back template works; a carrier word directly before a Tamil or Kannada amount does not (see section 3 above).

## 9. Next iteration, in this area

1. The adapter between W7's `Dialogue` protocol and `start` / `step`: persist `CallState` per session, send lines one at a time, fill turn times, map `Heard.text == ""` to silence, choose the interpreter.
2. Voice the 51 lines per language with Timbre (`Line.key` and `Line.slots` identify each clip; only the read-back lines and the three slots vary) and listen to them.
3. A fluent reader for Hindi and Hinglish, and reviewers for Tamil and Kannada, for the lines and the lexicons.
4. Rerun `eval-turns` on real STT output of improvised replies once recordings exist. The LLM-written set is a stopgap.
5. Decide whether live calls use the LLM fallback, given 0.74 s median added silence.
6. Add a lender name to `LoanRecord`, or keep it as call configuration.
