"""Tamil and Kannada number words fuse (sandhi). This module splits a fused word back into morphs.

இரண்டு + ஆயிரம் -> இரண்டாயிரம்: the final short u drops and the next word's vowel attaches
as a vowel sign. `segment` reverses that by rule against the morph tables, so every
coefficient-unit combination is covered without listing surface forms.
Not human-reviewed.
"""

from dataclasses import dataclass
from functools import lru_cache

from samajh.amounts._lexicon import JF, KN, TA, Atom, Morph


@dataclass(frozen=True)
class Script:
    name: str
    lex: dict[str, Morph]
    first: int  # code point of the block start
    signs: dict[str, str]  # vowel sign -> independent vowel
    a: str  # independent short a (has no sign)
    u: str  # short u sign, dropped in sandhi
    restore: tuple[str, ...]  # endings a left part may have lost before a vowel
    long_u: str = ""  # Kannada ಒಂದೂ-: lengthened u that joins a fraction
    m_final: str = ""  # Tamil -ம், replaced by case endings (ஆயிரம் -> ஆயிரத்தை)
    ablative: str = ""  # ending of "from X" (கணக்கிலிருந்து, ಖಾತೆಯಿಂದ): such a word is not a number

    def is_consonant(self, char: str) -> bool:
        return self.first + 0x15 <= ord(char) <= self.first + 0x39

    def owns(self, word: str) -> bool:
        return bool(word) and self.first <= ord(word[0]) < self.first + 0x80


TAMIL = Script(
    name="ta",
    lex=TA,
    first=0x0B80,
    signs=dict(zip("ாிீுூெேைொோௌ", "ஆஇஈஉஊஎஏஐஒஓஔ", strict=True)),
    a="அ",
    u="ு",
    restore=("ு", "ி"),
    m_final="ம்",
    ablative="ருந்து",  # -இலிருந்து, and இருந்து written apart
)
KANNADA = Script(
    name="kn",
    lex=KN,
    first=0x0C80,
    signs=dict(zip("ಾಿೀುೂೆೇೈೊೋೌ", "ಆಇಈಉಊಎಏಐಒಓಔ", strict=True)),
    a="ಅ",
    u="ು",
    restore=("ು", ""),
    long_u="ೂ",
    ablative="ಿಂದ",
)
SCRIPTS = (TAMIL, KANNADA)
# The longest number written as one word is under 30 characters; anything longer is not read.
MAX_WORD = 48
_BY_NAME = {s.name: s for s in SCRIPTS}


def fuse(script: Script, left: str, right: str) -> str:
    """Join two words the way a speaker does: sandhi before a vowel, plain otherwise."""
    if right[0] == script.a:
        return left[:-1] + right[1:]
    sign = next((s for s, vowel in script.signs.items() if vowel == right[0]), None)
    return left + right if sign is None else left[:-1] + sign + right[1:]


@lru_cache(maxsize=4096)
def _segment(name: str, word: str, top: bool) -> frozenset[tuple[tuple[Atom, ...], bool]]:
    """All readings of `word` as (atoms, may-attach-after-any-number)."""
    sc = _BY_NAME[name]

    def lookup(form: str) -> Morph | None:
        morph = sc.lex.get(form)
        return None if morph is None or (top and morph.suffix_only) else morph

    whole = lookup(word)
    if whole is not None:
        return frozenset({(whole.atoms, whole.head)})
    out = set()
    # Longest first morph wins: பத்தொன்பதாயிரம் is 19 thousand, not 10 and 9 thousand.
    for i in range(len(word) - 1, 0, -1):
        if out:
            break
        left, right = word[:i], word[i:]
        head = right[0]
        plain = lookup(left)
        if plain is not None:
            for atoms, attaches in _segment(name, right, False):
                if plain.oblique or attaches:
                    out.add((plain.atoms + atoms, plain.head))
        if head in sc.signs:
            for ending in sc.restore:
                morph = lookup(left + ending)
                if morph is not None and (ending or morph.oblique):
                    for atoms, _ in _segment(name, sc.signs[head] + right[1:], False):
                        out.add((morph.atoms + atoms, morph.head))
        elif sc.is_consonant(head) and sc.is_consonant(left[-1]):
            morph = lookup(left + sc.u)
            if morph is not None:
                for atoms, _ in _segment(name, sc.a + right, False):
                    out.add((morph.atoms + atoms, morph.head))
        if head == sc.long_u:
            morph = lookup(left + sc.u)
            if morph is not None:
                rest = right[1:]
                tails = _segment(name, rest, False) if rest else {((), True)}
                for atoms, _ in tails:
                    out.add((morph.atoms + (JF,) + atoms, morph.head))
    return frozenset(out)


def _tidy(atoms: tuple[Atom, ...]) -> tuple[Atom, ...]:
    """Inside one word: tens + unit is one number, and number + quarter/half is one number."""
    kept = [a for i, a in enumerate(atoms) if a.kind != "obl" or i == len(atoms) - 1]
    out: list[Atom] = []
    for atom in kept:
        prev = out[-1] if out else None
        if atom.kind == "n" and prev is not None:
            if prev.kind == "jf" and len(out) > 1 and _whole(out[-2]) and 0 < atom.value < 1:
                out[-2:] = [Atom("n", out[-2].value + atom.value)]
                continue
            if prev.kind == "n" and prev.joins and 1 <= atom.value < 10 and not atom.joins:
                out[-1] = Atom("n", prev.value + atom.value)
                continue
            if _whole(prev) and prev.value > 0 and 0 < atom.value < 1:
                out[-1] = Atom("n", prev.value + atom.value)
                continue
        out.append(atom)
    return tuple(out)


def _whole(atom: Atom) -> bool:
    return atom.kind == "n" and atom.value == atom.value.to_integral_value()


def segment(script: Script, word: str) -> set[tuple[Atom, ...]]:
    """Distinct readings of a whole word. Empty: not a number. More than one: unclear."""
    if len(word) > MAX_WORD:
        return set()
    return {_tidy(atoms) for atoms, _ in _segment(script.name, word, True)}


def number_stem(script: Script, word: str) -> tuple[bool, bool]:
    """(looks like a number with an unknown ending, that number has a unit).

    Case endings glue to numbers (இருபதாயிரத்தை). The parser cannot read those, and must not
    read the words before them as the whole amount.
    """
    found = unit = False
    if len(word) > MAX_WORD:
        return found, unit
    for i in range(4, len(word)):
        stem = word[:i]
        forms = [stem]
        if script.m_final:
            forms.append(stem + script.m_final)
        if i >= 5:
            forms.append(stem + script.u)
        for form in forms:
            for atoms, _ in _segment(script.name, form, True):
                found = True
                unit = unit or any(a.kind == "m" for a in atoms)
    return found, unit
