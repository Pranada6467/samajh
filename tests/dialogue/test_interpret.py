"""The rule interpreter: what each kind of customer turn is read as. Tamil and Kannada rows are not human-reviewed."""

from __future__ import annotations

import pytest

from samajh.dialogue import Expecting, Intent, RuleInterpreter
from samajh.dialogue.interpret import birth_year
from samajh.types import Language

HI, HE, TA, KN = Language.hi, Language.hi_en, Language.ta, Language.kn
E = Expecting
RULES = RuleInterpreter()

CASES = [
    # identity
    (HI, E.identity, "हाँ जी, बोल रहा हूँ", Intent.yes),
    (HI, E.identity, "जी", Intent.said),  # an acknowledgement, not a claim
    (HI, E.identity, "हाँ बोलिए", Intent.said),
    (HE, E.identity, "haan ji main hi bol raha hoon", Intent.yes),
    (HE, E.identity, "yes speaking", Intent.yes),
    (HI, E.identity, "नहीं, गलत नंबर है", Intent.wrong_person),
    (HI, E.identity, "जी नहीं", Intent.no),
    (HI, E.identity, "वो घर पर नहीं हैं, मैं उनकी पत्नी बोल रही हूँ", Intent.wrong_person),
    (HE, E.identity, "woh bahar gaye hain", Intent.wrong_person),
    (HI, E.identity, "हाँ, मैं उनका बेटा हूँ", Intent.wrong_person),
    (HI, E.identity, "मैं उनकी पत्नी बोल रही हूँ", Intent.wrong_person),
    (HI, E.identity, "हाँ मैं ही बोल रहा हूँ, आप कौन?", Intent.asks_who),
    (HI, E.identity, "कौन बोल रहा है?", Intent.asks_who),
    (HI, E.identity, "हाँ, कौन?", Intent.asks_who),
    (HI, E.identity, "आप कहाँ से बोल रहे हैं?", Intent.asks_who),
    (HI, E.identity, "क्या? समझा नहीं", Intent.asks_repeat),
    (HI, E.identity, "फिर से बोलिए", Intent.asks_repeat),
    (HI, E.identity, "", Intent.silence),
    (TA, E.identity, "ஆமா, நான்தான்", Intent.yes),
    (TA, E.identity, "இல்லை, ராங் நம்பர்", Intent.wrong_person),
    (TA, E.identity, "யார் பேசுறீங்க?", Intent.asks_who),
    (KN, E.identity, "ಹೌದು, ಹೇಳಿ", Intent.said),
    (KN, E.identity, "ಇಲ್ಲ, ಅವರು ಮನೆಯಲ್ಲಿ ಇಲ್ಲ", Intent.wrong_person),
    (KN, E.identity, "ಯಾರು?", Intent.asks_who),
    # go ahead
    (HI, E.go_ahead, "हाँ ठीक है, पूछिए", Intent.yes),
    (HI, E.go_ahead, "क्यों नहीं, बोलिए", Intent.yes),
    (HI, E.go_ahead, "नहीं", Intent.no),
    (HI, E.go_ahead, "नहीं रहने दीजिए", Intent.no),
    (HI, E.open, "रहने दीजिए", Intent.maybe_decline),
    (HI, E.stop_check, "हाँ, रोक दीजिए", Intent.maybe_decline),
    (HI, E.stop_check, "नहीं नहीं, पूछिए", Intent.no),
    (HE, E.go_ahead, "ok go ahead", Intent.yes),
    (HE, E.go_ahead, "abhi time nahin hai, baad mein call karna", Intent.call_later),
    (HI, E.go_ahead, "सही है ना", Intent.yes),
    (TA, E.go_ahead, "சரி, சொல்லுங்க", Intent.yes),
    (TA, E.go_ahead, "வேண்டாம்", Intent.no),
    (KN, E.go_ahead, "ಸರಿ, ಕೇಳಿ", Intent.yes),
    (KN, E.go_ahead, "ಬೇಡ", Intent.no),
    # decline and human, anywhere
    (HI, E.open, "मुझे बात नहीं करनी", Intent.decline),
    (HI, E.open, "अभी मैं बिज़ी हूँ, बाद में कॉल कीजिए", Intent.call_later),
    (HI, E.amount, "फ़ोन रख रहा हूँ", Intent.decline),
    (HI, E.told, "बंद करो", Intent.maybe_decline),
    (HE, E.open, "please don't call me again", Intent.do_not_call),
    (HE, E.open, "I'm not interested", Intent.decline),
    (HE, E.confirmation, "stop", Intent.maybe_decline),
    (TA, E.open, "போதும்", Intent.maybe_decline),
    (KN, E.open, "ಸಾಕು", Intent.maybe_decline),
    (HI, E.open, "किसी इंसान से बात कराइए", Intent.wants_human),
    (HI, E.open, "मुझे मैनेजर से बात करनी है", Intent.wants_human),
    (HE, E.amount, "can I talk to a person", Intent.wants_human),
    (HE, E.open, "mujhe kisi agent se baat karni hai", Intent.wants_human),
    (HE, E.identity, "customer care se baat karao", Intent.wants_human),
    (TA, E.open, "எனக்கு பேச விருப்பம் இல்லை", Intent.decline),
    (TA, E.open, "அப்புறம் கூப்பிடுங்க", Intent.call_later),
    (TA, E.open, "ஒரு அதிகாரி கிட்ட பேசணும்", Intent.wants_human),
    (KN, E.open, "ಕರೆ ಮಾಡಬೇಡಿ", Intent.do_not_call),
    (KN, E.open, "ಆಮೇಲೆ ಕಾಲ್ ಮಾಡಿ", Intent.call_later),
    (KN, E.open, "ಮ್ಯಾನೇಜರ್ ಜೊತೆ ಮಾತಾಡಬೇಕು", Intent.wants_human),
    # answers that hold decline-like or human-like words and must stay answers
    (HI, E.open, "बाद में पता चला कि यह बीमा है", Intent.said),
    (HI, E.open, "बाद में पता चला मुझे इसका", Intent.said),
    (TA, E.open, "அது பத்தி நான் அப்புறம் தான் தெரிஞ்சுகிட்டேங்க", Intent.said),
    (HE, E.open, "I got to know about it later", Intent.said),
    (HI, E.open, "उन्होंने पढ़ने का समय नहीं दिया, बस साइन करवा लिया", Intent.said),
    (HI, E.open, "मैं मना कर रहा था पर उन्होंने दे दिया", Intent.said),
    (HI, E.told, "बोला था एक महीने में बंद कर दो तो पूरा पैसा वापस मिल जाएगा", Intent.said),
    (HI, E.open, "मैंने मैनेजर से बात की थी, उन्होंने बोला ज़रूरी है", Intent.said),
    (HI, E.open, "मुझे यह नहीं चाहिए था, ज़बरदस्ती दिया", Intent.said),
    (HI, E.open, "मैं एफडी में पैसा रख रहा था", Intent.said),
    (HE, E.open, "I was not interested but they said it is compulsory", Intent.said),
    (HE, E.open, "agent ne bola tha chinta mat karo", Intent.said),
    (TA, E.open, "மேனேஜர் கிட்ட பேசினேன், கட்டாயம் என்று சொன்னார்", Intent.said),
    (KN, E.open, "ಮ್ಯಾನೇಜರ್ ಜೊತೆ ಮಾತಾಡಿದೆ, ಕಡ್ಡಾಯ ಅಂದರು", Intent.said),
    # don't know, repeat, filler, silence
    (HI, E.open, "पता नहीं", Intent.dont_know),
    (HI, E.amount, "याद नहीं कितना था", Intent.dont_know),
    (HE, E.open, "I don't know", Intent.dont_know),
    (HE, E.amount, "mujhe nahi pata", Intent.dont_know),
    (TA, E.open, "தெரியாது", Intent.dont_know),
    (KN, E.amount, "ಗೊತ್ತಿಲ್ಲ", Intent.dont_know),
    (HI, E.open, "क्या?", Intent.asks_repeat),
    (HI, E.open, "समझ नहीं आया", Intent.asks_repeat),
    (HI, E.open, "कौन सी चीज़?", Intent.asks_repeat),
    (HE, E.open, "sorry?", Intent.asks_repeat),
    (HE, E.told, "can you repeat", Intent.asks_repeat),
    (HI, E.open, "मुझे उस दिन समझ नहीं आया था कि यह क्या चीज़ दे रहे हैं", Intent.said),
    (TA, E.open, "புரியல", Intent.asks_repeat),
    (KN, E.open, "ಮತ್ತೆ ಹೇಳಿ", Intent.asks_repeat),
    (HI, E.open, "हम्म", Intent.filler),
    (HI, E.open, "हाँ", Intent.filler),
    (HI, E.amount, "अच्छा ठीक है", Intent.filler),
    (HE, E.open, "ok", Intent.filler),
    (TA, E.open, "ம்ம்", Intent.filler),
    (KN, E.open, "ಹೂಂ", Intent.filler),
    (HI, E.open, "   ", Intent.silence),
    (HI, E.open, "...", Intent.silence),
    # "were you told" questions: a bare yes or no is an answer
    (HI, E.told, "नहीं", Intent.no),
    (HI, E.told, "हाँ, बताया था", Intent.yes),
    (HI, E.told, "कुछ नहीं बताया", Intent.no),
    (KN, E.told, "ಇಲ್ಲ", Intent.no),
    # plain answers
    (HI, E.open, "बस एक एफडी, लोन सिक्योरिटी के लिए", Intent.said),
    (HI, E.open, "कुछ नहीं लिया", Intent.took_nothing),
    (HE, E.open, "ek insurance policy li thi", Intent.said),
    (TA, E.open, "ஒரு எஃப்டி மட்டும்", Intent.said),
    (KN, E.open, "ಒಂದು ಎಫ್‌ಡಿ ಮಾತ್ರ", Intent.said),
    # read-back
    (HI, E.confirmation, "हाँ, सही है", Intent.yes),
    (HI, E.confirmation, "बिल्कुल", Intent.yes),
    (HI, E.confirmation, "नहीं, गलत है", Intent.no),
    (HI, E.confirmation, "सही नहीं है", Intent.no),
    (HE, E.confirmation, "yes correct", Intent.yes),
    (HE, E.confirmation, "no that's wrong", Intent.no),
    (TA, E.confirmation, "ஆமா சரி", Intent.yes),
    (TA, E.confirmation, "இல்லை, தவறு", Intent.no),
    (KN, E.confirmation, "ಹೌದು ಸರಿ", Intent.yes),
    (KN, E.confirmation, "ಇಲ್ಲ, ತಪ್ಪು", Intent.no),
]


@pytest.mark.parametrize("language, expecting, text, intent", CASES)
def test_intent(language, expecting, text, intent):
    assert RULES.interpret(text, language=language, expecting=expecting).intent is intent


@pytest.mark.parametrize(
    "language, text, amount",
    [
        (HI, "बावन हज़ार", 52000),
        (HI, "नहीं, पचपन हज़ार", 55000),
        (HI, "हाँ बावन हज़ार ही", 52000),
        (HI, "52,000 रुपये", 52000),
        (HE, "fifty two thousand", 52000),
        (HE, "52 hazaar", 52000),
        (TA, "ஐம்பத்திரண்டாயிரம்", 52000),
        (KN, "ಐವತ್ತೆರಡು ಸಾವಿರ", 52000),
        (HI, "शायद बावन हज़ार", None),  # hedged: not a figure to read back
        (HI, "पचास या बावन हज़ार", None),
        (HI, "पाँच लाख का लोन था, उसमें से बावन हज़ार कटे", None),  # two amounts
        (HE, "bavan hazaar", None),  # romanised Hindi numbers are refused by samajh.amounts
        (HI, "पता नहीं", None),
        # outside what a read-back can say and parse back: treated as no figure
        (HI, "0 रुपये", None),
        (HI, "निन्यानवे रुपये", None),
        (HI, "1000000000", None),
        (HI, "5000000000", None),
        (HI, "100 रुपये", 100),
        (HI, "999999999", 999_999_999),
    ],
)
def test_amount_comes_from_the_amount_parser(language, text, amount):
    assert RULES.interpret(text, language=language, expecting=Expecting.amount).amount_inr == amount


@pytest.mark.parametrize(
    "text, year",
    [
        ("1984", 1984),
        ("१९८४", 1984),
        ("उन्नीस सौ चौरासी", 1984),
        ("सन उन्नीस सौ चौरासी में", 1984),
        ("चौरासी", 84),
        ("84", 84),
        ("nineteen eighty four", 1984),
        ("eighty four", 84),
        ("मेरा जन्म 1984 में हुआ था", 1984),
        ("ஆயிரத்து தொள்ளாயிரத்து எண்பத்து நான்கு", 1984),
        ("two thousand one", 2001),
        ("नहीं बताऊँगा", None),
        ("52,000", None),
        ("", None),
    ],
)
def test_birth_year(text, year):
    assert birth_year(text) == year


def test_year_is_read_only_when_a_year_is_expected():
    assert RULES.interpret("1984", language=HI, expecting=Expecting.birth_year).year == 1984
    assert RULES.interpret("1984", language=HI, expecting=Expecting.amount).year is None


@pytest.mark.parametrize("language", list(Language))
def test_every_amount_the_interpreter_reports_can_be_spoken(language):
    from samajh.amounts import spoken_amount
    from samajh.dialogue.interpret import READ_BACK_LIMIT, READ_BACK_MIN, Interpretation

    assert spoken_amount(READ_BACK_MIN, language) and spoken_amount(READ_BACK_LIMIT - 1, language)
    for amount in (0, READ_BACK_MIN - 1, READ_BACK_LIMIT):
        with pytest.raises(ValueError, match="amount_inr"):
            Interpretation(intent=Intent.said, amount_inr=amount)
