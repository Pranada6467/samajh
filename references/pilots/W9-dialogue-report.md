# W9 report: dialogue (call state machine and scripts)

Date: 2026-11-10. Built by the first W9 worker, which stopped on a usage limit before its review. Reviewed, fixed and finished by a second worker (W9b) that wrote none of the original code. Sections 1 to 4 and 6 describe the code as it stands after the review; section 5 is the review.

Goal: the bank's non-sales team needs a callback that tests what a borrower understood without telling them the answer. W9 is the conversation itself: a pure core that takes a loan record and the customer's words and decides the bot's next line, in the customer's language, following the v2 flow in DESIGN.md section 5. The experiment is void if the bot leaks a value it is testing, and the product is unsafe if it tells a stranger about the loan, never ends, or says something the design bans.

## 1. What was built (paths)

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
tests/dialogue/    10 test files, `dialogue_kit.py`, fixtures, `probes/gen_turns.py`
```

### Public surface

```python
from samajh.dialogue import start, step, CallState, BotUtterance, EndOfCall, Outcome, Limits, SecondReading

start(record: LoanRecord, language: Language, *, lender_name: str,
      call_id: str | None = None, limits: Limits | None = None) -> tuple[CallState, BotUtterance]
step(state: CallState, customer_text: str, *, second_reading: str | None = None,
     interpreter: TurnInterpreter = RuleInterpreter())
      -> tuple[CallState, BotUtterance | EndOfCall]

BotUtterance(language, lines: tuple[Line, ...]); .text joins the lines
Line(key, slots, text, step: CallStep, asks: Question | None, product_id: ProductId | None)
EndOfCall(utterance: BotUtterance, outcome: Outcome, transcript: Transcript, unresolved: tuple[Unresolved, ...])
CallState: .transcript() -> samajh.types.Transcript; model_dump_json() / model_validate_json() to persist
           .second_readings: tuple[SecondReading(turn_id, text, agreed), ...]
Outcome: completed, wrong_party, not_confirmed, no_go_ahead, second_check_failed, declined,
         human_requested, turn_limit
Limits(max_bot_turns=60, max_read_backs=3, max_stop_checks=2)

class TurnInterpreter(Protocol):
    def interpret(self, text, *, language, expecting: Expecting, question: str) -> Interpretation
Interpretation(intent, amount_inr, figures, year)

from samajh.dialogue.llm_fallback import LlmFallbackInterpreter, FALLBACK_MODEL
LlmFallbackInterpreter(llm: LlmClient, rules=None, *, model=FALLBACK_MODEL, max_tokens=512)
```

`step` raises `ValueError` on a call that has ended. `customer_text=""` means nothing was heard.

### How the states work

`CallState.position` says which reply the bot is waiting for. Each position is its own type:
`AtIdentity`, `AtGoAhead`, `AtBirthYear`, `AtRecall`, `AtTeachBack(product, question)`, `AtConsent`,
`AtReadBack(product, amount_inr, read_backs)`, `AtRestate(product, read_backs, rejected_inr)`, `AtStopCheck(wish, resume)`, `Ended(outcome)`.
The interpreter turns the reply into an `Intent` (the event). `step` maps (position, intent) to the next position and the next lines.

Four decisions shape everything else.

1. **The state does not hold the record.** `start` keeps a `CallPlan`: loan id, first name, birth year and product ids. Nothing else from the record survives, so no line can depend on a tested value. The only figures the bot says are ones the customer said first. The question list is the same for every record (choice of provider is always asked, though the rules need it only when the product was required), because which questions are asked would otherwise reveal `required_for_loan`.
2. **Products are named by ordinal, never by kind.** One product: "the thing taken with the loan". Several: "the first / second thing on our record with the loan". The words insurance, policy, premium, cover, FD and deposit are banned from every line by the lint, so the design's "Is this insurance, FD or something else?" became "आपके हिसाब से वो चीज़ क्या है?" and "What does it cover?" became "what do you get from it, and up to what amount?".
3. **Only a plain refusal ends the call at once.** A weak signal gets one question, "क्या आप यह कॉल यहीं रोकना चाहते हैं?". Yes ends the call; anything else goes back to the pending question as if its last reply had been unclear. Three things count as weak: a short "रहने दो", an LLM's guess, and (added in review) a refusal inside a sentence that recounts the sale ("मैंने कहा था मुझे इंटरेस्ट नहीं है पर उन्होंने..."). The question is asked twice a call at most; a third signal ends the call.
4. **An amount turn can be heard twice** (added in review; DESIGN.md section 15 item 16). `step` takes an optional `second_reading`, the transcript of the same audio from the other Prisma model. `samajh.amounts.cross_check` says whether the two agree. Every figure is read back before the close either way. Where the readings differ, the call acts on the first unless only the second brings a figure the customer has not just heard or rejected. `Turn.text` holds the reading the call acted on, so the rule engine reads the same figure the bot read back; the other reading is kept in `CallState.second_readings` with the `agreed` flag, for the evidence log. A second reading is ignored on turns where no figure is asked for.

One bot utterance can hold several lines (the disclosure is seven). Each line becomes its own bot `Turn`, and the last line is always the question, so the rules' "reply to the turn before it" linkage holds.

## 2. Evidence

```
$ uv run pytest tests/dialogue -q
........................................................................ [ 10%]
........................................................................ [ 21%]
........................................................................ [ 32%]
........................................................................ [ 42%]
........................................................................ [ 53%]
........................................................................ [ 64%]
........................................................................ [ 75%]
........................................................................ [ 85%]
........................................................................ [ 96%]
.......................                                                  [100%]
671 passed in 62.32s (0:01:02)
$ echo $?
0

$ uv run ruff check samajh/dialogue tests/dialogue
All checks passed!
$ uv run ruff format --check samajh/dialogue tests/dialogue
20 files already formatted
```

580 tests passed before the review. The review added 91: 86 in `test_review_findings.py` (76 of them failed before their fixes; 10 are controls that passed throughout), 4 in `test_no_leak_and_termination.py` (a property test written with the second-reading feature), 1 in `test_cli.py` (failed first). `tests/core` and `tests/server` were run afterwards as a check that nothing outside the lane moved: 1,483 passed.

What the tests cover, by file:

| File | Tests | What it holds the code to |
|---|---|---|
| `test_call_paths.py` | 279 | Scripted calls in all four languages: happy path; wrong party; no confirmation; decline and human request at each of 15 stages; unclear answers asked once more then recorded; "don't know" not re-asked; read-back of the customer's figure (record says 61,000, customer says 52,000, bot reads 52,000); correction and rejection at read-back; bounded read-back loop; two products; zero products; second check; weak stop signals; JSON round trip at every turn; turn budget |
| `test_no_leak_and_termination.py` | 41 | 200 random customers per language, each played against two records that differ in every tested value. Bot lines must be word-for-word identical, hold no record value, and the call must end inside its own bounds with the budget set to 10,000. The random pool includes the records' own values, format strings and out-of-range amounts. The same again with half the turns given a second transcript drawn from that pool. A self-test proves the scan fails on nine planted leaks |
| `test_review_findings.py` | 86 | Section 5: every defect the review proved, as a test that failed before its fix |
| `test_prompts.py` | 59 | Every language defines every line with a design paragraph; slots are exactly the declared ones; no banned wording, no digit; every line at most 240 characters; a read-back line parses back to its amount (about 2,500 amounts per language and line); 30 bad lines the lint must reject; a prompt file with banned wording or a wrong slot does not load |
| `test_interpret.py` | 151 | 118 labelled turns, including answers that hold refusal-like words and must stay answers; amounts; birth years |
| `test_llm_fallback.py` | 37 | The LLM is not called when the rules settle a turn; it sees only the question and the reply; no label ends a call; a failed call leaves the rule reading |
| `test_rules_consume_the_call.py` | 7 | A finished Hindi call plus a faithful extraction goes through `to_beliefs` and `evaluate` with no `not_asked`, `quote_not_grounded` or `readback_mismatch` gap, and flags `kind`, `bundling` and `belief_mismatch`; a premium corrected at read-back is the one compared |
| `test_heldout_turns.py` | 4 | Pins the measurement in section 4 |
| `test_cli.py` | 7 | `play` in each language, with the transcript written and re-validated; a turn typed as `first \|\| second` is heard twice |

### One full Hindi call

Typed lines were piped from a file; the CLI echoes them. One answer is unclear on purpose, and one answer quotes a refusal from the sale: the bot asks whether to stop and, on "no", goes back to the question.

```
$ uv run python -m samajh.dialogue play --record tests/dialogue/fixtures/record_gold_loan.json --lang hi < hi_call.txt
[hi prompts: written by the build agent, register pass by the review agent; no fluent human reviewer yet]
BOT  [right_party_check] नमस्ते। क्या मेरी बात Ramesh जी से हो रही है?
YOU> हाँ जी, बोल रहा हूँ
BOT  [disclosure] धन्यवाद। यह कॉल Namoona Bank की कस्टमर केयर टीम की तरफ़ से है। मैं एक ऑटोमेटेड ए-आई असिस्टेंट हूँ, कोई इंसान नहीं।
BOT  [disclosure] यह सेल्स कॉल नहीं है। इस कॉल में आपको कुछ भी बेचा नहीं जाएगा।
BOT  [disclosure] यह कॉल सिर्फ़ आपका फ़ीडबैक लेने के लिए है। फ़ीडबैक सही-सही दर्ज रहे, इसलिए कॉल रिकॉर्ड हो रही है। आपकी जानकारी का इस्तेमाल कैसे होता है, यह Namoona Bank के लिखित नोटिस में दिया है।
BOT  [disclosure] आप चाहें तो मना कर सकते हैं, बीच में कभी भी कॉल रोक सकते हैं, या किसी इंसान से बात करने को कह सकते हैं।
BOT  [disclosure] कॉल असली है या नहीं, यह जाँचने के लिए आप फ़ोन रखकर Namoona Bank के काग़ज़ों पर छपे कस्टमर केयर नंबर पर कॉल कर सकते हैं।
BOT  [disclosure] इस कॉल में आपसे ओ-टी-पी, पिन, पासवर्ड या खाता नंबर कभी नहीं पूछा जाएगा।
BOT  [disclosure] क्या हम आगे बढ़ें?
YOU> हाँ, ठीक है
BOT  [second_check] धन्यवाद। बस यह पक्का करने के लिए कि बात आप ही से हो रही है, अपने जन्म का साल बता दीजिए। सिर्फ़ साल, पूरी तारीख़ नहीं।
YOU> उन्नीस सौ चौरासी
BOT  [context] धन्यवाद। यह कॉल उस लोन के बारे में है जो आपने हाल ही में Namoona Bank से लिया है।
BOT  [open_recall] लोन के साथ आपने और क्या-क्या लिया, और कितने का? अपने शब्दों में बताइए।
YOU> बस एक एफडी, लोन सिक्योरिटी के लिए, बावन हज़ार की
BOT  [teach_back] धन्यवाद। अब लोन के साथ जो चीज़ ली गई, उसके बारे में कुछ छोटे-छोटे सवाल हैं।
BOT  [teach_back/kind] आपके हिसाब से वो चीज़ क्या है?
YOU> एफडी है
BOT  [teach_back/premium] उसके लिए आपने कितने पैसे दिए?
YOU> बावन हज़ार
BOT  [teach_back/payment_source] वो पैसे कहाँ से और कैसे दिए गए?
YOU> क्या? फिर से बोलिए
BOT  [teach_back/payment_source] मतलब, उस चीज़ का पैसा आपने कैसे भरा?
YOU> लोन में से कट गया
BOT  [teach_back/required_for_loan] लोन मिलने के लिए वो चीज़ लेना ज़रूरी था, या आपकी मर्ज़ी थी? आपको क्या बताया गया था?
YOU> मैंने कहा था मुझे इंटरेस्ट नहीं है पर उन्होंने बोला ज़रूरी है
BOT  [teach_back] क्या आप यह कॉल यहीं रोकना चाहते हैं?
YOU> नहीं नहीं, पूछिए
BOT  [teach_back/required_for_loan] मतलब, अगर आप वो चीज़ न लेते, तो क्या लोन मिलता? इस बारे में आपको क्या बताया गया था?
YOU> हाँ, बोला था ज़रूरी है
BOT  [teach_back/provider_choice] वो चीज़ कहाँ से लेनी है, इस बारे में आपको क्या बताया गया था?
YOU> कुछ नहीं बताया
BOT  [teach_back/cover] उस चीज़ से आपको क्या मिलता है, और कितनी रक़म तक?
YOU> पैसा सुरक्षित रहेगा
BOT  [teach_back/term] वो कितने समय के लिए है?
YOU> दो साल
BOT  [teach_back/cancel_window] क्या आपको बताया गया था कि वो चीज़ आप कैंसल करा सकते हैं या नहीं? और अगर हाँ, तो कब तक?
YOU> नहीं बताया
BOT  [teach_back/features] अगर आप यह पैसा वापस लेना चाहें, तो क्या होगा? अपने हिसाब से बताइए।
YOU> एक साल बाद निकाल सकते हैं
BOT  [consent_check/consent] लोन लेते समय आपने किन-किन चीज़ों के लिए हाँ की थी, और हाँ कैसे की थी?
YOU> फॉर्म पर साइन किया था बस
BOT  [read_back/premium] आपने बताया था बावन हज़ार, यानी 52,000। क्या यह सही है?
YOU> हाँ, सही है
BOT  [close] आपके समय और जवाबों के लिए धन्यवाद।
BOT  [close] नमस्ते।
[call ended: completed; unresolved questions: 0]
```

### One full Hinglish call

The customer corrects the figure at read-back in a sentence the amount parser cannot settle ("not fifty two, fifty five thousand"). The bot does not repeat 52,000; it asks for the right amount.

```
$ uv run python -m samajh.dialogue play --record tests/dialogue/fixtures/record_gold_loan.json --lang hi-en < hien_call.txt
[hi-en prompts: written by the build agent, register pass by the review agent; no fluent human reviewer yet]
BOT  [right_party_check] Hello। क्या मेरी बात Ramesh जी से हो रही है?
YOU> yes, speaking
BOT  [disclosure] Thank you। यह call Namoona Bank की customer care team की तरफ़ से है। मैं एक automated A-I assistant हूँ, कोई इंसान नहीं।
BOT  [disclosure] यह sales call नहीं है। इस call में आपको कुछ भी sell नहीं किया जाएगा।
BOT  [disclosure] यह call सिर्फ़ आपका feedback लेने के लिए है। Feedback का सही record रहे, इसलिए call record हो रही है। आपका data कैसे use होता है, यह Namoona Bank के written notice में दिया है।
BOT  [disclosure] आप चाहें तो मना कर सकते हैं, call कभी भी रोक सकते हैं, या किसी इंसान से बात करने को कह सकते हैं।
BOT  [disclosure] Call genuine है या नहीं, यह check करने के लिए आप phone रखकर Namoona Bank के papers पर छपे customer care number पर call कर सकते हैं।
BOT  [disclosure] इस call में आपसे O-T-P, PIN, password या account number कभी नहीं पूछा जाएगा।
BOT  [disclosure] क्या हम आगे बढ़ें?
YOU> हाँ okay
BOT  [second_check] Thank you। Confirm करने के लिए बस अपना birth year बता दीजिए। सिर्फ़ year, पूरी date नहीं।
YOU> 1984
BOT  [context] Thank you। यह call उस loan के बारे में है जो आपने हाल ही में Namoona Bank से लिया है।
BOT  [open_recall] Loan के साथ आपने और क्या-क्या लिया, और कितने का? अपने words में बताइए।
YOU> बस एक FD ली थी loan security के लिए, fifty two thousand की
BOT  [teach_back] Thank you। अब loan के साथ जो चीज़ ली गई, उसके बारे में कुछ छोटे questions हैं।
BOT  [teach_back/kind] आपके हिसाब से वो चीज़ क्या है?
YOU> FD है
BOT  [teach_back/premium] उसके लिए आपने कितना amount pay किया?
YOU> fifty two thousand
BOT  [teach_back/payment_source] वो payment कहाँ से और कैसे हुई?
YOU> loan amount से cut हो गया
BOT  [teach_back/required_for_loan] Loan मिलने के लिए वो चीज़ लेना ज़रूरी था या आपकी choice थी? आपको क्या बताया गया था?
YOU> हाँ, बोला था compulsory है
BOT  [teach_back/provider_choice] वो चीज़ कहाँ से लेनी है, इस बारे में आपको क्या बताया गया था?
YOU> कुछ नहीं बताया
BOT  [teach_back/cover] उस चीज़ से आपको क्या मिलता है, और कितने amount तक?
YOU> पैसा safe रहेगा
BOT  [teach_back/term] वो कितने time के लिए है?
YOU> two years
BOT  [teach_back/cancel_window] क्या आपको बताया गया था कि वो चीज़ आप cancel कर सकते हैं या नहीं, और अगर हाँ, तो कब तक?
YOU> नहीं बताया
BOT  [teach_back/features] अगर आप यह पैसा वापस लेना चाहें, तो क्या होगा? अपने हिसाब से बताइए।
YOU> one year बाद withdraw कर सकते हैं
BOT  [consent_check/consent] Loan लेते time आपने किन-किन चीज़ों के लिए हाँ बोला था, और हाँ कैसे बोला था?
YOU> form पर sign किया था बस
BOT  [read_back/premium] आपने बताया था fifty two thousand, यानी 52,000। क्या यह सही है?
YOU> not fifty two, fifty five thousand
BOT  [read_back/premium] ठीक है। तो सही amount क्या है?
YOU> fifty five thousand
BOT  [read_back/premium] आपने बताया था fifty five thousand, यानी 55,000। क्या यह सही है?
YOU> yes, correct
BOT  [close] आपके time और जवाबों के लिए thank you।
BOT  [close] नमस्ते।
[call ended: completed; unresolved questions: 0]
```

## 3. Claims

Verified, with source:
- The call steps, the content of the disclosure, the open consent and cancel questions: DESIGN.md section 5 and `references/claims/design-corrections.md` items 4, 5, 11 and 12, read on 2026-11-10. Each line in `data/prompts/*.toml` names the paragraph it implements.
- The transcript contract (tags, read-back turn, consent question without a product): `references/pilots/W1-core-report.md` section 3, and proven by `test_rules_consume_the_call.py` against the real rule engine.
- A read-back line parses back to its amount in all four languages for amounts from 100 to 50,000,000 (about 2,500 sampled amounts per language and line; `test_prompts.py`), against the amount parser as changed on 2026-11-10. The first Tamil and Kannada wording failed this for 37 and 4 of 4,745 sampled amounts, because `parse_amount` refuses an unknown word directly before a unit word. A colon before the amount fixed it.
- The dialogue uses the current `samajh.amounts` surface: `parse_amount` with `Parsed` / `Ambiguous` / `NoAmount`, `cross_check` with `Agreed`, `spoken_amount`, `format_inr`. An `Ambiguous` reading is never read back; its candidates are used only to notice that the customer named some other figure.
- Two-reading design: DESIGN.md section 15 item 16 ("Agreement is taken as the amount; disagreement, or a missing reading, always triggers a spoken read-back. The read-back remains for every critical amount regardless"). `test_the_rules_pass_a_premium_that_only_the_second_reading_got_right` runs the documented v3.0 mis-format (3,02,000 for "तीन लाख दो सौ") through the call and the rule engine.

Not verified:
- `[unverified]` The Tamil and Kannada lines, lexicons and scripted customers. All are `not human-reviewed` and labelled so in the data and in the CLI. The review read the Tamil lines for structure only (no product named, no loan before the context step) and changed none.
- `[unverified]` The Hindi and Hinglish lines were written by one agent and revised for register by another. No fluent human has read them.
- `[unverified]` Nothing has been voiced. Whether Timbre reads the mixed-script Hinglish lines, "ए-आई", "ओ-टी-पी" and the 215-character Tamil recording line well is for the voice worker to check.
- `[unverified]` The reply set in section 4 is LLM-written. No human said or labelled any of it. The review's probe sentences (section 5) are the reviewer's own, also not from a human caller.
- `[unverified]` No real pair of Prisma transcripts has been played into `second_reading`. The tests use hand-written pairs.

## 4. Turn interpretation: the measured gap and what it changed

**What was measured.** 408 customer replies: 17 behaviours × 4 languages × 6 replies, written by `google/gemini-2.5-flash-lite` from a behaviour description (`tests/dialogue/probes/gen_turns.py`). The gold label is the effect the reply should have on the call (answered, reask, decline, human, confirmed, ...). It is what the writer was told to write, not a human judgement, and some labels are wrong (a "confirmation" that states a different amount, for example). Each reply is played into the real machine at the right position and the effect is compared (`python -m samajh.dialogue eval-turns`). Rows are split into two folds by a hash. Fold 0 (n = 209) was used to tune the word lists and the fallback prompt. Fold 1 (n = 199) was not, with one exception stated below.

Numbers after the review changes (rerun 2026-11-10):

| Fold 1 (held out), n = 199 | Rules only | Rules + LLM fallback |
|---|---|---|
| All replies with the labelled effect | 155 (78%) | 187 (94%) |
| Hindi / Hinglish / Tamil / Kannada | 41/49, 45/52, 36/53, 33/45 | 48/49, 50/52, 47/53, 42/45 |
| Asked for a human (n = 13) | 5 | 12 (7 of them after the stop-check) |
| Unclear or off-topic (n = 36) | 18 | 34 |
| Declined (n = 22) | 17 | 21 (4 after the stop-check) |
| Answers (n = 72) | 66 | 70 |
| Calls ended on a reply that was not a refusal | 0 | 0 |

Fold 0 for comparison (in-sample after tuning): rules 191/209, with the fallback 202/209.

The rules-only numbers are the same as before the review, row for row. The review's word-list additions came from the reviewer's own probes and none of them matched a missed row of this set, so they are not shown to help on it. With the fallback the total was 188 before the review and is 187 now: the Hindi question wording changed, the LLM sees the question, and it now reads "यह बहुत सुंदर है, लेकिन मुझे देर हो रही है।" as an answer. One reply is not a trend.

What limits these numbers: the replies are synthetic text, not speech and not STT output; one writer model; labels by construction; Tamil and Kannada unreviewed; n per cell is 3 to 9 in a fold. They show where the rules fail, not how the interpreter will do on real calls.

**What the measurement changed (first worker).**
- Before the fix, the rules ended 2 of the 72 fold-1 answers as declines. Both were a misled customer's sentence: "बाद में पता चला मुझे इसका" and its Tamil equivalent ("I found out about this later"). The cause was "later" as a short-turn decline word. Those two fold-1 rows were read, so the 0 in the table is not strictly held out. Bare "later" words are gone and short stop phrases no longer end a call: they lead to the stop-check.
- On fold 0 the LLM took "நான் கிளை மேலாளர்ட்ட பேசிட்டேங்க" ("I spoke to the branch manager about it") for a request for a human, and "क्या काम है?" for a wrong number. So no LLM label ends a call: `decline` and `wants_human` lead to the stop-check, a "no" to "may we go on?" leads to the stop-check, and `wrong_person` is ignored.
- The fallback is justified for three things the rules miss on held-out replies: requests for a human (5 of 13), off-topic replies (the rules cannot detect these at all) and soft declines. It is off by default. `play --llm` and `eval-turns --llm` turn it on; the adapter chooses for live calls.
- Cost of the fallback: one call for each turn the rules leave as plain `said` (115 of the 408 replies). Median 0.74 s and p95 1.87 s over the first worker's 506 calls of `mistralai/mistral-small-3.2-24b-instruct`; median 0.77 s and p95 1.22 s over the 42 uncached calls of the review rerun (from the shared ledger). That is added silence on the line and the adapter must decide whether it is worth it.

**Failures left on fold 1 with the fallback (all 12):** three identity replies that mix a no or a yes with "who is this?" are re-asked instead of ended or confirmed; one Tamil "nobody of that name here" is re-asked; "That's not the figure I gave" is re-asked instead of read as a rejection; "எனக்கு ஒன்னும் புரியல" ("I understand none of this", meant as an answer) is re-asked; one Tamil request for "someone else to help" is taken as an answer; a colloquial Tamil amount ("இருபத்தி ஐயாயிரம்") is not parsed by `samajh.amounts`; two Kannada go-ahead replies are re-asked; one Kannada off-topic reply ("I have to leave right now") gets the stop-check, which is arguably right; the Hindi off-topic reply above is taken as an answer.

## 5. Independent review

Reviewer: W9b, at high effort, having written none of the code under review. Method: read the spec and the code, then attack by running the real machine. Four scripts of probes (about 250 hand-written replies and prompt lines in Hindi, Hinglish and English, plus random and adversarial interpreters) were played into `start` / `step`. Every defect below was reproduced by a run before it was fixed, and each fix has a test that failed first (`tests/dialogue/test_review_findings.py`). The probes are the reviewer's sentences: no human said them, and the counts are counts of probes, not rates.

### Proved and fixed

| # | What was proved (run, before the fix) | Fix | Test |
|---|---|---|---|
| R1 | **The loan was named to someone who had just said they were not the borrower.** After a first-name "yes", "मैं उनकी पत्नी हूँ, उनका जन्म 1984 में हुआ" at the second check passed it, and the bot said "यह कॉल उस लोन के बारे में है...". Same for "पापा का जन्म 1984 का है", "रॉन्ग नंबर है, 1984" and an English form. "मैं उनका बेटा हूँ, हाँ बताइए" at the go-ahead went on to the second check. Cause: wrong-person phrases were read only at the first question. | They are read at all three steps before the loan is named, and the second check looks for them before it looks for the year. | `test_someone_who_says_they_are_not_the_borrower_cannot_pass_the_second_check`, `..._when_asked_to_go_on_ends_the_call` |
| R2 | **"एक बार फिर बोलिए" passed the second check** for a borrower born in 2001: "एक" was read as the two-digit year 01. "दो" passed for 2002, "पाँच" for 2005, "zero" for 2000, "one second" for 2001. | A two-digit year passes only from 10 up. "2002" and "दो हज़ार दो" still pass, and "84" still passes for 1984. | `test_a_single_digit_is_not_a_birth_year`, `test_the_year_itself_still_passes` |
| R3 | **A reply about the borrower in the third person was a "yes".** 9 of 21 identity probes: "हाँ जी, उसकी मम्मी बोल रही हूँ", "रमेश तो ऑफिस गए हैं, बताइए", "जी वो बाहर हैं आप बताइए", "this is his brother speaking", "he's at work, yes tell me". They got the disclosure, which names the lender (not the loan). | Added उसका / उसकी / उसके, इनका / इनकी / इनके, "बाहर हैं", "ऑफिस गए", "नहा रहे", "सो रहे", "his", "he's", "she's", "at work" and a few more to the wrong-person list. | `test_a_reply_that_speaks_of_the_borrower_as_someone_else_is_not_a_yes` |
| R4 | **An account of the sale that quoted a refusal ended the call.** 11 of 16 probes at a teach-back question: "मैंने कहा था मुझे इंटरेस्ट नहीं है पर उन्होंने ज़बरदस्ती दे दिया" ended as `declined`; "एजेंट ने कहा था मैनेजर से बात करा देंगे पर किसी ने नहीं कराई" ended as `human_requested`; "I told them I am not interested but they said it is compulsory" ended as `declined`. These are the sentences the product exists to hear. Turn length does not separate them from real refusals (real ones in the labelled set run to 12 words), so the fix does not use length. | From open recall on, a refusal phrase in a turn that also holds a past-tense or reported-speech word (था, थी, उन्होंने, मैंने, बोला, कहा, बताया; said, told, they, was, were) is a weak signal: the bot asks "क्या आप यह कॉल यहीं रोकना चाहते हैं?". Before open recall there is no sale to recount, so a refusal there still ends the call at once. Hindi and English only. | `test_a_refusal_quoted_in_an_answer_is_asked_about_and_does_not_end_the_call`, `test_a_refusal_before_the_questions_start_ends_the_call_at_once` |
| R5 | **The stop question had no limit of its own.** A customer who alternated "रहने दो" and "नहीं" was asked "do you want to stop this call?" 20 times in one call. DESIGN.md section 5 cites the "nagging" pattern (A20) as the reason for one re-ask. | `Limits.max_stop_checks = 2`. A third signal ends the call as declined (or human requested). | `test_the_stop_question_is_asked_twice_at_most_then_a_third_signal_ends_the_call` |
| R6 | **A correction at read-back was answered with the same figure again.** After "आपने बताया था बावन हज़ार...", the replies "शायद पचपन हज़ार", "पचपन", "not fifty two, fifty five thousand", "it was 55,000 not 52,000" and "fifty five" each got "एक बार फिर: बावन हज़ार, यानी 52,000। यह सही है या नहीं?". The parser rightly refuses to pick an amount from them, and the machine took "no amount" for "nothing said". | `Interpretation.figures` carries the numbers of an `Ambiguous` reading. At a read-back, a reply that names a figure other than the one read, without a yes, gets "तो सही रक़म क्या है?". The bot never speaks a figure from `figures`. A hedge that names no other figure ("शायद", "शायद बावन हज़ार") still gets the read-back once more. | `test_a_reply_that_names_another_figure_is_never_answered_with_the_same_read_back`, `test_a_hedge_that_names_no_other_figure_gets_the_read_back_once_more` |
| R7 | **"पता नहीं" to a read-back was read as "no"**, because it holds "नहीं". The bot replied "ठीक है। तो सही रक़म क्या है?" to a customer who had said they did not know. | At a read-back "don't know" is read before yes and no. The premium is recorded as unresolved, the bot says "कोई बात नहीं, आगे बढ़ते हैं" and does not ask again. | `test_dont_know_to_a_read_back_is_recorded_and_not_pressed`, `test_dont_know_beats_the_no_inside_it_when_a_read_back_is_answered` |
| R8 | **No second reading.** `step` took one transcript; `cross_check` was not used anywhere. | Decision 4 in section 1. With "3,02,000" and "तीन लाख दो सौ" as the two readings: the bot reads back 3,02,000, the customer says no, restates, the first reading is the rejected figure again, so the call acts on the second and reads back 3,00,200. A plain "yes" to a read-back stands whatever the second reading adds. | Seven tests named `..._reading...` / `..._readings...`, and a random-input property test in `test_no_leak_and_termination.py` |
| R9 | **The lint passed 23 of 52 bad probe lines.** Among them requests the spec names: "अपने खाते के आख़िरी चार अंक बताइए", "last four digits of your account", "अपनी जन्म तारीख़ बताइए", "डेट ऑफ बर्थ", "D.O.B.", "कार्ड के नंबर". Also "आपका पैसा लौटा दिया जाएगा", "आपको कैंसल करने का अधिकार है", "क्रेडिट लाइफ़", "हमारा नया प्लान लीजिए". No shipped line held any of these. | Added account, card and last-four-digit words, more date-of-birth forms, more money-back promises, a new ban on lines that state a right, benefit and guarantee words, and "शिकायत". 5 of the 52 still pass (see below). | `test_the_lint_rejects_what_the_review_slipped_past_it` (17 lines) |
| R11 | **The LLM fallback could fail without a trace.** Found by the coordinator after the review, not by it: the review reran the fallback while the client's default model was still the one the fallback had been tuned on. The fallback took the client's default model and sent `max_tokens=30`. When the default became `openai/gpt-6-luna`, a reasoning model, every call came back `finish_reason=length` with empty content, the error was caught, and the rule reading was returned as if the LLM had agreed. | The fallback names its own model (`FALLBACK_MODEL`, chosen by the measurement in section 4) and sends `max_tokens=512`. A failed call is read as the new `Intent.unclear`, so the bot asks once more, and a warning is logged with the error type, the model and the error text, never the customer's words. | `test_the_fallback_names_its_own_model_and_leaves_room_for_the_reply`, `test_a_failed_llm_call_is_read_as_unclear_and_the_reason_is_logged`, `test_a_failed_llm_call_gets_the_question_asked_once_more_and_never_ends_the_call` |
| R10 | **Short refusals got the next question.** Of 39 refusal phrasings at a teach-back question, 10 ended the call or got the stop question; 29 were taken as answers ("not interested", "मुझे नहीं बताना", "मैं नहीं बताऊंगा", "टाइम नहीं है मेरे पास", "अभी बात नहीं कर सकता", "ठीक है बाय"). The bot does not argue with them, but it does not stop either. | Ten Hindi and four English short phrases added as weak signals (they lead to the stop question, never straight to the end). Now 19 of the 39 are caught and 20 are not. | `test_a_short_refusal_gets_the_stop_question_not_the_next_question` |

### Tried and held

- **Revealing a tested value** (kind, premium, payment source, cover, term, cancel window, consent method, provider). The state keeps no tested value, so there is nothing to reveal; the attack was to find a path where the lines differ by record. Two records that differ in every tested value got identical bot lines over 200 random customers × 4 languages (existing test), over the same with second transcripts drawn from the records' own values (new test), and over 1,200 calls driven by an interpreter that returns random intents, amounts and years. No line held a record value. The only figures spoken were read-backs of what the customer had said.
- **Naming the loan before the checks.** With an interpreter that returns anything but the right year, 300 calls never reached the context step and no line held "लोन". No line before the context step holds a loan word in any language (existing scan). Apart from R1 and R2, nothing got through.
- **Running past its limits.** 1,200 random-interpreter calls all ended, the longest in 23 utterances against a bound of 117 with the turn budget set to 10,000. The random-interpreter calls end early because random refusals end them, so they say little about deep paths; the random-customer property tests cover those. Apart from R5, nothing found.
- **Banned wording, sales phrases, requests for secrets.** All 204 lines pass the lint, before and after its extension. The Hindi and Hinglish lines were also read one by one. The only line that names OTP, PIN, password or account number is the one that says they will never be asked for.
- **Arguing with or persuading a customer who declines.** After a refusal the bot says one closing line and stops, at each of 15 stages in four languages (existing test). After "no" or silence to the stop question it goes back to the pending question once. No line gives a reason to stay.
- **Reading back the record's premium.** 40 Hindi and 18 Hinglish reply shapes at read-back: the bot never said a figure the customer had not said. With the record at 61,000 and the customer at 52,000 it reads 52,000 (existing test).
- **A transcript the rules or the validators reject.** 400 finished random calls went through `to_beliefs` and `evaluate` with an empty extraction and raised nothing. Every customer turn follows a bot turn of the same step, and every state and transcript survived a JSON round trip.
- **The amount API.** The calls match `samajh.amounts` as it stands today. The ambiguous shapes the parser now refuses come back as no amount: the premium question is asked once more, and a read-back falls to R6's path.

### Proved and not fixed

1. "मैं रमेश नहीं हूँ पर 1984" at the second check still passes. Reading "नहीं हूँ" as "wrong person" fixed it but made two held-out identity replies end where the label says re-ask, so it was taken out. The speaker had said yes to the name one turn earlier.
2. "मैं सुरेश बोल रहा हूँ" at the first question is a "yes": the interpreter does not see the borrower's name. The speaker hears the lender's name and then meets the second check. A bare "बोलिए" or "जी" is also a yes, as designed.
3. "हाँ सही है। और कवर पाँच लाख था" at a read-back replaces the premium with 5,00,000 and reads that back. The customer can say no; the loop is bounded.
4. "no fifty five thousand" with no comma is refused by `parse_amount` (a negator before the amount), though "नहीं पचपन हज़ार" parses. The bot asks for the right amount, which costs one turn. The parser belongs to W1.
5. "कुछ नहीं दिया" and "फ्री था" at the premium question are asked once more and then recorded as unresolved. They are clear answers and the transcript keeps them for the extractor.
6. The bot's words show that the record holds a product ("the thing taken with the loan") and how many ("the first thing"). The design asks for teach-back per product on record, so this stays.
7. The lint is a word list. 5 of the 52 probe lines still pass: "एक मिनट और दीजिए प्लीज़", "आपको यह बात समझनी चाहिए", "आपके साथ ग़लत हुआ है", "यह कंपल्सरी नहीं था", "आप इसे तीस दिन में रद्द कर सकते हैं". A person must read any change to the prompt files.
8. R4 is Hindi and English only. A quoted refusal still ends a call in Tamil and Kannada. In any language a third quoted refusal in one call ends it (R5's limit).
9. R10 leaves 20 of 39 probe refusals unrecognised without the LLM fallback, among them "बाद में", "कल फोन करना", "मैं मीटिंग में हूँ", "i'm driving" and two 7-word refusals that the 6-word limit on weak signals excludes. Raising the limit to 8 changed nothing on the labelled set, so it stays at 6.

### Wording pass (Hindi and Hinglish)

Fourteen Hindi and eleven Hinglish lines were rewritten, and "वह" became "वो" in every spoken line of both files. Tamil and Kannada were not changed. Examples:

| Line | Before | After |
|---|---|---|
| `second_check.ask` (hi) | पुष्टि के लिए बस अपने जन्म का साल बता दीजिए। | बस यह पक्का करने के लिए कि बात आप ही से हो रही है, अपने जन्म का साल बता दीजिए। |
| `teach_back.intro_nth` (hi) | अब लोन के साथ दर्ज {ordinal} चीज़ के बारे में... | अब लोन के साथ हमारे रिकॉर्ड में जो {ordinal} चीज़ है, उसके बारे में... |
| `kind.ask` (hi, hi-en) | आपकी समझ से वह चीज़ क्या है? | आपके हिसाब से वो चीज़ क्या है? |
| `consent.ask` (hi) | ...क्या-क्या लेने की हामी भरी थी, और हामी किस तरह दी थी? | ...किन-किन चीज़ों के लिए हाँ की थी, और हाँ कैसे की थी? |
| `cancel_window.ask` (hi) | ...वह चीज़ आप रद्द कर सकते हैं या नहीं, और अगर हाँ, तो कब तक? | ...वो चीज़ आप कैंसल करा सकते हैं या नहीं? और अगर हाँ, तो कब तक? |
| `end.human` (hi) | हमारी टीम के एक साथी आपसे संपर्क करेंगे। | हमारी टीम से कोई आपको कॉल करेगा। |
| `end.neutral` (hi-en) | आपको disturb किया, sorry। | Disturb करने के लिए sorry। |
| `payment_source.ask` (hi-en) | वह payment कहाँ से और कैसे हुआ? | वो payment कहाँ से और कैसे हुई? |

The read-back lines were left alone: they are tied to the parse-back test. The files' `review` label now reads "written by the build agent, register pass by the review agent; no fluent human reviewer yet". This pass is one agent's judgement of register, not a native speaker's.

### What the review did not do

No second independent reviewer has seen the fixes in this section. Nothing was voiced or heard. Tamil and Kannada probes were not written, because the reviewer cannot judge them.

## 6. Failures, known gaps, and changes from the spec

**Changed from the spec, and why.**
1. `start` takes a required `lender_name`. `LoanRecord` has no lender name and the disclosure must say one.
2. The year-of-birth check accepts two digits ("84") when the year's last two digits are 10 or more. A mismatch and an unclear reply get the same re-ask line, so the bot does not confirm a wrong guess as wrong. Two tries, then the call ends with no mention of a loan.
3. A go-ahead question follows the disclosure ("क्या हम आगे बढ़ें?"). The design says the customer can decline; this is where they are asked.
4. The disclosure says "the customer-care number printed on your papers from the lender", not "on the loan papers". DESIGN.md line 80 names the loan papers in step 2, and line 82 says the loan is first mentioned in step 4.
5. The close says "our team may call you again" only when the live call left something unresolved (an unclear answer, a rejected read-back, the turn budget). The machine cannot know about flags: they are computed after the call by the extractor and the rules. There is no "within N days".
6. The money-back probe (`asks=features`) is asked for every product, as the rule engine requires (W1 report section 7, decision 1).
7. Amounts below 100 or from 1,000,000,000 up are treated as no figure. `spoken_amount` raises outside 1 to 999,999,999, and read-back lines are only known to parse back from 100.
8. The stop-check (section 1, decision 3) and its limit of two a call are not in the design.
9. On differing readings the design says only that a read-back follows. Which reading the call acts on, and that `Turn.text` holds that reading, are this package's choices (section 1, decision 4).
10. Process: the first worker wrote the code itself, and its reviewer subagent never ran. The review was done by a second worker with no subagents. The planning pass was inline, not through `pstack-architect`.

**Known gaps** (section 5 "Proved and not fixed" lists nine more).
- With several products of one family the customer cannot know which one "the first thing" is. Nothing that would tell them apart is safe to say. v1 has one product family and the demo record has one product.
- A customer who says in open recall that they took nothing is still asked nine questions about "the thing taken with the loan". They can say "don't know" to each (not re-asked), but it is a long call.
- The rule interpreter cannot tell an off-topic reply from an answer. Without the fallback such a reply is accepted and the call moves on; the extractor then finds no answer and the case goes to a human.
- Romanised Hindi amounts ("bavan hazaar") are refused by `samajh.amounts`, so a typed Hinglish call must use digits or English number words unless a second reading supplies them. Real Hinglish STT output with `format=transcribe` gives digits.
- Hedged amounts ("शायद बावन हज़ार") and two amounts in one reply are not taken as the premium. The premium question is asked once more, then left unresolved.
- A first-name "yes" from the wrong person followed by a correct birth year passes both checks. The design accepts this (section 5, "a first-name yes alone is a weak check").
- The 60-utterance budget ends a three-product call in which every answer is unclear before all questions are asked.
- `Turn.start_s` and `end_s` are left `None`. The transport knows the times; the adapter must fill them.
- The disclosure is one utterance of seven lines (about 700 characters in Hindi). W7's `BotUtterance.text` allows 600, so the adapter must send lines one by one.
- When the call acts on a second reading, the intent is also read from that reading. A first reading that said "don't know" and a second that holds a figure gives a read-back of the figure.
- With the LLM fallback on and OpenRouter failing, every reply the rules leave as plain `said` is read as unclear: each open question is asked twice and then recorded as unresolved. That is the price of not failing silently. How long a failing call holds a turn depends on the client the adapter passes in: `LlmClient` defaults to a 60 s timeout with retries, which is far too long for a live turn.
- Lexicons are short lists. Section 4 shows what they miss.

## 7. Spend

Gnani credits: 0. OpenRouter: about USD 0.02 by the first worker (0.0032 for writing the reply set, about 0.016 for 506 label calls) and USD 0.0007 by the review (115 label calls, 73 from cache; `mistralai/mistral-small-3.2-24b-instruct`). Both read from the shared ledger, so approximate. Subagents: none ran to completion; the review used none.

## 8. Documents this work makes stale

Line numbers as of 2026-11-10, after other workers' edits to the same files.

- `DESIGN.md` line 80 (step 2): "the customer-care number on the loan papers" names the loan before step 4. The line spoken says "papers from the lender". It also lacks the go-ahead question.
- `DESIGN.md` line 81 (step 3): does not say two tries, that a two-digit year passes only from 10 up, that a speaker who says they are someone else fails the check even with the right year, or that failure ends the call with no mention of the loan.
- `DESIGN.md` line 84 (step 6): the quoted questions name insurance, FD, cover and "another company". The lines spoken name none of them, refer to the product by ordinal, and include the money-back probe. "from the loan amount, or separately?" is asked open.
- `DESIGN.md` line 86 (step 8): the read-back wording is "आपने बताया था बावन हज़ार, यानी 52,000। क्या यह सही है?", bounded at three read-backs per product, and only the premium is read back. A reply that names another figure gets "तो सही रक़म क्या है?"; "don't know" is recorded and not pressed.
- `DESIGN.md` line 87 (step 9): "If anything was flagged: someone will call you within N days". The close says "may call again" and only on live signals; flags are not known during the call.
- `DESIGN.md` line 89: add the stop-check, its limit of two a call, and that a refusal quoted in an account of the sale leads to it; "marked `unclear → human`" is `EndOfCall.unresolved` in code.
- `DESIGN.md` line 105 (diagram): "SCRIPT BUILDER" is `samajh/dialogue` plus `data/prompts/`; prompts are templates, and read-backs cannot be pre-generated because they carry the customer's figure.
- `DESIGN.md` line 213 (models table): "LLM ... Extraction only". There is now an optional LLM fallback for live turn reading (a label only, never a number, never ends a call).
- `DESIGN.md` line 325 (milestones, week 2): "call state machine for the §5 flow" exists.
- `DESIGN.md` line 357 (open decision 16): add how the dialogue applies it: `step(..., second_reading=...)`; the call acts on the first reading unless only the second brings a figure the customer has not just heard or rejected; `Turn.text` is the reading acted on and the other is kept in `CallState.second_readings`.
- `ORCHESTRATION.md` line 82: W9 status ("Replacement W9b in progress") is now done: 671 tests, ruff clean, reviewed by W9b; the review's fixes have no second review. Report: `references/pilots/W9-dialogue-report.md`.
- `CLAUDE.md` line 57 (files list): "the extractor and dialogue are in progress (replacement workers W5b and W9b...)": dialogue is done. Add `samajh/dialogue/` (call core, `python -m samajh.dialogue play`) and `data/prompts/`.
- `CLAUDE.md` line 58: W7's `Dialogue` protocol still runs a `StubDialogue`; the adapter to `samajh.dialogue` is not written, and it is the place that must fetch the second Prisma reading on amount turns (`expecting(state.position)` says when).
- `references/pilots/W1-core-report.md` section 3, script-builder contract item 2: the suggested read-back template works; a carrier word directly before a Tamil or Kannada amount does not (see section 3 above). Line 64 can now say where `cross_check` is called: `samajh/dialogue/machine.py`, `step`.

## 9. Next iteration, in this area

1. The adapter between W7's `Dialogue` protocol and `start` / `step`: persist `CallState` per session, send lines one at a time, fill turn times, map `Heard.text == ""` to silence, choose the interpreter, and on turns where `expecting(state.position)` is `amount` or `confirmation` transcribe with both Prisma models and pass the second as `second_reading`. Which model is "first" is the adapter's choice; the 3,02,000 case argues for v2.5 first on amounts that skip a group, and nothing here measures it.
2. Play real pairs of Prisma transcripts (the 240-sentence amounts set has both models' output) through `step` and count how often the call ends on the right figure.
3. Voice the 51 lines per language with Timbre (`Line.key` and `Line.slots` identify each clip; only the read-back lines and the three slots vary) and listen to them.
4. A fluent human reader for Hindi and Hinglish, and reviewers for Tamil and Kannada, for the lines and the lexicons, including a reported-speech list so that R4 covers Tamil and Kannada.
5. Rerun `eval-turns` on real STT output of improvised replies once recordings exist. The LLM-written set is a stopgap, and section 5's probes are one reviewer's sentences.
6. Decide whether live calls use the LLM fallback, given about 0.75 s median added silence.
7. A second independent review of section 5's fixes.
8. Add a lender name to `LoanRecord`, or keep it as call configuration.
