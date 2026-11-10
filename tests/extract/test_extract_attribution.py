"""Which product on record a thing named in open recall is. Code decides; the model never sees the record."""

import devset

from samajh.extract import SlotKind, slots
from samajh.extract._extract import attribute
from samajh.types import CallStep, LoanRecord, RawRecallItem, Transcript

RECORD = devset.scenarios()[0].record
TWO = LoanRecord.model_validate(
    RECORD.model_dump() | {"products": [*RECORD.products, RECORD.products[0].model_copy(update={"id": "P2"})]}
)


def named(*kinds: str | None, grounded: bool = True) -> list[tuple[RawRecallItem, bool]]:
    return [
        (RawRecallItem(evidence={"quote": f"thing {k}", "turn_id": 2}, kind=kind), grounded)
        for k, kind in enumerate(kinds)
    ]


def matched(items, record=RECORD) -> list[str | None]:
    return [item.product_id for item in attribute(items, record)]


def test_the_kind_on_record_matches_the_product():
    assert matched(named("insurance")) == ["P1"]


def test_one_misdescribed_thing_is_the_one_product_on_record():
    assert matched(named("deposit")) == ["P1"]
    assert matched(named("investment")) == ["P1"]
    assert matched(named("other")) == ["P1"]


def test_a_fee_or_an_unnamed_kind_is_never_the_product():
    assert matched(named("fee")) == [None]
    assert matched(named(None)) == [None]
    assert matched(named("fee", "deposit")) == [None, "P1"]


def test_a_correctly_named_product_leaves_other_things_off_the_record():
    assert matched(named("deposit", "insurance")) == [None, "P1"]
    assert matched(named("insurance", "insurance")) == ["P1", None]  # one item per product


def test_two_misdescribed_things_and_one_product_are_not_guessed():
    assert matched(named("deposit", "investment")) == [None, None]


def test_an_item_whose_span_was_not_in_the_reply_is_never_matched():
    assert matched(named("insurance", grounded=False)) == [None]
    assert matched(named("deposit", grounded=False)) == [None]


def test_two_products_on_record():
    assert matched(named("insurance", "insurance"), TWO) == ["P1", "P2"]
    assert matched(named("insurance", "deposit"), TWO) == ["P1", "P2"]
    assert matched(named("deposit"), TWO) == [None]  # which of the two is it? not guessed


def _slot_kinds(turns: list[dict]) -> list[SlotKind]:
    transcript = Transcript.model_validate(
        {"call_id": "c", "loan_id": RECORD.loan_id, "language": "hi", "turns": turns}
    )
    return [s.kind for s in slots(transcript, RECORD)]


def test_what_a_reply_answers_follows_the_tags_of_the_bot_turn_before_it():
    def pair(n: int, step: CallStep, **tags) -> list[dict]:
        return [
            {"id": n, "speaker": "bot", "step": step, "text": "q", **tags},
            {"id": n + 1, "speaker": "customer", "step": step, "text": "a"},
        ]

    turns = [
        {"id": 1, "speaker": "customer", "step": "right_party_check", "text": "hello"},
        *pair(2, "disclosure"),
        *pair(4, "open_recall"),
        *pair(6, "teach_back", asks="kind", product_id="P1"),
        *pair(8, "read_back", asks="premium", product_id="P1"),
        *pair(10, "teach_back", asks="cover"),  # no product: the engine does not count it as asked
        *pair(12, "consent_check", asks="consent"),
        *pair(14, "read_back", asks="cover", product_id="P1"),  # only the premium has a read-back
        {"id": 16, "speaker": "customer", "step": "close", "text": "one more thing"},
    ]
    assert _slot_kinds(turns) == [
        SlotKind.other, SlotKind.other, SlotKind.recall, SlotKind.kind, SlotKind.readback, SlotKind.other,
        SlotKind.consent, SlotKind.other, SlotKind.other,
    ]  # fmt: skip
