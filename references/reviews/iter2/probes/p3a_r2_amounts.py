"""P3a re-verification (round 2): fresh amounts inputs for the fraction and "one" fixes. Pure, offline.

    uv run python references/reviews/iter2/probes/p3a_r2_amounts.py

Gold written by the verifier before the first run. Each case lists the readings accepted:
an int (exact figure), a (low, high) tuple (an approximate reading), or None (a refusal).
A result outside the accepted set is printed WRONG when it is a figure (a confident wrong amount)
and MISSED when it is a refusal of an amount that should have been read. Both parsers are run;
parse_approx_amount is what the rules use.
"""

import sys
from collections import Counter

from samajh.amounts import Approximate, Parsed, parse_amount, parse_approx_amount

N = None
CASES: list[tuple[str, str, set]] = [
    # --- "one" after a hundreds word is part of the number ------------------------------
    ("one", "तीन सौ एक दिए", {301}),
    ("one", "तीन सौ एक रुपये", {301}),
    ("one", "नौ सौ एक लगे थे", {901}),
    ("one", "पाँच सौ एक भरे", {501}),
    ("one", "ग्यारह सौ एक दिए", {1101}),
    ("one", "एक सौ एक रुपये कटे", {101}),
    ("one", "इकतालीस हज़ार तीन सौ एक दिए", {41301}),
    ("one", "इकतालीस हज़ार एक सौ एक", {41101}),
    ("one", "तीन सौ एक का प्रीमियम था", {301}),
    ("one", "तीन सौ एक हज़ार", {301000}),
    # --- "one" after a thousand-or-larger unit, before a verb: never the smaller figure -
    ("one", "पचास हज़ार एक दिए", {N, 50001}),
    ("one", "पचास हज़ार एक लगे", {N, 50001}),
    ("one", "पचास हज़ार एक था", {N, 50001}),
    ("one", "पचास हज़ार एक कटे थे", {N, 50001}),
    ("one", "पचास हजार एक दिये", {N, 50001}),
    ("one", "50 हज़ार एक दिए", {N, 50001}),
    ("one", "पचास हज़ार एक दिए गए", {N, 50001}),
    ("one", "पचास हज़ार एक जमा किए", {N, 50001}),
    ("one", "पचास हज़ार एक चुकाए", {N, 50001}),
    ("one", "पचास हज़ार एक कटवाए", {N, 50001}),
    ("one", "पचास हज़ार एक पे किए", {N, 50001}),
    ("one", "पचास हज़ार एक भर दिए", {N, 50001}),
    ("one", "पचास हज़ार एक गए", {N, 50001}),
    ("one", "पचास हज़ार एक रुपया दिया", {50001}),
    ("one", "fifty thousand one was deducted", {N, 50001}),
    ("one", "50 thousand one gave", {N, 50001}),
    ("one", "50 thousand one paid", {N, 50001}),
    ("one", "एक लाख एक दिया", {N, 100001}),
    ("one", "एक लाख एक", {N, 100001}),
    ("one", "दो लाख एक लगा", {N, 200001}),
    ("one", "पचास हज़ार एक", {N, 50001}),
    # added after the first run (same rule, more verbs; gold unchanged in kind)
    ("one", "पचास हज़ार एक लिए", {N, 50001}),
    ("one", "पचास हज़ार एक आए", {N, 50001}),
    ("one", "पचास हज़ार एक निकले", {N, 50001}),
    ("one", "पचास हज़ार एक लगाए", {N, 50001}),
    ("one", "पचास हज़ार एक ले लिए", {N, 50001}),
    ("one", "50 thousand one were cut", {N, 50001}),
    ("one", "पचास हज़ार एक डाले", {N, 50001}),
    ("one", "पचास हज़ार एक हुए", {N, 50001}),
    ("one", "पचास हज़ार एक दिया था", {N, 50001}),
    # --- "one" as a determiner after a thousand unit: the round figure ----------------
    ("one", "पचास हज़ार एक पॉलिसी के", {50000}),
    ("one", "पचास हज़ार एक बार", {50000}),
    ("one", "पचास हज़ार एक ही बार कटा", {50000, N}),
    ("one", "दो लाख एक हज़ार", {201000}),
    ("one", "पचास हज़ार एक सौ", {50100}),
    # --- fractions, misspelt or misheard: read right or refused, never the bare number -
    ("frac", "साडे तीन लाख", {350000, N}),
    ("frac", "सडे तीन लाख", {350000, N}),
    ("frac", "साढे तीन लाख", {350000, N}),
    ("frac", "सवाह लाख", {125000, N}),
    ("frac", "पौणे दो लाख", {175000, N}),
    ("frac", "पोना दो लाख", {175000, N}),
    ("frac", "डेड लाख", {150000, N}),
    ("frac", "डेड़ लाख", {150000, N}),
    ("frac", "देड लाख", {150000, N}),
    ("frac", "डेढ लाख", {150000, N}),
    ("frac", "ढाइ लाख", {250000, N}),
    ("frac", "अढाई लाख", {250000, N}),
    ("frac", "ढ़ाई लाख", {250000, N}),
    ("frac", "आधे लाख", {50000, N}),
    ("frac", "डेढ़ सौ", {150}),
    ("frac", "ढाई हज़ार", {2500}),
    ("frac", "साढ़े चार सौ", {450}),
    ("frac", "सवा सौ", {125}),
    ("frac", "पौने तीन सौ", {275}),
    ("frac", "dedh lakh", {150000, N}),
    ("frac", "ded lakh", {150000, N}),
    ("frac", "dhai lakh", {250000, N}),
    ("frac", "dhaai lakh", {250000, N}),
    ("frac", "sadhe 3 lakh", {350000, N}),
    ("frac", "saade 3 lakh", {350000, N}),
    ("frac", "sare 3 lakh", {350000, N}),
    ("frac", "pone 2 lakh", {175000, N}),
    ("frac", "paune 2 lakh", {175000, N}),
    ("frac", "swa 2 lakh", {225000, N}),
    ("frac", "sava 2 lakh", {225000, N}),
    ("frac", "sawaa 2 lakh", {225000, N}),
    ("frac", "dhed lakh", {150000, N}),
    ("frac", "adha lakh", {50000, N}),
    ("frac", "तीन लाख पचास हजर", {350000, N}),
    ("frac", "तीन लक पचास हज़ार", {350000, N}),
    ("frac", "तीन लाख पचास हज़र", {350000, N}),
    ("frac", "तीन लख पचास हज़ार", {350000, N}),
    ("frac", "तीन लाक पचास हज़ार", {350000, N}),
    ("frac", "तीन लैख पचास हज़ार", {350000, N}),
    ("frac", "तीन ला पचास हज़ार", {350000, N}),
    ("frac", "दो लक रुपये", {200000, N}),
    ("frac", "तीन करोर", {30000000, N}),
    ("frac", "3 lak 50 thousand", {350000, N}),
    ("frac", "3 lac", {300000, N}),
    ("frac", "3 laakh", {300000, N}),
    ("frac", "3.5 lac", {350000, N}),
    ("frac", "करीब डेड लाख", {(150000, 150000), N}),
    ("frac", "सारा तीन लाख कटा", {300000, N}),
    ("frac", "पूरा डेढ़ लाख", {150000, N}),
    ("frac", "भाई साढ़े तीन लाख", {350000}),
    ("frac", "साढ़े तीन लाख", {350000}),
    # --- ranges, hedges, corrections, comparisons --------------------------------------
    ("range", "चालीस पचास हज़ार", {(40000, 50000)}),
    ("range", "चालीस से अस्सी हज़ार", {(40000, 80000), N}),
    ("range", "चालीस से इक्यासी हज़ार", {N}),
    ("range", "तीस-चालीस हज़ार के बीच", {(30000, 40000)}),
    ("range", "डेढ़ से दो लाख", {(150000, 200000)}),
    ("range", "एक से तीन लाख", {N}),
    ("range", "1.5 se 2 lakh", {(150000, 200000), N}),
    ("range", "50-60k", {(50000, 60000), N}),
    ("range", "पचास हज़ार या एक लाख", {N, (50000, 100000)}),
    ("range", "पचास हज़ार से ज़्यादा", {N}),
    ("range", "पचास हज़ार से कम", {N}),
    ("range", "कम से कम पचास हज़ार", {N}),
    ("range", "पचास हज़ार से ऊपर", {N}),
    ("range", "पचास हज़ार नहीं, पचपन हज़ार", {N}),
    ("range", "पचास हज़ार, नहीं नहीं, पचपन हज़ार", {N}),
    ("range", "पचास हज़ार था, सॉरी, पचपन", {N}),
    ("range", "पचास हज़ार, अरे नहीं, पचपन हज़ार", {N}),
    ("range", "पचास हज़ार, मतलब पचपन हज़ार", {N}),
    ("range", "पचास हज़ार और दो हज़ार", {N}),
    ("range", "पचास हज़ार दो बार कटे", {N}),
    ("range", "दो किस्त पचास हज़ार की", {N, 50000}),
    ("range", "पचास पचास हज़ार दो बार", {N}),
    ("range", "मुझे लगता है पचास हज़ार, पक्का नहीं", {(50000, 50000), N}),
    ("range", "करीब पचास, शायद पचपन हज़ार", {N, (50000, 55000)}),
    ("range", "पचास हज़ार के लगभग", {(50000, 50000)}),
    ("range", "पचास हज़ार के ऊपर नीचे", {(50000, 50000), N}),
    ("range", "लगभग पैंतालीस पचास", {N, (45000, 50000), (45, 50)}),
    ("range", "पचास हज़ार तक", {N, 50000, (50000, 50000)}),
    ("range", "पैंतालीस से पचास हज़ार के बीच में कहीं", {(45000, 50000)}),
    ("range", "पचास हज़ार नहीं तो पचपन", {N}),
]


def read(result):
    if isinstance(result, Parsed):
        return result.rupees
    if isinstance(result, Approximate):
        return (result.low, result.high)
    return None


def main() -> int:
    totals: Counter = Counter()
    for group, text, want in CASES:
        got_approx = read(parse_approx_amount(text))
        got_exact = read(parse_amount(text))
        if got_approx in want:
            verdict = "ok"
        elif got_approx is None:
            verdict = "MISSED"
        else:
            verdict = "WRONG"
        totals[(group, verdict)] += 1
        if verdict != "ok":
            print(f"{verdict:6} [{group}] {text!r}: parse_approx {got_approx!r}, parse_amount {got_exact!r}, accept {want!r}")
        elif (
            got_exact is not None
            and got_exact not in want
            and not any(isinstance(w, tuple) and w[1] == got_exact for w in want)
        ):
            # parse_amount ignores a hedge word by design; only a different figure counts here
            print(f"WRONG-exact [{group}] {text!r}: parse_amount {got_exact!r}, accept {want!r}")
            totals[(group, "WRONG-exact")] += 1
    print()
    for group in ("one", "frac", "range"):
        row = {v: totals[(group, v)] for v in ("ok", "WRONG", "MISSED", "WRONG-exact") if totals[(group, v)]}
        print(f"{group:6} n={sum(totals[(group, v)] for v in ('ok', 'WRONG', 'MISSED'))} {row}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
