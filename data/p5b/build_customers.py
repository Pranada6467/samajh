"""Build the 24 synthetic P5b customers: fact sheets, lender records and gold (Stage 1 only).

Run: uv run python data/p5b/build_customers.py

P5b is a small fresh set for a check after a fix round, built the way P5 was built
(data/p5/build_customers.py is the template; data/p5/README.md the datasheet). Set seed:
`samajh-p5b-2026-11-13` (the disposition seed in data/p5b/topics.json).

Writes, deterministically:
  data/p5b/customers.jsonl   one fact sheet per customer (the only thing the word-writer sees)
  data/p5b/records/*.json    one CallRecord per customer
  data/p5b/gold.jsonl        the gold row per customer, set by eval/p5/gold-rules.md

Every customer is hand-written below. Gold grounds are not typed by hand: each customer carries
its beliefs (the gold `beliefs` object) and a `cite` map naming, for each ground, the fact-sheet
line it rests on; `grounds()` (copied unchanged from the P5 script) applies the table of
eval/p5/gold-rules.md to beliefs and record, and the build fails unless the cited rules are
exactly the rules that fire. All people, ids and companies are invented.

Freshness against P5 is checked here, not left to reading: no first name, sanctioned amount or
premium on a P5 record is reused, and no P5b belief set equals a P5 gold belief set.

Unlike the P5 script, this one loads `samajh/server/records.py` by file path, so the
`samajh.server` package (and with it the dialogue, rules and extractor modules) is never imported.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
P5 = ROOT / "data" / "p5"
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location("_p5b_records", ROOT / "samajh" / "server" / "records.py")
_records = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _records  # pydantic resolves the module's annotations through sys.modules
_spec.loader.exec_module(_records)
CallRecord = _records.CallRecord  # validation only
assert "samajh.server" not in sys.modules

SEED = "samajh-p5b-2026-11-13"

PROVIDERS = {
    "Kritrim": "Kritrim Life (synthetic)",
    "Prayogik": "Prayogik Suraksha (synthetic)",
    "Abhyasi": "Abhyasi Jeevan Bima (synthetic)",
    "Nakli": "Nakli Life Cover (synthetic)",
    "Pratiroop": "Pratiroop Insurance (synthetic)",
}
# Two invented lender names per lender type, all "नमूना ..." ("sample").
LENDERS = {
    "bank_a": ("bank", "नमूना बैंक"),
    "bank_b": ("bank", "नमूना भारत बैंक"),
    "nbfc_a": ("nbfc", "नमूना फ़ाइनेंस"),
    "nbfc_b": ("nbfc", "नमूना क्रेडिट"),
}


def R(first, surname, dob, lender, loan, sanctioned, premium, cover, term, tenure, pfl, req, window, method, on):
    return dict(first=first, surname=surname, dob=dob, lender=lender, loan=loan, sanctioned=sanctioned,
                premium=premium, cover=cover, term=term, tenure=tenure, pfl=pfl, req=req, window=window,
                method=method, on=on)


def S(you_are, what_happened, know, dont, talk, call="You pick up and are willing to talk."):
    return dict(you_are=you_are, what_happened=what_happened, what_you_know=know,
                what_you_do_not_know=dont, how_you_talk=talk, on_this_call=call)


def B(**kw):
    """Gold beliefs; anything not given is 'dont_know' (names_product_unprompted defaults to True)."""
    b = dict(names_product_unprompted=True, kind="dont_know", premium_inr="dont_know",
             payment_source="dont_know", payment_frequency="dont_know", required_for_loan="dont_know",
             told_could_take_elsewhere="dont_know", cover_inr="dont_know", term_months="dont_know",
             cancel={"allowed": "dont_know", "window_days": None}, money_back="dont_know",
             consent_method="dont_know", sale_concerns=[])
    for k in kw:
        if k not in b:
            raise KeyError(k)
    b.update(kw)
    return b


def cancel(allowed, window=None):
    return {"allowed": allowed, "window_days": window}


def rng(low, high):
    return {"low": low, "high": high}


C = []


def add(kind, lang, speaker, rec, sheet, beliefs=None, cite=None, notes="", why="", underlying=None):
    C.append(dict(kind=kind, underlying=underlying, language=lang, speaker=speaker, rec=rec, sheet=sheet,
                  beliefs=beliefs, cite=cite or {}, notes=notes, why=why))


M, F = "m", "f"
BOR = lambda g: {"who": "borrower", "relation": None, "gender": g}  # noqa: E731
TP = lambda rel, g: {"who": "third_party", "relation": rel, "gender": g}  # noqa: E731

# ======================================================================================
# misled (6): C001-C006
# ======================================================================================

# C001 told it is a compulsory gold safe-keeping charge
add("misled", "hi", BOR(M),
    R("Hemant", "Kritrim", "1974-03-08", "bank_a", "gold", 175000, 7350, 175000, 12, 12, True, False, 15, "signed_form", "2026-10-27"),
    S("You are Hemant, born 1974. (An invented person.) You run a roadside dhaba on a state highway.",
      "About two weeks ago you pledged your wife's gold bangles at the bank for a loan of one lakh seventy-five thousand, to buy a new gas stove and a deep freezer for the dhaba. The clerk said every gold loan has a safe-keeping charge for keeping the gold in the bank's vault, and that it has to be paid. You signed the papers he gave you.",
      ["The clerk said every gold loan has a safe-keeping charge for keeping your gold in the vault, and it has to be paid.",
       "Seven thousand three hundred fifty was cut from the loan money for it; you saw that figure on the slip.",
       "It was cut one time.",
       "It is the bank's own charge; nothing was said about paying it anywhere else.",
       "A charge does not come back, and it does not give you anything.",
       "You signed the papers the clerk gave you: the loan papers and one paper for this charge."],
      ["Whether it runs for any fixed period.",
       "Whether it can be cancelled."],
      "Easy-going, sure of himself, plain Hindi, short sentences."),
    B(kind="fee", premium_inr=7350, payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=True, told_could_take_elsewhere=False, cover_inr="names_no_amount",
      money_back="not_refundable", consent_method="signed_form"),
    {"kind": "k0", "bundling": "k3", "cover": "k4", "term": "u0", "cancel_window": "u1"},
    notes="'It has to be paid' read as told it was required. 'It does not give you anything' names no cover amount: a cover gap.",
    why="Believes the deduction was a compulsory vault safe-keeping charge for the gold loan.")

# C002 believes it is a health cover for hospital bills up to two lakh
add("misled", "hi-en", BOR(F),
    R("Jyoti", "Prayogik", "1990-07-14", "nbfc_a", "personal", 560000, 31920, 560000, 36, 36, True, False, 30, "digital_click", "2026-10-22"),
    S("You are Jyoti, born 1990. (An invented person.) You run a small home bakery that takes cake orders online.",
      "Three weeks ago you took a personal loan of five lakh sixty thousand in a finance company's app to buy a commercial oven and pay for a shop on rent. An agent on the phone said the app also offers a health cover with the loan that pays your hospital bills, and that a cashless card would come by post. You ticked it and clicked agree.",
      ["It is a health insurance: if you are admitted to hospital, it pays the bills.",
       "It covers hospital bills up to two lakh; the agent said so clearly and you are sure of that figure.",
       "The premium was thirty-one thousand nine hundred twenty, cut from the loan amount.",
       "One payment.",
       "It was optional; the app said you could take cover from any insurer.",
       "It runs three years, like the loan.",
       "You can cancel it within thirty days.",
       "The premium does not come back.",
       "You agreed by clicking in the app."],
      ["Why the cashless card has not come yet."],
      "Bright, talkative, Hindi mixed with English words like 'health cover', 'hospital', 'premium'."),
    B(kind="insurance", premium_inr=31920, payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=False, told_could_take_elsewhere=True, cover_inr=200000, term_months=36,
      cancel=cancel(True, 30), money_back="not_refundable", consent_method="digital_click"),
    {"cover": "k1"},
    notes="She calls it health insurance; the record holds a life cover on the loan. No rule reads the type of insurance, so only the cover figure (two lakh against the record's five lakh sixty thousand) is a ground; the health-cover belief is ours to note.",
    why="Believes the add-on is a health cover paying hospital bills up to two lakh; the record holds a life cover of the loan amount.")

# C003 told it costs only two thousand, believes it renews yearly
add("misled", "hi", BOR(M),
    R("Naresh", "Abhyasi", "1967-11-02", "bank_b", "personal", 425000, 21450, 425000, 24, 24, True, False, 15, "recorded_call", "2026-10-19"),
    S("You are Naresh, born 1967. (An invented person.) You are a retired mechanic from a state bus depot.",
      "Nearly a month ago you took a personal loan of four lakh twenty-five thousand from the bank to help your son open a mobile shop. The officer said there is a small life cover with the loan, 'only two thousand rupees'. Before the money came, someone from the bank phoned, said the call was being recorded, and you said yes to the loan and the cover. You have not looked at any statement since.",
      ["It is a life cover on the loan.",
       "It costs two thousand rupees; the officer said 'only two thousand', and you are sure of that figure.",
       "It was taken from the loan money.",
       "You believe it is two thousand every year, renewed each year while the loan runs.",
       "It was your choice; the officer said you could buy such a cover from any company.",
       "It covers the full loan, four lakh twenty-five thousand.",
       "It runs two years, as long as the loan.",
       "The money does not come back.",
       "You said yes on the bank's recorded phone call."],
      ["Whether it can be cancelled, or by when."],
      "Slow, friendly, plain Hindi; likes to repeat the officer's words."),
    B(kind="insurance", premium_inr=2000, payment_source="from_loan", payment_frequency="recurring",
      required_for_loan=False, told_could_take_elsewhere=True, cover_inr=425000, term_months=24,
      money_back="not_refundable", consent_method="recorded_call"),
    {"premium": "k1", "payment_frequency": "k3", "cancel_window": "u0"},
    notes="He states two thousand as the premium (the record holds twenty-one thousand four hundred fifty); 'every year' is a recurring-payment belief, a gap by the table.",
    why="Believes the cover costs two thousand a year; the record holds a single premium ten times that.")

# C004 believes she paid into an app wallet she can withdraw from any time
add("misled", "hi-en", BOR(F),
    R("Poonam", "Nakli", "1995-02-19", "nbfc_b", "personal", 210000, 11970, 210000, 24, 18, False, False, 15, "digital_click", "2026-10-30"),
    S("You are Poonam, born 1995. (An invented person.) You are a freelance graphic designer working from home.",
      "Two weeks ago you took a personal loan of two lakh ten thousand in a finance company's app to buy a laptop and a drawing tablet. In the app's chat, an agent told you about a 'safe wallet': you pay some money into it, it stays there as your balance, and you can take it out whenever you want. You paid into it yourself by UPI and clicked 'I agree'.",
      ["You believe it is money kept in the app's wallet, a kind of deposit in your name.",
       "You paid eleven thousand nine hundred seventy into it yourself by UPI; it was not cut from the loan.",
       "One payment.",
       "It was your choice; nobody said it was needed for the loan.",
       "You believe you can withdraw that money from the wallet any time you want.",
       "You agreed by clicking 'I agree' in the app."],
      ["What else it gives you, or up to what amount.",
       "How long it runs.",
       "Whether there is any cancelling; you think you can just withdraw.",
       "Anything about other companies; nothing like that came up."],
      "Relaxed, quick, Hindi mixed with a lot of English."),
    B(kind="deposit", premium_inr=11970, payment_source="separately", payment_frequency="one_time",
      required_for_loan=False, told_could_take_elsewhere="not_applicable", money_back="refundable_anytime",
      consent_method="digital_click"),
    {"kind": "k0", "belief_mismatch": "k4", "cover": "u0", "term": "u1", "cancel_window": "u2"},
    why="Believes she paid into an app wallet, a deposit she can withdraw at any time.")

# C005 record says paid separately; he believes it was cut from the loan
add("misled", "hi", BOR(M),
    R("Vinod", "Pratiroop", "1971-09-25", "bank_a", "personal", 340000, 18700, 340000, 30, 30, False, False, 30, "signed_form", "2026-10-24"),
    S("You are Vinod, born 1971. (An invented person.) You are a carpentry contractor who fits kitchens and wardrobes.",
      "Three weeks ago you took a personal loan of three lakh forty thousand from your bank to buy a panel-cutting machine. The officer explained a life cover on the loan and you took it. You did not ask how its premium would be paid; you only looked at what reached you.",
      ["It is a life cover on the loan: if you die, the loan is paid off.",
       "It cost eighteen thousand seven hundred.",
       "You believe it was cut from the loan money; the money that came looked short to you by about that much.",
       "One payment.",
       "It was your choice; the officer said any company's cover would do.",
       "It covers three lakh forty thousand, the loan amount.",
       "It runs as long as the loan, two and a half years.",
       "You can cancel it within thirty days.",
       "The money does not come back.",
       "You signed its form at the branch."],
      ["Anything about the entries in your savings account; you have not checked them."],
      "Practical, a little blunt, plain Hindi."),
    B(kind="insurance", premium_inr=18700, payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=False, told_could_take_elsewhere=True, cover_inr=340000, term_months="as_long_as_loan",
      cancel=cancel(True, 30), money_back="not_refundable", consent_method="signed_form"),
    {"loan_funded": "k2"},
    notes="Term: 'as long as the loan' is 30 months on the record, equal to the term, so it passes.",
    why="Knows every fact but believes the premium was cut from the loan; the record says it was paid separately.")

# C006 believes the premium is adjusted against her last EMIs if nothing happens
add("misled", "hi-en", BOR(F),
    R("Seema", "Kritrim", "1983-05-12", "nbfc_a", "personal", 480000, 26400, 480000, 24, 24, True, False, 15, "otp", "2026-11-03"),
    S("You are Seema, born 1983. (An invented person.) You run a home-tuition centre for school children.",
      "Ten days ago you took a personal loan of four lakh eighty thousand from a finance company to pay the advance on a bigger room for your classes. The executive said a loan cover comes with it, and that if nothing happens during the loan, the premium is adjusted against your last EMIs, so in the end it costs you nothing. You gave the OTP he asked for.",
      ["It is a loan insurance: if something happens to you, the loan is cleared.",
       "It was twenty-six thousand four hundred, cut from the loan amount.",
       "One payment.",
       "It was your choice; he said other insurers are fine too.",
       "It covers the full loan, four lakh eighty thousand.",
       "It runs two years, the same as the loan.",
       "You can cancel it within fifteen days.",
       "You believe that if nothing happens, the premium comes back to you at the end, adjusted against your last EMIs.",
       "You agreed by giving the OTP."],
      ["Exactly how that adjustment at the end will be shown."],
      "Organised, cheerful, Hindi mixed with English."),
    B(kind="insurance", premium_inr=26400, payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=False, told_could_take_elsewhere=True, cover_inr=480000, term_months=24,
      cancel=cancel(True, 15), money_back="withdrawable_after_period", consent_method="otp"),
    {"belief_mismatch": "k7"},
    notes="'Comes back at the end, adjusted against the last EMIs' read as money got back after a period.",
    why="Knows the cover but believes the premium comes back at the end of the loan if nothing happens.")

# ======================================================================================
# uninformed (2): C007 (knowledge gap only), C008 (problem)
# ======================================================================================

add("uninformed", "hi", BOR(M),
    R("Ravindra", "Prayogik", "1962-01-30", "nbfc_b", "gold", 125000, 4125, 125000, 9, 9, True, False, 30, "signed_form", "2026-10-29"),
    S("You are Ravindra, born 1962. (An invented person.) You are a cobbler with a small shop near a bus stand.",
      "Two weeks ago you pledged your wife's silver-and-gold anklets at a finance company for a gold loan of one lakh twenty-five thousand, to fix the roof of your house before winter. The executive mentioned some insurance with the loan, said take it if you want, and you signed a paper for it.",
      ["It is some insurance with the loan.",
       "It was cut from the loan money.",
       "It was taken one time.",
       "It was your choice; the executive said take it if you want.",
       "It runs as long as the loan.",
       "You signed a paper for it."],
      ["How much was cut.",
       "Anything about other companies.",
       "What it gives, or up to what amount.",
       "Whether it can be cancelled.",
       "Whether any money comes back."],
      "Quiet, honest, plain Hindi, says plainly when he does not know."),
    B(kind="insurance", payment_source="from_loan", payment_frequency="one_time", required_for_loan=False,
      term_months="as_long_as_loan", consent_method="signed_form"),
    {"premium": "u0", "cover": "u2", "cancel_window": "u3", "belief_mismatch": "u4"},
    notes="Term: 'as long as the loan' is 9 months on the record, equal to the term, so it passes.",
    why="Knows it is optional insurance cut once from the loan, running as long as the loan; knows no figure.")

add("uninformed", "hi-en", BOR(F),
    R("Komal", "Abhyasi", "1998-08-21", "bank_b", "personal", 230000, 6480, 230000, 18, 24, True, False, 30, "otp", "2026-10-17"),
    S("You are Komal, born 1998. (An invented person.) You are a nursing assistant at a private nursing home.",
      "Nearly a month ago you took a personal loan of two lakh thirty thousand from the bank for your mother's eye operation. A bank agent came to your home with a tablet to finish the papers and asked for an OTP at each step; you read out two or three OTPs to him. Later an SMS said six thousand four hundred eighty had been deducted from the loan.",
      ["Six thousand four hundred eighty was cut from the loan money; the SMS said so.",
       "It was cut one time.",
       "You read out two or three OTPs to the agent during the paperwork; you do not know what each one was for."],
      ["Whether you took anything besides the loan; when first asked, nothing comes to mind.",
       "What the six thousand four hundred eighty was for: some charge or some insurance, you cannot say.",
       "Whether it was needed, or whether it could be taken from somewhere else.",
       "What it gives, how long it runs, whether it can be cancelled, whether money comes back.",
       "What you agreed to with those OTPs."],
      "Soft-spoken, tired after night duty, Hindi mixed with English."),
    B(names_product_unprompted=False, kind="dont_know", premium_inr=6480, payment_source="from_loan",
      payment_frequency="one_time", consent_method="dont_know"),
    {"recall": "u0", "kind": "u1", "consent": "u4", "cover": "u3", "term": "u3", "cancel_window": "u3",
     "belief_mismatch": "u3"},
    notes="She knows the exact amount cut but not what it was for: kind not known (refer). She does not know what she agreed to with the OTPs: consent refer. Names nothing when first asked and does not deny: recall gap.",
    why="Knows the exact deduction from an SMS but not what it was for or what her OTPs agreed to.")

# ======================================================================================
# ordinary_informed (3): C009-C011
# ======================================================================================

add("ordinary_informed", "hi", BOR(F),
    R("Mamta", "Nakli", "1979-06-03", "bank_a", "personal", 360000, 16560, 360000, 30, 30, True, False, 15, "otp", "2026-10-21"),
    S("You are Mamta, born 1979. (An invented person.) You run a sweet shop with your husband in a market lane.",
      "Three weeks ago you took a personal loan of three lakh sixty thousand from the bank for new glass display counters. The officer explained a life cover on the loan and you took it, confirming with an OTP.",
      ["It is a life cover on the loan; if you die, the loan is paid off.",
       "It cost sixteen thousand five hundred sixty, cut from the loan money; you checked the slip.",
       "One payment.",
       "It was your choice; he said any company would do.",
       "It covers three lakh sixty thousand.",
       "You believe it runs three years.",
       "You can cancel it within fifteen days.",
       "The money does not come back.",
       "You agreed by giving the OTP."],
      ["How long the loan itself runs, to the month."],
      "Brisk, precise with money, plain Hindi."),
    B(kind="insurance", premium_inr=16560, payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=False, told_could_take_elsewhere=True, cover_inr=360000, term_months=36,
      cancel=cancel(True, 15), money_back="not_refundable", consent_method="otp"),
    {"term": "k5"},
    notes="Term: she says three years; the record term is 30 months, a gap.",
    why="Knows every fact except the term, which she gives as three years against thirty months.")

add("ordinary_informed", "hi", BOR(M),
    R("Sunil", "Pratiroop", "1969-12-15", "nbfc_a", "personal", 650000, 38350, 650000, 48, 48, False, True, 30, "signed_form", "2026-10-18"),
    S("You are Sunil, born 1969. (An invented person.) You own two goods tempos and drive one of them yourself.",
      "Nearly a month ago you took a personal loan of six lakh fifty thousand from a finance company for the down payment on a third tempo. The executive said a loan insurance is needed for this loan, but that you could bring a policy from any company; you took theirs because it was simpler, paid it by cheque and signed its form.",
      ["It is a loan insurance.",
       "The premium was thirty-eight thousand three hundred fifty; you paid it separately by cheque.",
       "One payment.",
       "It was needed for the loan, but you were told you could take it from any company.",
       "If something happens to you, it pays whatever loan is still left.",
       "You can cancel it within thirty days.",
       "The money does not come back.",
       "You signed its form."],
      ["Up to what amount exactly it pays.",
       "How long it runs."],
      "Steady, few words, plain Hindi."),
    B(kind="insurance", premium_inr=38350, payment_source="separately", payment_frequency="one_time",
      required_for_loan=True, told_could_take_elsewhere=True, cover_inr="names_no_amount",
      cancel=cancel(True, 30), money_back="not_refundable", consent_method="signed_form"),
    {"cover": "k4", "term": "u1"},
    notes="Cover 'pays whatever loan is still left' names no amount: a cover gap. Required, with a free choice of insurer: no bundling ground.",
    why="Required cover with a free choice of insurer, paid by cheque; cover named without an amount, term unknown.")

add("ordinary_informed", "hi-en", BOR(M),
    R("Tarun", "Kritrim", "1992-04-27", "bank_b", "gold", 270000, 9990, 270000, 12, 6, True, False, 30, "digital_click", "2026-11-06"),
    S("You are Tarun, born 1992. (An invented person.) You are a wedding photographer.",
      "Last week you took a six-month gold loan of two lakh seventy thousand in your bank's app for a new lens kit before the wedding season. The app showed a loan life cover with a short summary; you read it, added it and clicked agree.",
      ["It is a loan life cover.",
       "It was around ten and a half thousand, cut from the loan.",
       "It covers two lakh seventy thousand.",
       "It runs one year.",
       "It was optional; the app said any insurer would do.",
       "You can cancel it within thirty days.",
       "You agreed by clicking in the app."],
      ["Whether it is a one-time payment or renews every year.",
       "Whether any money comes back at the end."],
      "Casual, quick, Hindi mixed with English."),
    B(kind="insurance", premium_inr=10500, payment_source="from_loan", required_for_loan=False,
      told_could_take_elsewhere=True, cover_inr=270000, term_months=12, cancel=cancel(True, 30),
      consent_method="digital_click"),
    {"premium": "k1", "payment_frequency": "u0", "belief_mismatch": "u1"},
    notes="Premium: ten and a half thousand is about 5% over the record's nine thousand nine hundred ninety, a gap.",
    why="Knows what he bought; premium about 5% high, unsure whether it renews or whether money comes back.")

# ======================================================================================
# well_informed (2): C012-C013
# ======================================================================================

add("well_informed", "hi", BOR(M),
    R("Balram", "Prayogik", "1964-10-09", "bank_a", "personal", 750000, 46500, 750000, 60, 60, False, True, 15, "recorded_call", "2026-10-23"),
    S("You are Balram, born 1964. (An invented person.) You are an ex-serviceman who runs a small security-guard agency.",
      "Three weeks ago you took a personal loan of seven lakh fifty thousand from your bank to buy uniforms and two-wheelers for your guards. The officer said a loan life cover is needed for this loan but could be from any insurer; you compared two quotes and chose the bank's partner. You paid the premium yourself by bank transfer from your savings. The bank then called you, said the call was recorded, read out the details, and you said yes.",
      ["It is a life insurance on the loan: if you die, it clears the loan.",
       "The premium was forty-six thousand five hundred; you paid it separately by bank transfer from your savings.",
       "One payment.",
       "It was needed for the loan, but you could take it from any insurer.",
       "It covers seven lakh fifty thousand.",
       "It runs five years, as long as the loan.",
       "You can cancel it within fifteen days.",
       "The money does not come back; it is not a deposit.",
       "You said yes on the bank's recorded call."],
      ["Nothing important; you went through it carefully."],
      "Disciplined, clear, plain Hindi."),
    B(kind="insurance", premium_inr=46500, payment_source="separately", payment_frequency="one_time",
      required_for_loan=True, told_could_take_elsewhere=True, cover_inr=750000, term_months=60,
      cancel=cancel(True, 15), money_back="not_refundable", consent_method="recorded_call"),
    why="States every fact as on the record; required, with a free choice of insurer, paid separately.")

add("well_informed", "hi-en", BOR(F),
    R("Rukhsana", "Abhyasi", "1987-01-17", "nbfc_b", "gold", 190000, 5510, 170000, 9, 9, True, False, 30, "otp", "2026-10-31"),
    S("You are Rukhsana, born 1987. (An invented person.) You run a mehendi and bridal make-up business.",
      "Two weeks ago you took a nine-month gold loan of one lakh ninety thousand from a finance company to buy stock for the wedding season. The executive explained a loan life cover with a printed sheet, which you read; you took it and gave the OTP.",
      ["It is a life insurance on the loan.",
       "The premium was five thousand five hundred ten, cut from the loan.",
       "One payment.",
       "It was your choice; he said you could buy it from any insurer.",
       "It covers one lakh seventy thousand, a little less than the loan.",
       "It runs nine months, as long as the loan.",
       "You can cancel it within thirty days.",
       "The money does not come back.",
       "You agreed by giving the OTP."],
      ["Nothing important."],
      "Confident, warm, Hindi mixed with English."),
    B(kind="insurance", premium_inr=5510, payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=False, told_could_take_elsewhere=True, cover_inr=170000, term_months=9,
      cancel=cancel(True, 30), money_back="not_refundable", consent_method="otp"),
    why="States every fact as on the record, including a cover below the loan amount.")

# ======================================================================================
# took_nothing (2): C014-C015
# ======================================================================================

add("took_nothing", "hi", BOR(M),
    R("Chetan", "Nakli", "1976-08-05", "nbfc_a", "gold", 310000, 14880, 310000, 12, 12, True, False, 15, "signed_form", "2026-10-20"),
    S("You are Chetan, born 1976. (An invented person.) You sell utensils from a handcart and at weekly markets.",
      "Three weeks ago you closed your old gold loan at a finance company and took a fresh one of three lakh ten thousand on the same gold the same day, to buy stock for the festival. The money that came was less, and the executive said the old loan's dues were adjusted.",
      ["You took only the loan, nothing else.",
       "About fifteen, sixteen thousand less came; that was the pending interest of your old gold loan, adjusted.",
       "It was adjusted one time.",
       "That money went to the old loan; it does not come back.",
       "You signed the papers to close the old loan and take the new one, nothing else.",
       "If asked again, you say again that you took nothing else; the difference was the old loan's interest."],
      ["That anything else was added.",
       "Anything about it being needed, or other companies.",
       "That it gives anything, for how long, or whether it can be cancelled."],
      "Plain, slightly impatient, plain Hindi."),
    B(names_product_unprompted="denies", kind="other", premium_inr=rng(15000, 16000), payment_source="from_loan",
      payment_frequency="one_time", money_back="not_refundable", consent_method="did_not_agree"),
    {"recall": "k0", "kind": "k1", "premium": "k1", "consent": "k4", "cover": "u2", "term": "u2",
     "cancel_window": "u2"},
    notes="He knows roughly the amount cut but calls it the old loan's interest and says he took nothing: recall denied and kind other. 'Signed the papers to close the old loan and take the new one' read as an account of agreeing that leaves the product out. Blind second labelling (2026-11-13): the labeller also listed a refer ground on loan_funded ('does not know of any payment'); kept out, because only grounds reachable after a held denial count (the reading P5 used for C035 to C038). See CHANGELOG.",
    why="Says he took nothing; thinks the shortfall was his old gold loan's pending interest.")

add("took_nothing", "hi-en", BOR(F),
    R("Bhavna", "Pratiroop", "1993-03-29", "bank_b", "personal", 520000, 17940, 520000, 36, 36, True, False, 30, "digital_click", "2026-10-26"),
    S("You are Bhavna, born 1993. (An invented person.) You are a school counsellor.",
      "A little over two weeks ago you took a personal loan of five lakh twenty thousand in your bank's app for the down payment on a family car. The amount that reached your account was lower, and you assumed the bank took your first EMI in advance.",
      ["You took only the loan, nothing else.",
       "Seventeen thousand nine hundred forty less came; the bank took your first EMI in advance.",
       "It was taken one time.",
       "That was your EMI; it went towards the loan and does not come back.",
       "You clicked accept only for the loan in the app.",
       "If asked again, you say no, only the advance EMI was taken."],
      ["That anything else was added or debited.",
       "Anything about it being needed, or other companies.",
       "That it gives anything, for how long, or whether it can be cancelled."],
      "Calm, certain, Hindi mixed with English."),
    B(names_product_unprompted="denies", kind="other", premium_inr=17940, payment_source="from_loan",
      payment_frequency="one_time", money_back="not_refundable", consent_method="did_not_agree"),
    {"recall": "k0", "kind": "k1", "consent": "k4", "cover": "u2", "term": "u2", "cancel_window": "u2"},
    notes="She knows the exact amount cut but calls it an advance EMI and says she took nothing: recall denied and kind other. Blind second labelling (2026-11-13): the labeller also listed a refer ground on loan_funded ('does not know of any payment'); kept out, because only grounds reachable after a held denial count (the reading P5 used for C035 to C038). See CHANGELOG.",
    why="Says she took nothing; thinks the shortfall was her first EMI taken in advance.")

# ======================================================================================
# coached (2): C016-C017
# ======================================================================================

add("coached", "hi", BOR(M),
    R("Omprakash", "Kritrim", "1966-02-11", "nbfc_b", "personal", 290000, 13950, 290000, 24, 24, True, False, 15, "otp", "2026-10-25"),
    S("You are Omprakash, born 1966. (An invented person.) You run a cycle repair shop.",
      "About three weeks ago you took a personal loan of two lakh ninety thousand from a finance company to rebuild your shop's shutter and counter. The agent at the branch said a life cover 'costs only nine thousand', took your phone and typed in the OTP himself. He told you: a call will come from the company; just say you understood everything and chose it yourself.",
      ["The agent told you that when the company calls, you should say you understood everything and chose it yourself.",
       "It is a life cover on the loan.",
       "It cost nine thousand; that is what the agent said, and you believe him.",
       "It was cut from the loan money, one time.",
       "It was your choice; the agent said you could take it from anywhere.",
       "It runs as long as the loan.",
       "The money does not come back.",
       "You agreed with an OTP that came on your phone; the agent typed it in himself."],
      ["Up to what amount it covers.",
       "Whether it can be cancelled."],
      "Simple, agreeable, plain Hindi."),
    B(kind="insurance", premium_inr=9000, payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=False, told_could_take_elsewhere=True, term_months="as_long_as_loan",
      money_back="not_refundable", consent_method="otp", sale_concerns=["coached_answers"]),
    {"sale_conduct": "k0", "premium": "k2", "cover": "u0", "cancel_window": "u1"},
    notes="Premium: nine thousand against the record's thirteen thousand nine hundred fifty, more than 10% off. Term: 'as long as the loan' is 24 months on the record, equal to the term.",
    why="Coached to say he understood and chose it; believes the premium was nine thousand.")

add("coached", "hi-en", BOR(F),
    R("Sarita", "Abhyasi", "1989-09-07", "bank_a", "personal", 640000, 35200, 640000, 48, 48, True, False, 30, "digital_click", "2026-11-01"),
    S("You are Sarita, born 1989. (An invented person.) You are a store manager at a supermarket.",
      "Less than two weeks ago you took a personal loan of six lakh forty thousand from your bank for your flat's interiors. The relationship manager filled the whole application on his tablet at your workplace and then had you sign a printed form. Later he sent you a WhatsApp message: when the bank's call comes, just say yes, you read and understood everything.",
      ["The relationship manager told you on WhatsApp: when the bank calls, say yes, you read and understood everything.",
       "It is some life insurance with the loan.",
       "You agreed by signing a printed form he brought; you did not click anything yourself.",
       "It runs four years, like the loan."],
      ["How much it cost.",
       "Whether it was cut from the loan or paid some other way.",
       "Whether it is one payment.",
       "Whether it was needed, or whether you could take it elsewhere.",
       "Up to what amount it covers.",
       "Whether it can be cancelled.",
       "Whether any money comes back."],
      "Busy, direct, Hindi mixed with English."),
    B(kind="insurance", term_months=48, consent_method="signed_form", sale_concerns=["coached_answers"]),
    {"sale_conduct": "k0", "consent": "k2", "loan_funded": "u1", "premium": "u0", "payment_frequency": "u2",
     "cover": "u4", "cancel_window": "u5", "belief_mismatch": "u6"},
    notes="Consent: she names a signed form; the record holds a digital click. Payment source not known with the record saying paid from the loan: loan_funded refer.",
    why="Coached to say she understood; names a signed form against a digital click and knows little else.")

# ======================================================================================
# in_a_hurry (1): C018 (misled)
# ======================================================================================

add("in_a_hurry", "hi-en", BOR(F),
    R("Nirmala", "Pratiroop", "1985-12-01", "nbfc_a", "gold", 330000, 14520, 330000, 12, 12, True, False, 15, "signed_form", "2026-10-28"),
    S("You are Nirmala, born 1985. (An invented person.) You are a medical representative who visits doctors all day.",
      "Two weeks ago you took a gold loan of three lakh thirty thousand from a finance company to clear a car loan. The executive said an accident cover is needed with the gold loan, and that it pays one lakh if you die in an accident. You signed its form with the loan papers.",
      ["It is an accident insurance.",
       "It pays one lakh if you die in an accident; the executive said so.",
       "It was fourteen and a half thousand, cut from the loan.",
       "One payment.",
       "The executive said it was needed with the gold loan; nothing was said about any other company.",
       "It runs one year, like the loan.",
       "The money does not come back.",
       "You signed its form."],
      ["Whether it can be cancelled."],
      "Fast, clipped, Hindi mixed with English.",
      "You are in a clinic's waiting room between two doctors. You agree to talk but ask them to finish fast, and keep every answer very short."),
    B(kind="insurance", premium_inr=14500, payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=True, told_could_take_elsewhere=False, cover_inr=100000, term_months=12,
      money_back="not_refundable", consent_method="signed_form"),
    {"cover": "k1", "bundling": "k4", "cancel_window": "u0"},
    notes="Premium: fourteen and a half thousand is within 1% of the record's fourteen thousand five hundred twenty. 'Nothing said about any other company' with 'needed' read as told it was required and not told it could be taken elsewhere.",
    why="In a hurry; believes it is a required accident cover paying one lakh, against a life cover of the loan amount.",
    underlying="misled")

# ======================================================================================
# fraud_suspicion (1): C019 (ordinary_informed)
# ======================================================================================

add("fraud_suspicion", "hi", BOR(M),
    R("Kunal", "Kritrim", "1980-04-18", "bank_b", "gold", 410000, 19270, 410000, 12, 12, True, False, 15, "recorded_call", "2026-11-04"),
    S("You are Kunal, born 1980. (An invented person.) You are a grain trader in a mandi town.",
      "Last week you took a gold loan of four lakh ten thousand from the bank to pay farmers for a harvest purchase. The officer explained a loan life cover and you took it. The bank then phoned, said the call was recorded, and you said yes to it.",
      ["It is a life cover on the gold loan.",
       "It cost nineteen thousand two hundred seventy, cut from the loan money.",
       "One payment.",
       "It was your choice; the officer said any company's cover would do.",
       "It covers four lakh ten thousand.",
       "It runs one year, like the loan.",
       "You believe it can be cancelled within seven days.",
       "The money does not come back.",
       "You said yes on the bank's recorded call.",
       "Your cousin lost money to a fake 'bank KYC' call this year, so you are careful with unknown callers."],
      ["Nothing else important."],
      "Wary at first, then plain and cooperative, plain Hindi.",
      "First you ask who is calling and how you can know this is really from the bank and not a fraud. If told how to check, you agree to go on."),
    B(kind="insurance", premium_inr=19270, payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=False, told_could_take_elsewhere=True, cover_inr=410000, term_months=12,
      cancel=cancel(True, 7), money_back="not_refundable", consent_method="recorded_call"),
    {"cancel_window": "k6"},
    why="Asks whether the call is genuine; knows what he bought but gives a seven-day cancel window against fifteen.",
    underlying="ordinary_informed")

# ======================================================================================
# third_party (2): C020-C021
# ======================================================================================

add("third_party", "hi", TP("father", M),
    R("Akhil", "Prayogik", "1997-05-23", "bank_a", "gold", 275000, 9625, 275000, 12, 12, True, True, 30, "signed_form", "2026-10-16"),
    S("You are Akhil's father, born 1965. (An invented person.) You retired as a clerk at a milk cooperative. Akhil is your son; the phone is his.",
      "Akhil has gone to another city for a two-week work training and left his old phone at home. It rang and you picked it up.",
      ["You are not Akhil; you say plainly that you are his father and he is away for work training.",
       "You know he took some loan from the bank recently.",
       "You do not know any details of his loan.",
       "His loan is his matter; if asked, you say so."],
      ["Anything he took with the loan, any amount, how he paid, what he signed.",
       "His exact date of birth; and you would not give it to a caller anyway."],
      "Courteous, unhurried, plain Hindi.",
      "You say right away that you are Akhil's father and he is away for work training until next week; you offer to tell him someone called."),
    why="Father answers and says plainly he is not the borrower.")

add("third_party", "hi-en", TP("flatmate", F),
    R("Leela", "Nakli", "1994-11-08", "nbfc_b", "gold", 85000, 3060, 85000, 6, 6, True, False, 15, "otp", "2026-11-02"),
    S("You are Leela's flatmate, born 1996. (An invented person.) You work at a travel agency. Leela shares a rented flat with you; the phone is hers.",
      "Leela is in the shower and her phone kept ringing on the dining table, so you picked it up.",
      ["You are not Leela.",
       "You know nothing about any loan of hers.",
       "Her money matters are hers, not yours to answer."],
      ["Any loan, any amount, anything she agreed to.",
       "Her year of birth."],
      "Friendly, curious, Hindi mixed with English.",
      "You do not say who you are at first. You say 'she is busy right now, what is it about? I can pass on a message', and ask what the call is for."),
    why="Flatmate answers, does not say who she is, and asks what the call is about.")

# ======================================================================================
# refusal (1): C022
# ======================================================================================

add("refusal", "hi-en", BOR(M),
    R("Zubin", "Abhyasi", "1978-07-30", "bank_b", "personal", 1200000, 69600, 1200000, 60, 60, True, False, 30, "signed_form", "2026-10-19"),
    S("You are Zubin, born 1978. (An invented person.) You run a small bakery and café.",
      "Nearly a month ago you took a personal loan of twelve lakh from the bank to renovate the café. The officer said a life cover goes with it and you signed its form. You have since arranged money from family and plan to close the loan early next month.",
      ["It is a life cover on the loan.",
       "It was around seventy thousand, cut from the loan.",
       "One payment.",
       "You signed its form.",
       "You plan to close the loan early next month, and you are fed up with calls from the bank."],
      ["What it covers, how long it runs, whether it can be cancelled, whether money comes back.",
       "What was said about other companies."],
      "Short-tempered, firm, Hindi mixed with English.",
      "You confirm who you are, but when asked if you can talk for a few minutes, you say you are closing this loan anyway and do not want any more calls about it, and refuse."),
    why="Refuses at 'can we talk': is closing the loan and wants no more calls.")

# ======================================================================================
# call_back_later (1): C023
# ======================================================================================

add("call_back_later", "hi", BOR(F),
    R("Sudha", "Pratiroop", "1960-03-14", "nbfc_a", "gold", 110000, 4290, 110000, 6, 6, True, False, 15, "otp", "2026-10-30"),
    S("You are Sudha, born 1960. (An invented person.) You are a retired anganwadi supervisor.",
      "Two weeks ago you pledged a gold chain at a finance company for a loan of one lakh ten thousand to pay for your grandson's coaching. The executive mentioned an insurance with the loan and you gave an OTP for it.",
      ["It is some insurance with the loan.",
       "It was about four thousand, cut from the loan.",
       "One payment.",
       "You gave an OTP for it."],
      ["What it covers, how long it runs, whether it can be cancelled, whether money comes back.",
       "Whether it was needed, or what was said about other companies."],
      "Polite, worried, plain Hindi.",
      "You are at a hospital with your husband, who has a high fever. You confirm who you are and ask them to call on Sunday morning, saying the day and time yourself."),
    why="At a hospital; asks to be called on Sunday morning.")

# ======================================================================================
# language_switch (1): C024
# ======================================================================================

add("language_switch", "hi-en", BOR(M),
    R("Venkatesh", "Kritrim", "1982-06-26", "nbfc_b", "personal", 460000, 22080, 460000, 36, 36, True, True, 30, "digital_click", "2026-10-21"),
    S("You are Venkatesh, born 1982. (An invented person.) You are a site engineer from Andhra Pradesh working on a project in a central Indian city; you speak Telugu at home.",
      "Three weeks ago you took a personal loan of four lakh sixty thousand in a finance company's app. A loan life cover was needed for the loan; the app said any insurer's would do, and you added theirs and clicked agree.",
      ["It is a loan life cover.",
       "It was twenty-two thousand something, cut from the loan.",
       "One payment.",
       "It was needed, but any insurer's would do.",
       "You agreed by clicking in the app."],
      ["What it covers, how long it runs, whether it can be cancelled, whether money comes back."],
      "Halting Hindi with English words; fluent in Telugu and English.",
      "You confirm who you are, then say in broken Hindi and some English that your Hindi is weak and ask whether they can talk in Telugu."),
    why="Asks to continue in Telugu.")

# ======================================================================================
# gold rules (eval/p5/gold-rules.md, table "Grounds"); copied unchanged from data/p5/build_customers.py
# ======================================================================================

MONEY_BACK_REFER = {"refundable_anytime", "withdrawable_after_period", "guaranteed_return", "is_deposit"}


def _dev(x, ref):
    return abs(x - ref) / ref


def grounds(b, p, tenure):
    """(refer rules, gap rules, undecided notes) for one product, from beliefs `b` and record product `p`."""
    refer, gap, undecided = [], [], []
    n = b["names_product_unprompted"]
    if n == "denies":
        refer.append("recall")
    elif n is False:
        gap.append("recall")
    if b["kind"] != "insurance":
        refer.append("kind")
    pr = b["premium_inr"]
    if pr == "dont_know":
        gap.append("premium")
    elif isinstance(pr, dict):
        worst = max(_dev(pr["low"], p["premium_inr"]), _dev(pr["high"], p["premium_inr"]))
        assert worst <= 0.10, ("range wider than 10%", pr)
        gap.append("premium")
    elif _dev(pr, p["premium_inr"]) > 0.10:
        refer.append("premium")
    elif _dev(pr, p["premium_inr"]) > 0.01:
        gap.append("premium")
    cv = b["cover_inr"]
    if cv in ("dont_know", "names_no_amount") or isinstance(cv, dict):
        gap.append("cover")
    elif _dev(cv, p["cover_inr"]) > 0.01:
        refer.append("cover")
    t = b["term_months"]
    if t == "as_long_as_loan":
        if tenure != p["term_months"]:
            gap.append("term")
    elif t != p["term_months"]:
        gap.append("term")
    c = b["cancel"]
    if not (c["allowed"] is True and c["window_days"] == p["cancel_window_days"]):
        gap.append("cancel_window")
    m = b["consent_method"]
    if m == "dont_know_how":
        undecided.append("consent: agreed but cannot say how")
    elif m in ("did_not_agree", "dont_know") or m != p["consent"]["method"]:
        refer.append("consent")
    src = b["payment_source"]
    if (p["paid_from_loan"] and src in ("separately", "dont_know")) or (not p["paid_from_loan"] and src == "from_loan"):
        refer.append("loan_funded")
    required = p["required_for_loan"] or b["required_for_loan"] is True
    if required:
        if (b["kind"] == "deposit" or b["told_could_take_elsewhere"] is False
                or not p["risk_mitigant"] or not p["provider_choice_offered"]):
            refer.append("bundling")
        elif b["told_could_take_elsewhere"] == "dont_know":
            undecided.append("bundling: required, but whether told it could be taken elsewhere is unknown")
    elif b["required_for_loan"] == "dont_know":
        undecided.append("bundling: does not know whether it was required")
    mb = b["money_back"]
    if b["kind"] == "deposit" or mb in MONEY_BACK_REFER:
        refer.append("belief_mismatch")
    elif mb == "dont_know":
        gap.append("belief_mismatch")
    if b["payment_frequency"] in ("recurring", "dont_know"):
        gap.append("payment_frequency")
    if b["sale_concerns"]:
        refer.append("sale_conduct")
    return refer, gap, undecided


RECORD_FIELD = {
    "premium": lambda p, t: f"premium_inr {p['premium_inr']}",
    "cover": lambda p, t: f"cover_inr {p['cover_inr']}",
    "term": lambda p, t: f"term_months {p['term_months']}, tenure_months {t}",
    "cancel_window": lambda p, t: f"cancel_window_days {p['cancel_window_days']}",
    "consent": lambda p, t: f"consent.method {p['consent']['method']}",
    "loan_funded": lambda p, t: f"paid_from_loan {str(p['paid_from_loan']).lower()}",
    "bundling": lambda p, t: f"required_for_loan {str(p['required_for_loan']).lower()}, provider_choice_offered true",
    "belief_mismatch": lambda p, t: "features [one_time_payment]",
    "payment_frequency": lambda p, t: "features [one_time_payment]",
}

# Took nothing: after a firm denial the caller asks one neutral follow-up, then only what the person agreed
# to (gold-rules reading kept from P5, CHANGELOG 2026-11-10). Both P5b took-nothing customers name the
# deduction as something else in that follow-up, so kind is reachable for both.
REACHABLE_WHEN_DENIED = {"P5B-C014": {"recall", "consent", "kind"}, "P5B-C015": {"recall", "consent", "kind"}}

OUTCOME = {"third_party": "wrong_party", "refusal": "declined", "call_back_later": "call_back_later",
           "language_switch": "language_switch"}

BANNED = ["tier", "refer", "flag", "rule", "mis-sell", "missell", "bundl", "risk mitigant", "consent record",
          "understanding_gap", "credit_life", "signed_form"]


def quote(sheet, key):
    if key == "h":
        return f'what_happened: "{sheet["what_happened"]}"'
    if key == "c":
        return f'on_this_call: "{sheet["on_this_call"]}"'
    lst = sheet["what_you_know"] if key[0] == "k" else sheet["what_you_do_not_know"]
    label = "what_you_know" if key[0] == "k" else "what_you_do_not_know"
    return f'{label}: "{lst[int(key[1:])]}"'


def build():
    assert len(C) == 24, len(C)
    customers, gold, records = [], [], {}
    check_log = []
    for i, c in enumerate(C, 1):
        cid, rid = f"P5B-C{i:03d}", f"p5b-c{i:03d}"
        r = c["rec"]
        premium = r["premium"]
        lender_type, lender_name = LENDERS[r["lender"]]
        product = {
            "id": "P1", "kind": "credit_life", "provider": PROVIDERS[r["surname"]],
            "premium_inr": premium, "cover_inr": r["cover"], "term_months": r["term"],
            "paid_from_loan": r["pfl"], "required_for_loan": r["req"], "risk_mitigant": True,
            "provider_choice_offered": True, "cancel_window_days": r["window"],
            "features": ["one_time_payment"], "consent": {"method": r["method"], "at": r["on"]},
        }
        year = r["dob"][:4]
        loan_word = "a gold loan" if r["loan"] == "gold" else "a personal loan"
        record = {
            "id": rid,
            "label": f"Synthetic P5b record. {r['first']}: {loan_word} and one add-on",
            "description": f"Synthetic P5b record. {r['first']}, born {year}, took {loan_word} with one add-on. For the P5b evaluation only.",
            "lender_name": lender_name,
            "record": {
                "loan_id": f"TEST-P5B-LN-{i:03d}", "lender_type": lender_type,
                "borrower": {"name": f"{r['first']} {r['surname']}", "dob": r["dob"], "language": c["language"]},
                "loan_kind": r["loan"], "sanctioned_inr": r["sanctioned"],
                "disbursed_inr": r["sanctioned"] - premium if r["pfl"] else r["sanctioned"],
                "disbursed_on": r["on"], "products": [product], "tenure_months": r["tenure"],
            },
        }
        CallRecord.model_validate(record)
        assert "2026-10-16" <= r["on"] <= "2026-11-09", cid
        assert 1958 <= int(year) <= 2001, cid
        assert 0.027 <= premium / r["sanctioned"] <= 0.13, (cid, premium / r["sanctioned"])
        records[rid] = record

        sheet = c["sheet"]
        text = json.dumps(list(sheet.values()), ensure_ascii=False)  # the values, not the field names
        for word in BANNED:
            assert word not in text.lower(), (cid, word)
        assert not re.search(r"\w_\w", text), (cid, "underscore word")
        assert not re.search(r"\d", " ".join(json.dumps(v, ensure_ascii=False) for k, v in sheet.items()
                                              if k != "you_are")), (cid, "a digit outside the birth year")
        assert "(An invented person.)" in sheet["you_are"], cid
        m = re.search(r"born (\d{4})", sheet["you_are"])
        if c["speaker"]["who"] == "borrower":
            assert m and m.group(1) == year, (cid, "year of birth")
        else:
            assert year not in text, (cid, "third party must not know the borrower's year")
        customers.append({"id": cid, "kind": c["kind"], "underlying": c["underlying"], "language": c["language"],
                          "record_id": rid, "speaker": c["speaker"], "fact_sheet": sheet})

        row = {"id": cid, "kind": c["kind"], "language": c["language"], "record_id": rid,
               "refer_grounds_from_record": []}
        if c["kind"] in OUTCOME:
            assert c["beliefs"] is None and not c["cite"]
            row.update({"class": "procedural", "expected_outcome": OUTCOME[c["kind"]], "expected_tier": None,
                        "refer_grounds_from_call": [], "gap_grounds": [], "beliefs": None,
                        "notes": c["notes"], "rationale": c["why"] + " The call should end at the opening."})
            if c["kind"] == "third_party":
                row["loan_must_not_be_named"] = True
            check_log.append(f"{cid} {c['kind']}: procedural, no grounds")
        else:
            b = c["beliefs"]
            refer, gap, undecided = grounds(b, product, r["tenure"])
            refer_all = set(refer)
            cited = c["cite"]
            assert set(cited) == set(refer) | set(gap), (cid, sorted(cited), sorted(refer), sorted(gap))
            check_log.append(f"{cid} {c['kind']}: fired refer={sorted(refer)} gap={sorted(gap)}"
                             f" == cited {sorted(cited)}" + (f"; undecided: {undecided}" if undecided else ""))

            def ground(rule):
                because = quote(sheet, cited[rule])
                if rule in RECORD_FIELD:
                    because += f"; record {RECORD_FIELD[rule](product, r['tenure'])}"
                return {"rule": rule, "because": because}

            klass = "problem" if refer else ("knowledge_gap_only" if gap else "no_problem")
            tier = "refer" if refer else ("understanding_gap" if gap else "clear")
            notes = " ".join(filter(None, [c["notes"], *(f"Undecided, no ground: {u}." for u in undecided)]))
            if cid in REACHABLE_WHEN_DENIED:
                # A firm denial ends the product questions: list only the grounds the short call reaches.
                keep = REACHABLE_WHEN_DENIED[cid]
                assert "recall" in refer and keep <= set(refer) | set(gap), cid
                dropped = [x for x in refer + gap if x not in keep]
                refer = [x for x in refer if x in keep]
                gap = [x for x in gap if x in keep]
                notes += " Not reachable when the denial stands: " + "; ".join(
                    f"{x} ({'refer' if x in refer_all else 'gap'}: {ground(x)['because']})" for x in dropped) + "."
                check_log.append(f"  {cid} reachable when the denial stands: refer={refer} gap={gap}")
            summary = (f"Refer on {', '.join(refer)}." if refer else "No refer ground.") + (
                f" Gaps on {', '.join(gap)}." if gap else " No gaps.")
            row.update({"class": klass, "expected_outcome": "completed", "expected_tier": tier,
                        "refer_grounds_from_call": [ground(x) for x in refer],
                        "gap_grounds": [ground(x) for x in gap], "beliefs": b, "notes": notes,
                        "rationale": f"{c['why']} {summary}"})
        gold.append(row)
    check_counts(customers, gold, records)
    check_fresh(customers, gold, records)
    return customers, gold, records, check_log


# Largest-remainder allocation of P5's 60 to 24 (quota = P5 count x 24/60), then each kind split by
# language: even kinds half and half; the six odd kinds' extra customer alternates hi, hi-en in P5's
# kind order (ordinary_informed hi, in_a_hurry hi-en, fraud_suspicion hi, refusal hi-en,
# call_back_later hi, language_switch hi-en).
P5_KINDS = {"misled": 14, "uninformed": 6, "ordinary_informed": 8, "well_informed": 6, "took_nothing": 4,
            "coached": 4, "in_a_hurry": 2, "fraud_suspicion": 2, "third_party": 6, "refusal": 3,
            "call_back_later": 3, "language_switch": 2}


def allocate(total=24):
    quota = {k: n * total / sum(P5_KINDS.values()) for k, n in P5_KINDS.items()}
    alloc = {k: int(q) for k, q in quota.items()}
    order = sorted(P5_KINDS, key=lambda k: (-(quota[k] - alloc[k]), list(P5_KINDS).index(k)))
    for k in order[:total - sum(alloc.values())]:
        alloc[k] += 1
    split, extra = {}, "hi"
    for k in P5_KINDS:
        n = alloc[k]
        hi = n // 2
        if n % 2:
            hi += extra == "hi"
            extra = "hi-en" if extra == "hi" else "hi"
        split[k] = {"hi": hi, "hi-en": n - hi}
    return quota, alloc, split


def check_counts(customers, gold, records):
    _, alloc, split = allocate()
    kinds = Counter(c["kind"] for c in customers)
    assert dict(kinds) == {k: n for k, n in alloc.items() if n}, kinds
    for kind, want in split.items():
        langs = Counter(c["language"] for c in customers if c["kind"] == kind)
        assert {"hi": langs["hi"], "hi-en": langs["hi-en"]} == want, (kind, langs, want)
    assert Counter(c["language"] for c in customers) == {"hi": 12, "hi-en": 12}
    g = {r["id"]: r for r in gold}
    assert set(g) == {c["id"] for c in customers} and set(records) == {c["record_id"] for c in customers}
    cls = lambda k: Counter(r["class"] for r in gold if r["kind"] == k)  # noqa: E731
    assert cls("misled") == {"problem": 6}
    assert cls("uninformed") == {"knowledge_gap_only": 1, "problem": 1}
    assert cls("ordinary_informed")["problem"] == 0
    assert all(r["expected_tier"] == "clear" for r in gold if r["kind"] == "well_informed")
    assert cls("took_nothing") == {"problem": 2} and cls("coached") == {"problem": 2}
    for c in customers:
        if c["underlying"] is not None:
            assert c["kind"] in ("in_a_hurry", "fraud_suspicion")
        if c["underlying"] == "misled":
            assert g[c["id"]]["class"] == "problem"
        if c["underlying"] == "ordinary_informed":
            assert g[c["id"]]["class"] != "problem"
    prods = [r["record"]["products"][0] for r in records.values()]
    assert 3 <= sum(not p["paid_from_loan"] for p in prods) <= 5
    assert sum(p["required_for_loan"] for p in prods) >= 3
    assert {p["consent"]["method"] for p in prods} == {"signed_form", "otp", "digital_click", "recorded_call"}
    assert Counter(p["cancel_window_days"] for p in prods) == {15: 12, 30: 12}
    assert Counter(r["record"]["lender_type"] for r in records.values()) == {"bank": 12, "nbfc": 12}
    assert len({r["lender_name"] for r in records.values()}) == 4
    assert all(r["lender_name"].startswith("नमूना ") for r in records.values())
    assert Counter(c["speaker"]["who"] for c in customers) == {"borrower": 22, "third_party": 2}


def check_fresh(customers, gold, records):
    """No P5 first name, sanctioned amount or premium; no P5 gold belief set; no repeat within P5b."""
    p5 = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((P5 / "records").glob("*.json"))]
    p5_first = {r["record"]["borrower"]["name"].split()[0] for r in p5}
    p5_sanctioned = {r["record"]["sanctioned_inr"] for r in p5}
    p5_premium = {r["record"]["products"][0]["premium_inr"] for r in p5}
    p5_surname = {r["record"]["borrower"]["name"].split()[1] for r in p5}
    assert len(p5_first) == 60
    mine = [r["record"] for r in records.values()]
    firsts = [r["borrower"]["name"].split()[0] for r in mine]
    assert len(set(firsts)) == 24 and not set(firsts) & p5_first, set(firsts) & p5_first
    assert not {r["borrower"]["name"].split()[1] for r in mine} & p5_surname
    for r in mine:
        p = r["products"][0]
        assert r["sanctioned_inr"] not in p5_sanctioned, (r["loan_id"], r["sanctioned_inr"])
        assert p["premium_inr"] not in p5_premium, (r["loan_id"], p["premium_inr"])
    assert len({r["sanctioned_inr"] for r in mine}) == 24 and len({r["products"][0]["premium_inr"] for r in mine}) == 24
    p5_beliefs = [json.dumps(row["beliefs"], sort_keys=True)
                  for row in map(json.loads, (P5 / "gold.jsonl").read_text(encoding="utf-8").splitlines())
                  if row["beliefs"] is not None]
    mine_b = [json.dumps(row["beliefs"], sort_keys=True) for row in gold if row["beliefs"] is not None]
    assert not set(mine_b) & set(p5_beliefs), "a P5b belief set equals a P5 one"
    assert len(set(mine_b)) == len(mine_b), "two P5b customers share a belief set"


def dump_line(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def main():
    customers, gold, records, check_log = build()
    (HERE / "customers.jsonl").write_text("".join(dump_line(x) + "\n" for x in customers), encoding="utf-8")
    (HERE / "gold.jsonl").write_text("".join(dump_line(x) + "\n" for x in gold), encoding="utf-8")
    rdir = HERE / "records"
    rdir.mkdir(exist_ok=True)
    for stale in rdir.glob("p5b-c*.json"):
        if stale.stem not in records:
            stale.unlink()
    for rid, rec in records.items():
        (rdir / f"{rid}.json").write_text(json.dumps(rec, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                                          encoding="utf-8")
    quota, alloc, split = allocate()
    print("allocation (P5 count -> quota -> P5b, hi/hi-en):")
    for k in P5_KINDS:
        print(f"  {k:18s} {P5_KINDS[k]:2d} -> {quota[k]:.1f} -> {alloc[k]} ({split[k]['hi']}/{split[k]['hi-en']})")
    print("grounds check (rules fired == rules cited):")
    for line in check_log:
        print("  " + line)
    print(f"wrote {len(customers)} customers, {len(gold)} gold rows, {len(records)} records")


if __name__ == "__main__":
    main()
