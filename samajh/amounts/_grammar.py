"""Value of one run of adjacent number atoms. Decimal arithmetic only."""

from decimal import Decimal
from typing import NamedTuple

from samajh.amounts._lexicon import CRORE, HUNDRED, LAKH, THOUSAND, Atom

_ITN_UNITS = (CRORE, LAKH, THOUSAND, HUNDRED)
_ROOM_UNITS = (CRORE, LAKH, THOUSAND)
_QUARTER = Decimal("0.25")


class Value(NamedTuple):
    """`value` is None when the run breaks the grammar.

    `unit_missing`: a fraction had no unit to apply to ("साढ़े तीन"). The value is still
    given, because a duration ("साढ़े तीन साल") supplies the unit afterwards.
    """

    value: Decimal | None
    unit_missing: bool = False


_BROKEN = Value(None)


def _whole(value: Decimal) -> bool:
    return value == value.to_integral_value()


def _merge(atoms: list[Atom]) -> list[Atom] | None:
    """Fold tens+unit, number+quarter and spoken decimals into single coefficients."""
    out: list[Atom] = []
    i = 0
    while i < len(atoms):
        atom = atoms[i]
        prev = out[-1] if out else None
        if atom.kind == "obl":
            if i == len(atoms) - 1:
                return None  # a joining form with nothing joined to it
        elif atom.kind == "jf":
            nxt = atoms[i + 1] if i + 1 < len(atoms) else None
            if (
                prev
                and nxt
                and prev.kind in "nd"
                and _whole(prev.value)
                and nxt.kind == "n"
                and 0 < nxt.value < 1
            ):
                out[-1] = Atom("n", prev.value + nxt.value)
                i += 1
        elif atom.kind == "pt":
            digits = ""
            while i + 1 < len(atoms) and atoms[i + 1].kind == "n" and atoms[i + 1].value in range(10):
                digits += str(int(atoms[i + 1].value))
                i += 1
            if not (prev and prev.kind in "nd" and _whole(prev.value) and digits):
                return None
            out[-1] = Atom("n", prev.value + Decimal("0." + digits))
        elif atom.kind == "and":
            # Only "one hundred and five" / "two thousand and five". "ten lakh and fifty
            # thousand" may be two amounts, so it is not joined.
            rest = _merge(atoms[i + 1 :])
            small = rest is not None and len(rest) == 1 and rest[0].kind == "n" and rest[0].value < 100
            if not (prev and prev.kind == "m" and prev.value <= THOUSAND and small):
                return None
        elif atom.kind == "n" and prev and prev.kind == "n" and prev.joins and 1 <= atom.value < 10:
            out[-1] = Atom("n", prev.value + atom.value)
        else:
            out.append(atom)
        i += 1
    return out


def _itn(first: Atom, digits: Decimal) -> Value:
    """Prisma converted only the base number and left the fraction word in front of it."""
    if not _whole(digits):
        return _BROKEN
    if first.kind == "pre":  # सवा 2,00,000 -> 2.25 lakh
        for unit in _ITN_UNITS:
            if digits % unit == 0 and 0 < digits / unit < 100:
                return Value((digits / unit + first.value) * unit)
        return Value(digits + first.value, unit_missing=True)
    if digits in _ITN_UNITS:  # ஒன்றரை 1,00,000 -> 1.5 lakh
        return Value(first.value * digits)
    return _BROKEN


def evaluate(run: list[Atom]) -> Value:
    """Groups of `coefficient [unit]` with strictly decreasing magnitude.

    Two shapes of Prisma's partial number formatting are part of the grammar:
      * higher groups in digits, lower groups left as words ("5,00,000 दो सौ" = 5,00,200). The
        digits must be a whole number of thousands, lakhs or crores, and the group after them
        must carry a unit word and fit below that unit. "5,00,000 दो" and "1,00,000 50,000"
        stay broken: nothing says the second number continues the first.
      * never a coefficient of 1,000 or more on a thousand or lakh word ("6,13,00,020
        थाउज़ंड"), nor of 100 or more on a hundred word: a garbled number, not a product.
    """
    atoms = _merge(run)
    if not atoms:
        return _BROKEN
    if len(atoms) == 2 and atoms[1].kind == "d":
        first = atoms[0]
        if first.kind == "pre" or (first.kind == "n" and not _whole(first.value)):
            return _itn(first, atoms[1].value)

    def is_unit(k: int, hundred: bool) -> bool:
        return k < len(atoms) and atoms[k].kind == "m" and (atoms[k].value == HUNDRED) == hundred

    total = Decimal(0)
    ceiling: Decimal | None = None  # unit of the previous group; this group must stay below it
    fraction = unit_missing = False
    after_digits = False  # the previous group was unit-less digits with room below them
    i = 0
    while i < len(atoms):
        if fraction or ceiling == 1:
            return _BROKEN  # nothing may follow a fractional group or a group without a unit
        pre = coef = None
        if atoms[i].kind == "pre":
            pre = atoms[i].value
            i += 1
        typed = False  # "52000.50": a decimal in digits is not a spoken fraction
        if i < len(atoms) and atoms[i].kind in "nd":
            coef, typed = atoms[i].value, atoms[i].kind == "d" and pre is None
            i += 1
        digits = typed
        hundred = is_unit(i, True)
        i += hundred
        if pre is not None and coef is None:
            if abs(pre) != _QUARTER:
                return _BROKEN  # "साढ़े लाख"
            coef = 1 + pre  # सवा लाख, पौन लाख
        elif pre is not None:
            if not _whole(coef):
                return _BROKEN
            coef += pre
        elif coef is None:
            if not (hundred or is_unit(i, False)):
                return _BROKEN
            coef = Decimal(1)  # "हज़ार रुपये", "ஆயிரத்து ஐநூறு"
        fraction = not _whole(coef)
        small = coef
        if hundred:
            small = coef * HUNDRED
            if not fraction and i < len(atoms) and atoms[i].kind in "nd":
                tail = atoms[i].value
                if _whole(tail) and tail < HUNDRED:
                    small += tail
                    i += 1
        unit = Decimal(1)
        if is_unit(i, False):
            unit = atoms[i].value
            i += 1
        value = small * unit
        if ceiling is not None and not (unit < ceiling and value < ceiling):
            return _BROKEN
        unitless = unit == 1 and not hundred
        garbled = (hundred and coef >= HUNDRED) or (unit in (THOUSAND, LAKH) and small >= THOUSAND)
        if garbled or (after_digits and unitless):
            return _BROKEN
        unit_missing = fraction and not typed and unitless
        total += value
        ceiling = unit
        after_digits = False
        if digits and unitless and not fraction and coef > 0:
            room = next((u for u in _ROOM_UNITS if coef % u == 0), None)
            if room is not None:
                ceiling, after_digits = Decimal(room), True
    return Value(total, unit_missing)
