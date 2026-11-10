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
    # added for call v2 (P2)
    "ka": "का", "ki": "की", "ke": "के", "wale": "वाले", "waale": "वाले", "hamesha": "हमेशा", "bolte": "बोलते",
    "kehte": "कहते", "kahte": "कहते", "dete": "देते", "batata": "बताता", "batate": "बताते", "drive": "ड्राइव",
    "meeting": "मीटिंग", "kal": "कल", "shaam": "शाम", "sham": "शाम", "subah": "सुबह", "raat": "रात",
    "baje": "बजे", "ghante": "घंटे", "ghanta": "घंटा", "parso": "परसों", "parson": "परसों", "sawal": "सवाल",
    "sawaal": "सवाल", "question": "सवाल", "questions": "सवाल", "pucho": "पूछो", "poocho": "पूछो", "jaldi": "जल्दी",
    "bhi": "भी", "lekin": "लेकिन", "magar": "मगर", "bank": "बैंक", "fraud": "फ्रॉड", "asli": "असली",
    "nakli": "नकली", "liya": "लिया", "kuch": "कुछ", "sirf": "सिर्फ", "loan": "लोन", "free": "फ्री",
    "marzi": "मर्जी", "marji": "मर्जी", "marzee": "मर्जी", "zaroori": "जरूरी", "zaruri": "जरूरी", "jaruri": "जरूरी",
    "jaroori": "जरूरी", "apni": "अपनी", "meri": "मेरी", "khud": "खुद", "papa": "पापा", "daddy": "डैडी",
    "bhai": "भाई", "bhaiya": "भैया", "wife": "वाइफ", "husband": "हस्बैंड", "beta": "बेटा", "beti": "बेटी",
    "mummy": "मम्मी", "sir": "सर", "madam": "मैडम", "chahte": "चाहते", "possible": "पॉसिबल",
    "hindi": "हिंदी", "tamil": "तमिल", "english": "इंग्लिश", "angrezi": "अंग्रेजी", "kannada": "कन्नड",
    "marathi": "मराठी", "telugu": "तेलुगु", "bengali": "बंगाली", "bangla": "बांग्ला", "gujarati": "गुजराती",
    "malayalam": "मलयालम", "punjabi": "पंजाबी", "odia": "उडिया", "oriya": "उडिया", "aati": "आती", "aata": "आता",
    "diya": "दिया", "diye": "दिए", "paise": "पैसे", "paisa": "पैसा",
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
    # --- call v2 (P2). Empty by default: a language without a list simply never hears that signal.
    # A claim to be the person asked for. "बोलिए" or "go ahead" is not one: a relative says it too.
    identity_yes: frozenset[Phrase] = frozenset()
    self_ok: frozenset[Phrase] = frozenset()  # words that may stand beside that claim ("जी", "sir", "मैं")
    first_person: frozenset[Phrase] = frozenset()  # "मैं", "I": lets a name ride along ("मैं रमेश हूँ")
    # A relation or a third-person word: before the loan is named, a speaker who uses one is not the borrower.
    kin: frozenset[Phrase] = frozenset()
    possessive: frozenset[Phrase] = (
        frozenset()
    )  # "का/की/के": "रमेश की वाइफ़"; read at the first-name question only
    asks_who: frozenset[Phrase] = frozenset()  # "who is calling?", "is this a fraud call?"
    do_not_call: frozenset[Phrase] = frozenset()  # a refusal that also rules out a call back
    call_later: frozenset[Phrase] = frozenset()  # "call me later", "some other day"
    call_words: frozenset[Phrase] = frozenset()  # with a time word, a request for a call at that time
    time_words: frozenset[Phrase] = frozenset()
    occupied: frozenset[Phrase] = frozenset()  # "I am driving": cannot talk now
    hurry: frozenset[Phrase] = frozenset()  # "be quick": busy, but go on
    # Third-person or habitual narration ("वो लोग हमेशा बोलते हैं", "they always hang up"): refusal words
    # inside such a turn are an account of the sale, not a refusal of this call.
    narrative: frozenset[Phrase] = frozenset()
    took_nothing: frozenset[Phrase] = frozenset()  # "I took nothing with the loan"
    nothing: frozenset[Phrase] = frozenset()  # "कुछ नहीं", "nothing": a bare denial, read as "no"
    paid_nothing: frozenset[Phrase] = frozenset()  # "it was free", "paid nothing"
    own_choice: frozenset[Phrase] = frozenset()  # "it was my choice", "not required"
    forced: frozenset[Phrase] = frozenset()  # "it was compulsory", "nobody asked me": cancels own_choice
    language_cue: frozenset[Phrase] = frozenset()  # with a language name: a request to speak it
    cannot_follow: frozenset[Phrase] = frozenset()  # "हिंदी नहीं आती": with the call's own language

    def __or__(self, other: Lexicon) -> Lexicon:
        return Lexicon(*(getattr(self, name) | getattr(other, name) for name in self.__dataclass_fields__))


_EN = Lexicon(
    yes=_phrases("yes", "yeah", "yep", "ya", "ok", "correct", "right", "sure", "speaking", "go ahead",
                 "continue", "proceed", "of course", "thats me", "this is he", "this is she"),
    yes_despite_no=_phrases("why not", "no problem"),
    no=_phrases("no", "nope", "wrong", "incorrect", "not correct", "not right"),
    no_at_start=frozenset(),
    wrong_person=_phrases("wrong number", "not here", "not home", "not at home", "no such person",
                          "his wife", "her husband", "his son", "his daughter", "her son", "her daughter",
                          "he is not", "she is not", "my husband", "my wife", "my father", "my mother",
                          "his", "he is", "hes", "she is", "shes", "he was", "she was"),
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
        "do not call", "hang up", "call later", "call me later",
        "call back later", "later please", "end the call", "end this call", "i decline",
        "remove my number", "dont want to talk", "do not want to talk", "dont want to continue",
        "do not want to continue", "i am not interested", "im not interested", "not interested in this",
        "not available to talk", "cant talk", "cannot talk", "not free right now",
        "not interested in talking", "leave me alone", "cut the call",
        # call v2
        "have to go", "got to go", "gotta go", "need to go", "dont ask", "do not ask", "stop asking", "rather not",
        "im done", "i am done", "thats it", "no more questions", "dont have time", "do not have time",
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
    identity_yes=_phrases("yes", "yeah", "yep", "ya", "correct", "right", "speaking", "thats me", "this is he",
                          "this is she", "its me", "it is me", "i am", "myself"),
    self_ok=_phrases("sir", "madam", "hello", "hi", "tell me", "please", "here", "this is", "me", "go ahead", "ok",
                     "okay", "good morning", "good afternoon", "good evening"),
    first_person=_phrases("i", "i am", "im", "this is", "myself", "speaking"),
    kin=_phrases("wife", "husband", "son", "daughter", "father", "mother", "dad", "mom", "mum", "mummy", "papa",
                 "daddy", "brother", "sister", "uncle", "aunt", "neighbour", "neighbor", "colleague", "assistant",
                 "secretary", "driver", "servant", "friend", "boss", "he is", "she is", "hes", "shes", "he was",
                 "she was", "his", "her", "him", "he will", "she will", "he has", "she has", "sir is", "madam is",
                 "not here", "not at home", "not home", "office"),
    asks_who=_phrases("who is this", "whos this", "who is calling", "whos calling", "who are you", "who is speaking",
                      "where are you calling from", "calling from where", "where from", "is this real",
                      "is this genuine", "real call", "genuine call", "fake call", "fraud call", "scam",
                      "is this a fraud", "how do i know", "how can i trust", "which bank", "which company"),
    do_not_call=_phrases("dont call", "do not call", "stop calling", "never call", "remove my number"),
    call_later=_phrases("call later", "call me later", "call back later", "call me back", "call back", "later please",
                        "some other day", "some other time", "another day", "another time", "other day",
                        "talk later", "speak later"),
    call_words=_phrases("call", "phone", "ring", "talk", "speak"),
    time_words=_phrases("tomorrow", "tonight", "evening", "morning", "afternoon", "night", "oclock", "pm", "hour",
                        "hours", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
                        "weekend", "next week"),
    occupied=_phrases("driving", "in a meeting", "at work", "in office", "in the office", "on the way",
                      "in the hospital", "busy right now", "i am busy", "im busy", "busy now", "on another call",
                      "eating", "in a train", "on a train", "travelling", "traveling"),
    hurry=_phrases("quick", "quickly", "fast", "make it quick", "be quick", "hurry"),
    narrative=_phrases("they", "them", "their", "always", "keeps", "keep saying", "every time", "nobody", "no one",
                       "but", "the agent", "agent said", "the branch", "the bank", "bank people",
                       "manager said", "added", "in my loan", "this thing", "at that time", "picks up"),
    took_nothing=_phrases("took nothing", "nothing else", "only the loan", "just the loan", "only loan", "just loan",
                          "didnt take anything", "did not take anything", "didnt buy anything",
                          "did not buy anything", "nothing with the loan"),
    nothing=_phrases("nothing", "no", "nope", "none", "nothing at all"),
    paid_nothing=_phrases("free", "paid nothing", "nothing", "zero", "didnt pay", "did not pay", "no money"),
    own_choice=_phrases("my choice", "own choice", "my wish", "optional", "not compulsory", "not required",
                        "not mandatory", "not necessary", "i wanted it", "voluntary"),
    forced=_phrases("compulsory", "must", "mandatory", "forced", "had to", "required", "no choice"),
    language_cue=_phrases("in", "please", "speak", "talk", "language", "can you", "only"),
    cannot_follow=_phrases("dont understand", "do not understand", "dont speak", "do not speak", "cant understand"),
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
    is_self=_phrases("बोल रहा हूं", "बोल रही हूं", "मैं ही", "मुझसे ही", "आप मुझसे ही बात कर रहे हैं"),
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
        "तंग मत", "अभी टाइम नहीं", "अभी समय नहीं", "पास टाइम नहीं", "पास समय नहीं",
        "बाद में कॉल", "बाद में बात", "बाद में फोन", "बाद में करना", "बाद में करिए", "बाद में कीजिए",
        "इंटरेस्ट नहीं है", "इंटरेस्टेड नहीं हूं", "दिलचस्पी नहीं है", "जवाब नहीं देना", "जवाब नहीं दूंगा",
        "जवाब नहीं दूंगी", "मना कर रहा हूं", "मना कर रही हूं", "मना करता हूं", "मना करती हूं", "आगे नहीं बढ़ना",
        "कॉल नहीं चाहिए", "not interested हूं",
        # call v2
        "कुछ नहीं कहना", "कुछ नहीं बताना", "नहीं बताना", "कोई रुचि नहीं", "रुचि नहीं", "मत पूछो", "मत पूछिए", "सवाल मत",
        "बस हो गया", "हो गया बस", "बहुत हो गया", "छोड़िए ये सब", "छोड़ो ये सब", "ये सब छोड़िए", "नहीं चाहिए ये कॉल",
        "ये कॉल नहीं चाहिए", "नहीं बताऊंगा", "नहीं बताऊंगी", "सवाल नहीं चाहिए", "बात नहीं हो सकती", "पॉसिबल नहीं",
        "नहीं हो पाएगा", "अब और नहीं", "ये बातें नहीं करनी", "नहीं करनी मुझे", "बात नहीं करनी",
    ),
    decline_short=_phrases("बंद करो", "बंद कीजिए", "बंद करिए", "बंद कर दो", "बंद कर दीजिए", "बस करो", "बस कीजिए",
                           "रहने दो", "रहने दीजिए", "रहने दें", "फिर कभी", "नहीं बताना", "नहीं बताऊंगा",
                           "नहीं बताऊंगी", "टाइम नहीं है", "समय नहीं है", "बात नहीं कर सकता", "बात नहीं कर सकती",
                           "बाय", "रखता हूं", "रखती हूं", "छोड़िए", "छोड़ो", "बस अब"),
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
    identity_yes=_phrases("हां", "जी", "हांजी", "जी हां", "बिल्कुल", "सही", "यस", "करेक्ट", "राइट", "बोल रहा हूं",
                          "बोल रही हूं", "मैं ही", "मैं हूं"),
    self_ok=_phrases("जी", "सर", "साहब", "मैडम", "बोलिए", "बताइए", "कहिए", "बोलो", "बताओ", "हेलो", "नमस्ते", "नमस्कार",
                     "मैं", "ही", "हूं", "खुद", "बोल", "रहा", "रही", "ओके", "ठीक", "है", "प्रणाम", "राम राम"),
    first_person=_phrases("मैं", "बोल रहा हूं", "बोल रही हूं", "हूं"),
    kin=_phrases("पापा", "पिताजी", "पिता", "डैडी", "डैड", "मम्मी", "मां", "माताजी", "बेटा", "बेटी", "पति", "पत्नी",
                 "वाइफ", "हस्बैंड", "मिसेज", "भाई", "भैया", "भाभी", "बहन", "दीदी", "चाचा", "चाची", "मामा", "मामी",
                 "ताऊ", "ससुर", "सास", "बहू", "दामाद", "जीजा", "नाना", "नानी", "दादा", "दादी", "पोता", "पोती", "पड़ोसी",
                 "ड्राइवर", "नौकर", "असिस्टेंट", "सेक्रेटरी", "कलीग", "दोस्त", "मालिक", "उनका", "उनकी", "उनके",
                 "उनसे", "उनको", "उन्हें", "वो नहा", "वो सो", "वो बाहर", "वो तो", "गए हैं", "गई हैं", "गया है", "गए है",
                 "बुला*", "फोन देत*", "फोन दे रह*", "डेस्क", "ऑफिस से", "घर से बोल*", "घर पर ही हैं", "घर पर हैं"),
    possessive=_phrases("का", "की", "के"),
    asks_who=_phrases("कौन बोल रहा", "कौन बोल रहे", "कौन बोल रही", "कौन हो", "कौन हैं", "आप कौन", "कहां से बोल*",
                      "कहां से हो", "कहां से हैं", "किधर से", "किस बैंक", "किस कंपनी", "बैंक से हो", "बैंक से हैं",
                      "फ्रॉड कॉल", "फ्रॉड तो नहीं", "फ्राड", "असली", "नकली", "फर्जी", "स्कैम", "कैसे पता", "कैसे मानूं",
                      "कैसे मान लूं", "भरोसा कैसे", "किसलिए कॉल", "क्यों कॉल"),
    do_not_call=_phrases("कॉल मत", "फोन मत", "कॉल नहीं चाहिए", "नंबर हटा*", "कॉल ना करें", "कॉल न करें",
                         "फोन ना करें", "फोन न करें", "दोबारा मत"),
    call_later=_phrases("बाद में कॉल", "बाद में फोन", "बाद में बात", "बाद में करना", "बाद में करिए", "बाद में कीजिए",
                        "बाद में करो", "बाद में कर लेना", "बाद में कर लीजिए", "फिर कभी", "किसी और दिन", "दूसरे दिन",
                        "किसी और टाइम", "किसी और समय"),
    call_words=_phrases("कॉल", "फोन", "बात करना", "बात करें", "बात करेंगे", "बात कर लेंगे", "बात कीजिए", "बात करिए",
                        "बात कर लेना", "करना", "कर लेना", "कीजिए", "करिए"),
    time_words=_phrases("कल", "परसों", "शाम", "सुबह", "रात", "दोपहर", "बजे", "घंटे", "घंटा", "मिनट बाद", "संडे",
                        "सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार", "मंडे", "हफ्ते",
                        "वीकेंड", "थोड़ी देर", "लंच के बाद"),
    occupied=_phrases("गाड़ी चला*", "ड्राइव कर*", "ड्राइविंग", "मीटिंग में", "मीटिंग चल*", "ऑफिस में हूं", "दफ्तर में हूं",
                      "काम पर हूं", "काम में हूं", "काम कर रहा", "काम कर रही", "किसी और काम में", "खाना खा रहा",
                      "खाना खा रही", "मेहमान", "ट्रेन में", "बस में हूं", "रास्ते में", "हॉस्पिटल में", "अस्पताल में",
                      "बिजी हूं", "व्यस्त हूं", "अभी बिजी", "बिजी है", "थोड़ा बिजी", "दूसरी कॉल पर", "नहा रहा",
                      "पूजा कर रहा", "पूजा कर रही"),
    hurry=_phrases("जल्दी", "फटाफट", "शॉर्ट में"),
    narrative=_phrases("वो लोग", "वे लोग", "बैंक वाले", "ब्रांच वाले", "वाले", "एजेंट ने", "एजेंट बोल*", "एजेंट कह*",
                       "मैनेजर ने", "उन्होंने", "उन्होने", "उसने", "बोलते", "कहते", "देते", "सुनता", "सुनते",
                       "बोलता", "कहता", "उठाता", "उठाते", "बताते", "बताता", "टाल*", "हमेशा", "आज तक", "जब भी", "हर बार",
                       "फिर भी", "लेकिन", "मगर", "जोड़ दिया", "डाल दिया", "लगा दिया", "ऐड कर दिया", "कोई सुनता",
                       "कोई नहीं आया", "वहां", "इसमें", "इस चीज", "उस वक्त", "उस समय", "बिना इसके", "जबरदस्ती", "वो बोले",
                       "वो बोला"),
    took_nothing=_phrases("कुछ नहीं लिया", "कुछ भी नहीं लिया", "और कुछ नहीं लिया", "कोई चीज नहीं ली", "कुछ और नहीं लिया",
                          "नहीं लिया", "नहीं ली", "बस लोन", "सिर्फ लोन", "केवल लोन", "लोन ही लिया", "लोन के अलावा कुछ नहीं",
                          "कुछ नहीं खरीदा"),
    nothing=_phrases("कुछ नहीं", "कुछ भी नहीं", "नहीं", "जी नहीं", "नहीं जी", "ना", "कोई नहीं"),
    paid_nothing=_phrases("कुछ नहीं दिया", "पैसे नहीं दिए", "कोई पैसा नहीं", "एक पैसा नहीं", "फ्री", "मुफ्त", "जीरो",
                          "कुछ नहीं", "पैसा नहीं दिया", "कुछ भी नहीं"),
    own_choice=_phrases("मर्जी", "मेरी इच्छा", "अपनी इच्छा", "जरूरी नहीं", "खुद लिया", "मैंने खुद", "अपने से", "ऑप्शनल",
                        "चॉइस"),
    forced=_phrases("मर्जी नहीं", "बिना पूछे", "जबरदस्ती", "जरूरी है", "जरूरी था", "जरूरी बोला", "जरूरी बताया",
                    "लेना पड़ेगा", "लेना पड़ा", "कंपलसरी", "मजबूरी"),
    language_cue=_phrases("में", "बोलिए", "बोलो", "बोल*", "बात", "भाषा", "आती", "आता", "समझ*", "चलेगा", "प्लीज"),
    cannot_follow=_phrases("नहीं आती", "नहीं आता", "समझ नहीं", "समझ में नहीं", "नहीं समझ*"),
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
        "பேச முடியல", "விருப்பம் இல்லை", "கேக்காதீங்க", "கட் பண்றேன்", "போனை கட்", "இன்ட்ரஸ்ட் இல்ல", "விட்டுடுங்க", "விடுங்க",
    ),
    decline_short=_phrases("நிறுத்துங்க", "நிறுத்துங்கள்", "போதும்*"),
    dont_know=_phrases("தெரியாது", "தெரியல", "தெரியலை", "தெரியவில்லை", "தெரியலங்க", "தெரியாதுங்க", "ஞாபகம் இல்ல",
                       "ஞாபகம் இல்லை", "நினைவில்லை", "நினைவில்ல", "நினைவு இல்லை", "நினைவில் இல்லை", "theriyadhu", "theriyathu",
                       "theriyala"),
    asks_repeat=_phrases("புரியல", "புரியலை", "புரியவில்லை", "மறுபடியும்", "திரும்ப சொல்லுங்க", "இன்னொரு தடவை",
                         "இன்னொரு முறை", "கேக்கல", "கேட்கல", "கேட்கவில்லை", "என்ன சொன்னீங்க", "எந்த பொருள்"),
    asks_repeat_whole=_phrases("என்ன", "என்னது", "ஹலோ", "எது"),
    filler=_phrases("ம்ம்", "ம்", "சரி", "ஆமா", "ஓகே", "ஹ்ம்", "அப்படியா", "ஆ"),
    recounts=frozenset(),
    # call v2 additions: not human-reviewed; written to the reviewer's probes, with no fresh Tamil set
    identity_yes=_phrases("ஆமா", "ஆமாம்", "ஆம்", "ஆமாங்க", "நான்தான்", "நான் தான்", "பேசுறேன்", "பேசுகிறேன்", "aama",
                          "aamam"),
    self_ok=_phrases("சொல்லுங்க", "சொல்லுங்கள்", "ஹலோ", "வணக்கம்", "நான்", "சார்", "மேடம்", "ஓகே", "சரி", "கேளுங்க"),
    first_person=_phrases("நான்", "நான்தான்", "பேசுறேன்", "பேசுகிறேன்"),
    kin=_phrases("மனைவி", "கணவர்", "வீட்டுக்காரர்", "அப்பா", "அம்மா", "தம்பி", "அண்ணன்", "அக்கா", "தங்கை", "மகன்", "மகள்",
                 "அவர்", "அவரு", "அவங்க", "அவன்", "அவள்", "இருக்காரு", "இருக்கார்", "போயிருக்கார்", "போயிருக்கான்",
                 "தூங்குறாங்க", "தூங்குறார்", "பிறந்தார்", "கூப்பிடுறேன்"),
    asks_who=_phrases("யார் பேசுறீங்க", "யாரு பேசுறது", "எங்கிருந்து", "எந்த பேங்க்", "மோசடி"),
    do_not_call=_phrases("கூப்பிடாதீங்க", "அழைக்காதீர்கள்"),
    call_later=_phrases("அப்புறம் கூப்பிடுங்க", "அப்புறம் பேசலாம்", "பிறகு அழையுங்கள்", "பிறகு பேசலாம்", "அப்புறம் பாக்கலாம்",
                        "வேற நாள் கூப்பிடுங்க"),
    call_words=_phrases("கூப்பிடுங்க", "கால்", "போன்", "பேசலாம்"),
    time_words=_phrases("நாளைக்கு", "நாளை", "சாயங்காலம்", "காலையில", "மதியம்", "இரவு", "மணிக்கு"),
    occupied=_phrases("வண்டி ஓட்டிட்டு", "வண்டி ஓட்டுறேன்", "வேலையில இருக்கேன்", "வேலையா இருக்கேன்", "பிஸியா இருக்கேன்",
                      "மீட்டிங்ல இருக்கேன்"),
    narrative=_phrases("அவங்க", "சொல்லி", "சொன்னேன்", "சொன்னாங்க", "சொல்றாங்க", "ஆனாலும்", "கேட்டேன்", "கேட்டா", "னு",
                       "என்று", "யாரும்", "சேர்த்துட்டாங்க", "போட்டாங்க", "அனுப்பிட்டாங்க", "ஆனா"),
    took_nothing=_phrases("எதுவும் வாங்கல", "ஒண்ணும் வாங்கல", "லோன் மட்டும்", "கடன் மட்டும்"),
    nothing=_phrases("ஒண்ணும் இல்ல", "எதுவும் இல்லை", "இல்லை", "இல்ல"),
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
        "ಮಾತಾಡೋಕೆ ಆಗ್ತಿಲ್ಲ", "ಇಷ್ಟ ಇಲ್ಲ", "ಕೇಳಬೇಡಿ", "ಕಟ್ ಮಾಡ್ತೀನಿ", "ಇಂಟ್ರೆಸ್ಟ್ ಇಲ್ಲ", "ಬಿಟ್ಟುಬಿಡಿ",
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
    # call v2 additions: not human-reviewed; written to the reviewer's probes, with no fresh Kannada set
    identity_yes=_phrases("ಹೌದು", "ಹೌದ್ರಿ", "ಹೂ", "ಹೂಂ", "ಹಾ", "ಹಾಂ", "ನಾನೇ", "ಮಾತಾಡ್ತಿದ್ದೀನಿ", "ಮಾತನಾಡುತ್ತಿದ್ದೇನೆ", "houdu"),
    self_ok=_phrases("ಹೇಳಿ", "ಹಲೋ", "ನಮಸ್ಕಾರ", "ನಾನು", "ಸರ್", "ಮೇಡಂ", "ಓಕೆ", "ಸರಿ", "ಕೇಳಿ"),
    first_person=_phrases("ನಾನು", "ನಾನೇ", "ಮಾತಾಡ್ತಿದ್ದೀನಿ"),
    kin=_phrases("ಹೆಂಡತಿ", "ಗಂಡ", "ಅಪ್ಪ", "ಅಮ್ಮ", "ತಮ್ಮ", "ಅಣ್ಣ", "ಅಕ್ಕ", "ತಂಗಿ", "ಮಗ", "ಮಗಳು", "ಅವರು", "ಅವನು", "ಅವಳು",
                 "ಇದ್ದಾರೆ", "ಹೋಗಿದ್ದಾರೆ", "ಹೋಗಿದ್ದಾನೆ", "ಮಲಗಿದ್ದಾರೆ", "ಮೀಟಿಂಗ್*", "ಕರೀತೀನಿ", "ಆಫೀಸಿಗೆ"),
    asks_who=_phrases("ಯಾರು ಮಾತಾಡ್ತಿರೋದು", "ಎಲ್ಲಿಂದ", "ಯಾವ ಬ್ಯಾಂಕ್", "ಮೋಸ"),
    do_not_call=_phrases("ಕರೆ ಮಾಡಬೇಡಿ", "ಕಾಲ್ ಮಾಡಬೇಡಿ"),
    call_later=_phrases("ಆಮೇಲೆ ಕರೆ ಮಾಡಿ", "ಆಮೇಲೆ ಕಾಲ್ ಮಾಡಿ", "ಆಮೇಲೆ ಮಾತಾಡೋಣ", "ಆಮೇಲೆ ನೋಡೋಣ", "ನಂತರ ಕರೆ ಮಾಡಿ",
                        "ನಂತರ ಕಾಲ್ ಮಾಡಿ"),
    call_words=_phrases("ಫೋನ್", "ಕರೆ", "ಕಾಲ್"),
    time_words=_phrases("ನಾಳೆ", "ಸಂಜೆ", "ಬೆಳಿಗ್ಗೆ", "ರಾತ್ರಿ", "ಗಂಟೆಗೆ"),
    occupied=_phrases("ಗಾಡಿ ಓಡಿಸ್ತಿದ್ದೀನಿ", "ಕೆಲಸದಲ್ಲಿದ್ದೀನಿ", "ಕೆಲಸದಲ್ಲಿ ಇದ್ದೀನಿ", "ಬ್ಯುಸಿ ಇದ್ದೀನಿ", "ಬಿಸಿ ಇದ್ದೀನಿ"),
    narrative=_phrases("ಅವರು", "ಅಂತ", "ಆದ್ರೂ", "ಆದರೂ", "ಕೇಳಿದೆ", "ಕೇಳಿದ್ರೆ", "ಅಂತಾರೆ", "ಕಳಿಸಿದ್ರು", "ಸೇರಿಸಿದ್ರು", "ಹಾಕಿದ್ರು",
                       "ಯಾರೂ", "ಅಂದೆ"),
    took_nothing=_phrases("ಏನೂ ತಗೊಂಡಿಲ್ಲ", "ಸಾಲ ಮಾತ್ರ", "ಲೋನ್ ಮಾತ್ರ"),
    nothing=_phrases("ಏನೂ ಇಲ್ಲ", "ಇಲ್ಲ", "ಇಲ್ಲಾ"),
)  # fmt: skip

LEXICONS: dict[Language, Lexicon] = {
    Language.hi: _HI | _EN,
    Language.hi_en: _HI | _EN,
    Language.ta: _TA | _EN,
    Language.kn: _KN | _EN,
}


# Language names, folded, in any script: the English name in lower case.
_LANGUAGE_WORDS = {
    "hindi": ("हिंदी", "हिन्दी", "hindi", "ஹிந்தி", "இந்தி", "ಹಿಂದಿ"),
    "english": ("इंग्लिश", "अंग्रेजी", "english", "ஆங்கிலம்", "இங்கிலீஷ்", "ಇಂಗ್ಲಿಷ್", "ಇಂಗ್ಲೀಷ್"),
    "tamil": ("तमिल", "tamil", "தமிழ்", "ತಮಿಳು"),
    "kannada": ("कन्नड़", "kannada", "ಕನ್ನಡ", "கன்னடம்"),
    "telugu": ("तेलुगु", "telugu", "தெலுங்கு", "ತೆಲುಗು"),
    "marathi": ("मराठी", "marathi", "ಮರಾಠಿ"),
    "bengali": ("बंगाली", "बांग्ला", "bengali", "bangla"),
    "gujarati": ("गुजराती", "gujarati"),
    "malayalam": ("मलयालम", "malayalam", "மலையாளம்", "ಮಲಯಾಳಂ"),
    "punjabi": ("पंजाबी", "punjabi"),
    "odia": ("उड़िया", "ओड़िया", "odia", "oriya"),
}
LANGUAGE_NAMES: dict[str, str] = {
    token: name for name, words in _LANGUAGE_WORDS.items() for word in words for token in tokens(word)
}
# The languages a call is already in: asking for one of these is not a request to switch.
OWN_LANGUAGES: dict[Language, frozenset[str]] = {
    Language.hi: frozenset({"hindi"}),
    Language.hi_en: frozenset({"hindi", "english"}),
    Language.ta: frozenset({"tamil"}),
    Language.kn: frozenset({"kannada"}),
}
