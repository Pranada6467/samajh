"""Wording the bot must never speak. `load_prompts` runs this, so a banned line cannot be loaded.

Sources: DESIGN.md section 11 ("we can't say"), section 5 (no sales content, no explaining the
product, no secrets asked) and the rule that nothing said before or during teach-back may
suggest a value on the record. Matching is on whole words, folded as in `_lexicon.tokens`;
a word ending in `*` matches any word that starts with it.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from samajh.dialogue._lexicon import Phrase, found, tokens


@dataclass(frozen=True)
class Ban:
    name: str
    phrases: frozenset[Phrase]
    # Lines that may use the wording, and only to deny it ("this is not a sales call").
    denied_in: frozenset[str] = frozenset()


def _ban(name: str, *texts: str, denied_in: tuple[str, ...] = ()) -> Ban:
    return Ban(name, frozenset(tokens(text) for text in texts), frozenset(denied_in))


_OTP = ("otp", "o t p", "ओटीपी", "ओ टी पी", "ஓடிபி", "ஓ டி பி", "ಒಟಿಪಿ", "ಒ ಟಿ ಪಿ")

BANS: tuple[Ban, ...] = (
    _ban(
        "a finding (the bot never says mis-selling, fraud or violation)",
        "mis selling", "misselling", "mis sold", "missold", "मिस सेलिंग", "मिससेलिंग", "गलत बिक्री", "धोखा*", "ठगी",
        "fraud*", "फ्रॉड", "cheat*", "violation", "उल्लंघन", "illegal", "गैरकानूनी", "தவறான விற்பனை", "மோசடி",
        "ತಪ್ಪು ಮಾರಾಟ", "ಮೋಸ", "ವಂಚನೆ",
    ),
    _ban(
        "a promise of money back",
        "refund*", "रिफंड*", "ரீஃபண்ட்*", "ರೀಫಂಡ್*", "ಮರುಪಾವತಿ*", "वापस मिलेगा", "वापस मिलेंगे", "वापस मिल जाएगा",
        "वापस मिल जाएंगे", "वापस कर देंगे", "वापस करेंगे", "लौटा देंगे", "लौटाएंगे", "will get back", "get your money back",
        "compensation", "compensate*", "मुआवजा", "திரும்பக் கிடைக்கும்", "திருப்பித் தருவோம்", "இழப்பீடு",
        "ವಾಪಸ್ ಸಿಗುತ್ತದೆ", "ವಾಪಸ್ ಕೊಡುತ್ತೇವೆ", "ಪರಿಹಾರ",
    ),
    _ban(
        "a claim about the regulator or the law",
        "rbi", "आरबीआई", "आर बी आई", "रिजर्व बैंक", "reserve bank", "irdai", "ombudsman", "लोकपाल", "ரிசர்வ் வங்கி",
        "ஆர்பிஐ", "ಆರ್ಬಿಐ", "ರಿಸರ್ವ್ ಬ್ಯಾಂಕ್", "mandatory", "अनिवार्य", "कानूनन", "by law", "regulation*",
    ),
    _ban(
        "a word that names or explains the product",
        "insurance", "insured", "इंश्योरेंस", "बीमा", "policy", "पॉलिसी", "premium", "प्रीमियम", "cover", "कवर",
        "coverage", "fd", "एफडी", "fixed deposit", "फिक्स्ड डिपॉजिट", "deposit", "डिपॉजिट", "जमा", "credit life",
        "loan protection", "nominee", "नॉमिनी", "claim", "क्लेम", "maturity", "मैच्योरिटी", "காப்பீ*", "இன்சூரன்ஸ்*", "டெபாசிட்*",
        "பாலிசி", "பிரீமியம்", "எஃப்டி", "வைப்பு*", "ವಿಮೆ*", "ಇನ್ಶೂರೆನ್ಸ್", "ಪಾಲಿಸಿ", "ಪ್ರೀಮಿಯಂ", "ಎಫ್ಡಿ", "ಠೇವಣಿ*",
    ),
    _ban(
        "a suggestion of how the product was paid for",
        "लोन में से", "लोन से कट*", "लोन अमाउंट से", "कट गया", "काटा गया", "काट लिया", "deduct*", "अलग से", "separately",
        "नकद", "cash", "கடன் தொகையிலிருந்து", "தனியாக", "ಸಾಲದಿಂದ", "ಸಾಲದ ಮೊತ್ತದಿಂದ", "ಪ್ರತ್ಯೇಕವಾಗಿ",
    ),
    _ban(
        "a suggestion of how consent was given",
        "signature", "sign", "signed", "साइन", "हस्ताक्षर", "दस्तखत", "form", "फॉर्म", "click", "क्लिक", "tick", "टिक",
        "கையெழுத்து*", "படிவ*", "ಸಹಿ", "ಫಾರ್ಮ್",
    ),
    _ban(
        "a secret (OTP, PIN, password, account number, date of birth, card or ID number)",
        *_OTP, "pin", "पिन", "upi pin", "password", "पासवर्ड", "account number", "खाता नंबर", "खाता संख्या",
        "अकाउंट नंबर", "cvv", "card number", "कार्ड नंबर", "aadhaar", "aadhar", "आधार", "pan", "पैन", "date of birth",
        "dob", "birth date", "birthday", "जन्म तिथि", "जन्मतिथि", "जन्म की तारीख", "जन्मदिन", "பின்", "கடவுச்சொல்",
        "கணக்கு எண்", "பிறந்த தேதி", "பிறந்த நாள்", "ಪಿನ್", "ಪಾಸ್ವರ್ಡ್", "ಖಾತೆ ಸಂಖ್ಯೆ*", "ಹುಟ್ಟಿದ ದಿನಾಂಕ*",
        "ಜನ್ಮ ದಿನಾಂಕ*",
        denied_in=("disclosure.never_ask",),
    ),
    _ban(
        "sales talk",
        "sale*", "sell*", "सेल्स", "बेच*", "बिक्री", "விற்பனை", "விற்க*", "ಮಾರಾಟ*", "ಮಾರು*",
        denied_in=("disclosure.not_sales", "disclosure.reask"),
    ),
    _ban(
        "an offer",
        "offer*", "ऑफर*", "discount*", "डिस्काउंट", "छूट", "scheme", "स्कीम", "योजना", "upgrade", "अपग्रेड", "special",
        "स्पेशल", "limited time", "buy", "खरीद*", "free", "फ्री", "मुफ्त", "cashback", "कैशबैक", "top up", "टॉप अप",
        "new loan", "नया लोन", "credit card", "क्रेडिट कार्ड", "interest rate", "ब्याज", "सलाह", "recommend*",
        "சலுகை", "தள்ளுபடி", "இலவச*", "ಕೊಡುಗೆ", "ರಿಯಾಯಿತಿ", "ಉಚಿತ*",
    ),
)  # fmt: skip

_DENIALS = frozenset(
    tokens(text)
    for text in ("नहीं", "never", "not", "ஒருபோதும்", "அல்ல", "விற்கப்படாது", "ಎಂದಿಗೂ", "ಅಲ್ಲ", "ಮಾರುವುದಿಲ್ಲ")
)


def banned_in(text: str) -> list[tuple[Ban, Phrase]]:
    """Every banned phrase found in a text, with its ban."""
    words = tokens(text)
    return [(ban, phrase) for ban in BANS for phrase in found(words, ban.phrases)]


def lint_line(key: str, template: str) -> list[str]:
    """Problems with one template; an empty list means it may be spoken."""
    problems = []
    if any(unicodedata.category(ch) == "Nd" for ch in template):
        problems.append(f"{key}: contains a digit; the only figures the bot says come from the customer")
    denies = bool(found(tokens(template), _DENIALS))
    for ban, phrase in banned_in(template):
        if key not in ban.denied_in:
            problems.append(f"{key}: {ban.name}: {' '.join(phrase)!r}")
        elif not denies:
            problems.append(f"{key}: {ban.name}: {' '.join(phrase)!r} may appear here only when it is denied")
    return problems
