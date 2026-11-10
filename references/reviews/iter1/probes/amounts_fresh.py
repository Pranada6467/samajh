"""Verifier probe: fresh inputs for `samajh.amounts.parse_amount`. Pure, no network.

    uv run python references/reviews/iter1/probes/amounts_fresh.py

Inputs were written by the verifier (not taken from data/amounts, tests or the reports) before
running the parser. `gold` is the rupee amount a careful listener would take, or None when the
text has no single amount (a range, two amounts, a correction left open). `left` marks a shape
the builders said they deliberately refuse or read literally. The verifier is fluent in Hindi
and English only: the Tamil and Kannada gold is NOT from a fluent reader.

Outcomes, counted separately:
  right      Parsed == gold, or refused when gold is None
  refused    gold is a number and the parser returned no amount (leads to a read-back)
  WRONG      Parsed and != gold (a confident wrong amount)
  ACCEPTED   gold is None and the parser returned an amount
"""

from collections import Counter

from samajh.amounts import Parsed, parse_amount

HI = [
    ("बावन हज़ार रुपये कटे थे", 52000, ""),
    ("पौने दो लाख का था", 175000, ""),
    ("सवा लाख", 125000, ""),
    ("साढ़े तीन लाख रुपये", 350000, ""),
    ("डेढ़ लाख", 150000, ""),
    ("ढाई हज़ार", 2500, ""),
    ("एक लाख बीस हज़ार", 120000, ""),
    ("अड़तीस हज़ार पाँच सौ", 38500, ""),
    ("उनतालीस हज़ार", 39000, ""),
    ("उनासी हज़ार", 79000, ""),
    ("नवासी हज़ार", 89000, ""),
    ("निन्यानवे हज़ार नौ सौ निन्यानवे", 99999, ""),
    ("तीन लाख दो सौ", 300200, ""),
    ("छह हज़ार पच्चीस", 6025, ""),
    ("पैंतालीस सौ", 4500, ""),
    ("बारह सौ पचास रुपये", 1250, ""),
    ("डेढ़ सौ", 150, ""),
    ("ढाई लाख", 250000, ""),
    ("सवा दो लाख", 225000, ""),
    ("पौने पाँच हज़ार", 4750, ""),
    ("साढ़े बारह हज़ार", 12500, ""),
    ("एक करोड़ दस लाख", 11000000, ""),
    ("इक्यावन हज़ार एक सौ एक", 51101, ""),
    ("5 साल में 60 हज़ार", 60000, ""),
    ("2 लाख 40 हज़ार", 240000, ""),
    ("₹52,000", 52000, ""),
    ("52000/-", 52000, ""),
    ("1.5 लाख", 150000, ""),
    ("52,000 रुपये, यानी बावन हज़ार", 52000, ""),
    ("पचपन सौ", 5500, ""),
    ("सैंतालीस हज़ार तीन सौ", 47300, ""),
    ("छियासठ हज़ार", 66000, ""),
    ("सड़सठ हज़ार", 67000, ""),
    ("उनहत्तर हज़ार", 69000, ""),
    ("तिरासी हज़ार", 83000, ""),
    ("छियानवे हज़ार", 96000, ""),
    ("चौरानवे हज़ार पाँच सौ", 94500, ""),
    ("अट्ठावन हज़ार", 58000, ""),
    ("बीमा के बावन हज़ार कटे, बस", 52000, ""),
    ("मेरे हिसाब से इकसठ हज़ार दो सौ पचास", 61250, ""),
    ("पौने तीन लाख रुपये का कवर", 275000, ""),
    ("सवा तीन हज़ार", 3250, ""),
    ("साढ़े सात सौ", 750, ""),
    ("ढाई सौ", 250, ""),
    # ranges, two amounts, open corrections: no single amount
    ("करीब चालीस बयालीस हज़ार", None, ""),
    ("चालीस से पैंतालीस हज़ार के बीच", None, ""),
    ("पहले बावन हज़ार बोला था फिर अड़तालीस हज़ार कटा", None, ""),
    ("लोन पाँच लाख का था और बीमा बावन हज़ार का", None, ""),
    ("दस-बारह हज़ार", None, ""),
    ("हज़ार बारह सौ", None, ""),
    ("बावन हज़ार तो नहीं था", None, ""),
    ("पचास हज़ार से ज़्यादा", None, ""),
    ("शायद बावन हज़ार", None, ""),
    ("बावन या पचपन हज़ार", None, ""),
    # shapes the builders said they left
    ("एक लाख बीस", 120000, "left: bare number after lakh, read literally"),
    ("एक लाख पच्चीस", 125000, "left: bare number after lakh"),
    ("दो लाख पचास", 250000, "left: bare number after lakh"),
    ("पचास हज़ार दो एफडी", 50000, "left: amount then a count"),
    ("पचास हज़ार, दो FD", 50000, "left: amount then a count"),
    ("दो एफडी पचास हज़ार की", 50000, "count then amount"),
    ("फिफ्टी 2,000", 52000, "left: number word before digits"),
    ("ट्वेंटी 5,000", 25000, "left: number word before digits"),
    ("एक 50,000 की policy", 50000, "left: number word before digits (a determiner here)"),
    ("तीन 25,000", 325000, "left: number word before digits (gold uncertain: 3,25,000?)"),
]

HI_EN = [
    ("52 thousand rupees kata tha", 52000, ""),
    ("fifty two thousand", 52000, ""),
    ("1.75 lakh", 175000, ""),
    ("one point seven five lakh", 175000, ""),
    ("one and a half lakh", 150000, ""),
    ("two and a half lakhs", 250000, ""),
    ("premium 38,500 tha", 38500, ""),
    ("thirty eight thousand five hundred", 38500, ""),
    ("around 40k", 40000, ""),
    ("1 lakh 20 thousand", 120000, ""),
    ("1,20,000", 120000, ""),
    ("120000", 120000, ""),
    ("Rs. 52,000/-", 52000, ""),
    ("half lakh", 50000, ""),
    ("twenty five k", 25000, ""),
    ("three lakh two hundred", 300200, ""),
    ("six thousand twenty five", 6025, ""),
    ("six thousand and twenty five", 6025, ""),
    ("ninety nine thousand nine hundred ninety nine", 99999, ""),
    ("5 lakh", 500000, ""),
    ("5.25 lakh", 525000, ""),
    ("52.5 thousand", 52500, ""),
    ("0.5 lakh", 50000, ""),
    ("ten thousand five hundred fifty", 10550, ""),
    ("premium फिफ्टी टू थाउज़ंड था", 52000, ""),
    ("वन लाख ट्वेंटी थाउज़ंड", 120000, ""),
    ("टू पॉइंट फाइव लाख", 250000, ""),
    ("थर्टी एट थाउज़ंड फाइव हंड्रेड", 38500, ""),
    ("25K का premium", 25000, ""),
    ("twelve hundred", 1200, ""),
    ("fifteen hundred rupees", 1500, ""),
    ("a thousand rupees", 1000, ""),
    ("insurance के लिए forty one thousand three hundred कटा", 41300, ""),
    ("premium 41,300 rupees, one time", 41300, ""),
    ("52,000 for 3 years", 52000, ""),
    ("3 saal ke liye 52,000", 52000, ""),
    ("EMI 8,500 hai aur premium 52,000", None, ""),
    ("40 se 45 thousand", None, ""),
    ("loan 5 lakh ka tha, insurance 52 thousand ka", None, ""),
    ("maybe 50 thousand", None, ""),
    ("not 52,000", None, ""),
    ("less than 50,000", None, ""),
    ("50 ya 55 thousand", None, ""),
    # romanised Hindi: the builders say these are refused
    ("bavan hazaar", 52000, "left: romanised Hindi"),
    ("dedh lakh", 150000, "left: romanised Hindi"),
    ("paune do lakh", 175000, "left: romanised Hindi"),
    ("ek lakh bees hazaar", 120000, "left: romanised Hindi"),
    ("sawa lakh", 125000, "left: romanised Hindi"),
    ("paanch hazaar", 5000, "left: romanised Hindi"),
    ("pachas hazar", 50000, "left: romanised Hindi"),
    ("saath hazaar", 60000, "left: romanised Hindi"),
    ("teen lakh", 300000, "left: romanised Hindi"),
    ("do lakh", 200000, "left: romanised Hindi"),
    ("do hazaar", 2000, "left: romanised Hindi"),
    ("barah hazaar paanch sau", 12500, "left: romanised Hindi"),
    ("char lakh pachaas hazaar", 450000, "left: romanised Hindi"),
    ("dhai lakh", 250000, "left: romanised Hindi"),
    ("sade teen lakh", 350000, "left: romanised Hindi"),
    ("pachpan hazaar rupaye", 55000, "left: romanised Hindi"),
    ("chalis hazar", 40000, "left: romanised Hindi"),
    ("das hazaar", 10000, "left: romanised Hindi"),
    ("che lakh", 600000, "left: romanised Hindi"),
    ("ek lakh", 100000, "left: romanised Hindi"),
    ("so rupaye", 100, "left: romanised Hindi"),
    ("paanch sau rupaye", 500, "left: romanised Hindi"),
    ("premium tha 2 lakh, matlab do lakh", 200000, "left: romanised Hindi beside digits"),
    ("bees 000", 20000, "left: romanised Hindi beside digits"),
    ("paune 2 lakh", 175000, "left: romanised fraction beside digits (wrong if read as 2,00,000)"),
    ("sadhe 3 lakh", 350000, "left: romanised fraction beside digits (wrong if read as 3,00,000)"),
    ("dedh 1 lakh", 150000, "left: romanised fraction beside digits"),
    ("sava 2 lakh", 225000, "left: romanised fraction beside digits (wrong if read as 2,00,000)"),
    ("pone do lakh", 175000, "left: romanised Hindi, variant spelling"),
    ("saadhey teen lakh", 350000, "left: romanised Hindi, variant spelling"),
    ("dhaai lakh", 250000, "left: romanised Hindi, variant spelling"),
    ("derh lakh", 150000, "left: romanised Hindi, variant spelling"),
    ("savaa do lakh", 225000, "left: romanised Hindi, variant spelling"),
    ("pauney 2 lakh", 175000, "left: romanised fraction, variant spelling, beside digits"),
    ("saade 3 lakh", 350000, "left: romanised fraction, variant spelling, beside digits"),
    ("sawa 2 lakh", 225000, "left: romanised fraction beside digits"),
    ("fifty thousand two FDs", 50000, "left: amount then a count"),
    ("one lakh twenty", 120000, "left: bare number after lakh"),
    ("ninety 1,80,000", 9080000, "left: number word before digits (gold uncertain)"),
]

TA = [
    ("ஐம்பதாயிரம் ரூபாய்", 50000, ""),
    ("ஐம்பத்திரண்டாயிரம் ரூபாய்", 52000, ""),
    ("இருபத்தைந்தாயிரம்", 25000, ""),
    ("ஒன்றரை லட்சம்", 150000, ""),
    ("இரண்டரை லட்சம்", 250000, ""),
    ("மூன்றரை லட்சம்", 350000, ""),
    ("முப்பத்தைந்தாயிரம்", 35000, ""),
    ("நாற்பத்தெட்டாயிரம்", 48000, ""),
    ("பதினெட்டாயிரத்து ஐநூறு", 18500, ""),
    ("ஒரு லட்சத்து இருபதாயிரம்", 120000, ""),
    ("முக்கால் லட்சம்", 75000, ""),
    ("அரை லட்சம்", 50000, ""),
    ("கால் லட்சம்", 25000, ""),
    ("ஒன்றேகால் லட்சம்", 125000, ""),
    ("எழுபத்தைந்தாயிரம்", 75000, ""),
    ("தொண்ணூறாயிரம்", 90000, ""),
    ("பன்னிரண்டாயிரம்", 12000, ""),
    ("மூன்று லட்சத்து இருநூறு", 300200, ""),
    ("ஆறாயிரத்து இருபத்தைந்து", 6025, ""),
    ("50,000 ரூபாய்", 50000, ""),
    ("இரண்டு லட்சத்து ஐம்பதாயிரம்", 250000, ""),
    ("பத்தாயிரம்", 10000, ""),
    ("ஒரு லட்சம்", 100000, ""),
    ("லட்ச ரூபாய்", 100000, ""),
    ("ஐயாயிரம்", 5000, ""),
    ("ஏழாயிரத்து ஐநூறு", 7500, ""),
    ("தொள்ளாயிரம்", 900, ""),
    ("ஆயிரத்து ஐநூறு", 1500, ""),
    ("முப்பதாயிரம் ரூபா கட்டினேன்", 30000, ""),
    ("ஐம்பத்திரண்டாயிரத்து ஐநூறு", 52500, ""),
    ("அறுபத்திரண்டாயிரம்", 62000, ""),
    ("நாற்பத்தோராயிரத்து முந்நூறு", 41300, ""),
    ("ஒரே தடவைதான், ஐம்பத்திரண்டாயிரம் ரூபாய்", 52000, ""),
    ("ரெண்டு லட்சம்", 200000, "colloquial"),
    ("மூணு லட்சம்", 300000, "colloquial"),
    ("அம்பதாயிரம்", 50000, "colloquial"),
    ("நாப்பதாயிரம்", 40000, "colloquial"),
    ("ஒண்ணரை லட்சம்", 150000, "colloquial"),
    ("ஒன்னேகால் லட்சம்", 125000, "colloquial"),
    ("அம்பத்திரெண்டாயிரம்", 52000, "colloquial"),
    ("நாற்பது நாற்பத்தைந்தாயிரம்", None, ""),
    ("ஐம்பதாயிரம் இல்லை", None, ""),
    ("ஐம்பதாயிரம் ரெண்டு FD", 50000, "left: amount then a count"),
    ("3/4 லட்சம்", 75000, "left: 3/4 before a unit"),
]

KN = [
    ("ಐವತ್ತು ಸಾವಿರ ರೂಪಾಯಿ", 50000, ""),
    ("ಐವತ್ತೆರಡು ಸಾವಿರ", 52000, ""),
    ("ಇಪ್ಪತ್ತೈದು ಸಾವಿರ", 25000, ""),
    ("ಒಂದೂವರೆ ಲಕ್ಷ", 150000, ""),
    ("ಎರಡೂವರೆ ಲಕ್ಷ", 250000, ""),
    ("ಮೂರೂವರೆ ಲಕ್ಷ", 350000, ""),
    ("ಮೂವತ್ತೈದು ಸಾವಿರ", 35000, ""),
    ("ನಲವತ್ತೆಂಟು ಸಾವಿರ", 48000, ""),
    ("ಹದಿನೆಂಟು ಸಾವಿರದ ಐನೂರು", 18500, ""),
    ("ಒಂದು ಲಕ್ಷದ ಇಪ್ಪತ್ತು ಸಾವಿರ", 120000, ""),
    ("ಮುಕ್ಕಾಲು ಲಕ್ಷ", 75000, ""),
    ("ಅರ್ಧ ಲಕ್ಷ", 50000, ""),
    ("ಒಂದೂಕಾಲು ಲಕ್ಷ", 125000, ""),
    ("ಎರಡೂಕಾಲು ಲಕ್ಷ", 225000, ""),
    ("ಎಪ್ಪತ್ತೈದು ಸಾವಿರ", 75000, ""),
    ("ತೊಂಬತ್ತು ಸಾವಿರ", 90000, ""),
    ("ಹನ್ನೆರಡು ಸಾವಿರ", 12000, ""),
    ("ಮೂರು ಲಕ್ಷ", 300000, ""),
    ("ಎರಡು ಲಕ್ಷ ಐವತ್ತು ಸಾವಿರ", 250000, ""),
    ("ಮೂರು ಲಕ್ಷದ ಇನ್ನೂರು", 300200, ""),
    ("ಆರು ಸಾವಿರದ ಇಪ್ಪತ್ತೈದು", 6025, ""),
    ("50,000 ರೂಪಾಯಿ", 50000, ""),
    ("ಹತ್ತು ಸಾವಿರ", 10000, ""),
    ("ಒಂದು ಲಕ್ಷ", 100000, ""),
    ("ಲಕ್ಷ ರೂಪಾಯಿ", 100000, ""),
    ("ಐದು ಸಾವಿರ", 5000, ""),
    ("ಏಳು ಸಾವಿರದ ಐನೂರು", 7500, ""),
    ("ಒಂಬೈನೂರು", 900, ""),
    ("ಸಾವಿರದ ಐನೂರು", 1500, ""),
    ("ಮೂವತ್ತು ಸಾವಿರ ರೂಪಾಯಿ ಕಟ್ಟಿದೆ", 30000, ""),
    ("ಐವತ್ತೆರಡು ಸಾವಿರದ ಐನೂರು", 52500, ""),
    ("ಅರವತ್ತೆರಡು ಸಾವಿರ", 62000, ""),
    ("ನಲವತ್ತೊಂದು ಸಾವಿರದ ಮುನ್ನೂರು", 41300, ""),
    ("ಒಂದೇ ಸಲ, ಐವತ್ತೆರಡು ಸಾವಿರ ರೂಪಾಯಿ", 52000, ""),
    ("ನಲವತ್ತು ನಲವತ್ತೈದು ಸಾವಿರ", None, ""),
    ("ಐವತ್ತು ಸಾವಿರ ಅಲ್ಲ", None, ""),
    ("ಒಂದು ಕಾಲು ಲಕ್ಷ", 125000, "left: ondu kaalu before a unit"),
    ("ಒಂದು ಮುಕ್ಕಾಲು ಲಕ್ಷ", 175000, "left: ondu mukkaalu before a unit"),
    ("ಐವತ್ತು ಸಾವಿರ ಎರಡು FD", 50000, "left: amount then a count"),
]

SETS = {"hi": HI, "hi-en": HI_EN, "ta (not a fluent reader)": TA, "kn (not a fluent reader)": KN}


def outcome(text: str, gold: int | None) -> tuple[str, str]:
    result = parse_amount(text)
    if isinstance(result, Parsed):
        if gold is None:
            return "ACCEPTED", str(result.rupees)
        return ("right" if result.rupees == gold else "WRONG"), str(result.rupees)
    reason = getattr(result, "reason", None)
    said = f"{result.status}" + (f"/{reason.value}" if reason else "")
    return ("right" if gold is None else "refused"), said


def main() -> int:
    grand = Counter()
    for name, rows in SETS.items():
        for label, keep in (("ordinary shapes", lambda note: not note.startswith("left")),
                            ("shapes the builders left", lambda note: note.startswith("left"))):
            tally = Counter()
            lines = []
            for text, gold, note in rows:
                if not keep(note):
                    continue
                kind, got = outcome(text, gold)
                tally[kind] += 1
                grand[(label, kind)] += 1
                if kind != "right":
                    lines.append(f"    {kind:8} {text!r}: gold {gold}, parser {got}" + (f"  [{note}]" if note else ""))
            if tally:
                print(f"{name} - {label}: n={sum(tally.values())} " + ", ".join(f"{k} {v}" for k, v in sorted(tally.items())))
                print("\n".join(lines))
    print("\nTOTAL", {f"{a} / {b}": n for (a, b), n in sorted(grand.items())})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
