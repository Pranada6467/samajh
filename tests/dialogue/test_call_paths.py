"""Scripted conversations in every language: what the bot does on each path through the call."""

from __future__ import annotations

import pytest
from dialogue_kit import CUSTOMERS, LANGUAGES, LENDER, YEAR_POLICY, play, product, record

from samajh.amounts import parse_amount
from samajh.dialogue import PRODUCT_QUESTIONS, CallState, Ended, Limits, Outcome, start, step
from samajh.types import CallStep, Question, Speaker, Transcript

# Index of each reply in `Customer.happy()` for a one-product record. The read-back follows the premium.
IDENTITY, GO_AHEAD, YEAR, RECALL, FIRST_ANSWER = 0, 1, 2, 3, 4
PREMIUM = FIRST_ANSWER + PRODUCT_QUESTIONS.index(Question.premium)
READ_BACK = PREMIUM + 1
CONSENT = FIRST_ANSWER + len(PRODUCT_QUESTIONS) + 1
AFTER_PREMIUM = PRODUCT_QUESTIONS[PRODUCT_QUESTIONS.index(Question.premium) + 1 :]
HAPPY_STEPS = (
    [CallStep.right_party_check, CallStep.disclosure, CallStep.second_check, CallStep.open_recall]
    + [CallStep.teach_back, CallStep.teach_back, CallStep.read_back]
    + [CallStep.teach_back] * len(AFTER_PREMIUM)
    + [CallStep.consent_check, CallStep.close]
)


def product_questions(pid: str, *, read_back: bool = True) -> list[tuple[CallStep, Question, str]]:
    """The questions asked of one product, in call order, with the read-back after the premium."""
    asked = [(CallStep.teach_back, Question.kind, pid), (CallStep.teach_back, Question.premium, pid)]
    if read_back:
        asked.append((CallStep.read_back, Question.premium, pid))
    return asked + [(CallStep.teach_back, q, pid) for q in AFTER_PREMIUM]


def questions_asked(transcript: Transcript) -> list[tuple[CallStep, Question | None, str | None]]:
    return [(t.step, t.asks, t.product_id) for t in transcript.turns if t.speaker is Speaker.bot and t.asks]


@pytest.mark.parametrize("language", LANGUAGES)
def test_happy_path_follows_the_design_flow(language):
    customer = CUSTOMERS[language]
    call = play(record(), language, customer.happy())

    assert call.end is not None and call.end.outcome is Outcome.completed
    assert call.end.unresolved == ()
    assert [u.lines[-1].step for u in call.utterances] == HAPPY_STEPS
    assert questions_asked(call.end.transcript) == [
        *product_questions("P1"),
        (CallStep.consent_check, Question.consent, None),
    ]
    assert "close.may_call_back" not in call.keys


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_customer_turn_replies_to_the_question_before_it(language):
    transcript = play(record(), language, CUSTOMERS[language].happy()).end.transcript
    customer_turns = [t for t in transcript.turns if t.speaker is Speaker.customer]
    assert [t.text for t in customer_turns] == CUSTOMERS[language].happy()
    for turn in customer_turns:
        asked = transcript.turns[turn.id - 2]
        assert asked.speaker is Speaker.bot and asked.step is turn.step
    assert [t.id for t in transcript.turns] == list(range(1, len(transcript.turns) + 1))


@pytest.mark.parametrize("language", LANGUAGES)
def test_context_comes_after_the_second_check_and_recall_before_any_product_question(language):
    call = play(record(), language, CUSTOMERS[language].happy())
    steps = [line.step for line in call.lines]
    assert steps.index(CallStep.context) > steps.index(CallStep.second_check)
    between = steps[steps.index(CallStep.context) : steps.index(CallStep.open_recall)]
    assert set(between) == {CallStep.context}  # the loan line and the right to stop, nothing else
    assert steps.index(CallStep.teach_back) > steps.index(CallStep.open_recall)


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("reply", ["wrong_person", "reject"])
def test_wrong_person_ends_the_call_with_one_neutral_line(language, reply):
    call = play(record(), language, [getattr(CUSTOMERS[language], reply)])
    assert call.end.outcome is Outcome.wrong_party
    assert call.keys == ("right_party.ask", "end.third_party")


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("replies", [("repeat", "repeat"), ("", "filler"), ("filler", "filler")])
def test_no_confirmation_is_asked_once_more_then_the_call_ends(language, replies):
    said = [getattr(CUSTOMERS[language], r) if r else "" for r in replies]
    call = play(record(), language, said)
    assert call.end.outcome is Outcome.not_confirmed
    assert call.keys == ("right_party.ask", "right_party.reask", "end.third_party")
    assert all(LENDER not in line.text for line in call.lines)


@pytest.mark.parametrize("language", LANGUAGES)
def test_who_is_this_gets_the_purpose_without_the_lender_then_the_reask(language):
    customer = CUSTOMERS[language]
    call = play(record(), language, [customer.who, customer.filler])
    assert call.keys == ("right_party.ask", "purpose.before_confirm", "right_party.reask", "end.third_party")
    assert call.end.outcome is Outcome.not_confirmed
    assert all(LENDER not in line.text for line in call.lines)


@pytest.mark.parametrize("language", LANGUAGES)
def test_silence_at_the_first_question_twice_ends_the_call_as_no_response(language):
    call = play(record(), language, ["", ""])
    assert call.end.outcome is Outcome.no_response
    assert call.keys == ("right_party.ask", "right_party.reask", "end.no_response")


@pytest.mark.parametrize("language", LANGUAGES)
def test_who_is_this_then_yes_goes_on_to_the_disclosure(language):
    customer = CUSTOMERS[language]
    call = play(record(), language, [customer.who, customer.identity])
    assert call.end is None
    assert call.keys[:4] == (
        "right_party.ask",
        "purpose.before_confirm",
        "right_party.reask",
        "disclosure.who",
    )


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("stage", range(CONSENT + 1))
@pytest.mark.parametrize("wish, outcome, line", [("decline", Outcome.declined, "end.declined"),
                                                 ("human", Outcome.human_requested, "end.human")])  # fmt: skip
def test_decline_or_human_request_at_any_stage_ends_at_once(language, stage, wish, outcome, line):
    customer = CUSTOMERS[language]
    replies = customer.happy()[:stage] + [getattr(customer, wish)]
    call = play(record(), language, replies)

    assert call.end is not None and call.end.outcome is outcome
    assert tuple(l.key for l in call.end.utterance.lines) == (line,)
    assert len(call.utterances) == stage + 2  # one bot utterance per earlier reply, then the goodbye
    assert isinstance(call.state.position, Ended)


@pytest.mark.parametrize("language", LANGUAGES)
def test_no_to_going_ahead_is_a_decline(language):
    customer = CUSTOMERS[language]
    call = play(record(), language, [customer.identity, customer.reject])
    assert call.end.outcome is Outcome.declined
    assert call.keys[-1] == "end.declined"


@pytest.mark.parametrize("language", LANGUAGES)
def test_unclear_go_ahead_gets_one_short_reask_then_ends(language):
    customer = CUSTOMERS[language]
    call = play(record(), language, [customer.identity, customer.repeat, customer.filler])
    assert call.end.outcome is Outcome.no_go_ahead
    assert call.keys[-2:] == ("disclosure.reask", "end.neutral")


@pytest.mark.parametrize("language", LANGUAGES)
def test_second_check_fails_after_one_reask_and_the_loan_is_never_mentioned(language):
    # Wave 2: one attempt: a wrong year ends at once; a reply with no year gets the one re-ask.
    customer = CUSTOMERS[language]
    call = play(record(), language, [customer.identity, customer.go_ahead, "1990"])
    assert call.end.outcome is Outcome.second_check_failed
    assert call.keys[-2:] == ("second_check.ask", "end.check_failed")
    call = play(record(), language, [customer.identity, customer.go_ahead, "", "1991"])
    assert call.end.outcome is Outcome.second_check_failed
    assert call.keys[-3:] == ("second_check.ask", "second_check.reask", "end.check_failed")
    assert CallStep.context not in {line.step for line in call.lines}


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("years", [["84"], ["हम्म", "1984"], [""] + ["1984"]])  # wave 2: no "1990" first
def test_second_check_passes_on_two_digits_or_on_the_second_try(language, years):
    customer = CUSTOMERS[language]
    call = play(record(), language, [customer.identity, customer.go_ahead, *years])
    assert call.end is None
    assert call.keys[-3:] == ("context.loan", "disclosure.rights", "open_recall.ask")


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("unclear", ["repeat", "filler"])
def test_an_unclear_answer_is_asked_once_more_then_recorded_and_the_call_moves_on(language, unclear):
    customer = CUSTOMERS[language]
    noise = getattr(customer, unclear)
    replies = [customer.identity, customer.go_ahead, customer.year, customer.recall]
    replies += [noise] * (2 * (len(PRODUCT_QUESTIONS) + 1) + 1)  # every question twice, and the one check
    call = play(record(), language, replies)

    assert call.end.outcome is Outcome.completed
    assert call.keys.count("stop_check.disengaged") == 1  # after the first two unusable replies, once a call
    # Iteration 3 (gain 8): the recall reply named something, so the kind question is `kind.ask_named`.
    named = {"kind.ask_named": "kind.ask"}
    asked = [named.get(key, key) for key in call.keys if key.endswith((".ask", ".reask")) or key in named]
    for name in [*[q.value for q in PRODUCT_QUESTIONS], "consent"]:
        assert asked.count(f"{name}.ask") == 1 and asked.count(f"{name}.reask") == 1
    assert len(call.end.unresolved) == len(PRODUCT_QUESTIONS) + 1
    assert {(u.asks, u.product_id) for u in call.end.unresolved} >= {(q, "P1") for q in PRODUCT_QUESTIONS}
    assert CallStep.read_back not in {line.step for line in call.lines}  # no premium was stated
    assert call.keys[-4:] == ("close.thanks", "close.may_call_back", "close.verify", "close.bye")


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("unclear", ["repeat", "filler"])
def test_an_open_recall_unclear_twice_gets_the_one_follow_up(language, unclear):
    customer = CUSTOMERS[language]
    noise = getattr(customer, unclear)
    call = play(
        record(), language, [*customer.happy()[:RECALL], noise, noise, noise, noise, customer.consent]
    )
    assert call.keys.count("stop_check.disengaged") == 1
    assert call.keys.count("open_recall.reask") == 1 and call.keys.count("open_recall.nothing") == 1
    assert call.end.outcome is Outcome.completed
    assert [u.step for u in call.end.unresolved] == [CallStep.open_recall, CallStep.open_recall]


@pytest.mark.parametrize("language", LANGUAGES)
def test_a_clear_answer_to_the_reask_leaves_nothing_unresolved(language):
    customer = CUSTOMERS[language]
    replies = customer.happy()
    replies[RECALL:RECALL] = [customer.repeat]
    replies[PREMIUM + 1 : PREMIUM + 1] = [customer.filler]
    call = play(record(), language, replies)
    assert call.end.outcome is Outcome.completed and call.end.unresolved == ()
    assert call.keys.count("open_recall.reask") == 1 and call.keys.count("premium.reask") == 1
    assert "bridge.moving_on" not in call.keys


@pytest.mark.parametrize("language", LANGUAGES)
def test_dont_know_is_an_answer_and_is_not_asked_again(language):
    customer = CUSTOMERS[language]
    replies = customer.happy()[:FIRST_ANSWER] + [customer.dont_know] * (len(PRODUCT_QUESTIONS) + 2)
    call = play(record(), language, replies)
    assert call.end.outcome is Outcome.completed and call.end.unresolved == ()
    assert call.keys.count("stop_check.disengaged") == 1  # after three in a row; going on keeps the answer
    assert not [key for key in call.keys if key.endswith(".reask")]
    assert CallStep.read_back not in {line.step for line in call.lines}


@pytest.mark.parametrize("language", LANGUAGES)
def test_read_back_says_the_customers_figure_in_words_and_digits(language):
    call = play(record(product(premium_inr=61000)), language, CUSTOMERS[language].happy())
    read_back = next(line for line in call.lines if line.key == "read_back.confirm")
    assert parse_amount(read_back.text).rupees == 52000  # what the customer said, not the 61,000 on record
    assert read_back.asks is Question.premium and read_back.product_id == "P1"
    assert not any(ch.isdigit() for ch in read_back.text)  # words only: the voice says it once


@pytest.mark.parametrize("language", LANGUAGES)
def test_customer_corrects_the_figure_at_read_back(language):
    customer = CUSTOMERS[language]
    replies = customer.happy()[:READ_BACK] + [customer.correction, customer.confirm]
    replies += customer.happy()[READ_BACK + 1 :]
    call = play(record(), language, replies)

    assert call.end.outcome is Outcome.completed and call.end.unresolved == ()
    read_backs = [line for line in call.lines if line.key == "read_back.confirm"]
    assert [parse_amount(line.text).rupees for line in read_backs] == [52000, 55000]
    assert call.state.premium_of(0) == 55000


@pytest.mark.parametrize("language", LANGUAGES)
def test_customer_rejects_the_read_back_then_gives_the_right_figure(language):
    customer = CUSTOMERS[language]
    replies = customer.happy()[:READ_BACK] + [customer.reject, customer.corrected, customer.confirm]
    replies += customer.happy()[READ_BACK + 1 :]
    call = play(record(), language, replies)

    assert call.end.outcome is Outcome.completed and call.end.unresolved == ()
    tail = [line for line in call.lines if line.step is CallStep.read_back]
    assert [line.key for line in tail] == ["read_back.confirm", "read_back.restate", "read_back.confirm"]
    assert all(line.asks is Question.premium and line.product_id == "P1" for line in tail)
    assert parse_amount(tail[-1].text).rupees == 55000


@pytest.mark.parametrize("language", LANGUAGES)
def test_read_back_loop_is_bounded(language):
    customer = CUSTOMERS[language]
    replies = customer.happy()[:READ_BACK] + [customer.reject, customer.corrected] * 2 + [customer.reject]
    replies += customer.happy()[READ_BACK + 1 :]
    call = play(record(), language, replies, limits=Limits(max_read_backs=3))

    assert call.end.outcome is Outcome.completed
    assert call.keys.count("read_back.confirm") == 3
    assert [(u.step, u.asks) for u in call.end.unresolved] == [(CallStep.read_back, Question.premium)]
    assert "close.may_call_back" in call.keys


@pytest.mark.parametrize("language", LANGUAGES)
def test_unclear_reply_to_a_read_back_repeats_it_then_gives_up(language):
    customer = CUSTOMERS[language]
    replies = customer.happy()[:READ_BACK] + [customer.filler] * 3 + customer.happy()[READ_BACK + 1 :]
    call = play(record(), language, replies, limits=Limits(max_read_backs=2))
    assert call.end.outcome is Outcome.completed
    assert [k for k in call.keys if k.startswith("read_back")] == ["read_back.confirm", "read_back.reconfirm"]
    assert len(call.end.unresolved) == 1


@pytest.mark.parametrize("language", LANGUAGES)
def test_two_products_are_asked_in_record_order_by_ordinal(language):
    customer = CUSTOMERS[language]
    rec = record(product("P1"), product("P2", premium_inr=9000))
    replies = customer.happy(products=2)
    second_premium = PREMIUM + len(PRODUCT_QUESTIONS) + 1
    replies[second_premium] = customer.dont_know  # no figure for the second product, so no read-back
    del replies[second_premium + 1]
    call = play(rec, language, replies)

    assert call.end.outcome is Outcome.completed
    assert questions_asked(call.end.transcript) == [
        *product_questions("P1"),
        *product_questions("P2", read_back=False),
        (CallStep.consent_check, Question.consent, None),
    ]
    # Wave 2: the first product is introduced as in a one-product record; `intro_nth` only from the second.
    assert [line.key for line in call.lines if line.key.startswith("teach_back.intro")] == [
        "teach_back.intro", "teach_back.intro_nth"]  # fmt: skip
    intros = [line for line in call.lines if line.key == "teach_back.intro_nth"]
    assert [line.slots["ordinal"] for line in intros] == list(call_ordinals(language)[1:2])


@pytest.mark.parametrize("language", LANGUAGES)
def test_two_products_get_a_read_back_each(language):
    rec = record(product("P1"), product("P2"))
    call = play(rec, language, CUSTOMERS[language].happy(products=2))
    assert call.end.outcome is Outcome.completed and call.end.unresolved == ()
    read_backs = [line.product_id for line in call.lines if line.key == "read_back.confirm"]
    assert read_backs == ["P1", "P2"]


def call_ordinals(language):
    from samajh.dialogue import load_prompts

    return load_prompts(language).ordinals


@pytest.mark.parametrize("language", LANGUAGES)
def test_a_record_with_no_products_goes_from_recall_to_consent_to_close(language):
    customer = CUSTOMERS[language]
    rec = record().model_copy(update={"products": ()})
    call = play(
        rec,
        language,
        [customer.identity, customer.go_ahead, customer.year, customer.recall, customer.consent],
    )
    assert call.end.outcome is Outcome.completed
    assert [u.lines[-1].step for u in call.utterances][3:] == [
        CallStep.open_recall, CallStep.consent_check, CallStep.close
    ]  # fmt: skip


@pytest.mark.parametrize("language", LANGUAGES)
def test_state_survives_a_json_round_trip_at_every_turn(language):
    replies = CUSTOMERS[language].happy()
    state, _ = start(record(), language, lender_name=LENDER, identity=YEAR_POLICY)
    for reply in replies:
        restored = CallState.model_validate_json(state.model_dump_json())
        assert restored == state
        state, said = step(restored, reply)
    assert said.outcome is Outcome.completed
    assert said.transcript == play(record(), language, replies).end.transcript


def test_the_state_keeps_only_the_plan_not_the_record():
    state, _ = start(record(), LANGUAGES[0], lender_name=LENDER, identity=YEAR_POLICY)
    kept = state.model_dump_json()
    for secret in (
        "52000",
        "500000",
        "448000",
        "credit_life",
        "Namoona Life",
        "Kalpit",
        "06-15",
        "cancel",
        "consent",
    ):
        assert secret not in kept


def test_a_finished_call_cannot_be_stepped():
    call = play(record(), LANGUAGES[0], [CUSTOMERS[LANGUAGES[0]].wrong_person])
    with pytest.raises(ValueError, match="ended"):
        step(call.state, "हाँ")


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("budget", [2, 5, 9])
def test_the_turn_budget_ends_the_call(language, budget):
    call = play(record(), language, CUSTOMERS[language].happy(), limits=Limits(max_bot_turns=budget))
    assert call.end.outcome is Outcome.turn_limit
    assert len(call.utterances) == budget
    assert call.keys[-3:] == ("close.thanks", "close.may_call_back", "close.bye")


def test_start_rejects_what_it_cannot_call():
    with pytest.raises(ValueError, match="lender_name"):
        start(record(), LANGUAGES[0], lender_name="  ")
    with pytest.raises(ValueError, match="ordinal"):
        start(record(*[product(f"P{k}") for k in range(9)]), LANGUAGES[0], lender_name=LENDER)
    with pytest.raises(ValueError, match="max_bot_turns"):
        start(record(), LANGUAGES[0], lender_name=LENDER, limits=Limits(max_bot_turns=1))


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("stage", [RECALL, PREMIUM, READ_BACK, CONSENT])
def test_a_weak_stop_signal_is_checked_once_and_no_ends_the_call(language, stage):
    """The one question is "shall we go on?": a no ends the call."""
    customer = CUSTOMERS[language]
    call = play(record(), language, [*customer.happy()[:stage], customer.weak_stop, customer.reject])
    assert call.end.outcome is Outcome.declined
    assert call.keys[-2:] == ("stop_check.decline", "end.declined")
    check = call.lines[-2]
    assert check.asks is None and check.product_id is None  # a reply to it can never ground an answer


@pytest.mark.parametrize("language", LANGUAGES)
def test_yes_to_the_stop_check_goes_back_to_the_question_in_simpler_words(language):
    customer = CUSTOMERS[language]
    replies = [*customer.happy()[:PREMIUM], customer.weak_stop, customer.confirm, *customer.happy()[PREMIUM:]]
    call = play(record(), language, replies)
    assert call.end.outcome is Outcome.completed and call.end.unresolved == ()
    k = call.keys.index("stop_check.decline")
    assert call.keys[k - 1 : k + 2] == ("premium.ask", "stop_check.decline", "premium.reask")


@pytest.mark.parametrize("language", LANGUAGES)
def test_weak_stop_signals_cannot_hold_a_question_open(language):
    customer = CUSTOMERS[language]
    replies = [
        *customer.happy()[:PREMIUM],
        *[customer.weak_stop, customer.confirm] * 2,
        *customer.happy()[READ_BACK + 1 :],
    ]
    call = play(record(), language, replies)
    assert call.end.outcome is Outcome.completed
    assert call.keys.count("stop_check.decline") == 2 and call.keys.count("premium.reask") == 1
    assert [(u.step, u.asks) for u in call.end.unresolved] == [(CallStep.teach_back, Question.premium)]


@pytest.mark.parametrize("language", LANGUAGES)
def test_a_plain_refusal_during_the_stop_check_ends_the_call(language):
    customer = CUSTOMERS[language]
    for reply, outcome in [(customer.decline, Outcome.declined), (customer.human, Outcome.human_requested),
                           (customer.weak_stop, Outcome.declined)]:  # fmt: skip
        call = play(record(), language, [*customer.happy()[:RECALL], customer.weak_stop, reply])
        assert call.end.outcome is outcome
