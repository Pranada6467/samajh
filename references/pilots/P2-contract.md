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

## 6. Review round 2 (after the iteration-2 verifier; wins over §5 where they differ)

- **Line keys added:** `purpose.before_confirm` (no slots: "what is this about?" before anyone has
  claimed to be the borrower), `verify.short` (`lender`; said with the birth-year question),
  `cover.say_again`, `stop_check.disengaged`, `end.do_not_call`, `end.written`. None removed or
  renamed. Reworded: `right_party.ask`, `end.third_party`, `disclosure.who`, `disclosure.recording`,
  `disclosure.reask`, `verify.before_loan`, `verify.after_loan`, `context.loan`, `consent.ask`,
  `consent.reask`, `read_back.confirm`, `read_back.cover_confirm`, `read_back.reconfirm`,
  `stop_check.decline` ("क्या मैं आगे बढ़ूँ?"), `stop_check.human`, `end.human`.
- **Slots:** every read-back line takes `amount_words` only; `amount_digits` is no longer used by any
  line (the voice said the figure twice).
- **Outcomes added:** `do_not_call`, `written_requested`. `FROM_DIALOGUE` in `samajh/ops/model.py`
  needs both (P2 does not edit it).
- **Who is believed:** only an explicit first-person claim confirms ("हाँ जी, मैं ही बोल रहा हूँ",
  "speaking"); an acknowledgement ("हाँ जी", "बोलिए", "hello") is re-asked once and then ends as
  `not_confirmed`. A reply with a name or a title goes to the classifier; with no classifier, or a
  failed one, it does not confirm. At the birth-year question a year among other words confirms only
  when the classifier reads it as the speaker's own.
- **Expecting:** the cover question is now `amount`, so the phone fetches a second reading there.
- **Classifier (`LlmFallbackInterpreter`, same constructor):** asked about every go-ahead reply and
  every reading the word lists do not settle (`Interpretation.settled`); every label honoured;
  any exception or a timeout leaves the turn readable. Later in the call a failed classifier gets one
  "shall I go on?" per call.
- **`EndOfCall.carried_forward` / `CallState.carried_forward`:** answers given in open recall and not
  asked again (today: a single premium figure, read back after the kind question). **The extractor
  must accept the recall turn as the premium's quote for these**, or the premium reads as a gap.

## 7. Round 3 (wins over §6 where they differ)

- **Two tiers at the first-name question.** A *strong* claim (an explicit first-person claim, by the word
  lists or by the classifier's `confirms_self` with a first-person word) keeps the §6 path unchanged:
  `disclosure.who`, `disclosure.not_sales`, `disclosure.recording`, `disclosure.go_ahead`, then
  `disclosure.never_ask`, `verify.short`, `second_check.ask`, then `context.loan`, `disclosure.rights`,
  `open_recall.ask`. An *ordinary* confirmation (`Intent.acknowledges`: a yes or go-on word, no denial,
  no third-person pronoun, no stop, who or repeat reading, at most 2 other words; the classifier's `yes`,
  or `confirms_self` without "I") goes straight to the year: [`purpose.before_confirm` if neither it nor
  `right_party.reask` was said yet], `disclosure.never_ask`, `second_check.ask`; on a pass, the four
  `disclosure.*` lines with the go-ahead question; on yes, `context.loan`, `disclosure.rights`,
  `open_recall.ask`. Before the year on this path, "who is this?" gets `purpose.before_confirm`, a failed
  year ends `second_check_failed` with `end.third_party`. A plain yes at the re-ask is an ordinary
  confirmation. Tamil and Kannada have no ordinary confirmation (no `ack_ok` list).
- **Invariant (tested by a walk):** the lender is named only after a strong claim at the first-name
  question or after the birth year has passed; the loan and products only after the year has passed.
- **State:** `AtBirthYear.early` and `AtGoAhead.year_passed`, both default False, so states saved before
  round 3 load unchanged.
- **Open recall:** `Interpretation.names_something` (word lists only; survives the classifier): a figure,
  a thing, or something done, taken, deducted, paid, signed or required, in a clause the customer does
  not deny ("took" does not count in a clause that names the loan). The nothing branch needs a nothing
  reading and `names_something` False, at recall and at the follow-up.
- **Read-back:** a reply that repeats the figure read back (same low and high) with only yes-words,
  fillers and "that is what I paid" words (`Lexicon.restates`) confirms it; a denial does not.
- **Two readings:** a stop intent in either reading wins over a figure or answer in the other, most
  protective first (`wrong_person`, `do_not_call`, `decline`, `wants_human`, `written_request`,
  `call_later`, `other_language`, then the weak `maybe_decline`, `maybe_human`); that reading becomes
  `Turn.text` and the other `SecondReading.text`.
- **Classifier use:** the go-ahead reply made only of yes-words (or only no-words) is settled; a later
  free answer holding a word of `Lexicon.substance` (hi and hi-en only) is settled
  (`interpret.SETTLE_ON_SUBSTANCE`, one switch).
- **`LlmFallbackInterpreter.begin(text, *, language, expecting, question)`** starts the classifier call
  now when `interpret` would ask it; `interpret` with the same arguments then waits only for what is left
  of `timeout_s`, counted from `begin`. At most 16 begun calls are kept; never raises.
  **`samajh.dialogue.prefetch(state, customer_text, *, interpreter)`** works out the stage and question
  from the state and calls `begin`; a no-op without one; never raises. `step` begins both readings
  itself on a two-reading turn. **Server change (not made here):** call `prefetch(state, text,
  interpreter=...)` as soon as the first transcript of a turn arrives, before waiting for the second
  reading, then call `step` as today with the same text.

### §7, wave 2 (verifier conditions on 993edf4)

- **Substance skip narrowed:** a free answer is settled on a substance word only with no risk cue (a
  no-word, a talk / call / phone / branch / manager / feedback / email / number word, a command to the
  caller, a relation or third-person word, a who/why question, a first-person future such as "करूंगा").
- **Opening:** an address form ("भाई", "sir", "यार") beside a yes or go-on word, with no possessive and no
  relation word followed by "हूं / बोल रहा / am", is address, not a relation. A claim or acknowledgement
  with a who/why question is a confirmation (the following lines answer the question).
- **Conflicted stop readings:** a refusal, busy, hand-off or call-back phrase beside a go-on word, or a
  no-word beside a go-on word at the go-ahead, is unsettled: the classifier judges; without one the call
  asks once (the go-ahead re-ask, later the stop check). At the go-ahead a classifier `answer` or `yes`
  is yes only with a yes or go-on word in the reply, else the re-ask.
- **Call-back:** `AtCallbackTime.resume` (optional; old states end as before). A reply that means now and
  names no later time goes back to the pending question.
- **Birth year, one attempt:** a year that does not match, or two different years, ends at once
  (`second_check_failed`; `end.third_party` on the ordinary path). Only a reply with no year, or the right
  year not taken as the speaker's own, gets the one re-ask. A question ("…है ना? सही है?") holds no year.
  Courtesy and calendar words, the same year said twice and Latin-script frames are tight.
- **`CallState.speaker_confirmed` / `EndOfCall.speaker_confirmed`:** True only once the birth year has
  passed (both paths). Outcome names are unchanged.
- **Mid-call takeover:** `Interpretation.possible_takeover` (the borrower away, the phone theirs, a wrong
  number, "मैं … नहीं हूं", a relation word followed by "हूं / बोल रही"). A classifier's judgment clears it.
  Without one (no classifier, a failure, `unclear`) the call asks `right_party.reask` as a check
  (`AtStopCheck.wish = "who"`) that remembers the pending question: a yes or claim resumes it, anything
  else ends `wrong_party` with `end.third_party`; at most `max_stop_checks` checks per call. A takeover in
  either of two readings ranks just after `wrong_person`. A failed classifier turn stays in
  `degraded_turns`.
- **Recall:** `Interpretation.names_nothing` (a denial and no evidence) sends a reply to the follow-up,
  and at the follow-up to consent, whatever the intent. The loan's money or the pledge is the loan.
- **Lines:** `cancel_window.reask` reworded; `teach_back.intro_nth` (hi, hi-en) has no ordinal (the slot is
  now optional, `LineSpec.optional`; ta and kn keep it). The first product of any record gets
  `teach_back.intro`; `intro_nth` comes before the second and later products only. A denial that names
  nothing at a later product's first question marks the remaining products unresolved and goes to
  consent.

### §7, wave 3

- **Birth year:** a month name makes the reply a date of birth; a 1-31 number beside the month (not part of a
  longer number) is the day. Birth words ("पैदाइश", "born", "की है") ride along. A year (or year-like number)
  with a hedge, a tag ("है ना", "right"), an "or" or a self-correction ("नहीं", "no") is a guess and ends
  the check at once. A bare "?" is not a guess.
- **Go-ahead:** the word lists end the call only on a reply with no yes-word (except "जी", "बिल्कुल") and no
  go-on word; "no problem" forms are a yes despite the no-word; go-on now includes start/continue forms.
- **Call-back:** a now-word with a go-on or do-it-now word resumes the call whatever else is said.
- **Takeover:** also "I + possessive pointing elsewhere + one word + am" ("मैं उनका बेटा हूँ", "this is his
  brother"), a phone handed over, the borrower gone or not on the call, "I am …" beside "उनको / unko", and a
  mid-call who-question that names or addresses someone else. A classifier can end the call on a takeover
  but cannot clear the flag: anything else still gets the who-check, which comes before `verify.after_loan`.
- **Recall:** the act and thing vocabulary covers romanised and English forms (deduct, charges, staff ne
  bola, protection, haan kar di…).
- **Re-ask:** at the re-ask only, a reply that starts with a yes-word and holds no third-person word, relation
  or denial is an ordinary confirmation whatever its length.

### §7, wave 4

- **Birth year, script parity:** at the year question only, romanised Hindi number words (0 to 99 with common
  spellings, "sau", "hazaar") are written in Devanagari before the year is read (`ROMAN_NUMBERS` and
  `roman_key` in `_lexicon.py`, `_devanagari_numbers` in `interpret.py`), so "unnees sau chaurasi",
  "chaurasi mein", "main chaurasi ka hoon" and "do hazaar do" read as their Devanagari forms do. The
  frame words were already in `year_ok` through the romanised fold.
- The safety rules are unchanged and apply to the romanised forms: a wrong year or two years fail at once, a
  hedge or tag is a guess, a year about someone else ("unka …") never passes, a reply with no year gets one
  re-ask. Not a general fold: "do", "sath", "tera" stay ordinary words everywhere else.
- **Probe harness:** `p2_round3_measure.py --data MODULE` picks the probe data module (default
  `p2_round3_openings`); `openings` also prints, per scope, the genuine cases that did not pass both checks.

## 8. Round 4 (wins over §7 where they differ)

- **Signs of another speaker, after the opening** (`Interpretation.other_speaker`, Hindi and Hinglish).
  Strong (`possible_takeover`, as §7 plus "I" beside a relation of someone else, "मैं उनका भाई"). Weak: a
  relation of someone else without "I" ("unka bhai"); the speaker's own relative owning or doing something
  ("मेरे पति का", "मेरे बेटे ने"); "talk to me" / "now I am speaking"; a greeting with a question word. Read at
  every position after the opening, including the stop checks and the call-back question. A sign makes the
  reading unsettled unless it ends the call.
- **`Interpretation.classifier_label`:** the label the reading follows; None when no label was used (none,
  failure, timeout, `unclear`, a settled turn). `asks_repeat`, `who_or_why`, `off_topic` also count as no
  label for a sign.
- **Order in `step`:** after the definite ends (language, human, decline, do-not-call, written, wrong person)
  and before the call-back question, the call-back request, the stop checks and "who is this?": a strong
  sign, a sign with no label, or (`CallState.speaker_doubt`) an unsettled turn with no label after a sign a
  label let pass, gets the who-check (`AtStopCheck(wish="who")`, `right_party.reask`). It resumes the
  pending question (from the call-back question: asks "when?" again; from a stop check: its question).
- **The who-check reply**, the same in every arm: points elsewhere (`interpret.points_elsewhere`) ->
  `wrong_party`; affirmation (`interpret.affirms_self`, closed vocabulary plus the first name) or the
  classifier's `confirms_self` with a first-person word -> resume; a stop request -> its outcome;
  anything else -> `wrong_party`. The stop-check classifier table adds `confirms_self`, `wrong_person`,
  `third_party_handoff`, `remove_number`, `written_request`, `call_back`; its stage text mentions the
  who-check. At the stop checks a yes with words outside the closed vocabulary is unsettled.
- **`Limits.max_who_checks`** (default 2), separate from `max_stop_checks`; past it the turn ends as
  `wrong_party`. **`CallState.who_checks`, `CallState.speaker_doubt`** default 0 / False (old states load).
- **`wrong_party` always ends with `speaker_confirmed` False** (state and `EndOfCall`).
- **Birth year:** near-spellings (one edit to exactly one number word) are corrected before the year is
  read; an uncorrectable number-like word after "सौ"/"हज़ार", or one edit from two numbers, is "no year".
  "वो" before "तो", a year word or a number is not a third person.
- **Refusals:** `_refuses_to_talk` (structure) joins the `decline` list at every stage. At the opening a
  refusal with a third-person word is `wrong_person`.
- **`verify.before_loan`** only before the year passes (`AtGoAhead.year_passed` or `speaker_confirmed`).
- **Call-back "now":** `means_now` treats a no-word as the answer to "later?" unless it follows the now-word.
- **Folds added** (`_FOLD`, every stage): chale, chala, chali, nikal, nikle, mujhse, inka/inki/inke,
  uska/uski/uske, mera/mere, hamara/hamari/hamare, kiska/kiski/kiske, ne, sunna, rakho, rakhiye, rakhna.
- No line text, line key, outcome or `Expecting` value changed.
- **Follow-up:** at the opening, an address form inside a structural refusal (no possessive, no third-person word, no "हूं / बोल रहा / am" after it) is not a relation (`_only_address(..., beside_yes=False)`). At the who-check a leading no-word before a first-person claim is dropped before the reply is read.
