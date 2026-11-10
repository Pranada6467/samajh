"""Regression over every row of the spoken-amounts pilot: 80 real Prisma STT responses.

This is the non-circular evidence for the parser: the transcripts came from the live API,
the gold amounts from the sentences that were spoken (references/pilots/pilot.py).
"""

import json
from pathlib import Path

import pytest

from samajh.amounts import Parsed, parse_amount, spoken_amount
from samajh.types import Language

ROWS = json.loads(
    (Path(__file__).resolve().parents[2] / "references/pilots/results.json").read_text(encoding="utf-8")
)
# The one recognition miss: on phone audio v3.0 dropped "पौने" from "पौने दो लाख" (item hi08).
DROPPED_PAUNE = {("hi08", "v3.0_transcribe", "phone8k"), ("hi08", "v3.0_auto", "phone8k")}


def _key(row: dict) -> tuple[str, str, str]:
    return row["id"], row["config"], row["cond"]


def _named(rows: list[dict]) -> list:
    return [pytest.param(row, id="-".join(_key(row))) for row in rows]


OK = [row for row in ROWS if row["status"] == 200]
ERRORS = [row for row in ROWS if row["status"] != 200]
MISSES = [row for row in OK if _key(row) in DROPPED_PAUNE]
READABLE = [row for row in OK if _key(row) not in DROPPED_PAUNE]


def _rupees(row: dict) -> int | None:
    result = parse_amount(row["transcript"])
    return result.rupees if isinstance(result, Parsed) else None


def test_dataset_is_whole():
    assert (len(ROWS), len(OK), len(READABLE), len(MISSES), len(ERRORS)) == (80, 78, 76, 2, 2)
    wrong = {_key(row) for row in OK if _rupees(row) != row["gold"]}
    assert len(OK) - len(wrong) == 76
    assert wrong == DROPPED_PAUNE


@pytest.mark.parametrize("row", _named(READABLE))
def test_transcript_parses_to_the_spoken_amount(row):
    result = parse_amount(row["transcript"])
    assert isinstance(result, Parsed), result
    assert result.rupees == row["gold"]
    assert row["transcript"][result.span.start : result.span.end] == result.span.text


@pytest.mark.parametrize("row", _named(MISSES))
def test_dropped_fraction_word_is_wrong_and_the_read_back_exposes_it(row):
    assert row["gold"] == 175_000
    result = parse_amount(row["transcript"])
    # Wrong, and no parser can know: the word that made it 1,75,000 is not in the transcript.
    assert isinstance(result, Parsed) and result.rupees == 200_000
    heard = spoken_amount(result.rupees, Language.hi)
    assert heard == "दो लाख"
    assert heard != spoken_amount(row["gold"], Language.hi) == "एक लाख पचहत्तर हज़ार"


@pytest.mark.parametrize("row", _named(ERRORS))
def test_gateway_error_page_is_not_an_amount(row):
    assert row["status"] == 504 and row["transcript"].startswith("<!DOCTYPE html>")
    assert not isinstance(parse_amount(row["transcript"]), Parsed)
