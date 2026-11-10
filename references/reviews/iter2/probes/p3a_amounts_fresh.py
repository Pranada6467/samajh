"""P3a verifier probe: fresh Hindi/Hinglish inputs for parse_approx_amount and parse_amount. Pure.

    uv run python references/reviews/iter2/probes/p3a_amounts_fresh.py

Inputs and gold written by the verifier before running. Gold is (low, high) for what a careful
listener takes, or None when the text should be refused (a correction left open, a negation, a
comparison, an absurdly wide range, a misspelt fraction or unit). Exact single figures are (x, x).

Outcomes, counted separately:
  right     result equals gold (Parsed x -> (x, x); Approximate -> (low, high)); or refused when gold None
  refused   gold is a value and the parser refused (leads to a read-back or a gap)
  WRONG     a value that differs from gold (a confident wrong amount)
  ACCEPTED  gold None and the parser returned a value

Part 2 reruns the iter1 amounts_fresh.py ordinary shapes through parse_approx_amount and reports
any that parse_amount got right and parse_approx_amount gets different.
Part 3: is_loan_tenure and has_doubt_word on fresh inputs.
"""

import sys
from collections import Counter
from pathlib import Path

from samajh.amounts import Approximate, Parsed, has_doubt_word, is_loan_tenure, parse_amount, parse_approx_amount

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "iter1" / "probes"))
import amounts_fresh  # noqa: E402

X = lambda v: (v, v)  # noqa: E731

CASES = [
    # approximate single figures
    ("करीब पचास हज़ार", X(50000)),
    ("लगभग चालीस हज़ार रुपये कटे थे", X(40000)),
    ("पचास हज़ार के आसपास", X(50000)),
    ("मुझे लगता है बावन हज़ार था", X(52000)),
    ("शायद साढ़े तीन लाख", X(350000)),
    ("तकरीबन पौने दो लाख", X(175000)),
    ("kareeb 50 hazaar", X(50000)),
    ("around 52,000 rupees", X(52000)),
    ("lagbhag 40 thousand", X(40000)),
    ("I think 41,300", X(41300)),
    ("मेरे ख्याल से इकतालीस हज़ार तीन सौ", X(41300)),
    ("अंदाज़न पचास हज़ार", X(50000)),
    # ranges
    ("पचास बावन हज़ार", (50000, 52000)),
    ("पचास से बावन हज़ार", (50000, 52000)),
    ("50-52 hazaar", (50000, 52000)),
    ("50 से 52 हज़ार के बीच", (50000, 52000)),
    ("चालीस पैंतालीस हज़ार के आसपास", (40000, 45000)),
    ("एक डेढ़ लाख", (100000, 150000)),
    ("दो ढाई लाख", (200000, 250000)),
    ("बीस पच्चीस हज़ार", (20000, 25000)),
    ("40,000 से 45,000 तक", (40000, 45000)),
    ("40 se 45 hazaar", (40000, 45000)),
    ("40 ya 45 thousand", (40000, 45000)),
    ("तीन चार लाख", (300000, 400000)),
    # absurdly wide or odd ranges: refuse
    ("दस से पचास हज़ार", None),
    ("एक से पाँच लाख", None),
    ("10-50 hazaar", None),
    ("पाँच हज़ार से एक लाख", None),
    ("बावन पचास हज़ार", None),  # high before low
    # corrections, negations, comparisons
    ("पचास नहीं बावन हज़ार", None),
    ("पचास हज़ार से ज़्यादा था", None),
    ("पचास हज़ार से कम", None),
    ("करीब पचास हज़ार नहीं था", None),
    ("not 50, 52 thousand", None),
    ("पचास हज़ार और दो हज़ार फ़ाइल चार्ज", None),
    ("पचास हज़ार, सॉरी, बावन हज़ार", None),
    # misspelt fraction words (Devanagari)
    ("सारे तीन लाख", None),
    ("साड़े तीन लाख", None),
    ("सारहे तीन लाख", None),
    ("पोने दो लाख", None),
    ("पौन दो लाख", None),
    ("सव्वा लाख", None),
    ("सवाह लाख", None),
    ("करीब सारे तीन लाख", None),
    ("सारे तीन चार लाख", None),
    # misspelt fraction words (Latin)
    ("saare teen lakh", None),
    ("saare 3 lakh", None),
    ("paune 2 lakh", None),
    ("pone 2 lakh", None),
    ("sava 2 lakh", None),
    ("swa 2 lakh", None),
    ("sadhe 3 lakh", None),
    ("around sarhe 3 lakh", None),
    # misspelt unit
    ("दो लख पचास हज़ार", None),
    ("बावन हजर", None),
    ("52 thousnd", None),
    # earlier known shapes (should still be what parse_amount gives)
    ("बावन हज़ार", X(52000)),
    ("पौने दो लाख", X(175000)),
    ("साढ़े तीन लाख", X(350000)),
    ("डेढ़ लाख", X(150000)),
    ("52,000", X(52000)),
    ("1.5 lakh", X(150000)),
    ("तीन लाख तक", X(300000)),
    ("41,300 one time payment", X(41300)),
    ("एक लाख बीस हज़ार", X(120000)),
    # hedge words that may not mean doubt
    ("about the premium, 52,000", X(52000)),  # 'about' as a preposition; marking approx is harmless
    ("दो एफडी पचास हज़ार की", None),  # two FDs of 50k each: count before amount
    ("पचास हज़ार दो बार कटे", None),  # 50k deducted twice: total ambiguous
]


def outcome(text: str, gold) -> tuple[str, str]:
    r = parse_approx_amount(text)
    got = (r.rupees, r.rupees) if isinstance(r, Parsed) else (r.low, r.high) if isinstance(r, Approximate) else None
    desc = f"{type(r).__name__}{'' if got is None else got}"
    if got is None and gold is None:
        return "right", desc
    if got is None:
        return "refused", desc
    if gold is None:
        return "ACCEPTED", desc
    return ("right" if got == gold else "WRONG"), desc


def main() -> int:
    tally = Counter()
    for text, gold in CASES:
        o, desc = outcome(text, gold)
        tally[o] += 1
        if o != "right":
            print(f"  {o:8} {text!r}: gold {gold}, got {desc}")
    print("part 1:", dict(tally), f"n={len(CASES)}")

    changed = 0
    for name, cases in amounts_fresh.SETS.items():
        for text, gold, _left in cases:
            a = parse_amount(text)
            b = parse_approx_amount(text)
            av = a.rupees if isinstance(a, Parsed) else None
            bv = (b.rupees, b.rupees) if isinstance(b, Parsed) else (b.low, b.high) if isinstance(b, Approximate) else None
            if (av, av) != bv and not (av is None and bv is None):
                changed += 1
                print(f"  part 2 {name}: {text!r} gold {gold}: parse_amount {av}, parse_approx {bv}")
    print("part 2: inputs where parse_approx differs from parse_amount:", changed)

    tenure = [
        ("जब तक लोन चलेगा", True), ("लोन जितना ही", True), ("jab tak loan chalega", True),
        ("जब तक लोन चलेगा, दो साल", False), ("लोन से ज़्यादा चलेगा", False),
        ("लोन ख़त्म होने के बाद भी चलेगा", False), ("जब तक लोन नहीं चुकता", False),
        ("loan ke baad bhi", False), ("same as the loan", True), ("लोन के बराबर नहीं", False),
    ]
    for text, want in tenure:
        got = is_loan_tenure(text)
        print(f"  {'ok ' if got == want else 'BAD'} is_loan_tenure({text!r}) = {got}")
    doubt = [
        ("शायद", True), ("लगता नहीं", False), ("पक्का", False), ("क़रीब", True), ("I think so", True),
        ("मुझे नहीं लगता", False), ("ऐसा लगता है", True), ("thinking", False),
    ]
    for text, want in doubt:
        got = has_doubt_word(text)
        print(f"  {'ok ' if got == want else 'BAD'} has_doubt_word({text!r}) = {got}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
