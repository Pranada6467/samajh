"""Fix round 3 in the extractor: a premium carried forward from open recall, the last denial, and
the conflict tolerance. Whole chain (extract -> to_beliefs -> evaluate) with a scripted model.

The carried premium is decided by code from the transcript alone (`carried_premiums`): the bot
read back a premium it never asked, and an open-recall reply reads, as a whole, to that figure.
"""

import pytest
from extractkit import BASE, PRODUCT, FakeLlm, build, record

from samajh.clients.errors import LlmOutputInvalid, TransportError
from samajh.extract import extract
from samajh.extract._wire import SCHEMA, SlotKind
from samajh.rules import evaluate, to_beliefs
from samajh.types import CallStep, GapReason, Question, Speaker, Stated, Tier, Transcript, Turn, Unclear

RECALL_Q = "लोन के साथ आपने कुछ और भी लिया था क्या? अगर हाँ, तो क्या, और कितने का?"
INTRO = "ठीक है, उसके बारे में कुछ छोटे सवाल हैं।"
KIND_Q = "वो क्या है? अपने शब्दों में बताइए।"
READ_BACK = "तो आपने उसके लिए {} रुपये दिए। सही है?"
RECALL_25 = "लोन के साथ हाँ, एक बीमा भी लिया था 25,000 रुपये का।"

# (step, asks, bot text, customer reply or None for a bot turn with no reply, model output)
Row = tuple[str, str | None, str, str | None, dict]


def recall_row(reply: str, kind: str = "insurance", span: str = "एक बीमा", amount: str | None = None) -> Row:
    items = [{"span": span, "kind": kind, "amount_span": amount}] if kind else []
    return ("open_recall", None, RECALL_Q, reply, {"items": items, "took_nothing": not items})


def kind_row(reply: str = "बीमा ही है insurance।", kind: str = "insurance") -> Row:
    return ("teach_back", "kind", KIND_Q, reply, {"status": "stated", "kind": kind, "clauses": [1]})


def read_back_row(
    words: str, reply: str = "हाँ, सही है", confirms: bool = True, corrected: str | None = None
) -> Row:
    output = {"status": "stated", "confirms": confirms, "clauses": [1], "corrected_amount_span": corrected}
    return ("read_back", "premium", READ_BACK.format(words), reply, output)


def rest(*skip: str) -> list[Row]:
    """BASE after the kind question, without the premium question and its read-back."""
    return [r for r in BASE[2:] if r[1] not in ("premium", *skip)]


def call(rows: list[Row]) -> tuple[Transcript, FakeLlm]:
    turns: list[Turn] = []
    outputs = {}
    for step, asks, bot, reply, output in rows:
        product = "P1" if asks and asks != "consent" else None
        turns.append(Turn(id=len(turns) + 1, speaker=Speaker.bot, step=CallStep(step), text=bot,
                          asks=Question(asks) if asks else None, product_id=product))  # fmt: skip
        if reply is None:
            continue
        turns.append(Turn(id=len(turns) + 1, speaker=Speaker.customer, step=CallStep(step), text=reply))
        if step == "open_recall":
            schema = "RecallReply"
        else:
            schema = SCHEMA[SlotKind.readback if step == "read_back" else SlotKind(asks)].__name__
        outputs[(schema, bot, reply)] = output
    return Transcript(call_id="c1", loan_id="L-FAKE-0001", language="hi", turns=tuple(turns)), FakeLlm(
        outputs
    )


def judged(rows: list[Row], premium: int = 25000):
    transcript, llm = call(rows)
    rec = record(PRODUCT.model_copy(update={"premium_inr": premium}))
    raw = extract(transcript, rec, llm)
    beliefs = to_beliefs(raw, rec, transcript)
    return raw, beliefs, evaluate(rec, beliefs)


def premium_outcomes(result) -> list[str]:
    product = result.products[0]
    return [o.reason.value for o in (*product.flags, *product.gaps) if o.rule_id.value == "premium"]


LIVE_SHAPE = [
    recall_row(RECALL_25, amount="25,000"),
    ("teach_back", None, INTRO, None, {}),
    kind_row(),
    read_back_row("पच्चीस हज़ार"),
    *rest(),
]


def test_the_live_shape_carries_the_recall_premium_and_passes_on_a_matching_record():
    raw, beliefs, result = judged(LIVE_SHAPE, premium=25000)
    premium = raw.products[0].premium
    assert isinstance(premium, Stated) and premium.evidence.quote == RECALL_25.strip()
    assert beliefs.for_product("P1").premium_inr.value == 25000
    assert premium_outcomes(result) == []
    assert result.tier is Tier.clear, (result.all_flags(), result.all_gaps())


def test_the_live_shape_on_a_differing_record_is_a_confirmed_difference():
    _, _, result = judged(LIVE_SHAPE, premium=41300)
    assert premium_outcomes(result) == ["premium_differs_confirmed"]
    assert result.tier is Tier.refer


def test_an_fd_named_in_recall_on_an_insurance_record_still_carries_its_premium():
    rows = [recall_row("बस एक FD बनवाई थी 12,500 की।", "deposit", "एक FD", "12,500"),
            ("teach_back", None, INTRO, None, {}), kind_row("FD है।", "deposit"),
            read_back_row("बारह हज़ार पाँच सौ"), *rest()]  # fmt: skip
    raw, _, result = judged(rows, premium=12500)
    assert raw.recall.items[0].product_id == "P1"  # the misdescription is paired to the one product
    assert premium_outcomes(result) == []
    assert "kind_differs" in {f.reason.value for f in result.all_flags()}
    _, _, differs = judged(rows, premium=41300)
    assert premium_outcomes(differs) == ["premium_differs_confirmed"]


def test_a_rejected_carried_premium_without_a_correction_is_a_read_back_gap():
    rows = [*LIVE_SHAPE[:3], read_back_row("पच्चीस हज़ार", "नहीं।", False), *rest()]
    _, _, result = judged(rows, premium=25000)
    assert premium_outcomes(result) == ["readback_rejected"]
    assert result.tier is Tier.incomplete


def test_a_correction_at_the_read_back_replaces_the_carried_premium():
    rows = [*LIVE_SHAPE[:3], read_back_row("पच्चीस हज़ार", "नहीं, तीस हज़ार।", False, "तीस हज़ार"), *rest()]
    raw, beliefs, result = judged(rows, premium=30000)
    assert beliefs.for_product("P1").premium_inr.value == 30000
    assert not raw.products[0].conflicts  # a correction at the read-back is never a conflict
    assert premium_outcomes(result) == ["readback_rejected"]  # as for any premium corrected at the read-back
    confirmed = [*rows[:4], ("read_back", "premium", READ_BACK.format("तीस हज़ार"), "हाँ।",
                             {"status": "stated", "confirms": True, "clauses": [1], "corrected_amount_span": None}),
                 *rows[4:]]  # fmt: skip
    _, _, again = judged(confirmed, premium=30000)
    assert premium_outcomes(again) == []


def test_a_recall_reply_with_two_amounts_carries_nothing_and_says_so():
    rows = [recall_row("एक बीमा लिया था 25,000 का और एक FD 10,000 की।", amount="25,000"),
            *LIVE_SHAPE[1:]]  # fmt: skip
    _, beliefs, result = judged(rows, premium=25000)
    premium = beliefs.for_product("P1").premium_inr
    assert isinstance(premium, Unclear) and premium.reason is GapReason.readback_mismatch
    assert premium_outcomes(result) == ["readback_mismatch"]  # not a quote-less "not asked"
    gap = next(g for g in result.products[0].gaps if g.rule_id.value == "premium")
    assert gap.quote == "हाँ, सही है"


def test_a_read_back_of_a_figure_no_recall_reply_said_carries_nothing():
    rows = [*LIVE_SHAPE[:3], read_back_row("तीस हज़ार"), *rest()]
    _, _, result = judged(rows, premium=30000)
    assert premium_outcomes(result) == ["readback_mismatch"]
    assert result.tier is Tier.incomplete


def test_a_normal_call_with_a_premium_question_is_unchanged():
    rows = [recall_row(RECALL_25, amount="25,000"), *BASE[1:]]  # BASE asks 41,300 and reads it back
    raw, _, result = judged(rows, premium=41300)
    assert raw.products[0].premium.evidence.quote == "इकतालीस हज़ार तीन सौ रुपये।"
    assert premium_outcomes(result) == []
    assert result.tier is Tier.clear


def test_a_recall_amount_with_no_read_back_later_is_never_the_premium():
    rows = [
        recall_row(RECALL_25, amount="25,000"),
        ("teach_back", None, INTRO, None, {}),
        kind_row(),
        *rest(),
    ]
    raw, _, result = judged(rows, premium=25000)
    assert raw.products[0].premium.status == "not_asked"
    assert premium_outcomes(result) == ["not_asked"]


# --- the last denial, in order -----------------------------------------------------------------

DENY = recall_row("कुछ नहीं लिया, बस लोन।", kind="")
AGAIN_Q = "और कुछ याद आ रहा है, लोन के साथ?"


def recall_again(reply: str, kind: str = "insurance", span: str = "एक बीमा") -> Row:
    row = recall_row(reply, kind, span)
    return (row[0], row[1], AGAIN_Q, row[3], row[4])


@pytest.mark.parametrize(
    ("recall_rows", "reason"),
    [
        ([DENY, recall_again("हाँ, एक बीमा लिया था।")], "recall_not_named"),
        ([recall_row("एक बीमा लिया था।"), recall_again("नहीं, कुछ नहीं लिया।", kind="")], "recall_denied"),
        ([DENY, recall_again("हाँ, एक बीमा लिया था।"),
          ("open_recall", None, "पक्का?", "नहीं, कुछ नहीं लिया।", {"items": [], "took_nothing": True})],
         "recall_denied"),
        ([DENY, recall_again("एक FD बनवाई थी।", "deposit", "एक FD")], "recall_denied"),
    ],
    ids=["deny_then_name", "name_then_deny", "deny_name_deny", "deny_then_misdescribe"],
)  # fmt: skip
def test_the_denial_that_stands_is_decided_by_order(recall_rows, reason):
    rows = [*recall_rows, *[r for r in BASE[1:] if r[1] != "kind"]]  # no kind question: recall alone decides
    _, beliefs, result = judged(rows, premium=41300)
    assert {f.reason.value for f in result.all_flags() if f.rule_id.value == "recall"} == {reason}
    if reason == "recall_denied":
        assert result.tier is Tier.refer
        assert (
            beliefs.recall.denial.quote
            == next(r[3] for r in reversed(recall_rows) if not r[4]["items"]).strip()
        )


# --- the conflict tolerance: 10% when either amount is hedged or a range, else 1% -------------


@pytest.mark.parametrize(
    ("again", "conflict"),
    [
        ("करीब चालीस हज़ार।", False),  # 3.1% from 41,300, hedged: within 10%
        ("चालीस बयालीस हज़ार।", False),  # a range around it
        ("चालीस हज़ार।", True),  # 3.1% and both exact: beyond 1%
        ("इकतालीस हज़ार।", False),  # 0.7%: within 1%
        ("करीब पैंतीस हज़ार।", True),  # 15%: beyond 10% even hedged
    ],
)
def test_two_premium_answers_conflict_only_beyond_their_tolerance(again, conflict):
    rows = []
    for row in BASE:
        rows.append(row)
        if row[1] == "premium" and row[0] == "teach_back":
            rows.append(("teach_back", "premium", "एक बार फिर बताइए, कितने दिए?", again,
                         {"status": "stated", "span": again.rstrip("।"), "clauses": [1]}))  # fmt: skip
    transcript, llm = build(rows)
    raw = extract(transcript, record(), llm)
    assert bool(raw.products[0].conflicts) is conflict


# --- the carry follows the recall reply's change check -----------------------------------------
# A premium is carried only when the recall reply's change check said `none`, or the reply had one
# clause and no marker word, so needed no check. Premium 41,300 never asked; the bot reads it back and hears "हाँ जी।".

READ_41 = "इकतालीस हज़ार तीन सौ"


def carry_rows(reply: str) -> list[Row]:
    return [recall_row(reply, amount=READ_41), ("teach_back", None, INTRO, None, {}), kind_row(),
            read_back_row(READ_41, "हाँ जी।"), *rest()]  # fmt: skip


def judged_scripted(reply: str, script):
    transcript, llm = call(carry_rows(reply))
    script(llm)
    rec = record(PRODUCT.model_copy(update={"premium_inr": 41300}))
    raw = extract(transcript, rec, llm)
    beliefs = to_beliefs(raw, rec, transcript)
    return raw, beliefs, evaluate(rec, beliefs)


def checked(reply: str, label: str, first=(), final=()):
    def script(llm: FakeLlm) -> None:
        llm.say("ChangeReply", reply, change=label, first_clauses=list(first), final_clauses=list(final))

    return script


def failing(schema: str, reply: str, error: Exception):
    def script(llm: FakeLlm) -> None:
        llm.errors[(schema, reply)] = error

    return script


def assert_not_carried(raw, beliefs, result) -> None:
    assert not isinstance(raw.products[0].premium, Stated)
    premium = beliefs.for_product("P1").premium_inr
    assert isinstance(premium, Unclear) and premium.reason is GapReason.readback_mismatch
    assert premium_outcomes(result) == ["readback_mismatch"]
    assert result.tier is not Tier.clear


@pytest.mark.parametrize(
    "reply",
    [
        "एक बीमा लिया था, इकतालीस हज़ार तीन सौ, नहीं नहीं, पता नहीं कितने का।",
        "एक बीमा लिया था, इकतालीस हज़ार तीन सौ का, नहीं, याद नहीं ठीक से।",
        "insurance liya tha, 41,300 ka, ruko, nahi, pakka nahi pata kitne ka.",
        "बीमा लिया था, इकतालीस हज़ार तीन सौ, अरे नहीं, वो तो लोन की किस्त थी।",
    ],
)
def test_a_premium_withdrawn_in_the_recall_reply_is_not_carried(reply):
    assert_not_carried(*judged_scripted(reply, checked(reply, "withdrawn", first=[1, 2])))


@pytest.mark.parametrize(
    ("reply", "first", "final"),
    [
        ("एक FD बनवाई थी, इकतालीस हज़ार तीन सौ की, नहीं, बीमा था।", [1, 2], [4]),
        ("बीमा लिया था, इकतालीस हज़ार तीन सौ, मतलब पत्नी के नाम पर नहीं, मेरे नाम पर।", [3], [4]),
    ],
)
def test_a_premium_in_a_recall_reply_the_check_found_corrected_is_not_carried(reply, first, final):
    assert_not_carried(*judged_scripted(reply, checked(reply, "corrected", first, final)))


TWO_CLAUSES = "एक बीमा लिया था, इकतालीस हज़ार तीन सौ का।"


@pytest.mark.parametrize(
    "error", [LlmOutputInvalid(model="m", attempts=3, last_error="x"), TransportError("down")]
)
def test_a_failed_check_on_the_recall_reply_carries_nothing(error):
    assert_not_carried(*judged_scripted(TWO_CLAUSES, failing("ChangeReply", TWO_CLAUSES, error)))


@pytest.mark.parametrize("reply", [TWO_CLAUSES, "एक बीमा लिया था इकतालीस हज़ार तीन सौ का।"])
@pytest.mark.parametrize(
    "error", [LlmOutputInvalid(model="m", attempts=3, last_error="x"), TransportError("down")]
)
def test_a_failed_answer_call_on_the_recall_reply_carries_nothing(reply, error):
    assert_not_carried(*judged_scripted(reply, failing("RecallReply", reply, error)))


@pytest.mark.parametrize("reply", [TWO_CLAUSES, "हाँ एक बीमा भी, इकतालीस हज़ार तीन सौ रुपये का।"])
def test_a_recall_reply_whose_check_said_none_still_carries_and_ends_clear(reply):
    raw, beliefs, result = judged_scripted(reply, checked(reply, "none"))
    premium = raw.products[0].premium
    assert isinstance(premium, Stated) and premium.evidence.quote == reply
    assert beliefs.for_product("P1").premium_inr.value == 41300
    assert premium_outcomes(result) == []
    assert result.tier is Tier.clear, (result.all_flags(), result.all_gaps())


@pytest.mark.parametrize(
    "reply", ["एक बीमा लिया था इकतालीस हज़ार तीन सौ का।", "बस एक बीमा लिया था इकतालीस हज़ार तीन सौ रुपये का।"]
)
def test_a_one_clause_recall_reply_gets_no_check_and_still_carries(reply):
    raw, beliefs, result = judged_scripted(reply, lambda llm: None)
    assert isinstance(raw.products[0].premium, Stated)
    assert beliefs.for_product("P1").premium_inr.value == 41300
    assert premium_outcomes(result) == []
    assert result.tier is Tier.clear, (result.all_flags(), result.all_gaps())
