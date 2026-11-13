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

import unicodedata
from functools import cache
from itertools import product

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
