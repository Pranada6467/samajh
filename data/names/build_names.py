"""Build `first-names.tsv`: first names in Latin and Devanagari, as Wikidata editors wrote them.

Source: Wikidata (CC0), queried on 2026-11-14 through the QLever endpoint https://qlever.dev/api/wikidata, CSV results.
Prefixes: wd = http://www.wikidata.org/entity/, wdt = http://www.wikidata.org/prop/direct/,
rdfs = http://www.w3.org/2000/01/rdf-schema#.

people.csv (columns item, en, hi; 18,966 rows), humans with Indian citizenship that have an English and a Hindi label:
    SELECT ?item ?en ?hi WHERE { ?item wdt:P31 wd:Q5 . ?item wdt:P27 wd:Q668 .
      ?item rdfs:label ?hi . FILTER(LANG(?hi)="hi") ?item rdfs:label ?en . FILTER(LANG(?en)="en") }

given.csv (columns item, cls, en, hi; 846 rows), given-name items (male, female, unisex) with both labels:
    SELECT ?item ?cls ?en ?hi WHERE { VALUES ?cls { wd:Q12308941 wd:Q11879590 wd:Q3409032 } ?item wdt:P31 ?cls .
      ?item rdfs:label ?hi . FILTER(LANG(?hi)="hi") ?item rdfs:label ?en . FILTER(LANG(?en)="en") }

Pairing and cleaning (README.md): no rule here uses the dialogue's name matcher.

    python3 data/names/build_names.py people.csv given.csv > data/names/first-names.tsv

It also writes `known-first-tokens.txt` next to itself: every first token of a person's English or Hindi label (one
script at a time, attested once or more, initials and dotted tokens left out) and every one-word given-name label, minus
the stoplist. That wider list only answers "is this word some person's first name?" for the right-party check; the
paired, cleaned `first-names.tsv` is what the property test reads.
"""

from __future__ import annotations

import csv
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
LATIN_WORD = re.compile(r"[A-Z][a-z]+")
DEVANAGARI_WORD = re.compile("[\u0900-\u0963\u0971-\u097f]+")  # no danda, digit or abbreviation sign (॰)
MIN_PEOPLE = 2


def stoplist() -> frozenset[str]:
    """Honorifics and name suffixes (README.md), Latin casefolded and Devanagari, one per line in stoplist.txt."""
    lines = (HERE / "stoplist.txt").read_text(encoding="utf-8").splitlines()
    return frozenset(line.strip().casefold() for line in lines if line.strip() and not line.startswith("#"))


def exclusions() -> frozenset[tuple[str, str]]:
    rows = csv.DictReader((HERE / "exclusions.tsv").open(encoding="utf-8"), delimiter="\t")
    return frozenset((row["latin"], row["devanagari"]) for row in rows)


def read_csv(path: str) -> list[dict[str, str]]:
    with open(path, encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def people_pairs(path: str) -> Counter[tuple[str, str]]:
    pairs: Counter[tuple[str, str]] = Counter()
    for row in read_csv(path):
        en, hi = nfc(row["en"]).split(), nfc(row["hi"]).split()
        if len(en) != len(hi) or len(en) < 2:
            continue
        if any("." in t or "॰" in t for t in en + hi):
            continue
        if LATIN_WORD.fullmatch(en[0]) and DEVANAGARI_WORD.fullmatch(hi[0]):
            pairs[(en[0], hi[0])] += 1
    return pairs


def given_pairs(path: str) -> set[tuple[str, str]]:
    pairs = set()
    for row in read_csv(path):
        en, hi = nfc(row["en"]).strip(), nfc(row["hi"]).strip()
        if LATIN_WORD.fullmatch(en) and DEVANAGARI_WORD.fullmatch(hi):
            pairs.add((en, hi))
    return pairs


def first_tokens(people_csv: str, given_csv: str) -> set[str]:
    tokens: set[str] = set()
    for row in read_csv(people_csv):
        for label, shape in ((row["en"], LATIN_WORD), (row["hi"], DEVANAGARI_WORD)):
            words = nfc(label).split()
            if words and shape.fullmatch(words[0]):
                tokens.add(words[0])
    for row in read_csv(given_csv):
        for label, shape in ((row["en"], LATIN_WORD), (row["hi"], DEVANAGARI_WORD)):
            if shape.fullmatch(nfc(label).strip()):
                tokens.add(nfc(label).strip())
    return tokens


def main(people_csv: str, given_csv: str) -> None:
    stop, excluded = stoplist(), exclusions()
    people = people_pairs(people_csv)
    given = given_pairs(given_csv)
    counts = {"people pairs (raw)": len(people)}
    kept: dict[tuple[str, str], tuple[int, str]] = {}
    for pair, n in people.items():
        if n >= MIN_PEOPLE:
            kept[pair] = (n, "people")
    counts[f"people pairs attested by >= {MIN_PEOPLE}"] = len(kept)
    indian = {latin for latin, _ in people} | {devanagari for _, devanagari in people}
    given = {pair for pair in given if pair[0] in indian or pair[1] in indian}
    counts["given-name items whose Latin or Hindi label is an Indian person's first token"] = len(given)
    for pair in given:
        n = people.get(pair, 0)
        kept[pair] = (n, "given_name" if pair not in kept else "people+given_name")
    counts["after adding given-name items"] = len(kept)
    kept = {p: v for p, v in kept.items() if p[0].casefold() not in stop and p[1] not in stop}
    counts["after the stoplist"] = len(kept)
    kept = {p: v for p, v in kept.items() if p not in excluded}
    counts["after exclusions.tsv"] = len(kept)
    out = csv.writer(sys.stdout, delimiter="\t", lineterminator="\n")
    out.writerow(("latin", "devanagari", "people", "source"))
    for (latin, devanagari), (n, source) in sorted(kept.items()):
        out.writerow((latin, devanagari, n, source))
    known = {t for t in first_tokens(people_csv, given_csv) if t.casefold() not in stop and t not in stop}
    known |= {spelling for pair in kept for spelling in pair}
    counts["known first tokens (both scripts)"] = len(known)
    header = "# Generated by build_names.py from Wikidata (CC0) labels, 2026-11-14. One first token per line.\n"
    (HERE / "known-first-tokens.txt").write_text(header + "\n".join(sorted(known)) + "\n", encoding="utf-8")
    for label, n in counts.items():
        print(f"{label}: {n}", file=sys.stderr)


if __name__ == "__main__":
    main(*sys.argv[1:3])
