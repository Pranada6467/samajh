"""Build the 60 synthetic P5 customers: fact sheets, lender records and gold.

Run: uv run python data/p5/build_customers.py

Writes, deterministically:
  data/p5/customers.jsonl   one fact sheet per customer (the only thing the word-writer sees)
  data/p5/records/*.json    one CallRecord per customer
  data/p5/gold.jsonl        the gold row per customer, set by eval/p5/gold-rules.md

Every customer is hand-written below. Gold grounds are not typed by hand: each customer carries
its beliefs (the gold `beliefs` object) and a `cite` map naming, for each ground, the fact-sheet
line it rests on; `grounds()` applies the table of eval/p5/gold-rules.md to beliefs and record,
and the build fails unless the cited rules are exactly the rules that fire. All people, ids and
companies are invented.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from samajh.server.records import CallRecord  # noqa: E402  (validation only)

PROVIDERS = {
    "Namoona": "Namoona Life (synthetic)",
    "Udaharan": "Udaharan Suraksha (synthetic)",
    "Kalpanik": "Kalpanik Jeevan Bima (synthetic)",
    "Banawati": "Banawati Life Cover (synthetic)",
    "Pareekshan": "Pareekshan Insurance (synthetic)",
}
LENDER_NAME = {"bank": "नमूना बैंक", "nbfc": "नमूना फ़ाइनेंस"}


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


C = []  # (kind, underlying, language, speaker, record, sheet, beliefs, cite, notes, why)


def add(kind, lang, speaker, rec, sheet, beliefs=None, cite=None, notes="", why="", underlying=None):
    C.append(dict(kind=kind, underlying=underlying, language=lang, speaker=speaker, rec=rec, sheet=sheet,
                  beliefs=beliefs, cite=cite or {}, notes=notes, why=why))


M, F = "m", "f"
BOR = lambda g: {"who": "borrower", "relation": None, "gender": g}  # noqa: E731

# ======================================================================================
# misled (14): C001-C014
# ======================================================================================

# C001 FD for loan security
add("misled", "hi", BOR(M),
    R("Suresh", "Namoona", "1979-04-11", "bank", "gold", 400000, 41500, 400000, 24, 24, True, False, 30, "signed_form", "2026-10-14"),
    S("You are Suresh, born 1979. (An invented person.) You run a small hardware shop in a district town.",
      "Last month you pledged your wife's gold at the bank branch for a loan of four lakh, to buy stock before the festival season. The loan officer told you that you also had to open an FD with the bank as security for the loan. You signed the loan papers and the FD form at his desk.",
      ["The officer said the FD was needed or the loan would not be passed.",
       "About forty, forty-two thousand was kept back from the loan money for the FD.",
       "It was taken one time, from the loan money; nobody has asked you for more.",
       "You think of it as the bank's own FD; nobody said anything about getting it from somewhere else.",
       "You believe the FD stays as long as the loan runs, and when you close the loan you will take the FD money out.",
       "You signed the FD form along with the loan papers."],
      ["What exactly the FD gives you, or any amount it pays.",
       "Whether it can be cancelled, or by when.",
       "The exact amount kept back, to the rupee."],
      "Friendly and sure of himself, short answers, plain Hindi."),
    B(kind="deposit", premium_inr=rng(40000, 42000), payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=True, told_could_take_elsewhere=False, term_months="as_long_as_loan",
      money_back="withdrawable_after_period", consent_method="signed_form"),
    {"kind": "h", "bundling": "k0", "belief_mismatch": "k4", "premium": "k1", "cover": "u0",
     "cancel_window": "u1"},
    why="Believes the product is a bank FD he was told was needed for the loan and that he will take the money out at the end.")

# C002 security deposit, refund at gold release
add("misled", "hi-en", BOR(F),
    R("Kavita", "Udaharan", "1988-09-02", "nbfc", "gold", 250000, 18500, 250000, 12, 12, True, False, 15, "otp", "2026-10-21"),
    S("You are Kavita, born 1988. (An invented person.) You work as a receptionist at a private clinic in a city.",
      "Three weeks ago you took a gold loan of two and a half lakh from a finance company to pay your brother's college fees. The executive said a small security deposit is kept with every gold loan, and you get it back when you take your gold back. He asked for an OTP on your phone and said it was for the loan and the deposit, and you read it out to him.",
      ["The deposit was eighteen thousand five hundred; you saw that figure in the SMS.",
       "It was kept back from the loan money, one time.",
       "The executive said it is standard, everyone who takes a gold loan has it.",
       "Nobody told you that you could keep the deposit somewhere else; it is their own.",
       "You believe you get the full eighteen and a half thousand back when you release your gold, at the end of the loan.",
       "It is just kept with them; it does not give you anything.",
       "You gave the OTP for the loan and the deposit.",
       "You believe the deposit stays with them until the loan ends."],
      ["Whether it can be cancelled.",
       "What it is called on the papers."],
      "Polite, quick, a bit chatty, Hindi mixed with English words like 'deposit', 'OTP', 'loan amount'."),
    B(kind="deposit", premium_inr=18500, payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=True, told_could_take_elsewhere=False, cover_inr="names_no_amount",
      term_months="as_long_as_loan", money_back="withdrawable_after_period", consent_method="otp"),
    {"kind": "h", "bundling": "k2", "belief_mismatch": "k4", "cover": "k5", "cancel_window": "u0"},
    notes="'Standard, everyone has it' read as told required.",
    why="Believes she paid a refundable security deposit, told it was standard with every gold loan.")

# C003 FD with interest, five years
add("misled", "hi", BOR(M),
    R("Rajesh", "Kalpanik", "1965-01-23", "bank", "personal", 800000, 104000, 800000, 60, 60, True, False, 30, "signed_form", "2026-10-12"),
    S("You are Rajesh, born 1965. (An invented person.) You are a retired railway clerk in a small city.",
      "A month ago you took a personal loan of eight lakh from your bank for your daughter's wedding. The branch manager said the bank would put part of it in a fixed deposit in your name as loan security, and that it earns interest. You signed the forms he showed you.",
      ["One lakh four thousand went into the FD; you saw it in your passbook.",
       "It came out of the loan money, one time.",
       "The manager said the loan would not be sanctioned without it.",
       "He said it is with the bank's own scheme; nothing was said about any other place.",
       "You believe the FD runs for five years and earns about seven percent interest, and you get it back with interest.",
       "You think you could break the FD early if needed, with some penalty, like any FD.",
       "You signed the forms at the branch."],
      ["Anything it pays besides the interest.",
       "Any time limit for breaking it."],
      "Slow, careful, respectful, plain Hindi; repeats figures to be sure."),
    B(kind="deposit", premium_inr=104000, payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=True, told_could_take_elsewhere=False, term_months=60, cancel=cancel(True, "dont_know"),
      money_back="guaranteed_return", consent_method="signed_form"),
    {"kind": "h", "bundling": "k2", "belief_mismatch": "k4", "cover": "u0", "cancel_window": "u1"},
    why="Believes a lakh went into an interest-earning FD that was a condition of the loan.")

# C004 deposit refunded at end with interest, app click
add("misled", "hi-en", BOR(F),
    R("Pooja", "Banawati", "1993-06-30", "nbfc", "personal", 300000, 23600, 300000, 36, 24, True, False, 15, "digital_click", "2026-10-28"),
    S("You are Pooja, born 1993. (An invented person.) You are a software tester living in a rented flat in a big city.",
      "Two weeks ago you took a personal loan of three lakh through a finance company's app to repay a credit card. An agent called to help you finish the application and said there was a 'loan protection deposit' that is part of the loan and is refunded at the end with interest. You tapped 'I agree' on the screens in the app.",
      ["Around twenty-three, twenty-four thousand was taken for it from the loan amount before it came to your account.",
       "It was taken one time.",
       "You believe it runs till the loan ends, and then the deposit comes back to you with interest.",
       "You agreed by tapping 'I agree' in the app."],
      ["Whether it was needed for the loan; you did not ask.",
       "Whether you could have kept it anywhere else.",
       "What it covers or gives besides the interest.",
       "Whether it can be cancelled."],
      "Confident, quick, Hindi mixed with a lot of English."),
    B(kind="deposit", premium_inr=rng(23000, 24000), payment_source="from_loan", payment_frequency="one_time",
      term_months="as_long_as_loan", money_back="withdrawable_after_period", consent_method="digital_click"),
    {"kind": "h", "belief_mismatch": "k2", "premium": "k0", "term": "k2", "cover": "u2",
     "cancel_window": "u3"},
    notes="Term: 'till the loan ends' is 24 months on the record against a 36-month term, a gap.",
    why="Believes a refundable deposit with interest was taken from her loan.")

# C005 FD compulsory, recorded call, gold
add("misled", "hi", BOR(M),
    R("Mahesh", "Pareekshan", "1971-12-05", "bank", "gold", 180000, 7080, 180000, 12, 6, True, True, 30, "recorded_call", "2026-11-02"),
    S("You are Mahesh, born 1971. (An invented person.) You drive an auto-rickshaw in a mid-sized town.",
      "Last week you took a gold loan of one lakh eighty thousand from the bank against your gold chain to repair your auto. The clerk said an FD for loan security is compulsory with this loan. Before the money came, someone from the bank phoned, said the call was being recorded, and asked you to say yes to the loan and the FD, and you said yes.",
      ["About seven thousand was kept for the FD from the loan money.",
       "It was one time.",
       "The clerk said it is compulsory and it has to be the bank's own FD.",
       "You believe the FD money comes back to you with your gold when you repay the loan.",
       "You said yes on the bank's recorded phone call."],
      ["How long the FD runs exactly.",
       "Whether it can be cancelled.",
       "What it gives you, or up to what amount."],
      "Short, a bit tired, plain Hindi, says 'haan ji' a lot."),
    B(kind="deposit", premium_inr=7000, payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=True, told_could_take_elsewhere=False, money_back="is_deposit",
      consent_method="recorded_call"),
    {"kind": "h", "bundling": "k2", "belief_mismatch": "k3", "premium": "k0", "cover": "u2", "term": "u0",
     "cancel_window": "u1"},
    why="Believes it is a compulsory bank FD that returns with his gold.")

# C006 insurance plan, withdraw after a year with bonus
add("misled", "hi-en", BOR(M),
    R("Arjun", "Namoona", "1990-03-17", "nbfc", "personal", 500000, 32400, 500000, 36, 36, True, False, 30, "otp", "2026-10-19"),
    S("You are Arjun, born 1990. (An invented person.) You are a sales executive at a car showroom.",
      "Three weeks ago you took a personal loan of five lakh from a finance company to buy furniture for your new flat. The agent said you could also take an insurance plan with it that works like savings: after one year you can withdraw the money with a bonus. You liked that and gave the OTP he asked for to add it.",
      ["It is an insurance plan.",
       "It was thirty-two thousand something; it was cut from the loan amount.",
       "One payment, at the start.",
       "It was your own choice; nobody forced you.",
       "If something happens to you, your family gets something from it.",
       "It runs as long as the loan runs.",
       "You believe after one year you can withdraw the money with a bonus.",
       "You agreed by giving the OTP."],
      ["The exact amount it pays your family.",
       "Whether you can cancel it, or by when.",
       "What you were told about taking it elsewhere; the topic never came up."],
      "Talkative, upbeat, Hindi mixed with English."),
    B(kind="insurance", premium_inr=rng(32000, 33000), payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=False, told_could_take_elsewhere="not_applicable", cover_inr="names_no_amount",
      term_months="as_long_as_loan", money_back="withdrawable_after_period", consent_method="otp"),
    {"belief_mismatch": "k6", "premium": "k1", "cover": "k4", "cancel_window": "u1"},
    why="Knows it is insurance but believes it can be withdrawn with a bonus after a year.")

# C007 insurance, money back any time
add("misled", "hi", BOR(F),
    R("Geeta", "Udaharan", "1962-08-14", "bank", "gold", 200000, 9800, 200000, 12, 6, True, False, 15, "signed_form", "2026-10-24"),
    S("You are Geeta, born 1962. (An invented person.) You are a homemaker in a small town; your son works in another city.",
      "Two weeks ago you took a gold loan of two lakh from the bank for your house roof. The bank lady said there was a small insurance with it and that the money is like kept with the bank: you can take it back any time you want. You signed the paper for it.",
      ["It is some insurance.",
       "It was nine thousand eight hundred, cut from the loan money.",
       "It was your choice; she said it is good to have.",
       "You believe you can cancel it and take the money back whenever you want.",
       "You signed a paper for it at the bank."],
      ["Whether more money will be taken for it later.",
       "What it gives, or how much.",
       "How long it runs.",
       "What she said about other companies; you do not remember any such talk."],
      "Warm, slow, a little unsure with numbers but sure of this one, plain Hindi."),
    B(kind="insurance", premium_inr=9800, payment_source="from_loan", required_for_loan=False,
      cancel=cancel(True, "dont_know"), money_back="refundable_anytime", consent_method="signed_form"),
    {"belief_mismatch": "k3", "cancel_window": "k3", "payment_frequency": "u0", "cover": "u1", "term": "u2"},
    notes="'Cancel whenever you want' read as allowed with a window other than 15 days (window_days dont_know).",
    why="Believes the insurance money can be taken back at any time.")

# C008 thinks paid separately each year, not cut
add("misled", "hi-en", BOR(M),
    R("Vikram", "Kalpanik", "1985-11-09", "nbfc", "personal", 400000, 14750, 400000, 24, 36, True, False, 30, "digital_click", "2026-10-30"),
    S("You are Vikram, born 1985. (An invented person.) You own a small mobile repair shop.",
      "Ten days ago you took a personal loan of four lakh from a finance company's app to expand your shop. In the app there was a loan insurance screen; you ticked it and clicked agree. The agent on the phone said its premium is paid yearly, separately.",
      ["It is a loan insurance; if you die the loan gets paid off.",
       "It covers four lakh, the same as the loan.",
       "You believe it costs about fifteen thousand a year, which you will pay separately each year.",
       "You believe nothing was cut from the loan; you think the full loan came.",
       "It was your own choice.",
       "The app said you can cancel within thirty days.",
       "It is not savings; the premium does not come back.",
       "You agreed by clicking in the app."],
      ["How long it runs.",
       "What the agent said about other companies; you did not ask."],
      "Practical, sure, a little impatient, Hindi mixed with English."),
    B(kind="insurance", premium_inr=15000, payment_source="separately", payment_frequency="recurring",
      required_for_loan=False, told_could_take_elsewhere="dont_know", cover_inr=400000, cancel=cancel(True, 30),
      money_back="not_refundable", consent_method="digital_click"),
    {"loan_funded": "k3", "payment_frequency": "k2", "premium": "k2", "term": "u0"},
    why="Knows it is insurance but believes he pays it separately each year; the record says it was cut from the loan.")

# C009 believes paid separately in cash
add("misled", "hi", BOR(F),
    R("Sunaina", "Pareekshan", "1976-02-27", "bank", "personal", 200000, 11200, 200000, 24, 36, True, False, 15, "otp", "2026-10-17"),
    S("You are Sunaina, born 1976. (An invented person.) You run a tailoring business from your home.",
      "Three weeks ago you took a personal loan of two lakh from the bank for new sewing machines. The officer said there was an insurance on the loan. You paid some cash at the counter that day and you believe that was for the insurance. You gave an OTP on your phone when they asked.",
      ["It is an insurance on the loan.",
       "It was about eleven thousand.",
       "You believe you paid it separately, in cash at the counter.",
       "It was one payment.",
       "The officer said it was up to you; you said fine.",
       "You agreed by giving the OTP."],
      ["What it gives or up to what amount.",
       "How long it runs.",
       "Whether you can cancel it.",
       "Whether you could get the money back.",
       "What was said about buying it elsewhere."],
      "Busy, clear, polite, plain Hindi."),
    B(kind="insurance", premium_inr=11000, payment_source="separately", payment_frequency="one_time",
      required_for_loan=False, told_could_take_elsewhere="dont_know", consent_method="otp"),
    {"loan_funded": "k2", "premium": "k1", "cover": "u0", "term": "u1", "cancel_window": "u2",
     "belief_mismatch": "u3"},
    why="Believes she paid for the insurance separately in cash; the record says it was cut from the loan.")

# C010 told it is free
add("misled", "hi-en", BOR(M),
    R("Imran", "Banawati", "1983-07-19", "bank", "gold", 350000, 21000, 350000, 12, 12, True, False, 30, "signed_form", "2026-10-26"),
    S("You are Imran, born 1983. (An invented person.) You run a tea and snacks stall near a bus stand.",
      "Two weeks ago you took a gold loan of three and a half lakh from the bank to buy a second stall. The officer said an insurance comes free with the gold loan; the bank pays for it. You signed the papers, including one for the insurance.",
      ["It is an insurance that comes with the gold loan.",
       "You believe it was free; the bank pays for it.",
       "The loan money that came was a bit less, but you think that was processing charges.",
       "Nobody said it was needed for the loan; it just came free with it.",
       "If something happens, it covers something.",
       "It runs as long as the loan.",
       "You signed a paper for it with the loan papers."],
      ["Any amount paid for it: as far as you know nothing was paid, because it is free.",
       "Where any money for it came from: you think the bank pays, and the shortfall in the money you got was processing charges.",
       "Whether it is paid once or more.",
       "Up to what amount it covers.",
       "Whether it can be cancelled.",
       "Whether there is any money to get back.",
       "What was said about other companies; nothing that you recall."],
      "Cheerful, chatty, Hindi mixed with English."),
    B(kind="insurance", premium_inr="dont_know", payment_source="dont_know", payment_frequency="dont_know",
      required_for_loan=False, told_could_take_elsewhere="dont_know", cover_inr="names_no_amount",
      term_months="as_long_as_loan", consent_method="signed_form"),
    {"premium": "u0", "loan_funded": "u1", "payment_frequency": "u2", "cover": "k4", "cancel_window": "u4",
     "belief_mismatch": "u5"},
    notes="'Free, the bank pays' is not a figure anyone can read back: premium is not known (a gap). Payment source not known (he thinks the bank pays and the shortfall was processing charges), so loan_funded is a refer ground. ground set changed after the blind second labelling of 2026-11-10; see CHANGELOG.",
    why="Believes the insurance was free and does not know it was paid from his loan.")

# C011 learned from SMS, OTP thought for loan
add("misled", "hi", BOR(M),
    R("Dinesh", "Udaharan", "1968-05-08", "nbfc", "gold", 120000, 4350, 120000, 12, 6, True, False, 15, "otp", "2026-11-04"),
    S("You are Dinesh, born 1968. (An invented person.) You are a vegetable wholesaler in a market town.",
      "A few days ago you took a gold loan of one lakh twenty thousand from a finance company to pay a supplier. You gave an OTP at the counter; you thought it was for the loan. The next day an SMS came saying a policy was issued with a premium of four thousand three hundred and fifty.",
      ["You learned of the policy only from the SMS, after the loan.",
       "The SMS said premium four thousand three hundred fifty.",
       "You only agreed to the loan; the OTP you gave was for the loan.",
       "From the SMS you understand it is some insurance policy."],
      ["Where the money for it came from.",
       "Whether it is one payment.",
       "Whether it was needed for the loan.",
       "Anything about other companies.",
       "What it gives, how long it runs, whether it can be cancelled.",
       "Whether the money can come back."],
      "Irritated about the SMS but not rude, plain Hindi, short sentences."),
    B(kind="insurance", premium_inr=4350, consent_method="did_not_agree", sale_concerns=["learned_after_sale"]),
    {"sale_conduct": "k0", "consent": "k2", "loan_funded": "u0", "payment_frequency": "u1", "cover": "u4",
     "term": "u4", "cancel_window": "u4", "belief_mismatch": "u5"},
    why="Learned of the policy from an SMS after the loan and says he agreed only to the loan.")

# C012 saw it in statement, applied only for loan
add("misled", "hi-en", BOR(F),
    R("Neha", "Kalpanik", "1995-10-21", "bank", "personal", 700000, 38900, 700000, 48, 60, True, False, 30, "digital_click", "2026-10-22"),
    S("You are Neha, born 1995. (An invented person.) You are a junior architect in a large city.",
      "Three weeks ago you applied in your bank's app for a personal loan of seven lakh for a course abroad deposit. You clicked through the screens quickly. Later, in the loan statement, you saw a line 'insurance premium thirty-eight thousand nine hundred'.",
      ["You found out about the insurance only from the loan statement, after the loan.",
       "The statement says thirty-eight thousand nine hundred, taken out of the loan amount.",
       "It shows once in the statement.",
       "From the statement you understand it is insurance.",
       "You applied only for the loan; you did not agree to any insurance."],
      ["Whether it was needed for the loan.",
       "Whether you could have taken it elsewhere.",
       "What it gives, up to what amount, how long it runs.",
       "Whether it can be cancelled.",
       "Whether you can get this money back; you would like to."],
      "Articulate, annoyed, Hindi mixed with English."),
    B(kind="insurance", premium_inr=38900, payment_source="from_loan", payment_frequency="one_time",
      consent_method="did_not_agree", sale_concerns=["learned_after_sale"]),
    {"sale_conduct": "k0", "consent": "k4", "cover": "u2", "term": "u2", "cancel_window": "u3",
     "belief_mismatch": "u4"},
    why="Learned of the insurance from her statement and says she applied only for the loan.")

# C013 compulsory, must be the company's tie-up insurer
add("misled", "hi", BOR(F),
    R("Rekha", "Banawati", "1981-04-03", "nbfc", "personal", 250000, 16400, 250000, 24, 24, True, True, 15, "signed_form", "2026-10-15"),
    S("You are Rekha, born 1981. (An invented person.) You teach at a private primary school.",
      "Last month you took a personal loan of two and a half lakh from a finance company for your mother's operation. The executive said a loan insurance is compulsory and it has to be from their own tie-up company; other insurance is not accepted. You signed the insurance form with the loan papers.",
      ["It is a loan insurance.",
       "It was about sixteen thousand, cut from the loan money.",
       "One payment.",
       "It was compulsory, and it had to be their company's; other insurance would not be accepted.",
       "It covers two and a half lakh, the loan amount.",
       "It runs as long as the loan.",
       "He said it cannot be cancelled once taken.",
       "It is not savings; nothing comes back.",
       "You signed the form for it."],
      ["The exact premium."],
      "Composed, precise, plain Hindi."),
    B(kind="insurance", premium_inr=16000, payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=True, told_could_take_elsewhere=False, cover_inr=250000, term_months="as_long_as_loan",
      cancel=cancel(False), money_back="not_refundable", consent_method="signed_form"),
    {"bundling": "k3", "premium": "k1", "cancel_window": "k6"},
    why="Told the insurance was compulsory and had to be the lender's tie-up company.")

# C014 compulsory and only this insurer, paid by cheque
add("misled", "hi-en", BOR(M),
    R("Sanjay", "Pareekshan", "1974-09-12", "bank", "personal", 1500000, 148000, 1500000, 60, 60, False, False, 30, "recorded_call", "2026-10-29"),
    S("You are Sanjay, born 1974. (An invented person.) You own a small printing press.",
      "Two weeks ago you took a personal loan of fifteen lakh from the bank for a new printing machine. The relationship manager said a life insurance on the loan was compulsory and only their partner company's would do. You paid it by a cheque from your current account. A bank person later called you, said it was recorded, and you said yes to it.",
      ["It is a life insurance on the loan.",
       "It cost one lakh fifty thousand.",
       "You paid it separately by cheque, one time.",
       "He said it was compulsory and only their partner company's insurance would do.",
       "It covers fifteen lakh.",
       "It runs five years.",
       "The premium does not come back; it is not savings.",
       "You said yes on the bank's recorded call."],
      ["Whether it can be cancelled."],
      "Businesslike, brisk, Hindi mixed with English."),
    B(kind="insurance", premium_inr=150000, payment_source="separately", payment_frequency="one_time",
      required_for_loan=True, told_could_take_elsewhere=False, cover_inr=1500000, term_months=60,
      money_back="not_refundable", consent_method="recorded_call"),
    {"bundling": "k3", "premium": "k1", "cancel_window": "u0"},
    why="Told the insurance was compulsory and only the partner company's would do; the record says it was optional.")

# ======================================================================================
# uninformed (6): C015-C020
# ======================================================================================

add("uninformed", "hi", BOR(F),
    R("Kamla", "Namoona", "1958-07-01", "bank", "gold", 80000, 2150, 80000, 12, 6, True, False, 15, "signed_form", "2026-10-13"),
    S("You are Kamla, born 1958. (An invented person.) You are a widow living with your son's family in a village near a town.",
      "Last month you pawned your bangles at the bank for eighty thousand to help with your grandson's school admission. Your son went with you. The officer gave papers and you signed where he showed, the loan paper and one more he said goes with it. Nobody explained what the second paper was.",
      ["A small amount was cut from the loan money for something.",
       "You signed the loan paper and one more paper the officer said goes with it.",
       "Nobody explained what the second paper was; you signed where he showed."],
      ["What that something is: maybe a charge, maybe insurance, you cannot say.",
       "How much was cut.",
       "Whether it is one time or more.",
       "Whether it was needed or what was said about it.",
       "What it gives, how long, whether it can be cancelled, whether money comes back.",
       "What you agreed to by signing the second paper."],
      "Soft, hesitant, plain Hindi, asks to repeat things."),
    B(names_product_unprompted=False, kind="dont_know", payment_source="from_loan", consent_method="dont_know",
      sale_concerns=["signed_without_explanation"]),
    {"recall": "k0", "kind": "u0", "premium": "u1", "payment_frequency": "u2", "cover": "u4", "term": "u4",
     "cancel_window": "u4", "belief_mismatch": "u4", "sale_conduct": "k2", "consent": "u5"},
    notes="'Something was cut' names nothing on the record and is not a denial: recall is a gap. She does not know what she agreed to by signing the second paper: consent refer. ground set changed after the blind second labelling of 2026-11-10; see CHANGELOG.",
    why="Knows something was cut from the loan but cannot say what it is.")

add("uninformed", "hi-en", BOR(M),
    R("Rohit", "Udaharan", "1997-12-18", "nbfc", "personal", 150000, 5900, 150000, 18, 12, True, False, 30, "digital_click", "2026-10-31"),
    S("You are Rohit, born 1997. (An invented person.) You are a delivery rider in a big city.",
      "Ten days ago you took a personal loan of one and a half lakh on a finance company's app to buy a new bike. You clicked 'I agree' on every screen to finish fast. There may have been some add-on screen; you are not sure.",
      ["The loan amount that came was a bit less than one and a half lakh; you do not know why.",
       "You clicked 'I agree' on every screen in the app without reading; you do not know what you agreed to."],
      ["Whether you took anything else; when first asked you cannot think of anything.",
       "What the add-on was, if there was one: some card, some protection, no idea.",
       "How much it was.",
       "Whether it is one payment, needed or not, from where it could be taken.",
       "What it gives, how long, whether it can be cancelled, whether money comes back.",
       "Why the money came short, or whether anything was cut from the loan for something."],
      "Casual, vague, Hindi mixed with English, says 'pata nahi yaar' style things."),
    B(names_product_unprompted=False, kind="dont_know", payment_source="dont_know",
      consent_method="dont_know"),
    {"recall": "u0", "kind": "u1", "premium": "u2", "payment_frequency": "u3", "cover": "u4", "term": "u4",
     "cancel_window": "u4", "belief_mismatch": "u4", "loan_funded": "u5", "consent": "k1"},
    notes="He knows the money came short but not why: payment source not known, so loan_funded is a refer ground. He does not know what he agreed to by clicking: consent refer. ground set changed after the blind second labelling of 2026-11-10; see CHANGELOG.",
    why="Names nothing when first asked and does not know what the add-on is.")

add("uninformed", "hi", BOR(M),
    R("Ramprasad", "Kalpanik", "1960-03-29", "bank", "personal", 100000, 3600, 100000, 12, 24, False, False, 15, "signed_form", "2026-10-16"),
    S("You are Ramprasad, born 1960. (An invented person.) You are a retired farmer who now runs a small flour mill.",
      "Last month you took a personal loan of one lakh from your bank to fix the mill motor. The bank man said there is some insurance with it. The money for it was taken from your savings account at the same bank, not from the loan.",
      ["It is some insurance; the bank man said so.",
       "It was taken from your savings account, separately, not from the loan.",
       "You signed a paper for it."],
      ["How much it was.",
       "Whether it is one time or every year.",
       "Whether it was needed or your choice; you just did what he said.",
       "What was said about other companies.",
       "What it gives, up to what amount, for how long.",
       "Whether it can be cancelled or the money comes back."],
      "Simple, honest, plain Hindi, says 'mujhe zyada nahi pata'."),
    B(kind="insurance", payment_source="separately", consent_method="signed_form"),
    {"premium": "u0", "payment_frequency": "u1", "cover": "u4", "term": "u4", "cancel_window": "u5",
     "belief_mismatch": "u5"},
    why="Knows it is insurance paid from his savings and that he signed for it; knows nothing else.")

add("uninformed", "hi-en", BOR(F),
    R("Anjali", "Banawati", "1992-05-25", "nbfc", "gold", 220000, 8640, 220000, 12, 6, True, False, 30, "otp", "2026-10-20"),
    S("You are Anjali, born 1992. (An invented person.) You are a beautician who works from a small parlour.",
      "Three weeks ago you took a gold loan of two lakh twenty thousand from a finance company to renovate the parlour. The executive mentioned some insurance and you said okay. You gave the OTP he asked for.",
      ["It is some insurance thing.",
       "They cut it from the loan amount.",
       "You agreed to it by giving the OTP."],
      ["How much it was; some thousands.",
       "Whether it is one time or more.",
       "Whether it was needed, or whether it could be taken from another company; you did not ask.",
       "What it gives, up to what amount, how long.",
       "Whether it can be cancelled, whether money comes back."],
      "Friendly, honest about not knowing, Hindi mixed with English."),
    B(kind="insurance", payment_source="from_loan", consent_method="otp"),
    {"premium": "u0", "payment_frequency": "u1", "cover": "u3", "term": "u3", "cancel_window": "u4",
     "belief_mismatch": "u4"},
    why="Knows it is insurance cut from the loan and that she agreed by OTP; knows nothing else.")

add("uninformed", "hi", BOR(F),
    R("Shanti", "Pareekshan", "1966-11-11", "nbfc", "personal", 120000, 6300, 120000, 24, 36, True, False, 15, "recorded_call", "2026-10-27"),
    S("You are Shanti, born 1966. (An invented person.) You sell sarees from home to neighbours.",
      "Two weeks ago you took a personal loan of one lakh twenty thousand from a finance company to buy stock. Before the money came someone called from the company, said the call is recorded, mentioned an insurance with the loan, and you said 'haan'.",
      ["It is an insurance with the loan.",
       "It was cut from the loan money.",
       "You said yes to it on that recorded phone call."],
      ["How much; some thousands, you do not recall.",
       "Whether it is one time.",
       "Whether it was needed or what was said about other companies.",
       "What it gives, up to what amount, how long it runs.",
       "Whether it can be cancelled or the money comes back."],
      "Chatty, warm, unsure of details, plain Hindi."),
    B(kind="insurance", payment_source="from_loan", consent_method="recorded_call"),
    {"premium": "u0", "payment_frequency": "u1", "cover": "u3", "term": "u3", "cancel_window": "u4",
     "belief_mismatch": "u4"},
    why="Knows it is insurance cut from the loan and that she said yes on a recorded call; knows nothing else.")

add("uninformed", "hi-en", BOR(M),
    R("Karan", "Namoona", "1999-01-14", "bank", "personal", 300000, 12600, 300000, 36, 36, True, False, 30, "digital_click", "2026-10-23"),
    S("You are Karan, born 1999. (An invented person.) You work at a call centre on night shifts.",
      "Two weeks ago you took a personal loan of three lakh in your bank's app for a laptop and to clear some dues. There was a life insurance checkbox with the loan and you ticked it and clicked agree.",
      ["It is a life insurance with the loan.",
       "It came out of the loan amount.",
       "You ticked the box and clicked agree in the app."],
      ["How much it was; maybe ten, maybe fifteen thousand, you really cannot say.",
       "Whether it is one time or monthly.",
       "Whether it was needed or optional, or whether another company's would do; you did not read.",
       "What it gives or up to what amount, how long.",
       "Whether you can cancel or get money back."],
      "Sleepy, relaxed, Hindi mixed with English."),
    B(kind="insurance", payment_source="from_loan", consent_method="digital_click"),
    {"premium": "u0", "payment_frequency": "u1", "cover": "u3", "term": "u3", "cancel_window": "u4",
     "belief_mismatch": "u4"},
    notes="'Maybe ten, maybe fifteen thousand' is too wide a range to compare: read as not knowing the amount.",
    why="Knows it is life insurance cut from the loan and agreed in the app; knows nothing else.")

# ======================================================================================
# ordinary_informed (8): C021-C028
# ======================================================================================

add("ordinary_informed", "hi", BOR(M),
    R("Mohan", "Udaharan", "1978-06-22", "bank", "gold", 300000, 15600, 300000, 12, 12, True, False, 30, "signed_form", "2026-10-18"),
    S("You are Mohan, born 1978. (An invented person.) You are a building contractor in a district town.",
      "Last month you took a gold loan of three lakh from the bank to pay your labour. The officer offered a loan insurance and explained it; you took it. You signed its form at the branch.",
      ["It is a loan insurance: if you die, the loan is paid off.",
       "It was around fifteen thousand, cut from the loan money.",
       "One payment.",
       "It was your choice; the officer said you could buy it from any company.",
       "It covers three lakh, the loan amount.",
       "It runs as long as the loan.",
       "There are some days to cancel it, maybe fifteen, maybe thirty.",
       "The money does not come back; it is not savings.",
       "You signed its form."],
      ["The exact premium.",
       "The exact cancel days."],
      "Steady, matter-of-fact, plain Hindi."),
    B(kind="insurance", premium_inr=15000, payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=False, told_could_take_elsewhere=True, cover_inr=300000, term_months="as_long_as_loan",
      cancel=cancel(True, "dont_know"), money_back="not_refundable", consent_method="signed_form"),
    {"premium": "k1", "cancel_window": "k6"},
    why="Knows what he bought; amount rough and cancel days unsure.")

add("ordinary_informed", "hi-en", BOR(F),
    R("Priya", "Kalpanik", "1987-08-08", "nbfc", "personal", 500000, 27500, 500000, 36, 36, True, True, 15, "otp", "2026-10-25"),
    S("You are Priya, born 1987. (An invented person.) You are an HR executive at a mid-sized company.",
      "Two weeks ago you took a personal loan of five lakh from a finance company for a car down payment. The executive said loan insurance is needed for this loan, but you could take it from any company and give the papers; you chose theirs because it was easier. You gave an OTP to confirm it.",
      ["It is a loan insurance.",
       "It was twenty-seven, twenty-eight thousand, cut from the loan.",
       "One payment.",
       "It was needed for the loan, but you were told you could take it from any company.",
       "If something happens to you, it pays off whatever loan is left.",
       "It runs as long as the loan.",
       "You can cancel it within some days.",
       "It is not savings; the money does not come back.",
       "You agreed by OTP."],
      ["The exact premium.",
       "The exact amount it pays.",
       "How many days you have to cancel."],
      "Organised, polite, Hindi mixed with English."),
    B(kind="insurance", premium_inr=rng(27000, 28000), payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=True, told_could_take_elsewhere=True, cover_inr="names_no_amount",
      term_months="as_long_as_loan", cancel=cancel(True, "dont_know"), money_back="not_refundable",
      consent_method="otp"),
    {"premium": "k1", "cover": "k4", "cancel_window": "k6"},
    notes="Cover 'pays off whatever loan is left' names no amount: read as a cover gap.",
    why="Required product, but she was told she could take it anywhere; amounts rough, cancel days unknown.")

add("ordinary_informed", "hi", BOR(M),
    R("Ashok", "Banawati", "1970-10-30", "bank", "personal", 200000, 9400, 200000, 24, 24, False, False, 30, "recorded_call", "2026-11-01"),
    S("You are Ashok, born 1970. (An invented person.) You are a government school peon nearing retirement.",
      "Last week you took a personal loan of two lakh from your bank to repair your house. The officer explained a life cover on the loan; you agreed and paid it yourself by UPI from your own account. Then someone from the bank called, said it was recorded, and you said yes.",
      ["It is a life cover on the loan.",
       "It was nine and a half thousand, you think.",
       "You paid it by UPI from your own account, one time.",
       "It was your choice; he said any company's would do.",
       "It covers two lakh.",
       "It runs two years.",
       "You can cancel it within thirty days.",
       "The money does not come back.",
       "You said yes on the bank's recorded call."],
      ["The premium to the rupee."],
      "Respectful, a little slow, plain Hindi."),
    B(kind="insurance", premium_inr=9500, payment_source="separately", payment_frequency="one_time",
      required_for_loan=False, told_could_take_elsewhere=True, cover_inr=200000, term_months=24,
      cancel=cancel(True, 30), money_back="not_refundable", consent_method="recorded_call"),
    {"premium": "k1"},
    why="Knows everything except the premium, which he gives about 1% high.")

add("ordinary_informed", "hi-en", BOR(M),
    R("Farhan", "Pareekshan", "1989-02-02", "nbfc", "gold", 150000, 5250, 150000, 12, 6, True, False, 15, "digital_click", "2026-10-16"),
    S("You are Farhan, born 1989. (An invented person.) You run a small online clothes reselling business.",
      "Three weeks ago you took a six-month gold loan of one and a half lakh from a finance company's app for stock. The app showed a loan insurance option with its details; you selected it and clicked agree.",
      ["It is a loan insurance.",
       "It was about five thousand, cut from the loan.",
       "One payment.",
       "It was optional; the app said you could use your own insurer.",
       "It covers one and a half lakh.",
       "You think it runs as long as the loan.",
       "The money does not come back.",
       "You agreed by clicking in the app."],
      ["Whether it can be cancelled, or within how many days."],
      "Quick, casual, Hindi mixed with English."),
    B(kind="insurance", premium_inr=5000, payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=False, told_could_take_elsewhere=True, cover_inr=150000, term_months="as_long_as_loan",
      money_back="not_refundable", consent_method="digital_click"),
    {"premium": "k1", "term": "k5", "cancel_window": "u0"},
    notes="Term: 'as long as the loan' is 6 months on the record against a 12-month term, a gap.",
    why="Knows what he bought; amount rough, term mismatched to the loan, cancel unknown.")

add("ordinary_informed", "hi", BOR(F),
    R("Lata", "Namoona", "1973-12-12", "nbfc", "personal", 350000, 19950, 350000, 36, 36, True, False, 30, "signed_form", "2026-10-19"),
    S("You are Lata, born 1973. (An invented person.) You run a small grocery shop with your husband.",
      "Three weeks ago you took a personal loan of three and a half lakh from a finance company to buy a freezer and stock. The executive explained a life insurance on the loan and you took it. You signed its form.",
      ["It is a life insurance on the loan.",
       "It was nineteen thousand something, cut from the loan money.",
       "One payment.",
       "It was your choice; he said you could take it from another company too.",
       "It runs three years, same as the loan.",
       "You can cancel within a month.",
       "It does not give money back; it is not savings.",
       "You signed its form."],
      ["Up to what amount it pays."],
      "Practical, a little hurried, plain Hindi."),
    B(kind="insurance", premium_inr=rng(19000, 20000), payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=False, told_could_take_elsewhere=True, term_months=36, cancel=cancel(True, 30),
      money_back="not_refundable", consent_method="signed_form"),
    {"premium": "k1", "cover": "u0"},
    notes="'Within a month' read as 30 days.",
    why="Knows what she bought; amount as a range, cover unknown.")

add("ordinary_informed", "hi-en", BOR(F),
    R("Swati", "Udaharan", "1991-04-16", "bank", "gold", 450000, 23400, 450000, 24, 12, False, False, 15, "otp", "2026-11-03"),
    S("You are Swati, born 1991. (An invented person.) You work as an assistant in a chartered accountant's office in a city.",
      "Last week you took a gold loan of four and a half lakh from the bank for your sister's wedding. The officer explained a loan insurance; you took it and paid it from your own account by net banking. You confirmed it with an OTP.",
      ["It is a loan insurance.",
       "It was twenty-three thousand four hundred; you paid it by net banking yourself.",
       "One payment.",
       "It was your choice; he said you could buy it from any insurer.",
       "It covers somewhere around four to four and a half lakh.",
       "You can cancel it within fifteen days.",
       "The money does not come back.",
       "You confirmed it with an OTP."],
      ["How long it runs: one year or two, you do not remember."],
      "Precise about money, relaxed otherwise, Hindi mixed with English."),
    B(kind="insurance", premium_inr=23400, payment_source="separately", payment_frequency="one_time",
      required_for_loan=False, told_could_take_elsewhere=True, cover_inr=rng(400000, 450000),
      cancel=cancel(True, 15), money_back="not_refundable", consent_method="otp"),
    {"cover": "k4", "term": "u0"},
    why="Knows what she bought; cover as a range and term unknown.")

add("ordinary_informed", "hi", BOR(M),
    R("Prakash", "Kalpanik", "1964-09-04", "bank", "personal", 250000, 10750, 250000, 24, 24, True, False, 30, "signed_form", "2026-10-21"),
    S("You are Prakash, born 1964. (An invented person.) You run a photocopy and stationery shop near a college.",
      "Three weeks ago you took a personal loan of two and a half lakh from your bank for your son's coaching fees. The officer explained a life cover on the loan and said it was up to you; you took it and signed the form.",
      ["It is a life cover on the loan.",
       "It cost ten, eleven thousand, cut from the loan money.",
       "One payment.",
       "It was your choice; he said you could take it from anywhere.",
       "It covers two and a half lakh.",
       "It runs as long as the loan.",
       "It can be cancelled, there is a month or so.",
       "The money does not come back.",
       "You signed the form."],
      ["The exact premium.",
       "The exact number of days to cancel."],
      "Calm, slightly formal, plain Hindi."),
    B(kind="insurance", premium_inr=rng(10000, 11000), payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=False, told_could_take_elsewhere=True, cover_inr=250000, term_months="as_long_as_loan",
      cancel=cancel(True, "dont_know"), money_back="not_refundable", consent_method="signed_form"),
    {"premium": "k1", "cancel_window": "k6"},
    notes="'A month or so' is hedged: read as not knowing the exact window.",
    why="Knows what he bought; amount as a range and the cancel window hedged.")

add("ordinary_informed", "hi-en", BOR(M),
    R("Nitin", "Banawati", "1986-01-28", "nbfc", "gold", 200000, 7900, 200000, 12, 12, True, False, 15, "recorded_call", "2026-10-29"),
    S("You are Nitin, born 1986. (An invented person.) You are a gym trainer.",
      "Two weeks ago you took a gold loan of two lakh from a finance company to buy gym equipment. They offered a loan insurance; you agreed. Before disbursal they called you, said the call is recorded, and you said yes to it.",
      ["It is a loan insurance.",
       "It was eight thousand, cut from the loan.",
       "One payment.",
       "It was optional; they said any insurer would do.",
       "It covers two lakh.",
       "It runs one year.",
       "You can cancel within fifteen days.",
       "You said yes on their recorded call."],
      ["Whether you would get any money back if you wanted; you don't think so, but you are not sure."],
      "Energetic, short answers, Hindi mixed with English."),
    B(kind="insurance", premium_inr=8000, payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=False, told_could_take_elsewhere=True, cover_inr=200000, term_months=12,
      cancel=cancel(True, 15), money_back="dont_know", consent_method="recorded_call"),
    {"premium": "k1", "belief_mismatch": "u0"},
    why="Knows what he bought; amount about 1% high and unsure whether money comes back.")

# ======================================================================================
# well_informed (6): C029-C034
# ======================================================================================

add("well_informed", "hi", BOR(F),
    R("Meena", "Pareekshan", "1980-05-05", "bank", "gold", 500000, 26000, 500000, 24, 24, True, False, 30, "signed_form", "2026-10-20"),
    S("You are Meena, born 1980. (An invented person.) You run a small catering business.",
      "Three weeks ago you took a gold loan of five lakh from the bank for catering equipment. The officer explained a loan life insurance, gave you its leaflet, and you read it before taking it. You signed its form at the branch.",
      ["It is a life insurance on the loan: if you die, it pays off the loan.",
       "It cost twenty-six thousand, taken from the loan money.",
       "One payment only.",
       "It was your own choice; the officer said you could take it from any company.",
       "It covers five lakh.",
       "It runs two years.",
       "You can cancel it within thirty days.",
       "The premium does not come back; it is not savings.",
       "You signed its form at the branch."],
      ["Nothing important; the leaflet covered it."],
      "Confident, clear, plain Hindi."),
    B(kind="insurance", premium_inr=26000, payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=False, told_could_take_elsewhere=True, cover_inr=500000, term_months=24,
      cancel=cancel(True, 30), money_back="not_refundable", consent_method="signed_form"),
    why="States every fact as on the record.")

add("well_informed", "hi-en", BOR(M),
    R("Aditya", "Namoona", "1994-07-07", "nbfc", "personal", 600000, 33750, 600000, 48, 36, False, False, 15, "digital_click", "2026-10-24"),
    S("You are Aditya, born 1994. (An invented person.) You are a data analyst at a logistics firm.",
      "Two weeks ago you took a personal loan of six lakh in a finance company's app to clear a family debt. The app showed a loan life cover with its terms; you read them, chose it, and clicked agree. You paid its premium yourself by UPI.",
      ["It is a life insurance cover: if you die, it pays.",
       "The premium was thirty-three thousand seven hundred fifty.",
       "You paid it separately by UPI, one time.",
       "It was optional; the app said you could use any insurer.",
       "It covers six lakh.",
       "It runs four years, longer than the loan.",
       "You can cancel within fifteen days.",
       "The premium does not come back.",
       "You agreed by clicking in the app."],
      ["Nothing important."],
      "Precise, quick, Hindi mixed with English."),
    B(kind="insurance", premium_inr=33750, payment_source="separately", payment_frequency="one_time",
      required_for_loan=False, told_could_take_elsewhere=True, cover_inr=600000, term_months=48,
      cancel=cancel(True, 15), money_back="not_refundable", consent_method="digital_click"),
    why="States every fact as on the record, including a term longer than the loan.")

add("well_informed", "hi", BOR(M),
    R("Gopal", "Udaharan", "1959-10-10", "bank", "personal", 400000, 22800, 400000, 36, 36, True, True, 30, "recorded_call", "2026-10-15"),
    S("You are Gopal, born 1959. (An invented person.) You are a retired school headmaster.",
      "Last month you took a personal loan of four lakh from your bank for medical bills. The officer said a loan life insurance is needed for this loan, but that you could buy it from any company you like; you chose the bank's partner. The bank then called you, said the call was recorded, read out the details, and you said yes.",
      ["It is a life insurance on the loan; if you die it clears the loan.",
       "The premium was twenty-two thousand eight hundred, taken from the loan money.",
       "One payment.",
       "It was needed for the loan, but you could take it from any company.",
       "It covers four lakh.",
       "It runs as long as the loan, three years.",
       "You can cancel within thirty days.",
       "The money does not come back; it is not a deposit.",
       "You said yes on the bank's recorded call."],
      ["Nothing important."],
      "Measured, polite, plain Hindi."),
    B(kind="insurance", premium_inr=22800, payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=True, told_could_take_elsewhere=True, cover_inr=400000, term_months=36,
      cancel=cancel(True, 30), money_back="not_refundable", consent_method="recorded_call"),
    why="States every fact as on the record; required, with a free choice of insurer.")

add("well_informed", "hi-en", BOR(F),
    R("Ritu", "Kalpanik", "1984-02-14", "bank", "gold", 240000, 6960, 240000, 12, 12, False, False, 15, "otp", "2026-10-27"),
    S("You are Ritu, born 1984. (An invented person.) You are a pharmacist at a chemist shop.",
      "Two weeks ago you took a gold loan of two lakh forty thousand from the bank for your son's admission. The officer explained a loan life insurance; you took it, paid it yourself by UPI, and confirmed with an OTP.",
      ["It is a life insurance on the loan.",
       "It cost six thousand nine hundred sixty; you paid it separately by UPI.",
       "One payment.",
       "It was your choice; he said you could buy it from any insurer.",
       "It covers two lakh forty thousand.",
       "It runs one year, as long as the loan.",
       "You can cancel within fifteen days.",
       "The money does not come back.",
       "You confirmed it with an OTP."],
      ["Nothing important."],
      "Clear, friendly, Hindi mixed with English."),
    B(kind="insurance", premium_inr=6960, payment_source="separately", payment_frequency="one_time",
      required_for_loan=False, told_could_take_elsewhere=True, cover_inr=240000, term_months=12,
      cancel=cancel(True, 15), money_back="not_refundable", consent_method="otp"),
    why="States every fact as on the record.")

add("well_informed", "hi", BOR(F),
    R("Savita", "Banawati", "1975-03-21", "nbfc", "gold", 300000, 12900, 300000, 18, 12, True, False, 30, "otp", "2026-10-30"),
    S("You are Savita, born 1975. (An invented person.) You run a dairy with two buffaloes and sell milk.",
      "Ten days ago you took a gold loan of three lakh from a finance company to buy a third buffalo. The executive explained a life insurance on the loan; your daughter read the papers with you. You gave the OTP to agree.",
      ["It is a life insurance on the loan.",
       "It was twelve thousand nine hundred, cut from the loan money.",
       "One payment.",
       "It was your choice; he said you could take it from any company.",
       "It covers three lakh.",
       "It runs eighteen months, longer than the loan.",
       "You can cancel within thirty days.",
       "The money does not come back.",
       "You agreed by giving the OTP."],
      ["Nothing important."],
      "Plain-spoken, sure, plain Hindi."),
    B(kind="insurance", premium_inr=12900, payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=False, told_could_take_elsewhere=True, cover_inr=300000, term_months=18,
      cancel=cancel(True, 30), money_back="not_refundable", consent_method="otp"),
    why="States every fact as on the record.")

add("well_informed", "hi-en", BOR(M),
    R("Rahul", "Pareekshan", "1996-06-06", "nbfc", "personal", 200000, 9150, 180000, 24, 24, True, False, 15, "digital_click", "2026-10-22"),
    S("You are Rahul, born 1996. (An invented person.) You are a physiotherapist.",
      "Three weeks ago you took a personal loan of two lakh from a finance company's app for clinic equipment. The app offered a life cover; you read the terms, selected it, and clicked agree.",
      ["It is a life insurance cover on the loan.",
       "The premium was nine thousand one hundred fifty, cut from the loan.",
       "One payment.",
       "It was optional; the app said you could choose any insurer.",
       "It covers one lakh eighty thousand, not the full loan.",
       "It runs two years.",
       "You can cancel within fifteen days.",
       "The premium does not come back.",
       "You agreed by clicking in the app."],
      ["Nothing important."],
      "Crisp, friendly, Hindi mixed with English."),
    B(kind="insurance", premium_inr=9150, payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=False, told_could_take_elsewhere=True, cover_inr=180000, term_months=24,
      cancel=cancel(True, 15), money_back="not_refundable", consent_method="digital_click"),
    why="States every fact as on the record, including a cover below the loan amount.")

# ======================================================================================
# took_nothing (4): C035-C038
# ======================================================================================

add("took_nothing", "hi", BOR(M),
    R("Lakhan", "Namoona", "1963-08-26", "nbfc", "gold", 100000, 3950, 100000, 12, 12, True, False, 15, "otp", "2026-10-23"),
    S("You are Lakhan, born 1963. (An invented person.) You are a mason.",
      "Two weeks ago you took a gold loan of one lakh from a finance company against your wife's earrings, for your mother's treatment. You gave an OTP at the counter for the loan. You took the cash and left.",
      ["You took only the loan, nothing else.",
       "You got about a lakh; you did not count to the rupee.",
       "The OTP you gave was for the loan.",
       "If asked again, you say again that you took nothing else."],
      ["That anything else was added.",
       "Any amount for anything else, how it was paid, how often.",
       "Anything about it being needed, or other companies.",
       "What it would give, how long, whether it can be cancelled, whether money comes back."],
      "Plain, a little puzzled by the question, plain Hindi."),
    B(names_product_unprompted="denies", kind="dont_know", consent_method="did_not_agree"),
    {"recall": "k0", "kind": "u0", "premium": "u1", "loan_funded": "u1", "payment_frequency": "u1",
     "consent": "k2", "cover": "u3", "term": "u3", "cancel_window": "u3", "belief_mismatch": "u3"},
    why="Says he took only the loan and keeps to it; does not know of the product.")

add("took_nothing", "hi-en", BOR(F),
    R("Divya", "Udaharan", "1990-01-31", "bank", "personal", 250000, 8200, 250000, 24, 24, False, False, 30, "signed_form", "2026-10-26"),
    S("You are Divya, born 1990. (An invented person.) You are a nursery school teacher.",
      "Two weeks ago you took a personal loan of two and a half lakh from your bank for a scooty and some home things. You signed the loan papers at the branch. The full loan came to your account.",
      ["You took only the loan, nothing else.",
       "The full two and a half lakh came to your account.",
       "You signed only the loan papers.",
       "If asked again, you say no, nothing was added."],
      ["That anything else was taken or debited.",
       "Any amount or payment for anything else.",
       "What it would be, give, or how long it would run.",
       "Anything about it being needed or other companies.",
       "Whether anything can be cancelled or money comes back."],
      "Polite, sure, Hindi mixed with English."),
    B(names_product_unprompted="denies", kind="dont_know", consent_method="did_not_agree"),
    {"recall": "k0", "kind": "u0", "premium": "u1", "payment_frequency": "u1", "consent": "k2",
     "cover": "u2", "term": "u2", "cancel_window": "u4", "belief_mismatch": "u4"},
    notes="The record says paid separately (from her savings); she does not know any payment, which raises no loan_funded ground under the rules.",
    why="Says she took only the loan and signed only loan papers; does not know of the product.")

add("took_nothing", "hi", BOR(F),
    R("Usha", "Kalpanik", "1969-04-19", "nbfc", "personal", 150000, 6750, 150000, 24, 18, True, False, 15, "signed_form", "2026-10-14"),
    S("You are Usha, born 1969. (An invented person.) You cook meals for two families in your colony.",
      "Last month you took a personal loan of one and a half lakh from a finance company for your son's shop deposit. You signed the papers. The money that came was less; the executive said it was the file charge.",
      ["You took only the loan, nothing else.",
       "About seven thousand was cut from the loan money; it was the file charge.",
       "It was cut one time.",
       "A charge is a charge; it does not come back.",
       "You signed the papers for the loan.",
       "If asked again, you say no, only the file charge was cut, you did not take anything."],
      ["Anything about it being needed or other companies.",
       "That it gives anything, for how long, or whether it can be cancelled."],
      "Straightforward, slightly defensive, plain Hindi."),
    B(names_product_unprompted="denies", kind="fee", premium_inr=7000, payment_source="from_loan",
      payment_frequency="one_time", money_back="not_refundable", consent_method="did_not_agree"),
    {"recall": "k0", "kind": "k1", "premium": "k1", "consent": "k4", "cover": "u1", "term": "u1",
     "cancel_window": "u1"},
    notes="She knows money was cut but calls it a file charge and says she took nothing: recall denied and kind fee. 'Signed the papers for the loan' read as an account of agreeing that leaves the product out.",
    why="Knows about seven thousand was cut but calls it a file charge and says she took nothing.")

add("took_nothing", "hi-en", BOR(M),
    R("Deepak", "Banawati", "1982-11-03", "bank", "gold", 300000, 14100, 300000, 12, 12, True, False, 30, "digital_click", "2026-10-28"),
    S("You are Deepak, born 1982. (An invented person.) You are a courier franchise owner.",
      "Two weeks ago you took a gold loan of three lakh through your bank's app and branch for a delivery van down payment. You clicked accept on the loan screens. The amount that came was about fourteen thousand less; you assume it was bank charges and GST.",
      ["You took only the loan, nothing else.",
       "Fourteen thousand was cut from the loan; bank charges, GST and all.",
       "It was cut one time.",
       "Charges don't come back.",
       "You clicked accept for the loan in the app.",
       "If asked again, you say no, just charges were cut."],
      ["Anything about it being needed or other companies.",
       "That it gives anything, for how long, or whether it can be cancelled."],
      "Confident, a bit dismissive, Hindi mixed with English."),
    B(names_product_unprompted="denies", kind="fee", premium_inr=14000, payment_source="from_loan",
      payment_frequency="one_time", money_back="not_refundable", consent_method="did_not_agree"),
    {"recall": "k0", "kind": "k1", "consent": "k4", "cover": "u1", "term": "u1", "cancel_window": "u1"},
    notes="Knows the amount cut (within 1%) but calls it bank charges and says he took nothing.",
    why="Knows fourteen thousand was cut but calls it bank charges and says he took nothing.")

# ======================================================================================
# coached (4): C039-C042
# ======================================================================================

add("coached", "hi", BOR(M),
    R("Santosh", "Pareekshan", "1977-07-27", "nbfc", "gold", 280000, 18200, 280000, 12, 12, True, False, 15, "otp", "2026-10-17"),
    S("You are Santosh, born 1977. (An invented person.) You own a small tent and decoration business.",
      "Three weeks ago you took a gold loan of two lakh eighty thousand from a finance company for wedding-season stock. The agent said a gold safety deposit had to be kept with the loan, and you gave the OTP for it. He also told you a checking call would come from the company and you should just say yes to everything and say all is fine.",
      ["The agent told you to say yes to everything on the checking call.",
       "It is a gold safety deposit.",
       "About eighteen thousand was kept from the loan money, one time.",
       "He said it had to be kept; it is their own deposit, nothing was said about anywhere else.",
       "You believe it comes back to you when you release the gold.",
       "You gave the OTP for the loan and the deposit."],
      ["What it gives besides coming back, or up to what amount.",
       "How long it runs exactly.",
       "Whether it can be cancelled."],
      "Agreeable, keen to finish, plain Hindi."),
    B(kind="deposit", premium_inr=18000, payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=True, told_could_take_elsewhere=False, money_back="withdrawable_after_period",
      consent_method="otp", sale_concerns=["coached_answers"]),
    {"sale_conduct": "k0", "kind": "k1", "premium": "k2", "bundling": "k3", "belief_mismatch": "k4",
     "cover": "u0", "term": "u1", "cancel_window": "u2"},
    why="Coached to say yes to everything; believes it is a refundable gold deposit he had to keep.")

add("coached", "hi-en", BOR(F),
    R("Pinky", "Namoona", "1998-03-03", "nbfc", "personal", 100000, 4800, 100000, 12, 12, False, False, 15, "digital_click", "2026-10-31"),
    S("You are Pinky, born 1998. (An invented person.) You work at a garment showroom counter.",
      "Ten days ago an agent helped you take a personal loan of one lakh from a finance company app for your mother's dental treatment. He did the clicking on your phone himself. He also asked you to send him about five thousand by UPI, and told you that when the company's call comes, just say yes, everything is fine.",
      ["The agent said: when the call comes, say yes to everything, all is fine.",
       "You sent the agent about five thousand by UPI separately; he said it was needed.",
       "It was one payment.",
       "The agent did the clicking on your phone; you do not know what all you agreed to."],
      ["What that five thousand was for: a charge, insurance, something else.",
       "From where else it could have been taken.",
       "What it gives, how long, whether it can be cancelled, whether money comes back."],
      "Nervous, eager to please, Hindi mixed with English."),
    B(kind="dont_know", premium_inr=5000, payment_source="separately", payment_frequency="one_time",
      required_for_loan=True, consent_method="dont_know", sale_concerns=["coached_answers"]),
    {"sale_conduct": "k0", "kind": "u0", "premium": "k1", "consent": "k3", "cover": "u2", "term": "u2",
     "cancel_window": "u2", "belief_mismatch": "u2"},
    notes="The agent called the payment 'needed': read as told it was required. She does not know what it was (not a deposit belief) and nothing about other companies.",
    why="Coached to say all is fine; does not know what the five thousand she paid was for or what she agreed to.")

add("coached", "hi", BOR(F),
    R("Radha", "Udaharan", "1972-09-09", "bank", "personal", 300000, 21600, 300000, 36, 36, True, False, 30, "signed_form", "2026-10-13"),
    S("You are Radha, born 1972. (An invented person.) You are an anganwadi helper in a village near a town.",
      "Last month you took a personal loan of three lakh from the bank to buy a small plot. The officer offered an insurance and said after three years the money comes back with interest. He said if anyone calls from the bank, tell them you understood everything. You signed its form.",
      ["The officer said to tell anyone who calls that you understood everything.",
       "It is an insurance.",
       "It was twenty-one thousand six hundred, cut from the loan money.",
       "One payment.",
       "It was your choice.",
       "It runs three years.",
       "You believe after three years the money comes back with interest.",
       "You signed the form."],
      ["What it pays if something happens, or how much.",
       "Whether it can be cancelled.",
       "What was said about other companies; nothing that you recall."],
      "Polite, eager to show she understood, plain Hindi."),
    B(kind="insurance", premium_inr=21600, payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=False, told_could_take_elsewhere="dont_know", term_months=36,
      money_back="guaranteed_return", consent_method="signed_form", sale_concerns=["coached_answers"]),
    {"sale_conduct": "k0", "belief_mismatch": "k6", "cover": "u0", "cancel_window": "u1"},
    why="Coached to say she understood; believes the money returns with interest after three years.")

add("coached", "hi-en", BOR(M),
    R("Varun", "Kalpanik", "1993-12-24", "bank", "gold", 400000, 19000, 400000, 12, 12, True, True, 15, "otp", "2026-11-05"),
    S("You are Varun, born 1993. (An invented person.) You run a phone accessories stall in a mall.",
      "A few days ago you took a gold loan of four lakh from the bank to restock. The officer said the loan insurance is compulsory and has to be the bank's company. He said a call will come, just say 'haan, all okay'. You gave an OTP for it.",
      ["The officer told you to just say 'haan, all okay' on the call.",
       "It is a loan insurance.",
       "It was compulsory and had to be the bank's company.",
       "You gave an OTP for it.",
       "It runs as long as the loan."],
      ["How much it cost.",
       "Where the money for it came from.",
       "Whether it is one payment.",
       "What it covers, or whether it can be cancelled.",
       "Whether any money comes back."],
      "Breezy, wants it over, Hindi mixed with English."),
    B(kind="insurance", required_for_loan=True, told_could_take_elsewhere=False, term_months="as_long_as_loan",
      consent_method="otp", sale_concerns=["coached_answers"]),
    {"sale_conduct": "k0", "bundling": "k2", "premium": "u0", "loan_funded": "u1", "payment_frequency": "u2",
     "cover": "u3", "cancel_window": "u3", "belief_mismatch": "u4"},
    why="Coached to say all okay; told the insurance was compulsory and the bank's own, and does not know how it was paid.")

# ======================================================================================
# in_a_hurry (2): C043 (ordinary_informed), C044 (misled)
# ======================================================================================

add("in_a_hurry", "hi", BOR(M),
    R("Harish", "Banawati", "1981-02-18", "nbfc", "gold", 260000, 11700, 260000, 12, 12, True, False, 30, "signed_form", "2026-10-25"),
    S("You are Harish, born 1981. (An invented person.) You are a wholesale fruit trader.",
      "Two weeks ago you took a gold loan of two lakh sixty thousand from a finance company to pay farmers. The executive explained a loan insurance; you took it and signed its form.",
      ["It is a loan insurance; if you die, the loan is cleared.",
       "It was around twelve thousand, cut from the loan.",
       "One payment.",
       "It was your choice; he said other companies are also fine.",
       "It covers two lakh sixty thousand, the same as the loan.",
       "It runs as long as the loan.",
       "You can cancel it within some days.",
       "The money does not come back.",
       "You signed its form."],
      ["The exact premium.",
       "How many days to cancel."],
      "Rushed, clipped, plain Hindi.",
      "You are at the market loading a truck. You agree to talk but say to be quick, and keep answers short."),
    B(kind="insurance", premium_inr=12000, payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=False, told_could_take_elsewhere=True, cover_inr=260000, term_months="as_long_as_loan",
      cancel=cancel(True, "dont_know"), money_back="not_refundable", consent_method="signed_form"),
    {"premium": "k1", "cancel_window": "k6"},
    why="In a hurry; knows what he bought, premium rough and cancel days unknown.", underlying="ordinary_informed")

add("in_a_hurry", "hi-en", BOR(F),
    R("Shalini", "Pareekshan", "1986-05-29", "bank", "personal", 900000, 61500, 900000, 60, 60, True, True, 30, "digital_click", "2026-10-18"),
    S("You are Shalini, born 1986. (An invented person.) You are a sales manager at a pharma company.",
      "Three weeks ago you took a personal loan of nine lakh from your bank for a home renovation. The relationship manager said it comes with an investment plan from their partner that gives good returns, and that it is part of the loan. You clicked agree in the app link he sent.",
      ["It is an investment plan.",
       "It was around sixty thousand, taken from the loan amount.",
       "One payment.",
       "He said it is part of the loan and comes from their partner; nothing about any other company.",
       "It runs five years, like the loan.",
       "You believe it gives good returns and you get the money back with returns at the end.",
       "You clicked agree on the app link."],
      ["Whether it pays anything if something happens to you, or how much.",
       "Whether it can be cancelled."],
      "Fast, a little impatient, Hindi mixed with English.",
      "You are between meetings. You agree to talk but say you have very little time, please be quick."),
    B(kind="investment", premium_inr=60000, payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=True, told_could_take_elsewhere=False, term_months=60, money_back="guaranteed_return",
      consent_method="digital_click"),
    {"kind": "k0", "premium": "k1", "bundling": "k3", "belief_mismatch": "k5", "cover": "u0",
     "cancel_window": "u1"},
    why="In a hurry; believes it is an investment with returns that came as part of the loan from the partner.",
    underlying="misled")

# ======================================================================================
# fraud_suspicion (2): C045 (misled), C046 (ordinary_informed)
# ======================================================================================

add("fraud_suspicion", "hi", BOR(M),
    R("Jagdish", "Namoona", "1961-06-13", "bank", "gold", 140000, 5600, 140000, 12, 12, True, False, 15, "signed_form", "2026-10-22"),
    S("You are Jagdish, born 1961. (An invented person.) You are a retired postman.",
      "Two weeks ago you took a gold loan of one lakh forty thousand from the bank for your grandson's fees. The officer mentioned an insurance with it and you signed the form. You believe you paid it separately, in cash, at the counter.",
      ["It is an insurance with the gold loan.",
       "It was about five and a half thousand.",
       "You believe you paid it in cash at the counter, separately.",
       "One payment.",
       "It was your choice.",
       "It runs as long as the loan.",
       "The money does not come back.",
       "You signed the form.",
       "Last year someone called pretending to be the bank and asked for your OTP; since then you are careful."],
      ["What it covers or how much.",
       "Whether it can be cancelled.",
       "What was said about other companies."],
      "Suspicious at first, then cooperative, plain Hindi.",
      "First you ask who is calling and whether this is a fraud call. If told how to check, you agree to go on."),
    B(kind="insurance", premium_inr=5500, payment_source="separately", payment_frequency="one_time",
      required_for_loan=False, told_could_take_elsewhere="dont_know", term_months="as_long_as_loan",
      money_back="not_refundable", consent_method="signed_form"),
    {"loan_funded": "k2", "premium": "k1", "cover": "u0", "cancel_window": "u1"},
    why="Asks whether the call is genuine; believes he paid the insurance in cash though the record says it was cut from the loan.",
    underlying="misled")

add("fraud_suspicion", "hi-en", BOR(F),
    R("Nisha", "Kalpanik", "1988-10-01", "nbfc", "personal", 400000, 20800, 400000, 24, 24, True, False, 30, "otp", "2026-11-04"),
    S("You are Nisha, born 1988. (An invented person.) You are a primary school vice-principal.",
      "A week ago you took a personal loan of four lakh from a finance company for your father's surgery. The executive explained a loan life insurance and you took it, confirming with an OTP.",
      ["It is a loan life insurance.",
       "It was twenty thousand something, cut from the loan.",
       "One payment.",
       "It was your choice; she said any insurer would do.",
       "It covers four lakh.",
       "It runs two years.",
       "You can cancel within thirty days.",
       "The money does not come back.",
       "You confirmed it with an OTP.",
       "You have read about fake loan calls, so you are careful with unknown callers."],
      ["The exact premium."],
      "Careful, articulate, Hindi mixed with English.",
      "First you ask who is calling and whether this call is genuine or a fraud. If told how to check, you agree to go on."),
    B(kind="insurance", premium_inr=rng(20000, 21000), payment_source="from_loan", payment_frequency="one_time",
      required_for_loan=False, told_could_take_elsewhere=True, cover_inr=400000, term_months=24,
      cancel=cancel(True, 30), money_back="not_refundable", consent_method="otp"),
    {"premium": "k1"},
    why="Asks whether the call is genuine; knows what she bought, premium as a range.",
    underlying="ordinary_informed")

# ======================================================================================
# third_party (6): C047-C052
# ======================================================================================

TP = lambda rel, g: {"who": "third_party", "relation": rel, "gender": g}  # noqa: E731

add("third_party", "hi", TP("husband", M),
    R("Kiran", "Udaharan", "1979-02-08", "bank", "personal", 300000, 13500, 300000, 24, 36, True, False, 30, "otp", "2026-10-20"),
    S("You are Kiran's husband, born 1975. (An invented person.) You drive a school van. Kiran is your wife; the phone is hers.",
      "Kiran left her phone at home while she went to the market. It rang and you picked it up.",
      ["You are not Kiran; you say plainly that you are her husband and she is not at home.",
       "You know she took some loan from the bank recently, for your daughter's fees.",
       "You do not know any details of her loan.",
       "Her loan is not yours to talk about; if asked, you say so."],
      ["Anything she took with the loan, any amount, how she paid, what she signed.",
       "Her year of birth for certain; and you would not give it to a stranger anyway."],
      "Plain, polite, plain Hindi.",
      "You say right away that you are her husband and Kiran is not here; you offer to tell her someone called."),
    why="Husband answers and says plainly he is not the borrower.")

add("third_party", "hi-en", TP("wife", F),
    R("Amit", "Banawati", "1985-09-15", "nbfc", "gold", 160000, 6400, 160000, 12, 6, False, False, 15, "signed_form", "2026-10-29"),
    S("You are Amit's wife, born 1988. (An invented person.) You work from home doing tuition. Amit is your husband; the phone is his.",
      "Amit has gone out and left his phone charging. It rang and you picked it up.",
      ["You are not Amit.",
       "You do not know about any loan of his.",
       "Whatever it is, it is his matter, not yours to answer."],
      ["Any loan, any amount, anything he signed.",
       "His year of birth exactly; you would not give it to an unknown caller."],
      "Curious, a bit protective, Hindi mixed with English.",
      "You do not say who you are straight away. You say 'he has gone out, tell me what it is', and ask what the call is about."),
    why="Wife answers and indirectly says the borrower is out, asking what it is about.")

add("third_party", "hi", TP("son", M),
    R("Sushila", "Pareekshan", "1960-12-20", "bank", "gold", 90000, 2700, 90000, 12, 6, True, False, 15, "recorded_call", "2026-10-16"),
    S("You are Sushila's son, born 1986. (An invented person.) You run a mobile recharge shop. Sushila is your mother; you keep her phone when she rests.",
      "Your mother is resting after lunch and her phone rang, so you answered it.",
      ["You are not Sushila; you say plainly that you are her son and she is resting.",
       "You know she pawned some gold at the bank recently.",
       "You do not know any details.",
       "It is her loan; you say it is not yours to answer."],
      ["What else she took, how much, how she paid, what she agreed to.",
       "Her exact year of birth; you think she is in her sixties."],
      "Direct, respectful, plain Hindi.",
      "You say at once you are her son and she is resting; you ask them to call back later."),
    why="Son answers and says plainly he is not the borrower.")

add("third_party", "hi-en", TP("brother", M),
    R("Manoj", "Namoona", "1990-04-04", "nbfc", "personal", 200000, 8900, 200000, 24, 36, True, True, 30, "digital_click", "2026-10-24"),
    S("You are Manoj's elder brother, born 1984. (An invented person.) You run a cyber cafe. Manoj left his phone at your cafe.",
      "Manoj left his phone on your counter. It rang and you picked it up.",
      ["You are not Manoj.",
       "You do not know about any loan of his.",
       "His matters are his; you will not answer for him."],
      ["Any loan, amount, or anything he agreed to.",
       "His year of birth for certain; and you would not tell a caller."],
      "Guarded, a bit gruff, Hindi mixed with English.",
      "You do not say who you are at first. You ask 'who is this, why do you want him?' and want to know the reason before anything else."),
    why="Brother answers and indirectly asks who is calling and why.")

add("third_party", "hi", TP("daughter", F),
    R("Babita", "Kalpanik", "1971-07-17", "bank", "personal", 500000, 24500, 500000, 36, 24, True, False, 30, "signed_form", "2026-10-19"),
    S("You are Babita's daughter, born 2000. (An invented person.) You are a college student. Babita is your mother; she left a spare phone at home.",
      "Your mother is at work and her phone rang at home, so you answered.",
      ["You are not Babita.",
       "You know nothing about any loan of your mother's.",
       "If it is about money, that is for her, not you."],
      ["Any loan or anything she signed.",
       "Her exact year of birth; you would have to check, and you would not give it on the phone."],
      "Polite but wary, plain Hindi.",
      "You do not say plainly who you are. You say 'Mummy is at work, what is it, tell me' and ask what they want."),
    why="Daughter answers and indirectly says the borrower is at work, asking what it is.")

add("third_party", "hi-en", TP("shop colleague", M),
    R("Raju", "Udaharan", "1983-03-11", "nbfc", "gold", 240000, 9600, 240000, 12, 6, True, False, 15, "otp", "2026-10-27"),
    S("You are Raju's colleague at his electronics shop, born 1993. (An invented person.) You work the counter. Raju left his phone at the shop.",
      "Raju stepped out to a supplier and left his phone at the shop. It kept ringing, so you picked it up.",
      ["You are not Raju; you say plainly that you work with him and this is his phone.",
       "You know nothing about his loans or money matters.",
       "It is not your place to answer about his loan."],
      ["Anything about any loan of his.",
       "His year of birth."],
      "Friendly, plain, Hindi mixed with English.",
      "You say straight away this is Raju's phone, you work with him at the shop, and he is out."),
    why="Shop colleague answers and says plainly he is not the borrower.")

# ======================================================================================
# refusal (3): C053-C055
# ======================================================================================

add("refusal", "hi", BOR(M),
    R("Bhupendra", "Banawati", "1967-01-09", "bank", "gold", 200000, 8350, 200000, 12, 6, True, False, 15, "signed_form", "2026-10-21"),
    S("You are Bhupendra, born 1967. (An invented person.) You run a hardware store and are always busy.",
      "Three weeks ago you took a gold loan of two lakh from the bank for shop stock. The officer said there was a loan insurance with it and you signed for it.",
      ["It is a loan insurance.",
       "It was around eight thousand, cut from the loan.",
       "One payment.",
       "It was your choice.",
       "It runs as long as the loan.",
       "You signed for it."],
      ["Up to what amount it covers.",
       "Whether it can be cancelled.",
       "Whether money comes back.",
       "What was said about other companies."],
      "Irritated, curt, plain Hindi.",
      "You confirm who you are, but when asked if you can talk for two or three minutes, you say you have no time for surveys and feedback calls, and refuse."),
    why="Refuses at 'can we talk': no time for surveys.")

add("refusal", "hi", BOR(F),
    R("Kusum", "Pareekshan", "1974-06-24", "nbfc", "personal", 180000, 9950, 180000, 24, 36, False, False, 30, "otp", "2026-10-15"),
    S("You are Kusum, born 1974. (An invented person.) You run a beauty parlour.",
      "Last month you took a personal loan of one lakh eighty thousand from a finance company. They added a life insurance which you paid yourself by UPI, and you gave an OTP for it.",
      ["It is a life insurance.",
       "It was ten thousand, paid by you separately by UPI.",
       "One payment.",
       "It was your choice.",
       "You gave the OTP for it."],
      ["What it covers, how long it runs, whether it can be cancelled.",
       "Whether money comes back.",
       "What was said about other companies."],
      "Polite at first, then firm, plain Hindi.",
      "You confirm who you are, agree to talk, and give your year of birth. When they ask what you took with the loan, you say you do not discuss money matters on the phone and will not go on."),
    why="Agrees to talk, then refuses after the first loan question.")

add("refusal", "hi-en", BOR(M),
    R("Sameer", "Namoona", "1992-08-31", "nbfc", "personal", 320000, 17300, 320000, 24, 36, True, False, 30, "digital_click", "2026-10-30"),
    S("You are Sameer, born 1992. (An invented person.) You are a software developer.",
      "Two weeks ago you took a personal loan of three lakh twenty thousand from a finance company's app. There was a loan insurance in the app; you clicked agree.",
      ["It is a loan insurance.",
       "It was seventeen thousand something, cut from the loan.",
       "One payment.",
       "It was optional.",
       "You clicked agree in the app."],
      ["What it covers, how long it runs, whether it can be cancelled, whether money comes back.",
       "What was said about other companies."],
      "Sharp, dismissive, Hindi mixed with English.",
      "When you hear it is an automated assistant and asked if you can talk, you say you do not talk to robots or automated calls, and refuse."),
    why="Refuses at 'can we talk': distrusts automated calls.")

# ======================================================================================
# call_back_later (3): C056-C058
# ======================================================================================

add("call_back_later", "hi", BOR(M),
    R("Ganesh", "Udaharan", "1976-11-27", "bank", "personal", 250000, 12250, 250000, 24, 36, True, False, 15, "signed_form", "2026-10-23"),
    S("You are Ganesh, born 1976. (An invented person.) You are a bus conductor on a city route.",
      "Last month you took a personal loan of two and a half lakh from the bank for a family function. The officer offered an insurance on it and you signed for it.",
      ["It is a loan insurance.",
       "It was about twelve thousand, cut from the loan.",
       "One payment.",
       "It was your choice.",
       "It covers the loan amount.",
       "You signed for it."],
      ["How long it runs, whether it can be cancelled, whether money comes back.",
       "What was said about other companies."],
      "Hurried, polite, plain Hindi.",
      "You are on duty in the bus. You confirm who you are and ask them to call after seven in the evening, saying the time yourself."),
    why="Busy; asks to be called after seven in the evening.")

add("call_back_later", "hi-en", BOR(F),
    R("Tanvi", "Kalpanik", "2001-05-10", "nbfc", "gold", 70000, 2050, 70000, 6, 3, True, False, 15, "digital_click", "2026-11-01"),
    S("You are Tanvi, born 2001. (An invented person.) You are a final-year college student who also tutors children.",
      "Last week you took a small gold loan of seventy thousand from a finance company's app against your earrings for your exam fees. The app had a small insurance which you clicked to add.",
      ["It is some insurance.",
       "It was about two thousand, cut from the loan.",
       "One payment.",
       "It was optional.",
       "You clicked to add it in the app."],
      ["What it covers, how long, whether it can be cancelled, whether money comes back.",
       "What was said about other companies."],
      "Friendly but distracted, Hindi mixed with English.",
      "You are about to enter an exam hall. You confirm who you are and ask them to call later, without saying when; if asked when, you say you are not sure, maybe tomorrow."),
    why="Busy; asks to be called later without naming a time.")

add("call_back_later", "hi-en", BOR(M),
    R("Yash", "Banawati", "1995-09-19", "bank", "gold", 380000, 16900, 380000, 12, 6, True, True, 30, "otp", "2026-10-26"),
    S("You are Yash, born 1995. (An invented person.) You are a field sales representative who drives a lot.",
      "Two weeks ago you took a gold loan of three lakh eighty thousand from the bank for a car repair and some dues. The officer said a loan insurance was needed but any company's would do; you took the bank's and gave an OTP.",
      ["It is a loan insurance.",
       "It was around seventeen thousand, cut from the loan.",
       "One payment.",
       "It was needed, but any company's would do.",
       "You gave an OTP for it."],
      ["What it covers, how long, whether it can be cancelled, whether money comes back."],
      "Short, distracted, Hindi mixed with English.",
      "You are driving. You confirm who you are and say you are driving, call later; you do not name a time, and if asked you say 'whenever, later'."),
    why="Driving; asks to be called later without naming a time.")

# ======================================================================================
# language_switch (2): C059-C060
# ======================================================================================

add("language_switch", "hi", BOR(M),
    R("Murugan", "Pareekshan", "1970-08-18", "nbfc", "gold", 200000, 9200, 200000, 12, 6, True, False, 15, "signed_form", "2026-10-28"),
    S("You are Murugan, born 1970. (An invented person.) You are a textile trader who moved from Tamil Nadu to a north Indian city years ago; you speak Tamil at home.",
      "Two weeks ago you took a gold loan of two lakh from a finance company. The executive told you about a loan insurance in Tamil and English, and you signed its form.",
      ["It is a loan insurance.",
       "It was about nine thousand, cut from the loan.",
       "One payment.",
       "It was your choice.",
       "It covers two lakh.",
       "You signed its form."],
      ["How long it runs, whether it can be cancelled, whether money comes back.",
       "What was said about other companies."],
      "Halting, simple Hindi with long pauses; fluent in Tamil.",
      "You confirm who you are in a few Hindi words, then say your Hindi is not good and ask if they can speak in Tamil."),
    why="Asks to continue in Tamil.")

add("language_switch", "hi-en", BOR(F),
    R("Sutapa", "Namoona", "1987-03-26", "bank", "personal", 300000, 15750, 300000, 24, 36, True, False, 30, "otp", "2026-10-19"),
    S("You are Sutapa, born 1987. (An invented person.) You are a librarian from West Bengal working in a city in another state; you speak Bengali at home.",
      "Three weeks ago you took a personal loan of three lakh from the bank. The officer explained a life insurance with it and you agreed with an OTP.",
      ["It is a life insurance on the loan.",
       "It was fifteen thousand something, cut from the loan.",
       "One payment.",
       "It was your choice.",
       "You agreed with an OTP."],
      ["What it covers, how long, whether it can be cancelled, whether money comes back.",
       "What was said about other companies."],
      "Halting Hindi with English words, fluent in Bengali.",
      "You confirm who you are, then say in broken Hindi and a little English that you are not comfortable in Hindi and ask whether they can talk in Bengali."),
    why="Asks to continue in Bengali.")

# ======================================================================================
# gold rules (eval/p5/gold-rules.md, table "Grounds")
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
# to. C037 and C038 call the deduction a charge in that follow-up, so kind is reachable for them.
REACHABLE_WHEN_DENIED = {"P5-C035": {"recall", "consent"}, "P5-C036": {"recall", "consent"},
                         "P5-C037": {"recall", "consent", "kind"}, "P5-C038": {"recall", "consent", "kind"}}
CHANGED_NOTE = "ground set changed after the blind second labelling of 2026-11-10; see CHANGELOG."

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
    assert len(C) == 60, len(C)
    customers, gold, records = [], [], {}
    for i, c in enumerate(C, 1):
        cid, rid = f"P5-C{i:03d}", f"p5-c{i:03d}"
        r = c["rec"]
        premium = r["premium"]
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
            "label": f"Synthetic P5 record. {r['first']}: {loan_word} and one add-on",
            "description": f"Synthetic P5 record. {r['first']}, born {year}, took {loan_word} with one add-on. For the P5 evaluation only.",
            "lender_name": LENDER_NAME[r["lender"]],
            "record": {
                "loan_id": f"TEST-P5-LN-{i:03d}", "lender_type": r["lender"],
                "borrower": {"name": f"{r['first']} {r['surname']}", "dob": r["dob"], "language": c["language"]},
                "loan_kind": r["loan"], "sanctioned_inr": r["sanctioned"],
                "disbursed_inr": r["sanctioned"] - premium if r["pfl"] else r["sanctioned"],
                "disbursed_on": r["on"], "products": [product], "tenure_months": r["tenure"],
            },
        }
        CallRecord.model_validate(record)
        assert "2026-10-12" <= r["on"] <= "2026-11-05", cid
        assert 1958 <= int(year) <= 2001, cid
        records[rid] = record

        sheet = c["sheet"]
        text = json.dumps(list(sheet.values()), ensure_ascii=False)  # the values, not the field names
        for word in BANNED:
            assert word not in text.lower(), (cid, word)
        assert not re.search(r"\w_\w", text), (cid, "underscore word")
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
        else:
            b = c["beliefs"]
            refer, gap, undecided = grounds(b, product, r["tenure"])
            refer_all = set(refer)
            cited = c["cite"]
            assert set(cited) == set(refer) | set(gap), (cid, sorted(cited), sorted(refer), sorted(gap))

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
                notes += " " + CHANGED_NOTE
            summary = (f"Refer on {', '.join(refer)}." if refer else "No refer ground.") + (
                f" Gaps on {', '.join(gap)}." if gap else " No gaps.")
            row.update({"class": klass, "expected_outcome": "completed", "expected_tier": tier,
                        "refer_grounds_from_call": [ground(x) for x in refer],
                        "gap_grounds": [ground(x) for x in gap], "beliefs": b, "notes": notes,
                        "rationale": f"{c['why']} {summary}"})
        gold.append(row)
    check_counts(customers, gold, records)
    return customers, gold, records


EXPECTED_KINDS = {"misled": 14, "uninformed": 6, "ordinary_informed": 8, "well_informed": 6, "took_nothing": 4,
                  "coached": 4, "in_a_hurry": 2, "fraud_suspicion": 2, "third_party": 6, "refusal": 3,
                  "call_back_later": 3, "language_switch": 2}


def check_counts(customers, gold, records):
    kinds = Counter(c["kind"] for c in customers)
    assert dict(kinds) == EXPECTED_KINDS, kinds
    assert Counter(c["language"] for c in customers) == {"hi": 30, "hi-en": 30}
    for kind, n in EXPECTED_KINDS.items():
        langs = Counter(c["language"] for c in customers if c["kind"] == kind)
        assert abs(langs["hi"] - langs["hi-en"]) <= 1, (kind, langs)
    g = {r["id"]: r for r in gold}
    assert set(g) == {c["id"] for c in customers} and set(records) == {c["record_id"] for c in customers}
    cls = lambda k: Counter(r["class"] for r in gold if r["kind"] == k)  # noqa: E731
    assert cls("misled") == {"problem": 14}
    assert cls("uninformed")["knowledge_gap_only"] >= 4 and cls("uninformed")["problem"] <= 2
    assert cls("ordinary_informed")["problem"] == 0
    assert all(r["expected_tier"] == "clear" for r in gold if r["kind"] == "well_informed")
    assert cls("took_nothing") == {"problem": 4} and cls("coached") == {"problem": 4}
    for c in customers:
        if c["underlying"] is not None:
            assert c["kind"] in ("in_a_hurry", "fraud_suspicion")
    assert {c["underlying"] for c in customers if c["kind"] == "in_a_hurry"} == {"ordinary_informed", "misled"}
    assert {c["underlying"] for c in customers if c["kind"] == "fraud_suspicion"} == {"ordinary_informed", "misled"}
    for c in customers:
        if c["underlying"] == "misled":
            assert g[c["id"]]["class"] == "problem"
        if c["underlying"] == "ordinary_informed":
            assert g[c["id"]]["class"] != "problem"
    prods = [r["record"]["products"][0] for r in records.values()]
    assert 8 <= sum(not p["paid_from_loan"] for p in prods) <= 12
    assert sum(p["required_for_loan"] for p in prods) >= 4
    assert {p["consent"]["method"] for p in prods} == {"signed_form", "otp", "digital_click", "recorded_call"}
    assert Counter(c["speaker"]["who"] for c in customers) == {"borrower": 54, "third_party": 6}


def dump_line(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def main():
    customers, gold, records = build()
    (HERE / "customers.jsonl").write_text("".join(dump_line(x) + "\n" for x in customers), encoding="utf-8")
    (HERE / "gold.jsonl").write_text("".join(dump_line(x) + "\n" for x in gold), encoding="utf-8")
    rdir = HERE / "records"
    rdir.mkdir(exist_ok=True)
    for stale in rdir.glob("p5-c*.json"):
        if stale.stem not in records:
            stale.unlink()
    for rid, rec in records.items():
        (rdir / f"{rid}.json").write_text(json.dumps(rec, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                                          encoding="utf-8")
    print(f"wrote {len(customers)} customers, {len(gold)} gold rows, {len(records)} records")


if __name__ == "__main__":
    main()
