"""Is a spoken word the borrower's first name? One comparison for Devanagari and Latin spellings of a name.

A Latin spelling is folded (`_fold`): long vowels written double become short, `sh`/`s`, `v`/`w`, `ph`/`f`, `z`/`j`,
`chh`/`ch`, doubled letters and a nasal before `p`/`b` are folded. A Devanagari spelling is romanised into the
spellings a Hindi speaker may mean (`_readings`): the inherent vowel of a consonant that follows the first vowel may
be dropped ("रामप्रसाद" -> "ramprasad" or "ramaprasad"); a word-final consonant is read with no vowel, or, after a
cluster and with no inherent vowel dropped, with "a" ("कृष्ण" -> "krishn" or "krishna"; "कमल" never reads "kamla", and
"राम" never reads "rama", which is "रमा").
Consonants and written vowels are never loosened beyond that: retroflex and dental letters fold together, as Latin
spelling does, and aspirated letters stay apart from plain ones, so "Ramesh" never matches "सुरेश" or "राजेश".
"""

from __future__ import annotations

import csv
import unicodedata
from enum import StrEnum
from functools import cache
from itertools import product
from pathlib import Path

_VIRAMA, _NUKTA, _ANUSVARA, _CHANDRABINDU, _VISARGA = "्", "़", "ं", "ँ", "ः"

_CONSONANTS = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n",
    "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "n",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "ळ": "l", "व": "v", "श": "sh", "ष": "sh", "स": "s", "ह": "h",
}  # fmt: skip
_VOWELS = {
    "अ": "a", "आ": "aa", "इ": "i", "ई": "ii", "उ": "u", "ऊ": "uu", "ऋ": "ri",
    "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au", "ऍ": "e", "ऑ": "o",
}  # fmt: skip
_SIGNS = {
    "ा": "aa", "ि": "i", "ी": "ii", "ु": "u", "ू": "uu", "ृ": "ri",
    "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ॅ": "e", "ॉ": "o",
}  # fmt: skip
_MAX_DROPPABLE = 6  # 64 readings; no first name comes near it

# A Latin spelling's folds, in order (`ee` and `oo` before doubled letters collapse).
_LATIN_FOLDS = (("x", "ks"), ("q", "k"), ("ph", "f"), ("w", "v"), ("z", "j"), ("chh", "ch"), ("sh", "s"),
                ("ee", "i"), ("oo", "u"), ("ou", "au"))  # fmt: skip


def _plain(word: str) -> str:
    """NFC without nukta (as `tokens` does), chandrabindu as anusvara, "ज्ञ" as "ग्य" (spelt "gya"), casefolded."""
    word = unicodedata.normalize("NFC", word).casefold().replace(_NUKTA, "").replace(_CHANDRABINDU, _ANUSVARA)
    return word.replace("ज्ञ", "ग्य")


def _devanagari(word: str) -> bool:
    return any("ऀ" <= ch <= "ॿ" for ch in word)


def _fold(spelling: str) -> str:
    key = "".join(ch for ch in spelling.casefold() if "a" <= ch <= "z")
    for spelled, said in _LATIN_FOLDS:
        key = key.replace(spelled, said)
    key = "".join(ch for k, ch in enumerate(key) if k == 0 or ch != key[k - 1])
    key = key.replace("mp", "np").replace("mb", "nb")
    return key[:-1] if key.endswith("ah") else key


# One piece of a romanised Devanagari word: a fixed spelling, a droppable inherent vowel, or a final one (silent;
# after a cluster it may be heard).
_FIXED, _DROPPABLE, _FINAL, _FINAL_AFTER_CLUSTER = "fixed", "droppable", "final", "final after a cluster"
_FINALS = (_FINAL, _FINAL_AFTER_CLUSTER)


def _pieces(word: str) -> list[tuple[str, str]]:
    pieces: list[tuple[str, str]] = []
    voiced = False  # has a vowel been heard yet? The first syllable's inherent vowel is never dropped.
    for k, ch in enumerate(word):
        following = word[k + 1] if k + 1 < len(word) else ""
        if ch in _CONSONANTS:
            pieces.append((_CONSONANTS[ch], _FIXED))
            if following in _SIGNS or following == _VIRAMA:
                continue
            if not following:  # "a" may be heard after a final cluster only: "कृष्ण" as "Krishna", not "शिव" as "Shiva"
                pieces.append(("a", _FINAL_AFTER_CLUSTER if k and word[k - 1] == _VIRAMA else _FINAL))
            elif following in _CONSONANTS and voiced:
                pieces.append(("a", _DROPPABLE))
            else:
                pieces.append(("a", _FIXED))
            voiced = True
        elif ch in _SIGNS or ch in _VOWELS:
            pieces.append(((_SIGNS | _VOWELS)[ch], _FIXED))
            voiced = True
        elif ch == _ANUSVARA:
            pieces.append(("n", _FIXED))
        elif ch in (_VIRAMA, _VISARGA):
            continue
        else:
            pieces.append((ch, _FIXED))
    return pieces


@cache
def _readings(word: str) -> frozenset[str]:
    """The folded Latin spellings a Devanagari word may stand for."""
    pieces = _pieces(word)
    droppable = [k for k, (_, kind) in enumerate(pieces) if kind == _DROPPABLE][:_MAX_DROPPABLE]
    readings = set()
    for kept in product((True, False), repeat=len(droppable)):
        dropped = {k for k, keep in zip(droppable, kept, strict=True) if not keep}
        base = "".join(text for k, (text, kind) in enumerate(pieces) if k not in dropped and kind not in _FINALS)
        readings.add(_fold(base))
        if not dropped and pieces and pieces[-1][1] == _FINAL_AFTER_CLUSTER:
            readings.add(_fold(base + "a"))  # only with every inherent vowel kept: "कमल्ल" never reads "kamlla"
    return frozenset(readings)


def _canonical(word: str) -> str:
    """One Devanagari spelling's comparison form: every inherent vowel kept, no final one."""
    return _fold("".join(text for text, kind in _pieces(word) if kind not in _FINALS))


@cache
def is_first_name(word: str, first_name: str) -> bool:
    """Is `word` (one spoken word) the record's `first_name`, in either script, spelled either way?

    Names of fewer than three letters in the folded form never match (too short to tell apart)."""
    word, name = _plain(word), _plain(first_name)
    if not word or not name:
        return False
    word_dev, name_dev = _devanagari(word), _devanagari(name)
    if len(_canonical(name) if name_dev else _fold(name)) < 3:
        return False
    if word_dev and name_dev:
        return _canonical(word) == _canonical(name)
    if word_dev:
        return _fold(name) in _readings(word)
    if name_dev:
        return _fold(word) in _readings(name)
    return _fold(word) == _fold(name)


# --- Iteration 4: a script-neutral phonetic key, a distance on it, and a judgement with three values. ---------------
#
# `is_first_name` above stays the exact fast path. `judge_name` puts the burden of proof where the right-party check
# needs it: a spoken word is `same` as the record's first name when one of its phonetic keys is within `SAME_MAX` of one
# of the name's; it is `other` only when it is positively another first name (one of its keys is the key of a first
# token in `data/names/known-first-tokens.txt`, from Wikidata labels, and it is not within `SAME_MAX`); a word that is
# no known name is `near` (taken as the name misspelt) within `NEAR_MAX`, else `unknown`.
#
# Keys (`_keys`). A Devanagari word is romanised piece by piece (`_pieces`), each medial inherent vowel kept or dropped
# (every combination), the final inherent vowel silent; ऋ is read "ri" and "ru"; anusvara and chandrabindu are `N`
# (n or m); the vowel before a final consonant is always said; ऐ before r is "a" (मैरी, Mary). Then both scripts fold alike (`_phonetic`): letters
# only; in a Latin spelling, `dny` as `gy` (Marathi ज्ञ), `c` before e/i/y as `s` and other `ck`/`c` (not in `ch`)
# as `k`; `jy` as `j` (Tamil "Jothi" for ज्योति); `x` as `ks`, `q`
# as `k`, `f` as `p`, `w` as `v`, `z` as `j`; an initial `hr` as `r`; an `h` straight after a consonant dropped
# (aspiration, and `sh`/`s`, `ch`/`c`); `ee`, `oo`, `ou`, `ei` as `i`, `u`, `au`, `i`; doubled letters single (so vowel
# length goes); a final `y`, `ie`, `ey` after a consonant
# as `i` (Latin); a final `ao`/`eo` as `av`/`ev` ("Baburao"/"बाबूराव", Latin); a final silent `e` after a consonant
# dropped ("Kishore", Latin); a final `a` dropped; an `a`/`e` between a consonant cluster and a final `r` dropped ("Surinder",
# "सुरेन्द्र", "Chander");
# then `y` after a vowel and before none as `i` ("Jai"/"जय", "Udaya"/"उदय"), and `iy` as `i` ("Priya"/"Pria").
# A final vowel that is said is kept as the mark `A`: a Devanagari word ending in ा or आ, or a Latin name ending in "a",
# except that both readings are kept where `first-names.tsv` also spells the name with a silent final vowel ("Shiva" as
# शिव, "Krishna" as कृष्ण) or, for a name not in it, where the "a" follows a consonant cluster ("Mahendra"). So "Amit" and "अमिता", "Kamal" and "कमला",
# "Vijay" and "Vijaya" stay apart, and "Shiva"/"शिव" and "Krishna"/"कृष्ण" match.
#
# Distance (`_weighted`): an edit distance on keys. Everything costs 1 except: `e`/`i` before "nd" ("Surinder"/
# "Surender"), `a`/`e` ("Ahmed"/"अहमद", "Mehboob"/"महबूब"), `b`/`v` ("Binod"/"विनोद"), each 0.5; `N` for `n` or `m`, 0;
# an `a` inserted or deleted between two consonants after the first syllable (a medial inherent vowel), or an `N`, 0.5; an `a` and an `r`
# swapped after the same consonant ("Pardeep"/"प्रदीप"), 0.5. So one spelling-level change is within `SAME_MAX` and
# any change of a consonant, of a vowel's quality, of a said final vowel, or of a first vowel is not (except `o`/`u` as
# the first letter, 0.5: "Omar"/"उमर").


NAMES_DIR = Path(__file__).resolve().parents[2] / "data" / "names"

# Chosen on `data/names/dev-pairs.tsv` (hand-written development list, 2026-11-14) and frozen; the dev-list result is
# pinned in `tests/dialogue/test_first_name_scripts.py` (`DEV_ERRORS`). Do not tune on any held-out set.
SAME_MAX = 0.5
# An unknown word (no lexicon name) this near the record's name, and within a third of its key length, is taken as the
# name misspelt (`NameMatch.near`): no evidence of anyone else. A farther unknown word is not taken as the name: in the
# speaker's place ("मैं manager बोल रहा हूँ") the call still reads it as someone else. Chosen with SAME_MAX, frozen.
NEAR_MAX = 1.5

_A, _N = "A", "N"  # a final vowel that is said; a nasal sign (n or m)
_VOWEL_LETTERS = frozenset("aeiou")
_CHEAP = {frozenset("ae"): 0.5, frozenset("bv"): 0.5, frozenset("nN"): 0.0, frozenset("mN"): 0.0}
_FIRST_CHEAP = {frozenset("ou"): 0.5}  # only as the first letter: "Omar"/"उमर"


def _consonant(ch: str) -> bool:
    return ch not in _VOWEL_LETTERS and ch != _A


def _phonetic(spelling: str, *, latin: bool) -> str:
    """The key stem of one romanised spelling (lower-case letters, and `N` for a nasal sign), final vowel dropped.
    `latin`: a Latin spelling, which also gets the folds of English-style spelling (`c`, silent final `e`, `-ie`)."""
    key = "".join(ch for ch in spelling if "a" <= ch <= "z" or ch == _N)
    if latin:
        key = key.replace("dny", "gy").replace("ck", "k")  # "Dnyaneshwar": Marathi spelling of ज्ञ, read "gy"
        key = "".join("s" if ch == "c" and key[k + 1 : k + 2] in ("e", "i", "y") else ch for k, ch in enumerate(key))
        key = "".join("k" if ch == "c" and key[k + 1 : k + 2] != "h" else ch for k, ch in enumerate(key))
    for spelled, said in (("x", "ks"), ("q", "k"), ("f", "p"), ("w", "v"), ("z", "j")):
        key = key.replace(spelled, said)
    if key.startswith("hr"):  # "Hrishikesh", "Hrithik": ऋ written with an h
        key = key[1:]
    key = "".join(ch for k, ch in enumerate(key) if not (ch == "h" and k and key[k - 1] not in "aeiouh"))
    for spelled, said in (("ee", "i"), ("oo", "u"), ("ou", "au"), ("ei", "i"), ("jy", "j")):  # "Jothi"/"ज्योति"
        key = key.replace(spelled, said)
    if not latin:
        key = key.replace("air", "ar")  # "मैरी" for "Mary": ऐ before r writes an English a
    key = "".join(ch for k, ch in enumerate(key) if k == 0 or ch != key[k - 1])
    if len(key) > 2 and key.endswith("y") and _consonant(key[-2]):
        key = key[:-1] + "i"
    if latin and len(key) > 3 and key[-2:] in ("ie", "ey") and _consonant(key[-3]):
        key = key[:-2] + "i"
    if latin and len(key) > 2 and key[-2:] in ("ao", "eo"):
        key = key[:-1] + "v"
    if latin and len(key) > 3 and key.endswith("e") and _consonant(key[-2]):
        key = key[:-1]
    if key.endswith("ah"):
        key = key[:-1]
    if len(key) > 1 and key.endswith("a"):
        key = key[:-1]
    if len(key) > 4 and key[-1] == "r" and key[-2] in "ae" and _consonant(key[-3]) and _consonant(key[-4]):
        key = key[:-2] + "r"
    key = "".join(
        "i" if ch == "y" and k and key[k - 1] in _VOWEL_LETTERS and key[k + 1 : k + 2] not in _VOWEL_LETTERS else ch
        for k, ch in enumerate(key)
    )
    return key.replace("iy", "i").replace("ii", "i")



def _devanagari_readings(word: str) -> tuple[set[str], bool, bool]:
    """Romanised readings of a Devanagari word (medial inherent vowels kept or dropped), whether it ends in a said
    `ा`/`आ`, and whether a final inherent vowel may be heard (after a cluster)."""
    pieces = _pieces(word.replace(_ANUSVARA, _N))
    # The inherent vowel before a final consonant is always said ("अभय" is "abhay", never "abhy").
    before_final = len(pieces) - 3 if len(pieces) > 2 and pieces[-1][1] == _FINAL else None
    droppable = [k for k, (_, kind) in enumerate(pieces) if kind == _DROPPABLE and k != before_final]
    droppable = droppable[:_MAX_DROPPABLE]
    readings = set()
    for kept in product((True, False), repeat=len(droppable)):
        dropped = {k for k, keep in zip(droppable, kept, strict=True) if not keep}
        readings.add("".join(t for k, (t, kind) in enumerate(pieces) if k not in dropped and kind not in _FINALS))
    said = word.endswith(("ा", "आ"))
    heard = bool(pieces) and pieces[-1][1] == _FINAL_AFTER_CLUSTER
    return readings, said, heard


@cache
def _final_vowels() -> dict[str, frozenset[bool]]:
    """For each Latin first name (casefolded) ending in "a" in `first-names.tsv`: is the final vowel said (True) or silent
    (False) in its Devanagari spellings there?"""
    found: dict[str, set[bool]] = {}
    for row in _rows("first-names.tsv"):
        latin = row["latin"].casefold()
        if latin.endswith("a"):
            found.setdefault(latin, set()).add(row["devanagari"].endswith(("ा", "आ")))
    return {latin: frozenset(said) for latin, said in found.items()}


@cache
def _keys(word: str) -> frozenset[str]:
    """Every phonetic key a spoken or written word may stand for (see the section comment)."""
    word = _plain(word)
    if not word:
        return frozenset()
    if _devanagari(word):
        variants = {word}
        if "ृ" in word or "ऋ" in word:  # ऋ is said and spelt "ri" or "ru" ("Amruta"/"अमृता", "Mrunal"/"मृणाल")
            variants.add(word.replace("ृ", "्रु").replace("ऋ", "रु"))
        keys: set[str] = set()
        for variant in variants:
            readings, said, heard = _devanagari_readings(variant)
            for stem in {_phonetic(r, latin=False) for r in readings}:
                keys |= {stem + _A} if said else ({stem, stem + _A} if heard else {stem})
        return frozenset(k for k in keys if k)
    letters = "".join(ch for ch in word if "a" <= ch <= "z")
    stem = _phonetic(letters, latin=True)
    if not stem:
        return frozenset()
    if not letters.endswith("a") or len(letters) < 2:
        return frozenset({stem})
    attested = _final_vowels().get(letters)
    if attested is not None:
        silent_too = False in attested
    else:  # not in the lexicon: an "a" after a consonant cluster may be silent ("Mahendra"), else it is said
        silent_too = len(stem) > 1 and _consonant(stem[-1]) and _consonant(stem[-2])
    return frozenset({stem, stem + _A}) if silent_too else frozenset({stem + _A})


def _indel(key: str, k: int) -> float:
    ch = key[k]
    if ch == _N:
        return 0.5
    medial = 1 < k < len(key) - 1 and _consonant(key[k - 1]) and _consonant(key[k + 1])  # never the first syllable
    return 0.5 if ch == "a" and medial else 1.0


def _substitution(a: str, i: int, b: str, j: int) -> float:
    ca, cb = a[i], b[j]
    if ca == cb:
        return 0.0
    pair = frozenset((ca, cb))
    if pair == frozenset("ei") and a[i + 1 : i + 3] in ("nd", "Nd") and b[j + 1 : j + 3] in ("nd", "Nd"):
        return 0.5
    if i == 0 and j == 0 and pair in _FIRST_CHEAP:
        return _FIRST_CHEAP[pair]
    return _CHEAP.get(pair, 1.0)


def _weighted(a: str, b: str) -> float:
    d = [[0.0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        d[i][0] = d[i - 1][0] + _indel(a, i - 1)
    for j in range(1, len(b) + 1):
        d[0][j] = d[0][j - 1] + _indel(b, j - 1)
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            best = min(
                d[i - 1][j] + _indel(a, i - 1),
                d[i][j - 1] + _indel(b, j - 1),
                d[i - 1][j - 1] + _substitution(a, i - 1, b, j - 1),
            )
            swapped = i > 2 and j > 2 and a[i - 2 : i] == b[j - 2 : j][::-1] and set(a[i - 2 : i]) == {"a", "r"}
            if swapped and a[i - 3] == b[j - 3] and _consonant(a[i - 3]):  # "par" for "pra" after one consonant
                best = min(best, d[i - 2][j - 2] + 0.5)
            d[i][j] = best
    return d[-1][-1]


@cache
def name_distance(word: str, first_name: str) -> float:
    """The smallest weighted edit distance between any key of `word` and any key of `first_name`."""
    keys_a, keys_b = _keys(word), _keys(first_name)
    if not keys_a or not keys_b:
        return float("inf")
    return min(_weighted(a, b) for a in keys_a for b in keys_b)


def phonetic_key(word: str) -> str:
    """One representative key of a word (the shortest of its keys; ties by spelling)."""
    keys = _keys(word)
    return min(keys, key=lambda k: (len(k), k)) if keys else ""


def _rows(name: str) -> list[dict[str, str]]:
    with (NAMES_DIR / name).open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _lines(name: str) -> list[str]:
    text = (NAMES_DIR / name).read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#")]


@cache
def _stoplist() -> frozenset[str]:
    return frozenset(_plain(line) for line in _lines("stoplist.txt"))


@cache
def _lexicon() -> dict[str, tuple[str, ...]]:
    """Each key of a first token in `known-first-tokens.txt`, with the spellings (both scripts) behind it."""
    spellings: dict[str, set[str]] = {}
    for spelling in _lines("known-first-tokens.txt"):
        for key in _keys(spelling):
            spellings.setdefault(key, set()).add(spelling)
    return {key: tuple(sorted(found)) for key, found in spellings.items()}


@cache
def _attested_keys() -> frozenset[str]:
    """Keys of the paired, twice-attested names in `first-names.tsv` (the strict lexicon)."""
    return frozenset(k for row in _rows("first-names.tsv") for s in (row["latin"], row["devanagari"]) for k in _keys(s))


@cache
def known_first_name(word: str, *, strict: bool = False) -> bool:
    """Is `word` some person's first name (by phonetic key), and not an honorific or name suffix (`stoplist.txt`)?

    The broad lexicon is every first token of `known-first-tokens.txt`; `strict` uses only the paired, twice-attested
    names of `first-names.tsv`, for a frame where a common word may stand ("मैं फ्री हूँ")."""
    word = _plain(word)
    if not word or word in _stoplist() or len(phonetic_key(word)) < 2:
        return False
    keys = _attested_keys() if strict else _lexicon()
    return any(key in keys for key in _keys(word))


class NameMatch(StrEnum):
    same = "same"  # the record's first name, spelled either way, in either script
    near = "near"  # no lexicon name, and near the record's name: taken as the name misspelt
    unknown = "unknown"  # no lexicon name, and not near the record's name
    other = "other"  # positively another first name: a lexicon name not within SAME_MAX

    @property
    def is_the_name(self) -> bool:
        """May the word stand for the borrower's own name in a self-claim?"""
        return self in (NameMatch.same, NameMatch.near)


@cache
def _aliases() -> dict[str, tuple[str, ...]]:
    """`aliases.tsv`: per-name groups of spellings that are one name but that no general fold joins (a name's own
    convention: "Balasubramanian"/"बालसुब्रमण्यम", "Ayesha"/"Aisha"). Keyed by each spelling, casefolded."""
    groups: dict[str, tuple[str, ...]] = {}
    for line in _lines("aliases.tsv"):
        spellings = tuple(part.strip() for part in line.split("\t") if part.strip())
        for spelling in spellings:
            groups[_plain(spelling)] = spellings
    return groups


def _record_spellings(first_name: str) -> tuple[str, ...]:
    return _aliases().get(_plain(first_name), (first_name,))


# W4 fix round: a long name said without, or with, its final vowel ("सत्यनारायण" for "Satyanarayana") is the same name.
# Only from this many key letters: short pairs that differ by the final vowel are different names (Amit/Amita,
# Vijay/Vijaya, Kamal/Kamla).
_FINAL_VOWEL_MIN = 8


def _final_vowel_only(word: str, first_name: str) -> bool:
    names = {key for spelling in _record_spellings(first_name) for key in _keys(spelling)}
    for a in _keys(word):
        for b in names:
            short, long_ = sorted((a, b), key=len)
            if long_ == short + _A and len(short) >= _FINAL_VOWEL_MIN:
                return True
    return False


@cache
def judge_name(word: str, first_name: str) -> NameMatch:
    """Is a spoken word the record's first name, another first name, or neither known? (See the section comment.)

    A record name with a one-letter key is `same` only on an exact key match."""
    if is_first_name(word, first_name):
        return NameMatch.same
    distance = min(name_distance(word, spelling) for spelling in _record_spellings(first_name))
    short = min((len(k) for k in _keys(first_name)), default=0) < 2
    if distance == 0 or (not short and distance <= SAME_MAX) or _final_vowel_only(word, first_name):
        return NameMatch.same
    if known_first_name(word):
        return NameMatch.other
    stem = min((len(k) for k in _keys(first_name)), default=0)
    return NameMatch.near if distance <= min(NEAR_MAX, stem / 3) else NameMatch.unknown


def keyterms_for(first_name: str, limit: int = 10) -> tuple[str, ...]:
    """Spellings of the record's first name to offer Prisma STT as `keyterms` on the identity turns: the record's own
    spelling first, then lexicon spellings (both scripts) judged `same`. Not wired into the server here."""
    found = [first_name]
    lexicon = _lexicon()
    for key in sorted(_keys(first_name)):
        found.extend(s for s in lexicon.get(key, ()) if s not in found and judge_name(s, first_name) is NameMatch.same)
    return tuple(found[:limit])
