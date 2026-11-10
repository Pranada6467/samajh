# Datasheet: amounts-v1

## What it is

240 short sentences, each containing one rupee amount spoken as words, with the amount in whole rupees as gold. 60 sentences each for Hindi (`hi`), Hinglish (`hi-en`), Tamil (`ta`) and Kannada (`kn`). The sentences are voiced by TTS and transcribed by Prisma STT; the set then scores how often `samajh.amounts.parse_amount` recovers the gold amount from the transcript.

Every sentence is synthetic. The set contains no real persons, lenders, insurers, accounts or records.

## How it is generated

```
uv run python -m samajh.evalkit.amounts --out data/amounts
```

- Generator: `samajh/evalkit/amounts/grammar.py`, `generate(seed=20261110)`.
- Files: `amounts-v1.jsonl` (one JSON object per line, UTF-8, sorted keys) and `amounts-v1.sha256`.
- sha256 of `amounts-v1.jsonl`: `62b0dd71085907386ffa173397cbb79fb06dd1cce10618f65581d7feed5e0d76`
- The set is frozen before any audio is made. The command refuses to overwrite a manifest whose bytes differ unless `--force` is given.
- The generator and its tests never call `parse_amount`, and no item was dropped, reworded or filtered by what the parser can read.

Row format:

```json
{"gold": {"amount_inr": 125000}, "id": "amt-hi-frac-01", "language": "hi",
 "tags": {"carrier": "hi-c09", "fold": "0", "form": "sawa", "round": "yes", "stratum": "fraction"},
 "text": "बीमा कवर सवा लाख रुपये का है।"}
```

Rows are interleaved by language and then stratum, so the first 20 rows hold 5 per language and cover all four strata for each language.

## Strata and counts

Counted from `amounts-v1.jsonl`. Each cell is total (round / not round). `round` is "yes" when the amount is one count times one unit word, and for every fraction item.

| Language | plain | lakh_crore | fraction | irregular_21_99 | Total |
|---|---|---|---|---|---|
| hi | 15 (5 / 10) | 15 (5 / 10) | 15 (15 / 0) | 15 (8 / 7) | 60 |
| hi-en | 15 (5 / 10) | 15 (5 / 10) | 15 (15 / 0) | 15 (8 / 7) | 60 |
| ta | 15 (5 / 10) | 15 (5 / 10) | 15 (15 / 0) | 15 (8 / 7) | 60 |
| kn | 15 (5 / 10) | 15 (5 / 10) | 15 (15 / 0) | 15 (8 / 7) | 60 |

- `plain`: below 1 lakh, no lakh or crore word: hundreds and thousands, and in 24 of the 60 items a part below one hundred as well (73,850; 370).
- `lakh_crore`: lakh and/or crore, alone or with a lower group.
- `fraction`: a fraction word applied to a unit word. Gold is fraction × unit, computed with `Decimal`.
- `irregular_21_99`: a count from 21 to 99 that is not a multiple of ten, times thousand or lakh, with or without a second group. Each language has 15 distinct counts: all eight decades, and at least four of 29, 39, 49, 59, 69, 79, 89.

Amounts are distinct within a language and lie between 100 and 40 crore. Each (language, stratum) cell is split into fold "0" (8 items) and fold "1" (7 items). Each language has 12 carrier sentences, each used 5 times; 4 of the 12 have no currency word after the amount (20 of 60 sentences per language).

Fraction forms per language (tag `form`, counted from the file):

| Language | Forms |
|---|---|
| hi | sawa 3, saadhe 3, paune 3, dedh 3, dhai 3 |
| hi-en | and_a_half 3, point 4, dedh 1, dhai 1, saadhe 2, sawa 2, paune 2 |
| ta | half 2, three_quarter 2, n_quarter 3, n_three_quarter 2, n_half 6 |
| kn | half 2, three_quarter 2, n_quarter 3, n_three_quarter 2, n_half 6 |

Text length in Unicode code points:

| Language | Median | Maximum | Total |
|---|---|---|---|
| hi | 34 | 58 | 2,150 |
| hi-en | 45.5 | 65 | 2,764 |
| ta | 44 | 77 | 2,782 |
| kn | 41 | 78 | 2,616 |

All 240 sentences total 10,312 code points.

## Word forms covered

- **Canonical forms** (`form: canonical`; strata plain, lakh_crore, irregular_21_99): the output of `samajh.amounts.spoken_amount(amount, language)`. Hindi is in Devanagari, Hinglish uses English number words with Indian units, and Tamil and Kannada use their fused tens-and-unit forms.
- **Hindi fractions:** सवा (alone = 1.25, and सवा दो to सवा पाँच), साढ़े तीन to साढ़े नौ, पौने दो to पौने पाँच, डेढ़ (1.5), ढाई (2.5), before सौ, हज़ार, लाख or करोड़.
- **Hinglish fractions:** "one and a half", "two and a half" and one more "N and a half"; "one point five", "two point two five", "three point five", "seven point five", before lakh or crore. Also the Hindi words डेढ़, ढाई, साढ़े N, सवा N, पौने N in Devanagari before an English unit (thousand, lakh, crore).
- **Tamil fractions:** அரை (0.5), முக்கால் (0.75), ஒன்றேகால் (1.25), இரண்டேகால் (2.25), ஒன்றே முக்கால் (1.75) before லட்சம் or கோடி; ஒன்றரை, இரண்டரை, மூன்றரை and three of நான்கரை to ஒன்பதரை before ஆயிரம், லட்சம் or கோடி.
- **Kannada fractions:** ಅರ್ಧ (0.5), ಮುಕ್ಕಾಲು (0.75), ಒಂದೂಕಾಲು (1.25), ಎರಡೂಕಾಲು (2.25), ಒಂದೂ ಮುಕ್ಕಾಲು (1.75) before ಲಕ್ಷ or ಕೋಟಿ; ಒಂದೂವರೆ, ಎರಡೂವರೆ, ಮೂರೂವರೆ and three of ನಾಲ್ಕೂವರೆ to ಒಂಬತ್ತೂವರೆ before ಸಾವಿರ, ಲಕ್ಷ or ಕೋಟಿ.

## Limits

- **Synthetic sentences.** No real persons or records. The sentences are written for this test, not sampled from calls.
- **Tamil and Kannada text is `not human-reviewed`.** No fluent reviewer has read the carriers, the fraction forms or the canonical number words. Forms may be unnatural or wrong.
- **The canonical word forms come from the parser's sibling.** `spoken_amount` lives in the same package as `parse_amount` and shares its word tables. A wrong word in a table shared by both would not show at text level. It can only show after TTS and STT, or under human review.
- **Easier than real calls.** Each sentence has one amount and no other number, range, negation or comparison. There is no hesitation, self-correction or second speaker.
- **Amount and carrier are paired at random.** Some sentences are implausible (a monthly instalment of several crore, a loan of two hundred rupees). This tests number recognition, not plausibility.
- **Fraction forms are not equally frequent in Tamil, Kannada and Hinglish.** The half, three-quarter and one-and-three-quarter forms have only two natural units (lakh, crore), so they get 2 items each and the N-and-a-half forms get 6. Hinglish डेढ़ and ढाई get 1 item each.
- **Per-cell n is small.** A stratum has 15 items per language and a fraction form has 1 to 6. Report results per stratum with n, and do not read a single form's result as a rate.
- **Hindi and Hinglish text was written by the generator's author and has had no second reviewer.**
