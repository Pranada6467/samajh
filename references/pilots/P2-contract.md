# P2 contract: call v2, public API of `samajh.dialogue`

Written 2026-11-10 by the P2 execution manager, before the code. P1 may code against this now.
Changes after this point are additive only. `samajh/dialogue/__init__.py` is the source if the two differ.

## 1. What does not change

```python
start(record, language, *, lender_name, call_id=None, limits=None) -> (CallState, BotUtterance)
step(state, customer_text, *, second_reading=None, interpreter=RuleInterpreter()) -> (CallState, BotUtterance | EndOfCall)
expecting(position) -> Expecting
BotUtterance(language, lines: tuple[Line, ...]).text;  Line(key, slots, text, step, asks, product_id)
EndOfCall(utterance, outcome, transcript, unresolved);  CallState JSON round trip;  CallState.transcript()
LINES, PRODUCT_QUESTIONS, load_prompts(language).render(key, **slots) / .ordinals
LlmFallbackInterpreter(llm, rules=None, *, model=FALLBACK_MODEL, max_tokens=512)
```

- The opening still takes three customer turns in the same order: first name, "may I ask a few questions?", year of birth. The loan is first named after the year passes, in the line whose key is still `context.loan`. The lender is first named in `disclosure.who`, after the first-name yes.
- `Expecting` values that exist keep their meaning for a listener: `identity`, `go_ahead`, `confirmation`, `stop_check` are yes/no; `birth_year` is short; `amount` and `confirmation` may carry a figure.
- Every existing `Outcome` value keeps its name and meaning.
- The only slots are still `first_name`, `lender`, `ordinal`, `amount_words`, `amount_digits`. A line with an amount slot cannot be pre-made.

## 2. Additive changes

```python
class Outcome:                      # new values
    call_back_later                 # the customer asked to be called another time
    language_switch                 # the customer asked for another language; the call ends, no live switch
    no_response                     # nothing heard `Limits.max_silences` times in a row

class EndOfCall / CallState:        # new optional fields, default None / empty
    callback_time: str | None       # the customer's own words for when to call ("शाम को कॉल करना"); never parsed
    requested_language: str | None  # English name in lower case: "tamil", "english", ...; None if not said
    degraded_turns: tuple[TurnId, ...]   # customer turns the LLM fallback failed on; they were read by the word lists alone

class Limits:                       # new fields with defaults
    max_silences: int = 2           # consecutive turns with nothing heard before the call ends as no_response
    max_side_answers: int = 2       # times a call answers "who is this / is this a fraud call?" before treating it as unclear

class Expecting:                    # new values; a listener that does not know one should listen as "open"
    either_or                       # "was it required, or your choice?": a bare yes or no is not an answer
    callback_time                   # "when should we call?": any reply is the answer

LlmFallbackInterpreter(..., timeout_s: float | None = 2.5)   # wall-clock limit on one LLM call, enforced here
call_seconds(transcript, *, words_per_second=2.5) -> float   # samajh.dialogue: speech time of a call; uses Turn.start_s/end_s where set, word counts elsewhere
```

`FROM_DIALOGUE` in `samajh/ops/model.py` needs three lines: `call_back_later -> call_back_later`, `language_switch -> incomplete` (or its own value), `no_response -> no_answer` (or `incomplete`). P2 does not edit that file.

## 3. Behaviour P1 must know

1. **Two readings.** Pass the two transcripts of an amount turn in either order. `second_reading=""` means the second model was asked and returned nothing; `None` means no second reading was tried (then the call behaves as with one model). On a premium answer: both give the same figure, it is read back at once; they differ or one has no figure, the bot asks the customer to say the amount once more (one time per product), then reads back. At a read-back: both say yes, confirmed; one yes and one no, the read-back is said again. The verifier's order question (H4) no longer matters: the call never reads back a figure only one model heard on the first try.
2. **The read-back now follows the premium answer directly** (`step=read_back`, `asks=premium`, same tags as before), not after the consent question.
3. **A bot utterance is at most 600 characters** in Hindi and Hinglish with a lender name of 40 characters or fewer (tested). The seven-line disclosure is gone: the opening utterance after the first-name yes is four short lines.
4. **Silence.** `step(state, "")` twice in a row ends the call as `no_response`.
5. **The LLM fallback.** Build the client as you do now (short timeout, one attempt). A failed or late LLM call no longer makes the bot re-ask: the turn is read by the word lists, a warning is logged and the turn id is added to `degraded_turns`. With the fallback on, an unlisted refusal ("I am driving") ends the call or gets one "shall I continue?"; with it off, only listed phrases do.
6. **Who is believed.** At the first-name question only an unambiguous first-person yes continues. Anything else gets one re-ask ("are you <first name> yourself?"), and a speaker who says or implies they are someone else gets `end.third_party` and `wrong_party`. The LLM is not consulted at this step.
7. **Line keys.** Added: `open_recall.nothing`, `payment_frequency.ask/.reask`, `premium.say_again`, `read_back.confirm_about`, `verify.before_loan`, `verify.after_loan`, `callback.when`, `end.call_back`, `end.language`, `end.third_party`, `end.no_response`, `close.verify`, `close.notice`. Removed: `disclosure.verify` (now `verify.*`, said on request and at the close). Read `LINES` for the list; do not hard-code keys.
8. **Questions.** Per product: kind, premium (then its read-back), payment source, payment frequency (`asks=Question.payment_frequency`, P3a contract), required for loan, provider choice (asked only when the customer does not say it was their own choice), cover, term, cancel window, features. A customer who says they took nothing gets one follow-up and the consent question; the product questions are then not asked, so the transcript has no turn tagged with them.

## 4. Open

- `parse_approx_amount` (P3a contract §4) is not in `samajh.amounts` yet. Until it is, an approximate amount is re-asked as today; the range read-back is built against the contract and switched on when the function exists.

## 5. As built (P2 builder, end of package; this section wins over §1 to §4 where they differ)

- **Line keys.** Added: `open_recall.nothing`, `payment_frequency.ask`, `payment_frequency.reask`,
  `premium.say_again`, `read_back.confirm_about`, `read_back.cover_confirm`, `verify.before_loan`,
  `verify.after_loan`, `callback.when`, `end.call_back`, `end.language`, `end.third_party`,
  `end.no_response`, `close.verify`. Removed: `disclosure.verify`, `read_back.intro_nth`.
  **Not added** (promised in §3.7): `close.notice`: the written-notice pointer stays in
  `disclosure.recording`, before the go-ahead. Kept but moved: `disclosure.never_ask` (said with the
  birth-year question, `step=second_check`), `disclosure.rights` (said with `context.loan`,
  `step=context`). Every surviving key's wording changed in Hindi and Hinglish; re-voice all of them.
- **Slots.** `read_back.confirm_about` takes `amount_words` only (a range is spoken as
  "<low> <range_word> <high>", `range_word` from the prompt file). Every other slot rule is unchanged.
- **`stop_check.decline` now asks "shall we carry on?"**: yes goes back to the question, no ends the
  call as `declined`. `stop_check.human` is unchanged (yes ends the call as `human_requested`).
- **Two readings.** `Turn.text` is the reading the call acted on: when only the second reading holds
  a figure, the two are swapped and `SecondReading.text` keeps the other. On the premium answer a
  disagreement (or one reading without a figure) gets `premium.say_again` once per product; if the
  readings still differ on that second try, the **first** reading's figure is read back and the
  customer confirms or corrects it. So the order still matters on the second try: pass **v2.5 first**
  on amount turns (verifier H4: 2 wrong figures held in 240 against 16 with v3.0 first).
  `premium.say_again` is tagged `asks=premium` like the first asking, so the extractor sees both.
- **Cover read-back** (coordinator decision): a cover figure the customer states is read back with
  `read_back.cover_confirm` (`step=read_back`, `asks=` `samajh.dialogue.machine.cover_read_back_question()`,
  today `Question.cover` until P3a names a value) and goes through the same confirm/correct loop;
  `read_back.reconfirm` and `read_back.restate` carry the asked item in `asks`. A range is not read
  back for cover.
- **Expecting** gained `either_or` (required-for-loan and payment-frequency questions) and
  `callback_time`. `AtRecallFollowUp`, `AtSayAgain`, `AtCallbackTime` are new positions.
- **`LlmFallbackInterpreter`** is also consulted on a weak stop signal from the word lists ("answer"
  clears it). It is never consulted at the first-name question.
