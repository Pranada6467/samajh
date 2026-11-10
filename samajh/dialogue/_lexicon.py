"""Words and phrases the rule interpreter listens for, per language.

Every phrase is written the way a customer might say it and is passed through the same
`tokens()` as the customer's turn, so spelling variants are folded once, in `_FOLD`.
A token ending in `*` matches any token that starts with it.

Hindi and Hinglish share one table: Hinglish turns arrive in Devanagari, Latin or a mix, so
romanised Hindi words fold to Devanagari. English phrases are heard in every language.
The Tamil and Kannada tables are not human-reviewed.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from functools import cache
from itertools import product

from samajh.types import Language

Phrase = tuple[str, ...]

# Spelling variants and romanised Hindi, folded to one form before matching.
_FOLD: dict[str, str] = {
    # Devanagari variants
    "नही": "नहीं", "नहि": "नहीं", "हा": "हां", "हाजी": "हांजी", "मे": "में", "काल": "कॉल", "कोल": "कॉल",
    "टाईम": "टाइम", "बीजी": "बिजी", "मालुम": "मालूम", "बिलकुल": "बिल्कुल", "ठिक": "ठीक", "दुबारा": "दोबारा",
    "वह": "वो", "हलो": "हेलो", "हैलो": "हेलो", "हु": "हूं", "यहा": "यहां",
    # English loanwords that are also written in Devanagari
    "call": "कॉल", "phone": "फोन", "time": "टाइम", "busy": "बिजी", "interest": "इंटरेस्ट",
    "interested": "इंटरेस्टेड", "disturb": "डिस्टर्ब", "agent": "एजेंट", "manager": "मैनेजर",
    "officer": "ऑफिसर", "executive": "एग्जीक्यूटिव", "staff": "स्टाफ", "customer": "कस्टमर", "care": "केयर",
    "number": "नंबर", "wrong": "रॉन्ग", "repeat": "रिपीट", "hello": "हेलो", "ok": "ओके", "okay": "ओके",
    # romanised Hindi
    "nahin": "नहीं", "nahi": "नहीं", "nhi": "नहीं", "nai": "नहीं", "nahee": "नहीं", "na": "ना",
    "haan": "हां", "han": "हां", "haa": "हां", "ha": "हां", "haanji": "हांजी", "hanji": "हांजी", "ji": "जी",
    "baat": "बात", "bat": "बात", "karni": "करनी", "karna": "करना", "band": "बंद", "mat": "मत",
    "abhi": "अभी", "paas": "पास", "pas": "पास", "hoon": "हूं", "hun": "हूं", "hu": "हूं", "baad": "बाद",
    "mein": "में", "me": "में", "rakh": "रख", "raha": "रहा", "rahi": "रही", "rahe": "रहे", "se": "से",
    "hai": "है", "hain": "हैं", "karo": "करो", "kijiye": "कीजिए", "kariye": "करिए", "kar": "कर",
    "dijiye": "दीजिए", "rehne": "रहने", "rahne": "रहने", "bas": "बस", "jawab": "जवाब", "dena": "देना",
    "mana": "मना", "pata": "पता", "maloom": "मालूम", "malum": "मालूम", "yaad": "याद", "yad": "याद",
    "sahi": "सही", "theek": "ठीक", "thik": "ठीक", "galat": "गलत", "bilkul": "बिल्कुल", "phir": "फिर",
    "fir": "फिर", "dobara": "दोबारा", "samajh": "समझ", "samjha": "समझा", "samjhi": "समझी", "sunai": "सुनाई",
    "kya": "क्या", "matlab": "मतलब", "kaun": "कौन", "insaan": "इंसान", "insan": "इंसान", "aadmi": "आदमी",
    "admi": "आदमी", "kisi": "किसी", "chahiye": "चाहिए", "unka": "उनका", "unki": "उनकी", "unke": "उनके",
    "main": "मैं", "mai": "मैं", "hi": "ही", "bol": "बोल", "kaat": "काट", "pareshan": "परेशान", "tang": "तंग",
    "samay": "समय", "kabhi": "कभी", "aage": "आगे", "wo": "वो", "woh": "वो", "vo": "वो", "ghar": "घर",
    "par": "पर", "bahar": "बाहर", "gaye": "गए", "karao": "कराओ", "karaiye": "कराइए", "karwao": "करवाओ",
    "karwaiye": "करवाइए", "karunga": "करूंगा", "karungi": "करूंगी", "karenge": "करेंगे", "boliye": "बोलिए",
    "bataiye": "बताइए", "kahiye": "कहिए", "chaliye": "चलिए", "chalo": "चलो", "poochiye": "पूछिए",
    "puchiye": "पूछिए", "zaroor": "जरूर", "jaroor": "जरूर", "badhiye": "बढ़िए", "kyon": "क्यों", "kyu": "क्यों",
    "kyun": "क्यों", "achha": "अच्छा", "accha": "अच्छा", "acha": "अच्छा", "idea": "आइडिया", "dhyan": "ध्यान",
    "kaha": "कहा", "bola": "बोला", "awaaz": "आवाज", "awaz": "आवाज", "yahan": "यहां", "kahan": "कहां",
    "koi": "कोई", "rehta": "रहता", "rehte": "रहते", "to": "तो", "ek": "एक", "minute": "मिनट", "ruko": "रुको",
    "rukiye": "रुकिए", "kis": "किस", "cheez": "चीज", "chiz": "चीज", "sa": "सा", "si": "सी", "badhna": "बढ़ना",
    "jaanta": "जानता", "janta": "जानता", "jaanti": "जानती", "janti": "जानती", "mujhe": "मुझे",
    "dunga": "दूंगा", "dungi": "दूंगी", "dilchaspi": "दिलचस्पी", "kon": "कौन", "baar": "बार", "bar": "बार",
    "cut": "कट", "wohi": "वही", "wahi": "वही", "yehi": "यही", "yahi": "यही", "sakta": "सकता", "sakti": "सकती",
    "sakte": "सकते", "jod": "जोड़", "connect": "कनेक्ट", "tha": "था", "thi": "थी", "unhone": "उन्होंने",
    "unhonne": "उन्होंने", "usne": "उसने", "maine": "मैंने", "bataya": "बताया", "boli": "बोली", "bole": "बोले",
    "bye": "बाय", "office": "ऑफिस",
}  # fmt: skip

_NUKTA = "़"
_CHANDRABINDU, _ANUSVARA = "ँ", "ं"
_APOSTROPHES = "'’‘`"


def tokens(text: str) -> Phrase:
    """Comparison form of a turn or a lexicon phrase: folded words, no punctuation."""
    kept = []
    for ch in unicodedata.normalize("NFC", text).casefold():
        category = unicodedata.category(ch)
        if ch == _NUKTA or ch in _APOSTROPHES or category == "Cf":
            continue
        if ch == _CHANDRABINDU:
            kept.append(_ANUSVARA)
        elif category[0] in "LMN" or ch == "*":
            kept.append(ch)
        else:
            kept.append(" ")
    return tuple(_FOLD.get(word, word) for word in "".join(kept).split())


def _same(pattern: str, word: str) -> bool:
    return word.startswith(pattern[:-1]) if pattern.endswith("*") else word == pattern


@cache
def _by_first_word(phrases: frozenset[Phrase]) -> tuple[dict[str, tuple[Phrase, ...]], tuple[Phrase, ...]]:
    """Phrases grouped by their first word, and those whose first word is a `*` pattern."""
    exact: dict[str, list[Phrase]] = {}
    wild = []
    for phrase in sorted(phrases, key=lambda p: (-len(p), p)):  # longest first
        if phrase[0].endswith("*"):
            wild.append(phrase)
        else:
            exact.setdefault(phrase[0], []).append(phrase)
    return {first: tuple(group) for first, group in exact.items()}, tuple(wild)


def phrase_at(words: Phrase, k: int, phrases: frozenset[Phrase]) -> Phrase | None:
    """The longest of `phrases` that starts at word `k`, if any."""
    exact, wild = _by_first_word(phrases)
    for phrase in (*exact.get(words[k], ()), *wild):
        window = words[k : k + len(phrase)]
        if len(window) == len(phrase) and all(_same(p, w) for p, w in zip(phrase, window, strict=True)):
            return phrase
    return None


def found(words: Phrase, phrases: frozenset[Phrase]) -> list[Phrase]:
    """Each of `phrases` that occurs in `words`, once, in order of first occurrence."""
    hits = (phrase_at(words, k, phrases) for k in range(len(words)))
    return list(dict.fromkeys(hit for hit in hits if hit is not None))


def _phrases(*texts: str) -> frozenset[Phrase]:
    return frozenset(tokens(text) for text in texts)


def _cross(*parts: tuple[str, ...]) -> tuple[str, ...]:
    """Every phrase made by taking one alternative from each part, in order."""
    return tuple(" ".join(choice) for choice in product(*parts))


@dataclass(frozen=True)
class Lexicon:
    yes: frozenset[Phrase]
    yes_despite_no: frozenset[Phrase]  # "why not": affirmative though it holds a no-word
    no: frozenset[Phrase]
    no_at_start: frozenset[Phrase]  # counts only as the first word ("ना", not "है ना")
    wrong_person: frozenset[Phrase]
    is_self: frozenset[Phrase]  # "speaking", "it is me"
    who: frozenset[Phrase]  # "who is this?"
    wants_human: frozenset[Phrase]
    decline: frozenset[Phrase]
    # A weak signal, and only in a short turn ("बंद करो"): the bot asks before it ends the call. No bare
    # "later" here: "बाद में पता चला" (I found out later) is what a misled customer says.
    decline_short: frozenset[Phrase]
    dont_know: frozenset[Phrase]
    asks_repeat: frozenset[Phrase]
    asks_repeat_whole: frozenset[Phrase]  # counts only when it is the whole turn ("क्या?")
    filler: frozenset[Phrase]  # a turn made only of these says nothing
    # Past tense and reported speech: with one of these a refusal may be quoted from the sale ("मैंने कहा
    # था मुझे इंटरेस्ट नहीं है"), so it does not end the call unasked. Hindi and English only: the Tamil
    # and Kannada tables have none, and a quoted refusal still ends a call in those languages.
    recounts: frozenset[Phrase]

    def __or__(self, other: Lexicon) -> Lexicon:
        return Lexicon(*(getattr(self, name) | getattr(other, name) for name in self.__dataclass_fields__))


_EN = Lexicon(
    yes=_phrases("yes", "yeah", "yep", "ya", "ok", "correct", "right", "sure", "speaking", "go ahead",
                 "continue", "proceed", "of course", "thats me", "this is he", "this is she"),
    yes_despite_no=_phrases("why not", "no problem"),
    no=_phrases("no", "nope", "wrong", "incorrect", "not correct", "not right"),
    no_at_start=frozenset(),
    wrong_person=_phrases("wrong number", "not here", "not available", "not home", "not at home", "no such person",
                          "his wife", "her husband", "his son", "his daughter", "her son", "her daughter",
                          "he is not", "she is not", "my husband", "my wife", "my father", "my mother",
                          "his", "he is", "hes", "she is", "shes", "he was", "she was", "at work"),
    is_self=_phrases("speaking", "thats me", "this is he", "this is she", "it is me", "its me"),
    who=_phrases("who", "whos", "where from"),
    wants_human=_phrases(
        "human", "real person", "live agent", "representative", "customer care executive",
        *_cross(("talk to", "speak to", "speak with", "talk with", "connect me to", "transfer me to", "give me"),
                ("a", "an", "some", "your", "the"),
                ("person", "agent", "manager", "officer", "executive", "someone", "somebody", "supervisor")),
        "talk to someone", "speak to someone", "talk to somebody", "speak to somebody",
    ),
    decline=_phrases(
        "no thanks", "no thank you", "stop calling", "stop the call", "stop this", "dont call",
        "do not call", "hang up", "i am busy", "im busy", "busy right now", "call later", "call me later",
        "call back later", "later please", "end the call", "end this call", "i decline",
        "remove my number", "dont want to talk", "do not want to talk", "dont want to continue",
        "do not want to continue", "i am not interested", "im not interested", "not interested in this",
        "not available to talk", "cant talk", "cannot talk", "not free right now",
        "not interested in talking", "leave me alone", "cut the call",
    ),
    decline_short=_phrases("stop", "not now", "leave it", "enough", "not interested", "dont want to answer",
                           "do not want to answer", "bye"),
    dont_know=_phrases("dont know", "do not know", "no idea", "not sure", "cant remember", "dont remember",
                       "do not remember", "cannot remember", "cant recall"),
    asks_repeat=_phrases("repeat", "pardon", "come again", "say again", "say that again", "cant hear",
                         "cannot hear", "didnt understand", "dont understand", "did not understand",
                         "which one", "what thing", "which thing", "what do you mean"),
    asks_repeat_whole=_phrases("what", "sorry", "hello", "hello hello", "huh", "excuse me"),
    filler=_phrases("ok", "hmm", "hm", "uh", "um", "er", "ah", "oh", "well", "so", "yes", "yeah", "wait",
                    "one minute", "one second"),
    recounts=_phrases("said", "told", "they", "was", "were"),
)  # fmt: skip

_HUMAN_HI = ("इंसान", "आदमी", "व्यक्ति", "एजेंट", "मैनेजर", "अधिकारी", "ऑफिसर", "एग्जीक्यूटिव", "स्टाफ",
             "कर्मचारी", "बंदे", "किसी", "कस्टमर केयर", "किसी और", "ब्रांच")  # fmt: skip
_ASK_TO_TALK_HI = ("करा*", "करवा*", "करनी है", "करना है", "करनी चाहिए", "करना चाहता*", "करना चाहती*",
                   "करना चाहते", "करूंगा", "करूंगी", "करेंगे", "कर सकता*", "कर सकती*", "कर सकते")  # fmt: skip

_HI = Lexicon(
    yes=_phrases("हां", "जी", "हांजी", "बिल्कुल", "सही", "ठीक", "यस", "ओके", "करेक्ट", "राइट", "बोलिए", "बताइए",
                 "कहिए", "बोल रहा हूं", "बोल रही हूं", "मैं ही", "चलिए", "चलो", "पूछिए", "पूछो", "बढ़िए", "जरूर",
                 "वही", "यही"),
    yes_despite_no=_phrases("क्यों नहीं", "कोई दिक्कत नहीं", "कोई प्रॉब्लम नहीं"),
    no=_phrases("नहीं", "गलत", "रॉन्ग", "मत"),
    no_at_start=_phrases("ना", "न"),
    wrong_person=_phrases("रॉन्ग नंबर", "गलत नंबर", "गलत लग*", "उनका", "उनकी", "उनके", "बाहर गए", "बाहर गई", "घर पर नहीं",
                          "यहां नहीं", "कोई नहीं", "नहीं रहते", "नहीं रहता", "नहीं रहती", "मेरे पति", "मेरी पत्नी",
                          "मेरे पापा", "मेरी मम्मी", "पापा का", "मम्मी का", "उसका", "उसकी", "उसके", "इनका", "इनकी",
                          "इनके", "बाहर हैं", "बाहर है", "ऑफिस गए", "ऑफिस गई", "काम पर गए", "काम पर गई",
                          "नहा रहे", "नहा रही", "सो रहे", "सो रही"),
    is_self=_phrases("बोल रहा हूं", "बोल रही हूं", "मैं ही"),
    who=_phrases("कौन", "किसका", "कहां से", "कहां"),
    wants_human=_phrases(
        *_cross(_HUMAN_HI, ("से बात",), _ASK_TO_TALK_HI),
        *_cross(("इंसान", "आदमी", "एजेंट", "मैनेजर", "अधिकारी", "ऑफिसर"), ("चाहिए", "को बुला*")),
        "असली आदमी", "असली इंसान", "किसी और से जोड़*", "किसी से जोड़*", "से कनेक्ट कर*",
    ),
    decline=_phrases(
        "बात नहीं करनी", "बात नहीं करना", "बात करनी नहीं", "नहीं करनी बात", "नहीं बात करनी", "कॉल बंद", "फोन बंद",
        "कॉल कट", "फोन कट", "कॉल काट*",
        "फोन काट*", "फोन रख*", "कॉल रख*", "कॉल मत", "फोन मत", "परेशान मत", "डिस्टर्ब मत",
        "तंग मत", "अभी टाइम नहीं", "अभी समय नहीं", "पास टाइम नहीं", "पास समय नहीं", "बिजी हूं", "व्यस्त हूं",
        "अभी बिजी", "बाद में कॉल", "बाद में बात", "बाद में फोन", "बाद में करना", "बाद में करिए", "बाद में कीजिए",
        "इंटरेस्ट नहीं है", "इंटरेस्टेड नहीं हूं", "दिलचस्पी नहीं है", "जवाब नहीं देना", "जवाब नहीं दूंगा",
        "जवाब नहीं दूंगी", "मना कर रहा हूं", "मना कर रही हूं", "मना करता हूं", "मना करती हूं", "आगे नहीं बढ़ना",
        "कॉल नहीं चाहिए", "not interested हूं",
    ),
    decline_short=_phrases("बंद करो", "बंद कीजिए", "बंद करिए", "बंद कर दो", "बंद कर दीजिए", "बस करो", "बस कीजिए",
                           "रहने दो", "रहने दीजिए", "रहने दें", "फिर कभी", "नहीं बताना", "नहीं बताऊंगा",
                           "नहीं बताऊंगी", "टाइम नहीं है", "समय नहीं है", "बात नहीं कर सकता", "बात नहीं कर सकती",
                           "बाय", "रखता हूं", "रखती हूं"),
    dont_know=_phrases("पता नहीं", "नहीं पता", "पता ही नहीं", "मालूम नहीं", "नहीं मालूम", "याद नहीं", "याद ही नहीं",
                       "नहीं याद", "ध्यान नहीं",
                       "जानकारी नहीं", "आइडिया नहीं", "नहीं जानता", "नहीं जानती", "क्या पता"),
    asks_repeat=_phrases("फिर से", "एक बार फिर", "दोबारा", "समझा नहीं", "समझी नहीं", "समझ नहीं", "समझ में नहीं", "नहीं समझा",
                         "नहीं समझी", "सुनाई नहीं", "आवाज नहीं", "क्या कहा", "क्या बोला", "क्या मतलब", "रिपीट",
                         "कौन सी चीज", "कौन सा", "किस चीज"),
    asks_repeat_whole=_phrases("क्या", "मतलब", "हेलो", "हेलो हेलो", "जी क्या", "हां क्या"),
    filler=_phrases("हम्म", "हूं", "हां", "जी", "हांजी", "अच्छा", "ओके", "ठीक", "है", "तो", "वो", "एक", "मिनट",
                    "रुको", "रुकिए"),
    recounts=_phrases("था", "थी", "थे", "उन्होंने", "उसने", "मैंने", "बोला", "बोली", "बोले", "कहा", "बताया"),
)  # fmt: skip

_HUMAN_TA = ("மனிதரிடம்", "மனுஷன் கிட்ட", "ஆள் கிட்ட", "யாராவது கிட்ட", "யாரிடமாவது", "அதிகாரியிடம்",
             "அதிகாரி கிட்ட", "மேனேஜர் கிட்ட", "மேனேஜரிடம்", "ஏஜென்ட் கிட்ட", "கஸ்டமர் கேர் கிட்ட",
             "நேரடியா", "நேரடியாக")  # fmt: skip
_ASK_TO_TALK_TA = ("பேசணும்", "பேசவேண்டும்", "பேச வேண்டும்", "பேச வேணும்", "பேசலாமா", "பேச முடியுமா",
                   "பேச வையுங்க")  # fmt: skip

_TA = Lexicon(
    yes=_phrases("ஆமா", "ஆமாம்", "ஆம்", "ஆமாங்க", "சரி", "சரிங்க", "சரிதான்", "சொல்லுங்க", "சொல்லுங்கள்",
                 "நான்தான்", "நான் தான்", "பேசுறேன்", "பேசுகிறேன்", "தொடருங்க", "தொடரலாம்", "கேளுங்க", "பேசுங்க",
                 "ஓகே", "யெஸ்", "கரெக்ட்", "அதே", "அதேதான்", "aama",
                 "aamam", "sari"),
    yes_despite_no=frozenset(),
    no=_phrases("இல்ல", "இல்லை", "இல்லைங்க", "இல்லங்க", "வேண்டாம்", "வேணாம்", "தப்பு", "தவறு", "கிடையாது",
                "illa", "illai", "vendam", "venam"),
    no_at_start=frozenset(),
    wrong_person=_phrases("ராங் நம்பர்", "தவறான நம்பர*", "தப்பான நம்பர*", "தவறான எண்", "அவரோட", "அவருடைய", "அவங்களோட",
                          "வெளியே போயிருக்கார்", "வெளியே போயிருக்காங்க", "வீட்டில் இல்ல", "வீட்ல இல்ல", "இங்க இல்ல",
                          "என் கணவர்", "என் மனைவி", "என் அப்பா", "என் அம்மா"),
    is_self=_phrases("நான்தான்", "நான் தான்", "பேசுறேன்", "பேசுகிறேன்"),
    who=_phrases("யார்", "யாரு", "யாருங்க", "எங்கிருந்து"),
    wants_human=_phrases(*_cross(_HUMAN_TA, _ASK_TO_TALK_TA), "மனிதர் வேண்டும்", "மனிதர் வேணும்",
                         "ஆளை கூப்பிடுங்க"),
    decline=_phrases(
        "பேச விருப்பமில்லை", "பேச விருப்பம் இல்லை", "பேச விருப்பம் இல்ல", "பேச விரும்பல", "பேச வேண்டாம்",
        "பேச வேணாம்", "பேச முடியாது", "கால் கட் பண்ணுங்க", "வேற நாள் கூப்பிடுங்க", "வேற ஒரு நாள் கூப்பிடுங்க",
        "கால் வேண்டாம்", "கால் வேணாம்", "அழைப்பு வேண்டாம்", "போன் வைக்கிறேன்", "போனை வைக்கிறேன்",
        "எனக்கு நேரம் இல்ல", "எனக்கு நேரம் இல்லை", "இப்போ நேரம் இல்ல", "இப்போது நேரம் இல்லை", "பிஸியா இருக்கேன்",
        "வேலையா இருக்கேன்", "அப்புறம் கூப்பிடுங்க", "அப்புறம் பேசலாம்", "பிறகு அழையுங்கள்", "பிறகு பேசலாம்",
        "தொந்தரவு பண்ணாதீங்க", "கூப்பிடாதீங்க", "அழைக்காதீர்கள்", "ஆர்வம் இல்லை", "ஆர்வம் இல்ல",
    ),
    decline_short=_phrases("நிறுத்துங்க", "நிறுத்துங்கள்", "போதும்"),
    dont_know=_phrases("தெரியாது", "தெரியல", "தெரியலை", "தெரியவில்லை", "தெரியலங்க", "தெரியாதுங்க", "ஞாபகம் இல்ல",
                       "ஞாபகம் இல்லை", "நினைவில்லை", "நினைவில்ல", "நினைவு இல்லை", "நினைவில் இல்லை", "theriyadhu", "theriyathu",
                       "theriyala"),
    asks_repeat=_phrases("புரியல", "புரியலை", "புரியவில்லை", "மறுபடியும்", "திரும்ப சொல்லுங்க", "இன்னொரு தடவை",
                         "இன்னொரு முறை", "கேக்கல", "கேட்கல", "கேட்கவில்லை", "என்ன சொன்னீங்க", "எந்த பொருள்"),
    asks_repeat_whole=_phrases("என்ன", "என்னது", "ஹலோ", "எது"),
    filler=_phrases("ம்ம்", "ம்", "சரி", "ஆமா", "ஓகே", "ஹ்ம்", "அப்படியா", "ஆ"),
    recounts=frozenset(),
)  # fmt: skip

_HUMAN_KN = ("ಮನುಷ್ಯ*", "ವ್ಯಕ್ತಿ*", "ಅಧಿಕಾರಿ*", "ಮ್ಯಾನೇಜರ್*", "ಏಜೆಂಟ್*", "ಸಿಬ್ಬಂದಿ*", "ಕಸ್ಟಮರ್ ಕೇರ್", "ಯಾರಾದರೂ",
             "ಯಾರಾದ್ರೂ")  # fmt: skip
_ASK_TO_TALK_KN = ("ಮಾತಾಡಬೇಕು", "ಮಾತನಾಡಬೇಕು", "ಮಾತಾಡ್ಬೇಕು", "ಮಾತಾಡಲು ಬಿಡಿ", "ಮಾತಾಡಿಸಿ", "ಮಾತಾಡಬಹುದಾ")

_KN = Lexicon(
    yes=_phrases("ಹೌದು", "ಹೌದ್ರಿ", "ಹೂ", "ಹೂಂ", "ಹಾ", "ಹಾಂ", "ಸರಿ", "ಆಯ್ತು", "ಹೇಳಿ", "ನಾನೇ", "ಮಾತಾಡ್ತಿದ್ದೀನಿ",
                 "ಮಾತನಾಡುತ್ತಿದ್ದೇನೆ", "ಮುಂದುವರಿಸಿ", "ಮುಂದೆ ಹೋಗಿ", "ಕೇಳಿ", "ಖಂಡಿತ", "ಓಕೆ", "ಯೆಸ್", "ಕರೆಕ್ಟ್", "ಅದೇ",
                 "houdu", "sari"),
    yes_despite_no=frozenset(),
    no=_phrases("ಇಲ್ಲ", "ಇಲ್ಲಾ", "ಇಲ್ರಿ", "ಬೇಡ", "ತಪ್ಪು", "ಅಲ್ಲ", "illa", "beda"),
    no_at_start=frozenset(),
    wrong_person=_phrases("ರಾಂಗ್ ನಂಬರ್", "ತಪ್ಪು ನಂಬರ್", "ತಪ್ಪಾದ ನಂಬರ್", "ತಪ್ಪು ಸಂಖ್ಯೆ", "ಇಲ್ಲಿಲ್ಲ", "ಅವರ", "ಹೊರಗೆ ಹೋಗಿದ್ದಾರೆ", "ಮನೆಯಲ್ಲಿ ಇಲ್ಲ",
                          "ಇಲ್ಲಿ ಇಲ್ಲ", "ನನ್ನ ಗಂಡ", "ನನ್ನ ಹೆಂಡತಿ", "ನನ್ನ ಅಪ್ಪ", "ನನ್ನ ಅಮ್ಮ"),
    is_self=_phrases("ನಾನೇ", "ಮಾತಾಡ್ತಿದ್ದೀನಿ", "ಮಾತನಾಡುತ್ತಿದ್ದೇನೆ"),
    who=_phrases("ಯಾರು", "ಯಾರ್", "ಯಾರಿದು", "ಎಲ್ಲಿಂದ"),
    wants_human=_phrases(*_cross(_HUMAN_KN, ("", "ಜೊತೆ", "ಹತ್ರ", "ಹತ್ತಿರ"), _ASK_TO_TALK_KN), "ಮನುಷ್ಯ ಬೇಕು",
                         "ಮನುಷ್ಯರು ಬೇಕು"),
    decline=_phrases(
        "ಮಾತಾಡಲು ಇಷ್ಟ ಇಲ್ಲ", "ಮಾತಾಡೋಕೆ ಇಷ್ಟ ಇಲ್ಲ", "ಮಾತಾಡೋದು ಬೇಡ", "ಕರೆ ಬೇಡ", "ಕಾಲ್ ಬೇಡ", "ಫೋನ್ ಇಡ್ತೀನಿ",
        "ಮಾತನಾಡಲು ಸಾಧ್ಯವಿಲ್ಲ", "ಮಾತಾಡೋಕೆ ಆಗಲ್ಲ", "ನಂತರ ಕರೆ ಮಾಡಿ", "ನಂತರ ಕಾಲ್ ಮಾಡಿ", "ನಂತರ ಮಾತನಾಡುತ್ತೇನೆ",
        "ಫೋನ್ ಇಡುತ್ತೇನೆ", "ನನಗೆ ಸಮಯ ಇಲ್ಲ", "ಈಗ ಸಮಯ ಇಲ್ಲ", "ನನಗೆ ಟೈಮ್ ಇಲ್ಲ", "ಈಗ ಟೈಮ್ ಇಲ್ಲ", "ಬ್ಯುಸಿ ಇದ್ದೀನಿ",
        "ಬಿಸಿ ಇದ್ದೀನಿ", "ಕೆಲಸದಲ್ಲಿ ಇದ್ದೀನಿ", "ಆಮೇಲೆ ಕರೆ ಮಾಡಿ", "ಆಮೇಲೆ ಕಾಲ್ ಮಾಡಿ", "ಆಮೇಲೆ ಮಾತಾಡೋಣ",
        "ತೊಂದರೆ ಕೊಡಬೇಡಿ", "ಕರೆ ಮಾಡಬೇಡಿ", "ಕಾಲ್ ಮಾಡಬೇಡಿ", "ಆಸಕ್ತಿ ಇಲ್ಲ",
    ),
    decline_short=_phrases("ನಿಲ್ಲಿಸಿ", "ಸಾಕು", "ಈಗ ಬೇಡ"),
    dont_know=_phrases("ಗೊತ್ತಿಲ್ಲ", "ಗೊತ್ತಿಲ್ರಿ", "ಗೊತ್ತು ಇಲ್ಲ", "ನೆನಪಿಲ್ಲ", "ನೆನಪು ಇಲ್ಲ", "ನೆನಪಾಗ್ತಿಲ್ಲ", "ನೆನಪಾಗುತ್ತಿಲ್ಲ",
                       "ಗೊತ್ತಾಗ್ತಿಲ್ಲ", "ತಿಳಿದಿಲ್ಲ", "gottilla",
                       "nenapilla"),
    asks_repeat=_phrases("ಅರ್ಥ ಆಗಲಿಲ್ಲ", "ಅರ್ಥವಾಗಲಿಲ್ಲ", "ಅರ್ಥ ಆಗ್ಲಿಲ್ಲ", "ಮತ್ತೆ ಹೇಳಿ", "ಇನ್ನೊಮ್ಮೆ", "ಇನ್ನೊಂದು ಸಲ",
                         "ಕೇಳಿಸ್ತಿಲ್ಲ", "ಕೇಳಿಸಲಿಲ್ಲ", "ಏನು ಹೇಳಿದ್ರಿ", "ಯಾವ ವಸ್ತು"),
    asks_repeat_whole=_phrases("ಏನು", "ಏನ್", "ಹಲೋ", "ಯಾವುದು"),
    filler=_phrases("ಹೂಂ", "ಹೂ", "ಹಾ", "ಸರಿ", "ಓಕೆ", "ಹ್ಮ್", "ಹೌದಾ", "ಆ"),
    recounts=frozenset(),
)  # fmt: skip

LEXICONS: dict[Language, Lexicon] = {
    Language.hi: _HI | _EN,
    Language.hi_en: _HI | _EN,
    Language.ta: _TA | _EN,
    Language.kn: _KN | _EN,
}
