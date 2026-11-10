"""Hand labels for every distinct failing (sentence, transcript) pair, written to failure_labels.tsv.

  uv run python eval/amounts/label_failures.py

The labels were assigned by reading each transcript next to its source sentence (2026-11-10).
They are kept as rules so the reasoning stays visible: for a sentence, the first rule whose
needle occurs in the transcript wins. The script fails if a failure has no rule, so a rerun
with new transcripts cannot leave an unlabelled failure behind. Tamil and Kannada labels were
made without a fluent reader: `not human-reviewed`.

Labels
  parser_gap         the number words are intact in the transcript (a spelling variant, a spacing,
                     another script); a reader gets gold, the parser does not
  partial_itn        Prisma formatted part of the number and left the rest as words; the pieces
                     still determine gold by a composition rule, like the fraction rule the parser has
  prisma_formatting  Prisma heard the words (its own word output for the same sentence is right)
                     and wrote digits that are another number; the transcript does not give gold
  recognition        the words are wrong or missing
  unresolved         prisma-v3.0 wrote wrong digits on clean or phone audio and there is no v3.0
                     word output for that sentence: formatting or recognition, not separable here
  source_or_voice    fails under every configuration: the written form or the TTS voice is suspect
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

PG, ITN, FMT, REC, UNR, SRC = (
    "parser_gap",
    "partial_itn",
    "prisma_formatting",
    "recognition",
    "unresolved",
    "source_or_voice",
)

HALF = "English in Devanagari, 'X एंड अ हाफ UNIT': parser reads only 'हाफ UNIT' and returns half a unit"
KN_60 = "ಅರುವತ್ತು, a spelling of ಅರವತ್ತು (60), is not in the lexicon"
KN_400 = "ನಾನ್ನೂರು / ನಾನ್ನೂರ, a spelling of ನಾನೂರು (400), is not in the lexicon"
KN_TENS = "tens word written with a virama (ಅರವತ್ತ್, ಎಪ್ಪತ್ತ್ನಾಲ್ಕು ...) is not in the lexicon"
KN_SPLIT = "v2.5 left the tens word and formatted the rest: tens word + digits compose to gold"
COUNT_UNIT = "count word left in front of the digits of one unit: count x unit"
REMAINDER = "higher groups as digits, lower groups left as words: add them"
CLOCK = "v2.5 wrote N-and-a-half / N-and-three-quarters as a clock time before the unit (08:30, 01:45)"
GAP = "v3.0 number formatting on an amount with an empty middle group; its verbatim output is right"
GAP_UNR = "same shape as the v3.0 skipped-group formatting error; no v3.0 word output for this sentence"
FRAC_FMT = "v3.0 formatted the fraction to the wrong number; its verbatim output has the right words"
FRAC_UNR = "v3.0 wrote a wrong number for the fraction; no v3.0 word output for this sentence"
NOISE = "right on phone audio, wrong under this noise"
TA_5K = "the fused form -த்தையாயிரம் (count ending in 5, times thousand) from spoken_amount is doubtful"

# sentence id (without the amt- prefix) -> ordered (needle, label, comment); "" matches anything.
RULES: dict[str, list[tuple[str, str, str]]] = {
    "hi-en-frac-01": [("", PG, HALF)],
    "hi-en-frac-02": [("", PG, HALF)],
    "hi-en-frac-03": [("", PG, HALF)],
    "hi-en-frac-05": [
        ("", FMT, "v2.5 wrote 'two point two five crore' as टू प्वाइंट + 25 crore; literal is right")
    ],
    "hi-en-frac-06": [
        ("", FMT, "v2.5 wrote 'three point five lakh' as थ्री प्वाइंट + 5 lakh; literal is right")
    ],
    "hi-en-frac-07": [("", FMT, "v2.5 wrote 7.5 crore as 7.50000000; literal is right; parser refuses")],
    "hi-en-frac-13": [("", REC, NOISE + " (सवा दो thousand became 2,500)")],
    "hi-en-frac-14": [("", REC, "v3.0 verbatim doubled the unit word (हज़ार हज़ार); parser refuses")],
    "hi-en-irr-04": [
        ("", ITN, "v2.5 split 'ninety four lakh ...' into नाइंटी + 4,13,000: tens word + digits")
    ],
    "hi-en-lc-04": [("", REC, "crore heard as क्लोज")],
    "hi-en-lc-06": [("", ITN, "v2.5 wrote 'ninety lakh eighty thousand' as नाइंटी + 1,80,000: " + COUNT_UNIT)],
    "hi-en-lc-08": [("", UNR, GAP_UNR + " (3 lakh 200 written 3,02,000)")],
    "hi-en-lc-09": [
        (
            "",
            FMT,
            "v2.5 wrote 6,13,00,020 थाउज़ंड; literal is right; parser multiplies it out to a wrong amount",
        )
    ],
    "hi-en-lc-13": [("", UNR, GAP_UNR + " (3 lakh 700 written 3,07,000)")],
    "hi-en-lc-15": [
        (
            "",
            FMT,
            "v2.5 wrote 9,00,014 थाउज़ंड ₹100; literal is right; parser multiplies it out to a wrong amount",
        )
    ],
    "hi-en-plain-15": [("", PG, "English in Devanagari: सेवेनटीन / सेवेंटी spellings are not in the lexicon")],
    "hi-frac-04": [("08:30", ITN, CLOCK), ("", REC, NOISE + " (साढ़े lost)")],
    "hi-frac-09": [("350", UNR, FRAC_UNR + " (पौने चार सौ = 375 written 350)"), ("", REC, NOISE)],
    "hi-frac-10": [("", REC, NOISE)],
    "hi-irr-06": [("", REC, NOISE + " (सैंतालीस became 45)")],
    "hi-lc-06": [("", REC, NOISE)],
    "hi-lc-08": [
        ("दो सौ", ITN, REMAINDER),
        ("5,00,000 200", ITN, REMAINDER),
        ("", UNR, GAP_UNR + " (5 lakh 200 written 5,00,000 or 5,200)"),
    ],
    "hi-plain-06": [("", REC, NOISE + " (छह सौ lost)")],
    "hi-plain-10": [("", FMT, GAP + " (6 thousand 25 written 6,250)")],
    "hi-plain-15": [
        ("रखती", REC, NOISE + " (अस्सी की है heard as रखती थी)"),
        ("", UNR, GAP_UNR + " (19 thousand 80 written 19,800)"),
    ],
    "kn-frac-01": [("", FMT, "v3.0 applied the half and kept the word (ಅರ್ಧ 50,00,000); parser refuses")],
    "kn-frac-02": [("", FMT, "v3.0 wrote half a lakh as 5,00,000; its verbatim output is right")],
    "kn-frac-04": [("", UNR, FRAC_UNR + " (three quarters of a crore written 75 crore)")],
    "kn-frac-05": [("", PG, "ಒಂದು ಕಾಲು (1.25) written as two words is not read")],
    "kn-frac-06": [("", UNR, FRAC_UNR + " (2.25 lakh written 2,00,000)")],
    "kn-frac-07": [("", UNR, FRAC_UNR + " (1.25 lakh written 1,00,000)")],
    "kn-frac-08": [
        ("01:45", ITN, CLOCK),
        ("1,25,000", FMT, FRAC_FMT + " (1.75 lakh written 1,25,000)"),
        ("", PG, "ಒಂದು ಮುಕ್ಕಾಲು (1.75) written as two words is not read"),
    ],
    "kn-frac-09": [
        ("ಹೋಗಿ", REC, "ಕೋಟಿ heard as ಹೋಗಿ"),
        ("01:45", ITN, CLOCK),
        ("1,25,00", UNR, FRAC_UNR + " (1.75 crore written 1.25 crore or 125 crore)"),
        ("", PG, "ಒಂದು ಮುಕ್ಕಾಲು (1.75) written as two words is not read"),
    ],
    "kn-frac-12": [
        ("1 03:30", REC, "ಎಂದು heard as ಒಂದು (one) in front of the amount"),
        ("ಒಂದು ಮೂರುವರೆ", REC, "ಎಂದು heard as ಒಂದು (one) in front of the amount"),
        ("03:30", ITN, CLOCK),
        ("", REC, NOISE),
    ],
    "kn-frac-13": [("", ITN, CLOCK)],
    "kn-frac-14": [("", REC, "the amount words were lost")],
    "kn-irr-02": [("", REC, NOISE + " (79,100 became 79,300)")],
    "kn-irr-06": [
        ("1,000", ITN, COUNT_UNIT + ", plus " + KN_400),
        ("64,000", ITN, REMAINDER + "; " + KN_400 + ", so the parser drops it and returns 64,000"),
        ("ಅರವತ್ತನಾಲ್ಕು", PG, KN_400 + ": the parser drops the word and returns 64,000"),
        ("", PG, KN_TENS + "; " + KN_400),
    ],
    "kn-irr-07": [("₹", ITN, KN_SPLIT), ("", PG, KN_TENS)],
    "kn-irr-08": [
        ("ಅರವತ್ತ್ 9,06,000", ITN, KN_SPLIT),
        ("ಅರವತ್ತ್ ಒಂಬತ್ತು", PG, KN_TENS),
        ("", REC, NOISE + " (the tens word was lost or changed)"),
    ],
    "kn-irr-10": [("", REC, "ನೂರು (hundred) lost at the end of the sentence")],
    "kn-irr-11": [("8,00,000", ITN, KN_SPLIT), ("", PG, KN_TENS)],
    "kn-irr-14": [("1,700", ITN, KN_SPLIT), ("", PG, KN_TENS)],
    "kn-irr-15": [("00,000", ITN, KN_SPLIT), ("", PG, KN_TENS)],
    "kn-lc-01": [("", PG, KN_60)],
    "kn-lc-08": [("", FMT, GAP + " (70 lakh 800 written 70,00,000)")],
    "kn-lc-11": [("", PG, KN_60)],
    "kn-lc-12": [("", PG, KN_60)],
    "kn-lc-13": [
        ("ಮುನ್ನೂರು ರೂಪಾಯಿ ಕಡಿತ ಮಾಡಿದರು", ITN, REMAINDER),
        ("ಅರುವತ್ತು", PG, KN_60),
        ("", FMT, GAP + " (60 lakh 300 written 60,00,000 or 60,300)"),
    ],
    "kn-plain-01": [("1400", REC, NOISE), ("", PG, KN_400)],
    "kn-plain-07": [
        ("31,450", REC, NOISE + " (21 became 31)"),
        ("21,000", ITN, REMAINDER + ", plus " + KN_400),
        ("", PG, KN_400),
    ],
    "kn-plain-09": [
        ("49,000", ITN, REMAINDER + "; " + KN_400 + ", so the parser drops it and returns 49,000"),
        ("", PG, KN_400 + ": the parser drops the word and returns 49,000"),
    ],
    "kn-plain-10": [("", UNR, GAP_UNR + " (20 thousand 20 written 20,20 or 20,200)")],
    "kn-plain-12": [("ಅರವತ್ತ್ 6", ITN, KN_SPLIT), ("", PG, KN_TENS)],
    "kn-plain-13": [("", PG, KN_60 + ": the parser drops the word and returns 300")],
    "ta-frac-02": [("", FMT, "v3.0 wrote half a lakh as 5,00,000 or 5,50,000; its verbatim output is right")],
    "ta-frac-03": [("", PG, "fraction written as 3/4 before the unit is not read")],
    "ta-frac-06": [
        ("2,50,000", UNR, FRAC_UNR + " (2.25 lakh written 2,50,000)"),
        ("", REC, "the amount words were lost"),
    ],
    "ta-frac-15": [
        (
            "1,00,00,000",
            ITN,
            "fraction word + unit digits, but எழரை (short vowel) is not in the lexicon: parser returns 1 crore",
        ),
        ("", PG, "எழரை, a short-vowel spelling of ஏழரை (7.5), is not in the lexicon"),
    ],
    "ta-irr-04": [("", UNR, GAP_UNR + " (45 lakh 1 thousand written 45,00,000)")],
    "ta-irr-06": [("", SRC, TA_5K + ": every configuration heard 90 thousand for 95 thousand")],
    "ta-irr-08": [("", REC, "the last word was cut (எட்டாயிரம் became எட்டா)")],
    "ta-irr-10": [("", REC, "the number word was misspelt (இருபத்தேறாயிரத்து for இருபத்தேழாயிரத்து)")],
    "ta-lc-02": [("", ITN, COUNT_UNIT)],
    "ta-lc-08": [("", FMT, GAP + " (16 lakh 700 written 16,700)")],
    "ta-lc-09": [
        ("கோடியே", ITN, REMAINDER),
        ("", FMT, "v3.0 wrote ஐம்பத்தையாயிரம் (55 thousand) as 50,000; its verbatim output is right. " + TA_5K),
    ],
    "ta-lc-10": [("", ITN, REMAINDER)],
    "ta-lc-11": [
        ("இருபத்தையாயிரம்", ITN, REMAINDER),
        ("இருபத்தையாரம்", REC, "the number word was shortened (இருபத்தையாரம்). " + TA_5K),
        ("", REC, NOISE + " (25 thousand became 20 thousand). " + TA_5K),
    ],
    "ta-lc-13": [("", FMT, GAP + " (3 lakh 200 written 3,200 or 3,02,000)")],
    "ta-plain-04": [("", PG, "a bare ஆயிரம் (one thousand, no count word) after an ordinary word is refused")],
    "ta-plain-15": [("", ITN, "v2.5 wrote 13 thousand 50 as பதிமூன்று + 1,050: " + COUNT_UNIT)],
}


def main() -> int:
    rows = [
        json.loads(line) for line in (HERE / "run" / "scores.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    pairs = dict.fromkeys(
        (row["item_id"], row["transcript"])
        for row in rows
        if row["method"] == "parser" and not row["correct"]
    )
    out, missing = [], []
    for item_id, transcript in pairs:
        rule = next((r for r in RULES.get(item_id.removeprefix("amt-"), []) if r[0] in transcript), None)
        if rule is None:
            missing.append((item_id, transcript))
        else:
            out.append({"item_id": item_id, "transcript": transcript, "label": rule[1], "comment": rule[2]})
    if missing:
        for item_id, transcript in missing:
            print(f"no rule: {item_id}\t{transcript}", file=sys.stderr)
        return 1
    with (HERE / "failure_labels.tsv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, ["item_id", "transcript", "label", "comment"], delimiter="\t")
        writer.writeheader()
        writer.writerows(out)
    print(f"{len(out)} labelled failures -> failure_labels.tsv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
