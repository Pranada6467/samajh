"""P3a re-verification (round 3): fresh spoken-amount sentences, gold written before the first run.

    uv run python references/reviews/iter2/probes/p3a_r3_amounts.py

Offline, pure. Gold:
  int        the sentence states this amount plainly: `parse_approx_amount` must give Parsed(int)
             (and `parse_amount` the same). A refusal is MISSED; any other figure is WRONG.
  "R"        must not come back as a confident plain figure (Parsed): a Parsed is WRONG.
             Approximate or a refusal is fine (reported).
  (lo, hi)   a range or bound: Approximate with those ends, or a refusal. A Parsed is WRONG.
"""

from samajh.amounts import Approximate, Parsed, parse_amount, parse_approx_amount

R = "R"
CASES = [
    # --- plain amounts that MUST parse (over-refusal check) ---
    ("पचास हज़ार रुपये दिए थे।", 50000),
    ("इकतालीस हज़ार तीन सौ रुपये कटे।", 41300),
    ("साढ़े बारह हज़ार का था।", 12500),
    ("दो लाख पच्चीस हज़ार।", 225000),
    ("पौने दो लाख का कवर है।", 175000),
    ("सवा लाख रुपये।", 125000),
    ("अठारह हज़ार नौ सौ निन्यानवे।", 18999),
    ("Maine 50,000 rupees diye the.", 50000),
    ("मैंने 41,300 रुपये दिए थे।", 41300),
    ("premium 1,25,000 tha.", 125000),
    ("कवर 3,50,000 का है जी।", 350000),
    ("Total 75,500 rupaye kate the.", 75500),
    ("forty one thousand three hundred rupees.", 41300),
    ("fifty thousand rupees diye.", 50000),
    ("तीन लाख पचास हज़ार का कवर।", 350000),
    ("एक लाख रुपये।", 100000),
    ("बीस हज़ार पांच सौ रुपये लगे।", 20500),
    ("उन्होंने 60000 रुपये काटे।", 60000),
    ("डेढ़ लाख का बीमा।", 150000),
    ("नौ हज़ार नौ सौ।", 9900),
    ("Approx nahi, exact 32,000 tha.", 32000),
    ("सात हज़ार रुपये महीने के नहीं, एक बार में।", 7000),
    # --- "one" after a complete round amount, before a non-number word ---
    ("पचास हज़ार एक बीमे के लिए कटे।", R),
    ("पचास हज़ार एक पॉलिसी के लिए।", R),
    ("चालीस हज़ार एक बार में कटा।", R),
    ("पचास हज़ार एक साथ दिए।", R),
    ("fifty thousand one time payment.", R),
    ("50 thousand one policy ke liye.", R),
    ("पचास हज़ार एक ही बार।", R),
    ("तीस हज़ार एक मुश्त दिए।", R),
    ("पचास हज़ार एक सौ।", 50100),
    ("पचास हज़ार एक।", R),
    # --- count words beside an amount ---
    ("पचास हज़ार तीन बार कटे।", R),
    ("तीन किस्तों में पचास हज़ार।", R),
    ("दो पॉलिसी बीस हज़ार की।", R),
    ("पचास हज़ार हर महीने, बारह महीने।", R),
    ("चार बीमे पच्चीस हज़ार वाले।", R),
    ("do baar 20 hazaar kate.", R),
    ("बीस हज़ार की दो किस्तें।", R),
    ("पच्चीस हज़ार दो दफ़ा कटे।", R),
    # --- misheard or unknown unit after a number ---
    ("तीन लख पचास हज़ार।", R),
    ("दो लाक बीस हज़ार।", R),
    ("तीन लैख रुपये।", R),
    ("पचास हजर रुपये।", R),
    ("चालीस हज़ा तीन सौ।", R),
    ("एक करोर रुपये।", R),
    ("teen lac pachas hazaar.", R),
    # --- bounds: at least / at most / up to / more than / less than ---
    ("कम से कम पचास हज़ार।", R),
    ("ज़्यादा से ज़्यादा पचास हज़ार।", R),
    ("पचास हज़ार तक।", R),
    ("पचास हज़ार से ज़्यादा।", R),
    ("पचास हज़ार से कम।", R),
    ("at least 50,000.", R),
    ("at most fifty thousand.", R),
    ("up to 40,000 rupees.", R),
    ("minimum pachas hazaar.", R),
    ("pachas hazaar se zyada tha.", R),
    ("50 hazaar se kam hi tha.", R),
    ("maximum 41,300.", R),
    ("कम से कम 41,300 रुपये।", R),
    ("लगभग पचास हज़ार।", (45000, 55000)),
    # --- ranges ---
    ("चालीस से पचास हज़ार।", (40000, 50000)),
    ("40 se 45 hazaar.", (40000, 45000)),
    # --- digits inside a sentence with other numbers ---
    ("2 saal pehle 50,000 diye the.", R),
    ("लोन 3,50,000 का, बीमा 41,300 का।", R),
]


def show(r):
    if isinstance(r, Parsed):
        return f"Parsed({r.rupees})"
    if isinstance(r, Approximate):
        return f"Approx({r.low},{r.high})"
    return type(r).__name__ + (f"({r.reason.value})" if hasattr(r, "reason") and hasattr(r.reason, "value") else "")


def main() -> int:
    wrong = missed = approx_r = 0
    plain = [c for c in CASES if isinstance(c[1], int)]
    plain_missed = 0
    for text, gold in CASES:
        a, p = parse_approx_amount(text), parse_amount(text)
        status = "ok"
        if isinstance(gold, int):
            if isinstance(a, Parsed) and a.rupees == gold and isinstance(p, Parsed) and p.rupees == gold:
                pass
            elif isinstance(a, Parsed) or isinstance(p, Parsed) or isinstance(a, Approximate):
                status = "WRONG" if (isinstance(a, Parsed) and a.rupees != gold) or (
                    isinstance(p, Parsed) and p.rupees != gold) else "MISSED"
            else:
                status = "MISSED"
        elif gold == R:
            if isinstance(a, Parsed) or isinstance(p, Parsed):
                status = "WRONG"
            elif isinstance(a, Approximate):
                approx_r += 1
                status = "ok(approx)"
        else:
            if isinstance(a, Parsed) or isinstance(p, Parsed):
                status = "WRONG"
            elif isinstance(a, Approximate) and (a.low, a.high) != gold:
                status = "WRONG-ENDS"
        wrong += status.startswith("WRONG")
        missed += status == "MISSED"
        plain_missed += status == "MISSED" and isinstance(gold, int)
        print(f"{status:10} gold={gold!s:16} approx={show(a):24} plain={show(p):24} | {text}")
    print(f"\n{len(CASES)} sentences: {wrong} wrong, {missed} missed; plain amounts {len(plain)}, "
          f"refused {plain_missed}; R-gold read as Approximate {approx_r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
