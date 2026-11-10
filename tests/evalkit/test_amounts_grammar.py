"""The amounts test set: shape, determinism, gold arithmetic. Never calls the parser under test."""

import hashlib
import json
import statistics
import unicodedata
from collections import Counter
from fractions import Fraction as F
from pathlib import Path

import pytest

from samajh.amounts import spoken_amount
from samajh.evalkit.amounts import generate, jsonl_bytes
from samajh.evalkit.amounts.__main__ import main
from samajh.types import Language

DATA = Path(__file__).parents[2] / "data" / "amounts"
LANGUAGES = ("hi", "hi-en", "ta", "kn")
STRATA = ("plain", "lakh_crore", "fraction", "irregular_21_99")
ROWS = generate()

# An independent table of fraction words, typed apart from the generator's.
_HI_COUNTS = "दो तीन चार पाँच छह सात आठ नौ"
_EN_COUNTS = "one two three four five six seven eight nine"
_TA_HALVES = "ஒன்றரை இரண்டரை மூன்றரை நான்கரை ஐந்தரை ஆறரை ஏழரை எட்டரை ஒன்பதரை"
_KN_HALVES = "ಒಂದೂವರೆ ಎರಡೂವರೆ ಮೂರೂವರೆ ನಾಲ್ಕೂವರೆ ಐದೂವರೆ ಆರೂವರೆ ಏಳೂವರೆ ಎಂಟೂವರೆ ಒಂಬತ್ತೂವರೆ"
_HI_COUNT = dict(zip(_HI_COUNTS.split(), range(2, 10)))
_EN_COUNT = dict(zip(_EN_COUNTS.split(), range(1, 10)))
_HI = (
    {"सवा": F(5, 4), "डेढ़": F(3, 2), "ढाई": F(5, 2)}
    | {f"सवा {w}": n + F(1, 4) for w, n in _HI_COUNT.items()}
    | {f"साढ़े {w}": n + F(1, 2) for w, n in _HI_COUNT.items()}
    | {f"पौने {w}": n - F(1, 4) for w, n in _HI_COUNT.items()}
)
FRACTION_WORDS = {
    "hi": _HI,
    "hi-en": _HI
    | {f"{w} and a half": n + F(1, 2) for w, n in _EN_COUNT.items()}
    | {f"{w} point five": n + F(5, 10) for w, n in _EN_COUNT.items()}
    | {f"{w} point two five": n + F(25, 100) for w, n in _EN_COUNT.items()},
    "ta": {"அரை": F(1, 2), "முக்கால்": F(3, 4), "ஒன்றேகால்": F(5, 4), "இரண்டேகால்": F(9, 4), "ஒன்றே முக்கால்": F(7, 4)}
    | {w: n + F(1, 2) for n, w in enumerate(_TA_HALVES.split(), 1)},
    "kn": {"ಅರ್ಧ": F(1, 2), "ಮುಕ್ಕಾಲು": F(3, 4), "ಒಂದೂಕಾಲು": F(5, 4), "ಎರಡೂಕಾಲು": F(9, 4), "ಒಂದೂ ಮುಕ್ಕಾಲು": F(7, 4)}
    | {w: n + F(1, 2) for n, w in enumerate(_KN_HALVES.split(), 1)},
}
UNIT_WORDS = {
    "hi": {"सौ": 10**2, "हज़ार": 10**3, "लाख": 10**5, "करोड़": 10**7},
    "hi-en": {"thousand": 10**3, "lakh": 10**5, "crore": 10**7},
    "ta": {"ஆயிரம்": 10**3, "லட்சம்": 10**5, "கோடி": 10**7},
    "kn": {"ಸಾವಿರ": 10**3, "ಲಕ್ಷ": 10**5, "ಕೋಟಿ": 10**7},
}
# The forms the brief names; each must start at least one fraction phrase in its language.
REQUIRED_FORMS = {
    "hi": ("सवा", "साढ़े", "पौने", "डेढ़", "ढाई"),
    "hi-en": (
        "one and a half",
        "two and a half",
        "one point five",
        "two point two five",
        "three point five",
        "seven point five",
        "ढाई",
        "डेढ़",
        "साढ़े",
        "सवा",
        "पौने",
    ),
    "ta": ("ஒன்றரை", "இரண்டரை", "மூன்றரை", "ஒன்றேகால்", "இரண்டேகால்", "ஒன்றே முக்கால்", "முக்கால்", "அரை"),
    "kn": ("ಒಂದೂವರೆ", "ಎರಡೂವರೆ", "ಮೂರೂವರೆ", "ಒಂದೂಕಾಲು", "ಎರಡೂಕಾಲು", "ಒಂದೂ ಮುಕ್ಕಾಲು", "ಮುಕ್ಕಾಲು", "ಅರ್ಧ"),
}
_HI_NUMBERS = "एक दो तीन चार पाँच छह सात आठ नौ दस बीस सौ हज़ार लाख करोड़ आधा डेढ़ ढाई सवा साढ़े पौने"
_EN_NUMBERS = "one two three four five six seven eight nine ten hundred thousand lakh crore half point"
_TA_NUMBERS = "ஒரு ஒன்று இரண்டு மூன்று நான்கு ஐந்து ஆறு ஏழு எட்டு ஒன்பது பத்து நூறு ஆயிரம் லட்சம் கோடி அரை கால் முக்கால்"
_KN_NUMBERS = "ಒಂದು ಎರಡು ಮೂರು ನಾಲ್ಕು ಐದು ಆರು ಏಳು ಎಂಟು ಒಂಬತ್ತು ಹತ್ತು ನೂರು ಸಾವಿರ ಲಕ್ಷ ಕೋಟಿ ಅರ್ಧ ಕಾಲು ಮುಕ್ಕಾಲು"
NUMBER_WORDS = {
    "hi": set(_HI_NUMBERS.split()),
    "hi-en": set(f"{_HI_NUMBERS} {_EN_NUMBERS}".split()),
    "ta": set(_TA_NUMBERS.split()),
    "kn": set(_KN_NUMBERS.split()),
}


def rows_of(language: str, stratum: str | None = None) -> list[dict]:
    return [
        r for r in ROWS if r["language"] == language and (stratum is None or r["tags"]["stratum"] == stratum)
    ]


def fraction_phrase(row: dict) -> tuple[str, int]:
    """The longest "<fraction words> <unit>" in the text, and fraction x unit."""
    language = row["language"]
    found = [
        (f"{words} {unit_word}", value * unit)
        for words, value in FRACTION_WORDS[language].items()
        for unit_word, unit in UNIT_WORDS[language].items()
        if f"{words} {unit_word}" in row["text"]
    ]
    phrase, amount = max(found, key=lambda pair: len(pair[0]))
    assert amount.denominator == 1
    return phrase, int(amount)


def amount_phrase(row: dict) -> str:
    if row["tags"]["form"] == "canonical":
        return spoken_amount(row["gold"]["amount_inr"], Language(row["language"]))
    return fraction_phrase(row)[0]


def test_same_seed_same_rows_and_other_seed_differs():
    assert generate() == ROWS
    assert generate(seed=1) != ROWS
    assert generate(seed=1) == generate(seed=1)


def test_committed_manifest_is_what_generate_writes():
    data = (DATA / "amounts-v1.jsonl").read_bytes()
    assert data == jsonl_bytes(ROWS)
    assert (
        DATA / "amounts-v1.sha256"
    ).read_text() == f"{hashlib.sha256(data).hexdigest()}  amounts-v1.jsonl\n"
    assert [json.loads(line) for line in data.decode("utf-8").splitlines()] == ROWS


def test_cli_refuses_to_overwrite_a_different_manifest(tmp_path):
    assert main(["--out", str(tmp_path)]) == 0
    manifest = tmp_path / "amounts-v1.jsonl"
    frozen = manifest.read_bytes()
    assert main(["--out", str(tmp_path)]) == 0  # same bytes: rerun is fine
    manifest.write_bytes(b"edited\n")
    assert main(["--out", str(tmp_path)]) == 1
    assert manifest.read_bytes() == b"edited\n"
    assert main(["--out", str(tmp_path), "--force"]) == 0
    assert manifest.read_bytes() == frozen


def test_row_format():
    assert len({r["id"] for r in ROWS}) == len(ROWS) == 240
    for row in ROWS:
        assert set(row) == {"id", "language", "text", "gold", "tags"}
        assert set(row["gold"]) == {"amount_inr"} and type(row["gold"]["amount_inr"]) is int
        assert set(row["tags"]) == {"stratum", "round", "form", "carrier", "fold"}
        assert all(type(value) is str for value in row["tags"].values())
        assert row["id"].startswith(f"amt-{row['language']}-")
        assert row["tags"]["round"] in ("yes", "no") and row["tags"]["carrier"].startswith(row["language"])


@pytest.mark.parametrize("language", LANGUAGES)
def test_counts_amounts_folds_and_carriers(language):
    rows = rows_of(language)
    assert len(rows) == 60
    amounts = [r["gold"]["amount_inr"] for r in rows]
    assert len(set(amounts)) == 60
    assert all(100 <= a <= 50 * 10**7 for a in amounts)
    for stratum in STRATA:
        folds = Counter(r["tags"]["fold"] for r in rows_of(language, stratum))
        assert folds == {"0": 8, "1": 7}
    assert all(r["gold"]["amount_inr"] < 10**5 for r in rows_of(language, "plain"))
    assert all(r["gold"]["amount_inr"] >= 10**5 for r in rows_of(language, "lakh_crore"))
    assert all(r["tags"]["round"] == "yes" for r in rows_of(language, "fraction"))
    carriers = Counter(r["tags"]["carrier"] for r in rows)
    assert len(carriers) >= 10 and max(carriers.values()) - min(carriers.values()) <= 1


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["id"])
def test_text_has_one_amount_in_words(row):
    text, language = row["text"], row["language"]
    assert not any(unicodedata.category(ch) == "Nd" for ch in text)
    phrase = amount_phrase(row)
    assert text.count(phrase) == 1
    carrier_words = text.replace(phrase, " ").replace("।", " ").replace(".", " ").split()
    assert not NUMBER_WORDS[language] & set(carrier_words)
    assert len(text) <= 100


@pytest.mark.parametrize(
    "row", [r for r in ROWS if r["tags"]["stratum"] == "fraction"], ids=lambda r: r["id"]
)
def test_fraction_gold_is_fraction_times_unit(row):
    assert row["tags"]["form"] != "canonical"
    assert fraction_phrase(row)[1] == row["gold"]["amount_inr"]


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_named_fraction_form_appears(language):
    phrases = [fraction_phrase(r)[0] for r in rows_of(language, "fraction")]
    forms = Counter(r["tags"]["form"] for r in rows_of(language, "fraction"))
    for form in REQUIRED_FORMS[language]:
        assert any(p.startswith(form) for p in phrases), form
    assert len(forms) >= 5 and min(forms.values()) >= 1


@pytest.mark.parametrize("language", LANGUAGES)
def test_irregular_counts_cover_the_decades(language):
    amounts = [r["gold"]["amount_inr"] for r in rows_of(language, "irregular_21_99")]
    counts = [a // 10**5 if a >= 10**5 else a // 10**3 for a in amounts]
    assert len(set(counts)) == 15
    assert all(21 <= c <= 99 and c % 10 for c in counts)
    assert {c // 10 for c in counts} == set(range(2, 10))
    assert sum(c % 10 == 9 and c < 90 for c in counts) >= 4  # उनतीस ... नवासी in Hindi


@pytest.mark.parametrize("language", LANGUAGES)
def test_median_text_length(language):
    assert statistics.median(len(r["text"]) for r in rows_of(language)) <= 60


def test_first_twenty_rows_are_a_fair_sample():
    head = ROWS[:20]
    assert Counter(r["language"] for r in head) == dict.fromkeys(LANGUAGES, 5)
    for language in LANGUAGES:
        assert {r["tags"]["stratum"] for r in head if r["language"] == language} == set(STRATA)
