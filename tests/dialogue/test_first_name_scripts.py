"""Is a spoken word the borrower's first name, another person's, or neither? (`samajh.dialogue._names.judge_name`)

Iteration 4 replaced 1,109 builder-written phrase cases (which missed "Kavitha"/"कविता") with:
- a property test over the first names in `data/names/first-names.tsv`, each written in Latin and in Devanagari by
  Wikidata editors (not by our transliterator): every pair must match itself, except the listed misses
  (`known-misses.tsv`, each with its class), so a new miss or a fixed one shows here;
- the development list `dev-pairs.tsv` that `SAME_MAX` was chosen on, with its error counts pinned;
- a few behaviour cases. Call-level behaviour is in `test_right_party_names.py`.
"""

from __future__ import annotations

import csv
from pathlib import Path

from samajh.dialogue._names import (
    NEAR_MAX,
    SAME_MAX,
    NameMatch,
    judge_name,
    keyterms_for,
    known_first_name,
)

NAMES = Path(__file__).resolve().parents[2] / "data" / "names"

# Error counts on `dev-pairs.tsv` at SAME_MAX and NEAR_MAX (2026-11-14): variants not taken as the name, different
# names taken as the name (`same` or `near`: the loan would be named to them), different names judged `unknown` (not in
# the lexicon and far from the name).
DEV_ERRORS = {"variant_not_the_name": 0, "different_taken_as_the_name": 0, "different_unknown": 2}


def _tsv(name: str) -> list[dict[str, str]]:
    with (NAMES / name).open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def test_every_wikidata_name_matches_itself_across_scripts():
    pairs = {(row["latin"], row["devanagari"]) for row in _tsv("first-names.tsv")}
    known = {(row["latin"], row["devanagari"]) for row in _tsv("known-misses.tsv")}
    assert len(pairs) - len(known & pairs) >= 1500
    missed = {
        (latin, devanagari)
        for latin, devanagari in pairs
        if judge_name(devanagari, latin) is not NameMatch.same or judge_name(latin, devanagari) is not NameMatch.same
    }
    assert sorted(missed - known) == [], "new misses: add a fold, or list them in known-misses.tsv with a class"
    assert sorted((known & pairs) - missed) == [], "fixed misses: remove them from known-misses.tsv"


def test_dev_list_error_counts_at_the_frozen_thresholds():
    assert (SAME_MAX, NEAR_MAX) == (0.5, 1.5)
    rows = _tsv("dev-pairs.tsv")
    judged = [(row["label"], judge_name(row["spoken"], row["record"])) for row in rows]
    errors = {
        "variant_not_the_name": sum(label == "same" and not got.is_the_name for label, got in judged),
        "different_taken_as_the_name": sum(label == "different" and got.is_the_name for label, got in judged),
        "different_unknown": sum(label == "different" and got is NameMatch.unknown for label, got in judged),
    }
    assert errors == DEV_ERRORS


def test_the_names_the_review_found_failing_are_the_same_name():
    for latin, devanagari in [("Kavitha", "कविता"), ("Shiva", "शिव"), ("Surinder", "सुरेन्द्र"),
                              ("Mahender", "महेंद्र"), ("Pinky", "पिंकी")]:  # fmt: skip
        assert judge_name(devanagari, latin) is NameMatch.same, (latin, devanagari)


def test_near_miss_names_are_another_person():
    for record, spoken in [("Ramesh", "राजेश"), ("Ramesh", "Rajesh"), ("Sunita", "Sunil"), ("Meena", "Meenal"),
                           ("Ramesh", "Rakesh"), ("Mahesh", "Mukesh"), ("Suresh", "Naresh"), ("Anil", "Sunil"),
                           ("Kamal", "Komal"), ("Amit", "अमिता"), ("Kamal", "कमला"), ("Vijay", "Vijaya")]:  # fmt: skip
        assert judge_name(spoken, record) is NameMatch.other, (record, spoken)


def test_spelling_variants_of_one_name_are_the_same():
    for record, spoken in [("Meena", "Mina"), ("Pooja", "Puja"), ("Laxmi", "लक्ष्मी"), ("Krishna", "कृष्ण"),
                           ("Pardeep", "प्रदीप"), ("Binod", "विनोद"), ("Ahmed", "अहमद")]:  # fmt: skip
        assert judge_name(spoken, record) is NameMatch.same, (record, spoken)


def test_a_word_that_is_no_known_name_is_near_or_unknown_not_another_person():
    assert judge_name("Zorblat", "Ramesh") is NameMatch.unknown
    assert judge_name("क्ष्यज्ञ", "Ramesh") is NameMatch.unknown
    assert judge_name("Kavithaa", "Kavitha") is NameMatch.same
    assert judge_name("Kavihta", "Kavitha") is NameMatch.near  # a misspelling no lexicon holds


def test_honorifics_and_suffixes_are_not_first_names():
    for word in ("देवी", "Devi", "कुमार", "सिंह", "जी", "भाई", "श्री", "साहब"):
        assert not known_first_name(word), word


def test_keyterms_start_with_the_record_spelling_and_hold_the_devanagari_one():
    terms = keyterms_for("Kavitha")
    assert terms[0] == "Kavitha" and "कविता" in terms and len(terms) <= 10
    assert all(judge_name(term, "Kavitha") is NameMatch.same for term in terms)
