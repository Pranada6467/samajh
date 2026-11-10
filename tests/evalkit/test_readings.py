"""Readings of one clip compared: outcomes, the digits-against-words mechanism, acceptance schemes."""

from __future__ import annotations

import pytest

from samajh.evalkit.plan import SttSpec, VoiceSpec
from samajh.evalkit.readings import (
    READINGS,
    Scheme,
    acceptance,
    clips,
    disagreement,
    mechanism,
    outcomes,
    rate,
    where,
)
from samajh.evalkit.score import ScoreRow
from samajh.types import Language

GOLD = 300_200
SPECS = {
    "v3.0 transcribe item": SttSpec(model="prisma-v3.0", format="transcribe"),
    "v3.0 verbatim item": SttSpec(model="prisma-v3.0", format="verbatim"),
    "v2.5 transcribe item": SttSpec(model="prisma-v2.5", format="transcribe"),
}


def rows(
    item: str, readings: dict[str, int | None], *, condition: str = "phone", **tags: str
) -> list[ScoreRow]:
    """Score rows for one clip, given each reading's value. Naive rows are added as a distractor."""
    out = []
    for name, value in readings.items():
        label, output = READINGS[name]
        for method, predicted in (("parser", value), ("naive", 1)):
            out.append(
                ScoreRow(
                    item_id=item,
                    language=Language.hi,
                    tags=tags,
                    voice=VoiceSpec(model="timbre-v3.0", voice="Shivani"),
                    condition=condition,
                    stt=SPECS[label],
                    output=output,
                    method=method,
                    transcript="",
                    gold=GOLD,
                    predicted=predicted,
                    note="",
                    correct=predicted == GOLD,
                )
            )
    return out


def clip_rows() -> list[ScoreRow]:
    def four(a, v, b, lit):
        return {"v3.0 transcribe": a, "v3.0 verbatim": v, "v2.5 transcribe": b, "v2.5 literal": lit}

    return [
        *rows("all-right", four(GOLD, GOLD, GOLD, GOLD), stratum="control"),
        *rows("formatting", four(302_000, GOLD, GOLD, GOLD), stratum="skipped"),
        *rows("misheard", four(302_000, 302_000, GOLD, GOLD), stratum="skipped"),
        *rows("words-refused", four(3_200, None, None, GOLD), stratum="skipped"),
        *rows("shared-error", four(5_000, 7_000, 5_000, 5_000), stratum="control"),
        *rows("both-refuse", four(None, GOLD, None, None), stratum="control"),
        *rows("all-right", four(GOLD, GOLD, GOLD, GOLD), condition="clean16k", stratum="control"),
    ]


@pytest.fixture
def phone():
    return where(clips(clip_rows()), condition="phone")


def test_clips_group_the_parser_rows_by_item_and_condition():
    found = clips(clip_rows())
    assert len(found) == 7
    assert {(clip.item_id, clip.condition) for clip in found} >= {
        ("all-right", "phone"),
        ("all-right", "clean16k"),
    }
    assert all(set(clip.values) == set(READINGS) for clip in found)
    assert all(clip.values["v3.0 transcribe"] == 1 for clip in clips(clip_rows(), method="naive"))


def test_a_wrong_amount_and_a_refusal_are_different_outcomes(phone):
    tally = outcomes(phone, "v3.0 transcribe")
    assert (tally.n, tally.correct, tally.refused, tally.wrong) == (6, 1, 1, 4)
    tally = outcomes(phone, "v2.5 transcribe")
    assert (tally.n, tally.correct, tally.refused, tally.wrong) == (6, 3, 2, 1)
    assert outcomes(where(phone, stratum="skipped"), "v3.0 transcribe").wrong == 3


def test_mechanism_splits_wrong_digits_by_what_the_words_say(phone):
    found = mechanism(phone, digits="v3.0 transcribe", words="v3.0 verbatim")
    assert found.digits_wrong == 4
    assert (found.words_right, found.words_same_wrong, found.words_other_wrong, found.words_refused) == (
        1,
        1,
        1,
        1,
    )


def test_a_scheme_accepts_only_equal_answers_and_counts_its_requests(phone):
    two_models = Scheme("two models", ("v3.0 transcribe", "v2.5 transcribe"))
    one_call = Scheme("literal check", ("v2.5 transcribe", "v2.5 literal"))
    assert two_models.requests == ("v3.0 transcribe item", "v2.5 transcribe item")
    assert one_call.requests == ("v2.5 transcribe item",)
    got = acceptance(phone, two_models)
    assert (got.n, got.accepted, got.accepted_right, got.accepted_wrong) == (6, 2, 1, 1)
    got = acceptance(phone, one_call)
    assert (got.n, got.accepted, got.accepted_right, got.accepted_wrong) == (6, 4, 3, 1)
    alone = acceptance(phone, Scheme("alone", ("v3.0 transcribe",)))
    assert (alone.accepted, alone.accepted_right) == (5, 1)


def test_disagreement_says_who_was_right_when_the_scheme_does_not_accept(phone):
    found = disagreement(phone, "v3.0 transcribe", "v2.5 transcribe")
    assert found.n == 4
    assert (found.both_answered, found.one_refused, found.both_refused) == (2, 1, 1)
    assert (found.first_right, found.second_right, found.neither_right) == (0, 2, 2)


def test_rate_text_and_filters(phone):
    assert rate(17, 240) == "17/240 (7%, 4-11)"
    assert rate(0, 0) == "0/0"
    assert len(where(phone, stratum="skipped", language="hi")) == 3
    assert where(phone, language="ta") == []
