"""P3a verifier probe: generated misspellings of सवा / साढ़े / पौने before a number. Pure.

    uv run python references/reviews/iter2/probes/p3a_fraction_sweep.py

A misspelt fraction word must never be dropped: the parse must refuse, or read the right
fraction. Counts: right (fraction applied), refused, WRONG (read as the bare number).
"""

from collections import Counter
from itertools import product

from samajh.amounts import Approximate, Parsed, parse_amount, parse_approx_amount

LATIN = {
    0.25: ["".join(p) for p in product(["s", "sh"], ["a", "aa", "u", "o", ""], ["v", "w", "vv", "ww"], ["a", "aa", "ah", "e", "aa"])],
    0.5: ["".join(p) for p in product(["s", "sh"], ["a", "aa", "e"], ["dh", "d", "rh", "r", "dd", "ddh", "dh"], ["e", "ey", "ay", "i", "ai", "a"])],
    -0.25: ["".join(p) for p in product(["p"], ["au", "aw", "o", "ou", "ow", "a", "u"], ["n", "nn"], ["e", "ey", "ay", "i", "a", "ai", ""])],
}
DEVA = {
    0.25: ["सवा", "स्वा", "सव्वा", "सवाह", "सवां", "सबा", "शवा", "सौवा", "स्वाँ", "सावा", "सोवा"],
    0.5: ["साढ़े", "साढे", "साडे", "साड़े", "सारे", "सारहे", "साढ़ें", "सढ़े", "सड़े", "साधे", "साठे", "शाढ़े", "सार्हे", "साड़ें"],
    -0.25: ["पौने", "पोने", "पौन", "पौना", "पौनें", "पउने", "पाउने", "पवने", "पोणे", "पैने", "पूने"],
}
BASES = [("2 lakh", 200000), ("दो लाख", 200000), ("3,00,000", 300000)]


def value(r):
    if isinstance(r, Parsed):
        return r.rupees
    if isinstance(r, Approximate) and r.low == r.high:
        return r.low
    return None


def main() -> int:
    tally = Counter()
    wrong = []
    for script, table in (("latin", LATIN), ("deva", DEVA)):
        for frac, words in table.items():
            for word in dict.fromkeys(words):
                for base, n in BASES:
                    if frac < 0:
                        right = n - 25000  # paune 2 lakh = 1,75,000
                    else:
                        right = n + int(100000 * frac)
                    for fn in (parse_amount, parse_approx_amount):
                        v = value(fn(f"{word} {base}"))
                        if v is None:
                            o = "refused"
                        elif v == right:
                            o = "right"
                        else:
                            o = "WRONG"
                            if v == n:
                                wrong.append((fn.__name__, script, f"{word} {base}", v))
                        tally[(fn.__name__, script, o)] += 1
    for k in sorted(tally):
        print(k, tally[k])
    print("\nread as the bare number (fraction dropped):")
    seen = set()
    for fn, script, text, v in wrong:
        if fn == "parse_approx_amount" and text not in seen:
            seen.add(text)
            print(f"  {script}: {text!r} -> {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
