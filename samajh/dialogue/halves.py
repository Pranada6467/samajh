"""A live, deterministic reading of a half answer (iteration 4, W4). No LLM and no record: only the reply's words.

The consent question asks two things (what was agreed to, and how). `consent_halves` reads each half from the reply as
the rules' answer types, so the call can ask `samajh.rules.halves.missing_half` which half is missing. `kind_is_half`
says a reply to the kind question gave a figure or what the thing does, and no word for what it is. Hindi and Hinglish
word lists (Devanagari and romanised); Tamil and Kannada read as no half answer (None / False)."""

from __future__ import annotations

import re

from samajh.types import Answer, ConsentMethod, Evidence, GapReason, Language, Stated, TurnId, Unclear

_READ = frozenset({Language.hi, Language.hi_en})

_HOW: tuple[tuple[ConsentMethod, tuple[str, ...]], ...] = (
    (ConsentMethod.otp, ("otp", "ओटीपी")),
    (ConsentMethod.signed_form, ("sign", "signature", "signed", "दस्तखत", "दस्तख़त", "हस्ताक्षर", "साइन", "form", "फॉर्म",
                                 "फ़ॉर्म", "फार्म", "काग़ज़", "कागज", "कागज़", "kagaz", "kaagaz", "paper", "पेपर", "अंगूठा")),
    (ConsentMethod.digital_click, ("app", "ऐप", "एप", "click", "clicked", "क्लिक", "tick", "टिक", "button", "बटन", "agree",
                                   "online", "ऑनलाइन", "link", "लिंक")),
    (ConsentMethod.recorded_call, ("call", "कॉल", "फ़ोन", "फोन", "phone", "recorded", "रिकॉर्डेड", "रिकॉर्ड")),
    (ConsentMethod.verbal, ("मुँह से", "मुंह से", "बोलकर", "बोल कर", "verbal", "zubani", "ज़ुबानी", "जुबानी")),
)  # fmt: skip
_WHAT = ("बीमा", "बिमा", "बीमे", "इन्शुरन्स", "इंसुरेंस", "इंश्योरेंस", "इंशोरेंस", "पॉलिसी", "पालिसी", "एफडी", "एफ़डी", "डिपॉजिट", "लोन", "कार्ड", "जमा", "प्लान",
         "योजना", "स्कीम", "सब कुछ", "सबकुछ", "सबके लिए", "सब के लिए", "उसके लिए", "इसके लिए", "दोनों", "insurance",
         "policy", "bima", "beema", "fd", "deposit", "loan", "card", "plan", "scheme", "everything", "sab kuch",
         "sabke liye", "sab ke liye", "uske liye", "iske liye", "dono", "both")  # fmt: skip
_KIND = ("बीमा", "बिमा", "बीमे", "इन्शुरन्स", "इंसुरेंस", "इंश्योरेंस", "इंशोरेंस", "पॉलिसी", "पालिसी", "एफडी", "एफ़डी", "डिपॉजिट", "जमा", "कार्ड", "प्लान", "योजना",
         "स्कीम", "insurance", "policy", "bima", "beema", "fd", "deposit", "card", "plan", "scheme")  # fmt: skip
_DOES = ("भर देगा", "भर देंगे", "भरेगा", "चुका", "चुक", "क्लियर", "काम आ", "बचत", "वापस मिल", "पे कर", "bhar", "chuka",
         "clear", "kaam aa", "bachat", "wapas mil", "vapas mil", "milega", "pay kar", "कवर", "मिलेगा", "मिलेंगे", "मिलता", "मिलती", "फ़ायदा", "फायदा", "ब्याज", "सुरक्षा", "कटे", "कटा", "कट गए", "कट गया",
         "cover", "benefit", "interest", "return", "protection", "deducted", "kata", "kate")  # fmt: skip


def _has(text: str, words: tuple[str, ...]) -> bool:
    folded = text.casefold()
    for word in words:
        if word.isascii():
            if re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", folded):
                return True
        # Devanagari: a whole word or its inflection, never inside another word ("बीमा" is not in "बीमार")
        elif re.search(rf"(?<![\u0900-\u097f]){re.escape(word)}(?![\u0915-\u0939\u0958-\u095f])", folded):
            return True
    return False


def _figure(text: str, figure: bool) -> bool:
    return figure or bool(re.search(r"\d{3}", text))  # a written figure of three digits or more


def consent_halves(
    text: str, language: Language, turn_id: TurnId, *, figure: bool = False
) -> tuple[Answer[bool], Answer[ConsentMethod]] | None:
    """The WHAT and HOW halves of a consent reply, each `Stated` or `Unclear(no_usable_answer)`, with the whole reply
    as evidence. None outside Hindi and Hinglish, or for an empty reply."""
    if language not in _READ or not text.strip():
        return None
    evidence = Evidence(quote=text, turn_id=turn_id)
    unclear = Unclear(reason=GapReason.no_usable_answer, evidence=evidence)
    given: Answer[bool] = (
        Stated[bool](value=True, evidence=evidence) if _has(text, _WHAT) or _figure(text, figure) else unclear
    )
    method = next((m for m, words in _HOW if _has(text, words)), None)
    how: Answer[ConsentMethod] = Stated[ConsentMethod](value=method, evidence=evidence) if method else unclear
    return given, how


def kind_is_half(text: str, language: Language, *, figure: bool = False) -> bool:
    """A reply to the kind question with no word for what the thing is, holding a figure or only what it does."""
    if language not in _READ or _has(text, _KIND):
        return False
    return _figure(text, figure) or _has(text, _DOES)
