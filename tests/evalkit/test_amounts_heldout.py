"""The held-out amounts set: shape, determinism, gold arithmetic. Never calls the parser under test."""

import hashlib
import json
import unicodedata
from collections import Counter
from fractions import Fraction as F
from pathlib import Path

import pytest

from samajh.amounts import spoken_amount
from samajh.evalkit.amounts import generate as generate_v1
from samajh.evalkit.amounts import heldout
from samajh.evalkit.amounts.__main__ import main
from samajh.evalkit.amounts.grammar import jsonl_bytes
from samajh.types import Language

DATA = Path(__file__).parents[2] / "data" / "amounts_v2"
ROWS = heldout.generate()
PER_LANGUAGE = {"skipped": 34, "control": 34, "general": 48, "fraction": 16, "large": 8}

# Typed apart from the generator's tables.
_COUNT_HI = dict(zip(["दो", "तीन", "चार", "पाँच", "छह", "सात", "आठ", "नौ"], range(2, 10), strict=True))
_COUNT_EN = dict(zip(["one", "two", "three", "four", "five", "six"], range(1, 7), strict=True))
_FRACTION_HI = (
    {"सवा": F(5, 4), "डेढ़": F(3, 2), "ढाई": F(5, 2)}
    | {f"सवा {w}": n + F(1, 4) for w, n in _COUNT_HI.items()}
    | {f"साढ़े {w}": n + F(1, 2) for w, n in _COUNT_HI.items()}
    | {f"पौने {w}": n - F(1, 4) for w, n in _COUNT_HI.items()}
)
_DECIMAL_EN = {"five": F(1, 2), "two five": F(1, 4), "seven five": F(3, 4)}
FRACTION_WORDS = {
    "hi": _FRACTION_HI,
    "hi-en": _FRACTION_HI
    | {f"{w} and a half": n + F(1, 2) for w, n in _COUNT_EN.items()}
    | {f"{w} point {d}": n + part for w, n in _COUNT_EN.items() for d, part in _DECIMAL_EN.items()},
}
UNIT_WORDS = {
    "hi": {"सौ": 10**2, "हज़ार": 10**3, "लाख": 10**5, "करोड़": 10**7},
    "hi-en": {"hundred": 10**2, "thousand": 10**3, "lakh": 10**5, "crore": 10**7},
}
_HI_NUMBERS = "एक दो तीन चार पाँच छह सात आठ नौ दस बीस सौ हज़ार लाख करोड़ आधा डेढ़ ढाई सवा साढ़े पौने"
_EN_NUMBERS = "one two three four five six seven eight nine ten hundred thousand lakh crore half point"
NUMBER_WORDS = {"hi": set(_HI_NUMBERS.split()), "hi-en": set(f"{_HI_NUMBERS} {_EN_NUMBERS}".split())}
# For each skipped shape: the unit words that must be spoken, and the ones that must not.
SPOKEN_UNITS = {
    "lakh_units": ((10**5,), (10**7, 10**3, 10**2)),
    "lakh_hundreds": ((10**5, 10**2), (10**7, 10**3)),
    "thousand_units": ((10**3,), (10**7, 10**5, 10**2)),
    "crore_thousands": ((10**7, 10**3), (10**5, 10**2)),
}


def rows_of(stratum: str, language: str | None = None) -> list[dict]:
    return [
        r for r in ROWS if r["tags"]["stratum"] == stratum and (language is None or r["language"] == language)
    ]


def fraction_phrase(row: dict) -> tuple[str, int]:
    found = [
        (f"{words} {unit_word}", value * unit)
        for words, value in FRACTION_WORDS[row["language"]].items()
        for unit_word, unit in UNIT_WORDS[row["language"]].items()
        if f"{words} {unit_word}" in row["text"]
    ]
    phrase, amount = max(found, key=lambda pair: len(pair[0]))
    assert amount.denominator == 1
    return phrase, int(amount)


def amount_phrase(row: dict) -> str:
    if row["tags"]["stratum"] == "fraction":
        return fraction_phrase(row)[0]
    return spoken_amount(row["gold"]["amount_inr"], Language(row["language"]))


def test_same_seed_same_rows_and_other_seed_differs():
    assert heldout.generate() == ROWS
    assert heldout.generate(seed=1) != ROWS


def test_committed_manifest_is_what_generate_writes():
    data = (DATA / "amounts-v2.jsonl").read_bytes()
    assert data == jsonl_bytes(ROWS)
    digest = hashlib.sha256(data).hexdigest()
    assert (DATA / "amounts-v2.sha256").read_text() == f"{digest}  amounts-v2.jsonl\n"
    assert [json.loads(line) for line in data.decode("utf-8").splitlines()] == ROWS


def test_the_cli_writes_either_set_and_keeps_v1_the_default(tmp_path):
    assert main(["--out", str(tmp_path), "--set", "v2"]) == 0
    assert (tmp_path / "amounts-v2.jsonl").read_bytes() == jsonl_bytes(ROWS)
    assert main(["--out", str(tmp_path)]) == 0
    assert (tmp_path / "amounts-v1.jsonl").read_bytes() == jsonl_bytes(generate_v1())
    (tmp_path / "amounts-v2.jsonl").write_bytes(b"edited\n")
    assert main(["--out", str(tmp_path), "--set", "v2"]) == 1


def test_row_format_and_counts():
    assert len({r["id"] for r in ROWS}) == len(ROWS) == 280
    for language in heldout.LANGUAGES:
        assert Counter(r["tags"]["stratum"] for r in ROWS if r["language"] == language) == PER_LANGUAGE
    for row in ROWS:
        assert set(row) == {"id", "language", "text", "gold", "tags"}
        assert type(row["gold"]["amount_inr"]) is int
        assert all(type(value) is str for value in row["tags"].values())
        assert row["id"].startswith(f"amt2-{row['language']}-{row['tags']['stratum']}-")
        assert row["tags"]["carrier"].startswith(row["language"])


def test_most_amounts_are_retail_and_the_band_tag_is_the_amount():
    for row in ROWS:
        assert (row["tags"]["band"] == "retail") == (500 <= row["gold"]["amount_inr"] <= 500_000)
    assert sum(r["tags"]["band"] == "retail" for r in ROWS) >= 0.7 * len(ROWS)
    assert all(r["tags"]["band"] == "retail" for r in rows_of("general"))
    assert all(r["tags"]["band"] == "outside" for r in rows_of("large"))
    assert sum(r["tags"]["band"] == "retail" for r in rows_of("skipped")) >= 40


@pytest.mark.parametrize(
    ("rupees", "skips"),
    [
        (300_200, True),
        (6_025, True),
        (19_080, True),
        (20_045_000, True),
        (500_025, True),
        (302_000, False),
        (6_250, False),
        (4_501_000, False),
        (52_000, False),
        (700, False),
        (12_345_678, False),
        (0, False),
    ],
)
def test_skips_a_group(rupees, skips):
    assert heldout.skips_a_group(rupees) is skips


def test_only_the_skipped_stratum_skips_a_group():
    for row in ROWS:
        if row["tags"]["stratum"] != "fraction":
            assert heldout.skips_a_group(row["gold"]["amount_inr"]) == (row["tags"]["stratum"] == "skipped")
    assert len(rows_of("skipped")) >= 60
    assert Counter(r["tags"]["shape"] for r in rows_of("skipped")) == {
        "lakh_units": 18,
        "lakh_hundreds": 18,
        "thousand_units": 20,
        "crore_thousands": 12,
    }


@pytest.mark.parametrize("row", rows_of("skipped"), ids=lambda r: r["id"])
def test_a_skipped_amount_is_spoken_without_the_middle_unit(row):
    words = row["text"].split()
    size = {unit: word for word, unit in UNIT_WORDS[row["language"]].items()}
    spoken, silent = SPOKEN_UNITS[row["tags"]["shape"]]
    assert all(size[unit] in words for unit in spoken)
    assert not any(size[unit] in words for unit in silent)


def test_each_skipped_item_has_one_control_that_differs_only_in_the_lower_group():
    pairs: dict[str, dict[str, dict]] = {}
    for row in rows_of("skipped") + rows_of("control"):
        pairs.setdefault(row["tags"]["pair"], {})[row["tags"]["stratum"]] = row
    assert len(pairs) == 68
    for pair in pairs.values():
        skipped, control = pair["skipped"], pair["control"]
        assert skipped["language"] == control["language"]
        assert skipped["tags"]["carrier"] == control["tags"]["carrier"]
        assert skipped["tags"]["shape"] == control["tags"]["shape"]
        assert skipped["tags"]["block"] == control["tags"]["block"] == "gap"
        # Same leading group: the two spoken amounts start with the same count and unit word.
        lead = amount_phrase(skipped).split()
        unit = next(i for i, word in enumerate(lead) if word in UNIT_WORDS[skipped["language"]])
        assert amount_phrase(control).split()[: unit + 1] == lead[: unit + 1]
    assert not any("pair" in r["tags"] for r in ROWS if r["tags"]["stratum"] not in ("skipped", "control"))


@pytest.mark.parametrize("language", heldout.LANGUAGES)
def test_amounts_are_new_against_v1_outside_the_fraction_stratum(language):
    v1 = {r["gold"]["amount_inr"] for r in generate_v1() if r["language"] == language}
    rows = [r for r in ROWS if r["language"] == language]
    whole = [r["gold"]["amount_inr"] for r in rows if r["tags"]["stratum"] != "fraction"]
    assert len(set(whole)) == len(whole) and not v1 & set(whole)
    for row in rows_of("fraction", language):
        assert (row["tags"]["v1_amount"] == "yes") == (row["gold"]["amount_inr"] in v1)
    v1_texts = {r["text"] for r in generate_v1()}
    assert not v1_texts & {r["text"] for r in ROWS}


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["id"])
def test_text_has_one_amount_in_words(row):
    text = row["text"]
    assert not any(unicodedata.category(ch) == "Nd" for ch in text)
    phrase = amount_phrase(row)
    assert text.count(phrase) == 1
    carrier_words = text.replace(phrase, " ").replace("।", " ").replace(",", " ").split()
    assert not NUMBER_WORDS[row["language"]] & set(carrier_words)
    assert len(text) <= 110


@pytest.mark.parametrize("row", rows_of("fraction"), ids=lambda r: r["id"])
def test_fraction_gold_is_fraction_times_unit(row):
    assert fraction_phrase(row)[1] == row["gold"]["amount_inr"]


def test_fraction_wordings_are_distinct_and_cover_the_forms():
    for language, forms in (("hi", 5), ("hi-en", 7)):
        rows = rows_of("fraction", language)
        assert len({fraction_phrase(r)[0] for r in rows}) == len(rows)
        assert len({r["tags"]["shape"] for r in rows}) == forms


def test_carriers_are_used_evenly_and_the_first_twenty_rows_are_a_fair_sample():
    for language in heldout.LANGUAGES:
        carriers = Counter(r["tags"]["carrier"] for r in ROWS if r["language"] == language)
        assert len(carriers) == 12 and max(carriers.values()) - min(carriers.values()) <= 8
    head = ROWS[:20]
    assert Counter(r["language"] for r in head) == {"hi": 10, "hi-en": 10}
    assert {"skipped", "control", "general"} <= {r["tags"]["stratum"] for r in head}
