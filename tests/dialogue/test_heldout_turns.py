"""The rule interpreter on the generated reply set (`fixtures/turns_heldout.jsonl`), played into the real machine.

n = 408 replies (17 behaviours x 4 languages x 6), written by a cheap LLM from a behaviour
description (`probes/gen_turns.py`). The label is what the writer was told to write, so some
labels are wrong, and the Tamil and Kannada rows are not human-reviewed. Fold 0 was used to tune
the word lists; fold 1 was not, except that two fold-1 replies were read because they had ended
a call wrongly ("बाद में पता चला मुझे इसका"), and the bare "later" words were then removed.

These tests pin the two things that matter: the rules never end a call on a reply that was not a
refusal, and their hit rate does not drop below what was measured. 2026-11-10 (iteration 1): fold 0
191/209, fold 1 155/199. Call v2 (P2): fold 0 189/209, fold 1 155/199. The rows lost are first-name
replies labelled "confirmed" that the stricter right-party rule now asks again by design, because
they do not claim to be the borrower ("ಹೇಳಿ.", "பேசுறது நான்தான். என்ன வேணும்?", "Haan, Ramesh hi.");
one fold-1 refusal is newly read ("இன்னைக்கு முடியாது, நாளைக்கு கூப்பிடுங்க.").
Round 2 (asymmetric opening): fold 0 180/209, fold 1 150/199, rules only. Lost: first-name replies the
set labels "confirmed" that are acknowledgements or carry a name ("हाँ, बोलिए।", "Yes, Ramesh speaking"),
which the rules alone now re-ask by design (the classifier judges the named ones); and premium replies
such as "Maine 50,000 rupees pay kiya." that samajh.amounts (P3a, changed meanwhile) now marks
malformed, so the call asks again. Every refusal row of fold 0 is now honoured.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from samajh.dialogue import RuleInterpreter
from samajh.dialogue.__main__ import effect_of
from samajh.types import Language

ROWS = [
    json.loads(line)
    for line in (Path(__file__).parent / "fixtures" / "turns_heldout.jsonl")
    .read_text(encoding="utf-8")
    .splitlines()
]
ENDS = {"decline", "human", "wrong_party"}
RULES = RuleInterpreter()


@pytest.fixture(scope="module")
def effects() -> dict[str, str]:
    return {
        row["id"]: effect_of(Language(row["language"]), row["question_key"], row["text"], RULES)
        for row in ROWS
    }


def test_the_set_is_the_one_measured():
    assert len(ROWS) == 408 and len({row["id"] for row in ROWS}) == 408
    assert {row["language"] for row in ROWS} == {language.value for language in Language}


def test_the_rules_never_end_a_call_on_a_reply_that_did_not_ask_for_it(effects):
    wrongly_ended = [
        (row["language"], row["gold"], effects[row["id"]], row["text"])
        for row in ROWS
        if row["gold"] not in ENDS and effects[row["id"]] in ENDS
    ]
    assert wrongly_ended == []


@pytest.mark.parametrize("fold, measured", [(0, 180), (1, 150)])
def test_the_rules_hit_rate_has_not_dropped(effects, fold, measured):
    rows = [row for row in ROWS if row["fold"] == fold]
    right = sum(effects[row["id"]] in (row["gold"], f"check_{row['gold']}") for row in rows)
    assert right >= measured, f"fold {fold}: {right}/{len(rows)}"
