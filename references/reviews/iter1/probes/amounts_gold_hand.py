"""32 Hindi and Hinglish sentences read by hand by the reviewer (before looking at gold), against gold.

The sample was drawn with random.Random(7): 4 per (language, stratum). Offline.

  uv run python references/reviews/iter1/probes/amounts_gold_hand.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HAND = {
    "amt-hi-plain-06": 20_600,  # बीस हज़ार छह सौ
    "amt-hi-plain-03": 700,  # सात सौ
    "amt-hi-plain-07": 73_850,  # तिहत्तर हज़ार आठ सौ पचास
    "amt-hi-plain-11": 10_500,  # दस हज़ार पाँच सौ
    "amt-hi-lc-01": 1_300_000,  # तेरह लाख
    "amt-hi-lc-02": 100_000_000,  # दस करोड़
    "amt-hi-lc-09": 31_710_000,  # तीन करोड़ सत्रह लाख दस हज़ार
    "amt-hi-lc-14": 81_815_000,  # आठ करोड़ अठारह लाख पंद्रह हज़ार
    "amt-hi-frac-06": 6_500,  # साढ़े छह हज़ार
    "amt-hi-frac-10": 150_000,  # डेढ़ लाख
    "amt-hi-frac-01": 125_000,  # सवा लाख
    "amt-hi-frac-09": 375,  # पौने चार सौ
    "amt-hi-irr-04": 6_618_000,  # छियासठ लाख अठारह हज़ार
    "amt-hi-irr-01": 31_000,  # इकतीस हज़ार
    "amt-hi-irr-02": 89_400,  # नवासी हज़ार चार सौ
    "amt-hi-irr-07": 8_300_000,  # तिरासी लाख
    "amt-hi-en-plain-07": 33_750,
    "amt-hi-en-plain-02": 3_000,
    "amt-hi-en-plain-04": 11_000,
    "amt-hi-en-plain-14": 13_700,
    "amt-hi-en-lc-09": 61_320_000,  # six crore thirteen lakh twenty thousand
    "amt-hi-en-lc-07": 95_000_000,  # nine crore fifty lakh
    "amt-hi-en-lc-01": 300_000,
    "amt-hi-en-lc-10": 660_200,  # six lakh sixty thousand two hundred
    "amt-hi-en-frac-02": 250_000,  # two and a half lakh
    "amt-hi-en-frac-04": 150_000,  # one point five lakh
    "amt-hi-en-frac-11": 45_000_000,  # साढ़े चार crore
    "amt-hi-en-frac-13": 2_250,  # सवा दो thousand
    "amt-hi-en-irr-10": 71_100,
    "amt-hi-en-irr-01": 38_000,
    "amt-hi-en-irr-15": 6_400_000,
    "amt-hi-en-irr-13": 43_000,
}
rows = {r["id"]: r for r in map(json.loads, (ROOT / "data/amounts/amounts-v1.jsonl").read_text(encoding="utf-8").splitlines())}
bad = [(k, v, rows[k]["gold"]["amount_inr"], rows[k]["text"]) for k, v in HAND.items() if rows[k]["gold"]["amount_inr"] != v]
print(f"hand readings {len(HAND)}, agree with gold {len(HAND) - len(bad)}, disagree {len(bad)}")
for row in bad:
    print("  DISAGREE", row)
