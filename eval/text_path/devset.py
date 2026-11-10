"""Development set for the extractor: 20 hand-written calls, 5 each in hi, hi-en, ta, kn.

Used to iterate on the prompt and to compare models. It is NOT the frozen gold set in
`data/scenarios/` and shares no text with it or with the examples inside the prompt.

Limits: one author wrote the customer replies, the gold labels and the prompt, so the labels
share the prompt author's reading of borderline replies. The text is typed, not speech-to-text
output. Tamil and Kannada are not human-reviewed. All names, ids and amounts are synthetic.

Every case states the verdict and the flagged rules it expects; `tests/extract/test_devset.py`
checks them by running the gold extraction through the rule engine, with no LLM.
"""

from dataclasses import dataclass, field

from scenario import GoldLabels, Scenario

from samajh.amounts import format_inr, spoken_amount
from samajh.rules import evaluate, to_beliefs
from samajh.types import LoanRecord, RawExtraction, RuleId, Transcript, Verdict

DK = "<dont_know>"
UN = "<unclear>"
P1 = "P1"

# --- what the bot says, per language (Tamil and Kannada: not human-reviewed) ----------------

BOT: dict[str, dict[str, str]] = {
    "hi": {
        "right_party": "नमस्ते, क्या मेरी बात {name} जी से हो रही है?",
        "disclosure": (
            "मैं नमूना बैंक की ग्राहक सेवा टीम की ओर से एक स्वचालित एआई सहायक बोल रही हूँ। यह बिक्री की "
            "कॉल नहीं है। आपकी राय दर्ज करने के लिए यह कॉल रिकॉर्ड हो रही है। क्या हम आगे बढ़ें?"
        ),
        "second_check": "पुष्टि के लिए, अपने जन्म का साल बताइए।",
        "context": "धन्यवाद। यह कॉल आपके हाल के लोन के बारे में है।",
        "recall": "लोन के साथ आपने क्या-क्या लिया, और कितने का?",
        "kind": "लोन के साथ जो चीज़ आपको दी गई, वह बीमा है, एफ़डी है या कुछ और?",
        "premium": "उसकी कीमत कितनी थी?",
        "readback": "{spoken}, यानी {inr}, सही है?",
        "payment_source": "यह पैसा कैसे दिया गया, लोन की रकम में से या अलग से?",
        "required_for_loan": "क्या यह लोन के लिए ज़रूरी था?",
        "provider_choice": "क्या आपको बताया गया था कि यह किसी और कंपनी से भी ले सकते हैं?",
        "cover": "इसमें कितने का कवर है?",
        "term": "यह कितने समय के लिए है?",
        "cancel_window": "क्या आपको बताया गया था कि इसे रद्द कर सकते हैं या नहीं, और कब तक?",
        "features": "अगर आप यह पैसा वापस लेना चाहें, तो क्या वापस मिल सकता है, और कब?",
        "consent": "लोन लेते समय आपने क्या-क्या लेने की सहमति दी थी, और कैसे?",
        "close": "आपका समय देने के लिए धन्यवाद।",
        "again": "ज़रा आसान शब्दों में फिर पूछती हूँ। ",
    },
    "hi-en": {
        "right_party": "Hello, क्या मैं {name} जी से बात कर रही हूँ?",
        "disclosure": (
            "मैं नमूना Finance की customer care team से एक automated AI assistant बोल रही हूँ। ये sales "
            "call नहीं है। आपका feedback record करने के लिए ये call record हो रही है। क्या हम continue करें?"
        ),
        "second_check": "Confirm करने के लिए, अपना birth year बताइए।",
        "context": "Thank you. ये call आपके recent loan के बारे में है।",
        "recall": "Loan के साथ आपने क्या-क्या लिया, और कितने का?",
        "kind": "Loan के साथ जो product आपको दिया गया, वो insurance है, FD है या कुछ और?",
        "premium": "उसका cost कितना था?",
        "readback": "{spoken}, यानी {inr}, सही है?",
        "payment_source": "ये payment कैसे हुआ, loan amount में से या अलग से?",
        "required_for_loan": "क्या ये loan के लिए ज़रूरी था?",
        "provider_choice": "क्या आपको बताया गया था कि ये किसी और company से भी ले सकते हैं?",
        "cover": "इसमें कितने का cover है?",
        "term": "ये कितने time के लिए है?",
        "cancel_window": "क्या आपको बताया गया था कि इसे cancel कर सकते हैं या नहीं, और कब तक?",
        "features": "अगर आप ये पैसा वापस लेना चाहें, तो क्या वापस मिल सकता है, और कब?",
        "consent": "Loan लेते time आपने क्या-क्या लेने के लिए agree किया था, और कैसे?",
        "close": "आपके time के लिए thank you.",
        "again": "एक बार फिर simple words में पूछती हूँ। ",
    },
    "ta": {
        "right_party": "வணக்கம், நான் {name} அவர்களிடம் பேசுகிறேனா?",
        "disclosure": (
            "நான் நமூனா வங்கியின் வாடிக்கையாளர் சேவைக் குழுவிலிருந்து பேசும் தானியங்கி AI உதவியாளர். இது "
            "விற்பனை அழைப்பு அல்ல. உங்கள் கருத்தைப் பதிவு செய்ய இந்த அழைப்பு பதிவாகிறது. தொடரலாமா?"
        ),
        "second_check": "உறுதிப்படுத்த, நீங்கள் பிறந்த வருடத்தைச் சொல்லுங்கள்.",
        "context": "நன்றி. இந்த அழைப்பு உங்கள் சமீபத்திய கடனைப் பற்றியது.",
        "recall": "கடனுடன் நீங்கள் என்னென்ன எடுத்தீர்கள், எவ்வளவுக்கு?",
        "kind": "கடனுடன் உங்களுக்குக் கொடுக்கப்பட்டது காப்பீடா, FD-யா, அல்லது வேறு ஏதாவதா?",
        "premium": "அதன் விலை எவ்வளவு?",
        "readback": "{spoken}, அதாவது {inr}, சரியா?",
        "payment_source": "அந்தப் பணம் எப்படி செலுத்தப்பட்டது, கடன் தொகையிலிருந்தா அல்லது தனியாகவா?",
        "required_for_loan": "கடன் கிடைக்க இது கட்டாயமா?",
        "provider_choice": "இதை வேறு நிறுவனத்திலும் வாங்கலாம் என்று உங்களிடம் சொன்னார்களா?",
        "cover": "இதில் எவ்வளவு கவர் உள்ளது?",
        "term": "இது எவ்வளவு காலத்துக்கு?",
        "cancel_window": "இதை ரத்து செய்ய முடியுமா என்று சொன்னார்களா, எத்தனை நாட்களுக்குள்?",
        "features": "இந்தப் பணத்தைத் திரும்பப் பெற விரும்பினால், கிடைக்குமா, எப்போது?",
        "consent": "கடன் வாங்கும்போது நீங்கள் எதையெல்லாம் வாங்க ஒப்புக்கொண்டீர்கள், எப்படி ஒப்புக்கொண்டீர்கள்?",
        "close": "உங்கள் நேரத்துக்கு நன்றி.",
        "again": "இன்னும் எளிமையாகக் கேட்கிறேன். ",
    },
    "kn": {
        "right_party": "ನಮಸ್ಕಾರ, ನಾನು {name} ಅವರ ಜೊತೆ ಮಾತನಾಡುತ್ತಿದ್ದೇನೆಯೇ?",
        "disclosure": (
            "ನಾನು ನಮೂನಾ ಬ್ಯಾಂಕ್‌ನ ಗ್ರಾಹಕ ಸೇವಾ ತಂಡದಿಂದ ಮಾತನಾಡುತ್ತಿರುವ ಸ್ವಯಂಚಾಲಿತ AI ಸಹಾಯಕ. ಇದು ಮಾರಾಟದ "
            "ಕರೆ ಅಲ್ಲ. ನಿಮ್ಮ ಅಭಿಪ್ರಾಯ ದಾಖಲಿಸಲು ಈ ಕರೆ ರೆಕಾರ್ಡ್ ಆಗುತ್ತಿದೆ. ಮುಂದುವರಿಯಬಹುದೇ?"
        ),
        "second_check": "ಖಚಿತಪಡಿಸಲು, ನಿಮ್ಮ ಹುಟ್ಟಿದ ವರ್ಷ ಹೇಳಿ.",
        "context": "ಧನ್ಯವಾದ. ಈ ಕರೆ ನಿಮ್ಮ ಇತ್ತೀಚಿನ ಸಾಲದ ಬಗ್ಗೆ.",
        "recall": "ಸಾಲದ ಜೊತೆ ನೀವು ಏನೇನು ತೆಗೆದುಕೊಂಡಿರಿ, ಎಷ್ಟಕ್ಕೆ?",
        "kind": "ಸಾಲದ ಜೊತೆ ನಿಮಗೆ ಕೊಟ್ಟಿದ್ದು ವಿಮೆಯೇ, FD-ಯೇ, ಅಥವಾ ಬೇರೆ ಏನಾದರೂ?",
        "premium": "ಅದರ ಬೆಲೆ ಎಷ್ಟು?",
        "readback": "{spoken}, ಅಂದರೆ {inr}, ಸರಿಯೇ?",
        "payment_source": "ಆ ಹಣ ಹೇಗೆ ಪಾವತಿಯಾಯಿತು, ಸಾಲದ ಮೊತ್ತದಿಂದಲೇ ಅಥವಾ ಬೇರೆಯಾಗಿ?",
        "required_for_loan": "ಸಾಲ ಸಿಗಲು ಇದು ಕಡ್ಡಾಯವಾಗಿತ್ತೇ?",
        "provider_choice": "ಇದನ್ನು ಬೇರೆ ಕಂಪನಿಯಿಂದಲೂ ತೆಗೆದುಕೊಳ್ಳಬಹುದು ಎಂದು ನಿಮಗೆ ಹೇಳಿದ್ದರೇ?",
        "cover": "ಇದರಲ್ಲಿ ಎಷ್ಟು ಕವರ್ ಇದೆ?",
        "term": "ಇದು ಎಷ್ಟು ಅವಧಿಗೆ?",
        "cancel_window": "ಇದನ್ನು ರದ್ದು ಮಾಡಬಹುದು ಎಂದು ಹೇಳಿದ್ದರೇ, ಎಷ್ಟು ದಿನದೊಳಗೆ?",
        "features": "ಈ ಹಣ ವಾಪಸ್ ಬೇಕೆಂದರೆ ಸಿಗುತ್ತದೆಯೇ, ಯಾವಾಗ?",
        "consent": "ಸಾಲ ತೆಗೆದುಕೊಳ್ಳುವಾಗ ನೀವು ಏನೇನು ತೆಗೆದುಕೊಳ್ಳಲು ಒಪ್ಪಿದ್ದಿರಿ, ಹೇಗೆ ಒಪ್ಪಿದ್ದಿರಿ?",
        "close": "ನಿಮ್ಮ ಸಮಯಕ್ಕೆ ಧನ್ಯವಾದ.",
        "again": "ಇನ್ನೂ ಸರಳವಾಗಿ ಕೇಳುತ್ತೇನೆ. ",
    },
}

# Default replies to the three opening turns and the close, per language.
OPENING: dict[str, tuple[str, str, str, str]] = {
    "hi": ("हाँ जी, बोल रहा हूँ।", "ठीक है, पूछिए।", "1988", "ठीक है, धन्यवाद।"),
    "hi-en": ("Yes, बोल रही हूँ.", "OK, बताइए.", "1992", "OK, thank you."),
    "ta": ("ஆமா, நான் தான்.", "சரி, கேளுங்க.", "1985", "சரி, நன்றி."),
    "kn": ("ಹೌದು, ನಾನೇ.", "ಸರಿ, ಕೇಳಿ.", "1990", "ಸರಿ, ಧನ್ಯವಾದ."),
}

_STEP = {
    "right_party": "right_party_check",
    "disclosure": "disclosure",
    "second_check": "second_check",
    "context": "context",
    "recall": "open_recall",
    "readback": "read_back",
    "consent": "consent_check",
    "close": "close",
}
_ASKS = {
    "kind", "premium", "payment_source", "required_for_loan", "provider_choice", "cover", "term",
    "cancel_window", "features",
}  # fmt: skip


@dataclass(frozen=True)
class Step:
    """One bot question and the customer's reply, with the gold labels for that reply."""

    key: str
    reply: str | None  # None: the bot speaks and the customer does not get a turn
    gold: dict[str, object] = field(default_factory=dict)  # RawProductAnswers field -> value, DK or UN
    items: tuple[tuple[str, str | None, str | None, str | None], ...] = ()  # span, kind, amount, product
    claims: tuple[tuple[str, str], ...] = ()  # claim, span
    concerns: tuple[tuple[str, str], ...] = ()  # concern, span
    amount: int | None = None  # the amount a read-back reads back


def _step(key: str, reply: str | None, gold: dict | None = None, **extra) -> Step:
    return Step(
        key=key,
        reply=reply,
        gold=gold or {},
        items=tuple(extra.get("items", ())),
        claims=tuple(extra.get("claims", ())),
        concerns=tuple(extra.get("concerns", ())),
        amount=extra.get("amount"),
    )


def say(key: str, reply: str | None, **extra) -> Step:
    """A turn that is not a checked question (opening, context, close)."""
    return _step(key, reply, **extra)


def recall(reply: str, *items: tuple, **extra) -> Step:
    return _step("recall", reply, items=items, **extra)


def kind(reply: str, value: str, **extra) -> Step:
    return _step("kind", reply, {"kind": value}, **extra)


def premium(reply: str, span: str, **extra) -> Step:
    return _step("premium", reply, {"premium": span}, **extra)


def readback(amount: int, reply: str, confirms: object, corrected: str | None = None, **extra) -> Step:
    gold: dict[str, object] = {"premium_readback": confirms}
    if corrected:
        gold["premium"] = corrected
    return _step("readback", reply, gold, amount=amount, **extra)


def payment(reply: str, value: str, **extra) -> Step:
    return _step("payment_source", reply, {"payment_source": value}, **extra)


def required(reply: str, value: object, **extra) -> Step:
    return _step("required_for_loan", reply, {"required_for_loan": value}, **extra)


def choice(reply: str, value: object, **extra) -> Step:
    return _step("provider_choice", reply, {"provider_choice_offered": value}, **extra)


def cover(reply: str, span: str, **extra) -> Step:
    return _step("cover", reply, {"cover": span}, **extra)


def term(reply: str, span: str, **extra) -> Step:
    return _step("term", reply, {"term": span}, **extra)


def cancel(reply: str, allowed: object, window: str = UN, **extra) -> Step:
    return _step("cancel_window", reply, {"cancel_allowed": allowed, "cancel_window": window}, **extra)


def features(reply: str, claims: object, **extra) -> Step:
    return _step("features", reply, {"feature_probe": claims}, **extra)


def consent(reply: str, given: object, method: str = UN, **extra) -> Step:
    return _step("consent", reply, {"consent_given": given, "consent_method": method}, **extra)


def rec(
    *,
    premium: int,
    cover: int,
    term: int,
    from_loan: bool = True,
    required: bool = False,
    mitigant: bool = True,
    choice: bool = True,
    cancel_days: int | None = 30,
    features: tuple[str, ...] = ("one_time_payment",),
    consent: str | None = "otp",
    lender: str = "bank",
    loan: str = "gold",
) -> dict:
    return {
        "lender_type": lender,
        "loan_kind": loan,
        "sanctioned_inr": 500000,
        "disbursed_inr": 500000 - premium if from_loan else 500000,
        "disbursed_on": "2026-10-12",
        "products": [
            {
                "id": P1,
                "kind": "credit_life",
                "provider": "Namoona Life (synthetic)",
                "premium_inr": premium,
                "cover_inr": cover,
                "term_months": term,
                "paid_from_loan": from_loan,
                "required_for_loan": required,
                "risk_mitigant": mitigant,
                "provider_choice_offered": choice,
                "cancel_window_days": cancel_days,
                "features": list(features),
                "consent": {"method": consent, "at": "2026-10-12"} if consent else None,
            }
        ],
    }


@dataclass(frozen=True)
class Case:
    id: str
    language: str
    record: dict
    steps: tuple[Step, ...]
    verdict: str
    flags: frozenset[str]  # rule ids expected to raise at least one flag
    note: str


def case(
    id: str, language: str, record: dict, steps: list[Step], verdict: str, flags: str, note: str
) -> Case:
    return Case(id, language, record, tuple(steps), verdict, frozenset(flags.split()), note)


CASES: tuple[Case, ...] = (
    # --- Hindi ----------------------------------------------------------------------------
    case(
        "hi-01",
        "hi",
        rec(premium=24000, cover=400000, term=36),
        [
            recall(
                "लोन के साथ एक बीमा भी लिया था, चौबीस हज़ार का।", ("एक बीमा", "insurance", "चौबीस हज़ार", P1)
            ),
            kind("बीमा है, लोन वाला बीमा।", "insurance"),
            premium("चौबीस हज़ार रुपये लगे थे।", "चौबीस हज़ार"),
            readback(24000, "हाँ जी, बिल्कुल ठीक।", True),
            payment("लोन की रकम में से ही कट गया था।", "from_loan"),
            required("नहीं, ज़रूरी नहीं था, मैंने अपनी मर्ज़ी से लिया।", False),
            cover("चार लाख का कवर है।", "चार लाख"),
            term("तीन साल के लिए है।", "तीन साल"),
            cancel("हाँ बताया था, तीस दिन के अंदर रद्द करवा सकते हैं।", True, "तीस दिन"),
            features("नहीं, यह तो बीमा है, इसका पैसा वापस नहीं आता।", ()),
            consent("बीमा के लिए हाँ की थी, फ़ोन पर ओटीपी आया था वो बताया था।", True, "otp"),
        ],
        "clear",
        "",
        "compliant customer, every answer matches the record",
    ),
    case(
        "hi-02",
        "hi",
        rec(premium=52000, cover=500000, term=60, required=True, choice=False, consent=None),
        [
            recall(
                "बस एक एफ़डी करवाई थी लोन की सिक्योरिटी के लिए, बावन हज़ार की।",
                ("एक एफ़डी", "deposit", "बावन हज़ार", P1),
            ),
            kind("एफ़डी है, मैनेजर साहब ने यही बताया था।", "deposit"),
            premium("बावन हज़ार।", "बावन हज़ार"),
            readback(52000, "हाँ।", True),
            payment("लोन में से ही काट लिए थे, हाथ में कम पैसे आए।", "from_loan"),
            required("हाँ, बोला था कि एफ़डी के बिना लोन नहीं मिलेगा।", True),
            choice("नहीं, ऐसा कुछ नहीं बताया।", False),
            cover("कवर? कवर का मुझे नहीं पता।", DK),
            term("पाँच साल की है।", "पाँच साल"),
            cancel("नहीं, रद्द करने की कोई बात नहीं हुई।", False),
            features(
                "हाँ, एक साल बाद निकाल सकते हैं, ब्याज भी मिलेगा।",
                ("withdrawable_after_period", "guaranteed_return"),
            ),
            consent("एफ़डी के फ़ॉर्म पर साइन किया था।", True, "signed_form"),
        ],
        "flag_for_review",
        "kind cover cancel_window consent loan_funded bundling belief_mismatch",
        "customer believes the product is an FD; no consent on record",
    ),
    case(
        "hi-03",
        "hi",
        rec(premium=18500, cover=250000, term=24, cancel_days=15, consent="signed_form"),
        [
            recall("कुछ नहीं लिया, बस लोन लिया था।"),
            kind("पता नहीं जी, क्या दिया था।", DK),
            premium("", UN),
            premium("याद नहीं है कितना था।", DK),
            payment("देखिए मेरी किस्त तो हर महीने पाँच तारीख को जाती है।", UN),
            required("ये मुझे नहीं मालूम।", DK),
            cover("हैलो? आवाज़ कट रही है।", UN),
            term("दो साल शायद, पक्का नहीं पता।", UN),
            cancel("किसी ने कुछ नहीं बताया इसके बारे में।", False),
            features("इसका मुझे कोई अंदाज़ा नहीं है।", DK),
            consent(
                "जहाँ बोला वहाँ साइन कर दिए, किसी ने समझाया नहीं कि किस चीज़ के कागज़ हैं।",
                UN,
                "signed_form",
                concerns=[("signed_without_explanation", "किसी ने समझाया नहीं कि किस चीज़ के कागज़ हैं")],
            ),
        ],
        "flag_for_review",
        "kind premium cancel_window recall belief_mismatch sale_conduct",
        "does not know, silence, off-topic, a guess",
    ),
    case(
        "hi-04",
        "hi",
        rec(premium=41000, cover=600000, term=48, from_loan=False, required=True, consent="digital_click"),
        [
            recall(
                "एक एफ़डी... नहीं नहीं, बीमा था, बीमा लिया था इकतालीस हज़ार का।",
                ("बीमा", "insurance", "इकतालीस हज़ार", P1),
            ),
            kind("डिपॉज़िट... अरे नहीं, बीमा है, बीमा।", "insurance"),
            premium("चालीस हज़ार था।", "चालीस हज़ार"),
            readback(40000, "नहीं, इकतालीस हज़ार था।", False, corrected="इकतालीस हज़ार"),
            readback(41000, "हाँ, अब सही है।", True),
            payment("अलग से दिया था, यूपीआई से।", "separately"),
            required("हाँ, लोन के लिए ज़रूरी बताया था।", True),
            choice("हाँ, बताया था कि किसी भी कंपनी से ले सकते हैं।", True),
            cover("छह लाख।", "छह लाख"),
            term("चार साल।", "चार साल"),
            cancel("हाँ, एक महीने के अंदर रद्द कर सकते हैं।", True, "एक महीने"),
            features("पैसा वापस नहीं मिलेगा, बस शुरू के तीस दिन में रद्द करें तो मिलता है।", ()),
            consent("बीमे के लिए टैबलेट पर टिक किया था।", True, "digital_click"),
        ],
        "clear",
        "",
        "self-corrections and a premium corrected at read-back",
    ),
    case(
        "hi-05",
        "hi",
        rec(premium=30000, cover=300000, term=36),
        [
            say("right_party", "हाँ जी।"),
            say(
                "disclosure",
                "हाँ हाँ, ब्रांच वालों ने बताया था कि कॉल आएगा तो सब में हाँ बोल देना।",
                concerns=[("coached_answers", "कॉल आएगा तो सब में हाँ बोल देना")],
            ),
            say("second_check", "1979"),
            say("context", None),
            recall("हाँ।"),
            kind("हाँ जी।", UN),
            kind("बीमा।", "insurance"),
            premium("हाँ, लोन में से कटा था।", UN),
            premium("तीस हज़ार।", "तीस हज़ार"),
            readback(30000, "हाँ।", True),
            payment("लोन में से।", "from_loan"),
            required("हाँ।", True),
            choice("हाँ।", True),
            cover("हाँ।", UN),
            term("तीन साल।", "तीन साल"),
            cancel("हाँ।", True),
            features("हाँ, जब चाहें तब मिल जाएगा।", ("refundable_anytime",)),
            consent("हाँ, ओटीपी दिया था।", UN, "otp"),
        ],
        "flag_for_review",
        "recall belief_mismatch sale_conduct",
        "coached customer who says yes to everything and answers a different question",
    ),
    # --- Hinglish -------------------------------------------------------------------------
    case(
        "en-01",
        "hi-en",
        rec(
            premium=12500,
            cover=200000,
            term=24,
            from_loan=False,
            cancel_days=None,
            consent="recorded_call",
            lender="nbfc",
            loan="personal",
        ),
        [
            recall(
                "Loan के साथ एक insurance policy भी ली थी, 12,500 की.",
                ("एक insurance policy", "insurance", "12,500", P1),
            ),
            kind("Insurance है, loan protection वाला.", "insurance"),
            premium("12,500 rupees.", "12,500"),
            readback(12500, "Yes, correct है.", True),
            payment("मैंने अलग से pay किया था, अपने account से.", "separately"),
            required("नहीं, compulsory नहीं था, मेरी choice थी.", False),
            cover("2 लाख का cover है.", "2 लाख"),
            term("2 साल का है.", "2 साल"),
            cancel("नहीं, cancel के बारे में कुछ नहीं बताया.", False),
            features("Refund नहीं मिलता, pure insurance है.", ()),
            consent("Insurance के लिए phone पे yes बोला था, call record हो रही थी.", True, "recorded_call"),
        ],
        "clear",
        "",
        "compliant; paid separately; no cancel window on record",
    ),
    case(
        "en-02",
        "hi-en",
        rec(premium=35000, cover=500000, term=60, loan="personal"),
        [
            recall(
                "Insurance लिया था, 20,000 का, और processing fee भी लगी थी.",
                ("Insurance", "insurance", "20,000", P1),
                ("processing fee", "fee", None, None),
            ),
            kind("Insurance.", "insurance"),
            premium("20,000 के आसपास था.", "20,000"),
            readback(20000, "हाँ, 20,000.", True),
            payment("Loan amount से ही deduct हुआ था.", "from_loan"),
            required("नहीं, मैंने खुद choose किया.", False),
            cover("5 lakh.", "5 lakh"),
            term("5 years.", "5 years"),
            cancel("हाँ, 30 days के अंदर cancel कर सकते हैं.", True, "30 days"),
            features("नहीं, पैसा वापस नहीं आता.", ()),
            consent("Insurance के form पे sign किया था branch में.", True, "signed_form"),
        ],
        "flag_for_review",
        "premium consent",
        "premium differs from the record and is confirmed; consent method differs",
    ),
    case(
        "en-03",
        "hi-en",
        rec(
            premium=28000,
            cover=350000,
            term=36,
            required=True,
            consent="digital_click",
            lender="nbfc",
            loan="personal",
        ),
        [
            recall(
                "कुछ खास नहीं, बस loan, बाद में statement में देखा कि 28,000 का insurance कटा है.",
                ("insurance", "insurance", "28,000", P1),
                concerns=[("learned_after_sale", "बाद में statement में देखा कि 28,000 का insurance कटा है")],
            ),
            kind("Insurance है, ऐसा statement में लिखा था.", "insurance"),
            premium("28,000.", "28,000"),
            readback(28000, "हाँ.", True),
            payment("Loan में से कटा, मुझे तो पूरा amount मिला ही नहीं.", "from_loan"),
            required("Agent ने बोला था compulsory है, इसके बिना loan approve नहीं होगा.", True),
            choice("नहीं, बोला यही company का लेना पड़ेगा.", False),
            cover("Cover कितना है वो नहीं पता.", DK),
            term("शायद 3 साल.", UN),
            cancel("पता नहीं, याद नहीं कि बताया था या नहीं.", DK),
            features(
                "Loan close होने के बाद ये amount वापस मिल जाएगा, ऐसा बोला था.",
                ("withdrawable_after_period",),
            ),
            consent("App पे accept button दबाया था, उसी में insurance भी था.", True, "digital_click"),
        ],
        "flag_for_review",
        "bundling cover cancel_window belief_mismatch sale_conduct",
        "required with no choice of provider; learned of it after the sale",
    ),
    case(
        "en-04",
        "hi-en",
        rec(premium=15000, cover=150000, term=12, cancel_days=15, consent="signed_form"),
        [
            recall(
                "एक insurance लिया 15,000 का, और एक mutual fund SIP भी शुरू करवाई थी.",
                ("एक insurance", "insurance", "15,000", P1),
                ("एक mutual fund SIP", "investment", None, None),
            ),
            kind("Insurance ही है.", "insurance"),
            premium("Fifteen thousand.", "Fifteen thousand"),
            readback(15000, "जी हाँ.", True),
            payment("Loan amount से cut हुआ.", "from_loan"),
            required("नहीं नहीं, ज़बरदस्ती नहीं थी.", False),
            cover("डेढ़ लाख.", "डेढ़ लाख"),
            term("1 साल.", "1 साल"),
            cancel("Cancel हो सकता है ये बताया था, लेकिन कितने दिन में वो याद नहीं.", True, DK),
            features("नहीं मिलेगा वापस.", ()),
            consent("Insurance और SIP दोनों के forms sign किए थे.", True, "signed_form"),
        ],
        "flag_for_review",
        "recall_unmatched cancel_window",
        "names a product that is not on the record; does not know the cancel window",
    ),
    case(
        "en-05",
        "hi-en",
        rec(premium=22000, cover=300000, term=36, loan="personal"),
        [
            recall(
                "Loan protection insurance लिया था, 22,000 का.",
                ("Loan protection insurance", "insurance", "22,000", P1),
            ),
            kind("Insurance.", "insurance"),
            premium("22,000 या 25,000, इन दोनों में से कुछ था.", UN),
            premium("22,000 ही था.", "22,000"),
            readback(22000, "Right.", True),
            payment("Loan से ही कटा था.", "from_loan"),
            required("Optional था.", False),
            cover("एक minute, network issue है... हाँ बोलिए.", UN),
            term("36 months.", "36 months"),
            cancel("हाँ, 30 दिन के अंदर.", True, "30 दिन"),
            features("नहीं, वापस नहीं मिलता, सिर्फ death होने पे family को claim मिलता है.", ()),
            consent("Insurance के लिए OTP share किया था.", True, "otp"),
        ],
        "unclear_needs_human",
        "",
        "everything right except the cover question, which got no answer",
    ),
    # --- Tamil (not human-reviewed) ---------------------------------------------------------
    case(
        "ta-01",
        "ta",
        rec(premium=18000, cover=300000, term=24, consent="signed_form"),
        [
            recall("கடனோட ஒரு இன்சூரன்ஸ் எடுத்தேன், 18,000 ரூபாய்.", ("ஒரு இன்சூரன்ஸ்", "insurance", "18,000", P1)),
            kind("அது இன்சூரன்ஸ் தான்.", "insurance"),
            premium("18,000 ரூபாய்.", "18,000"),
            readback(18000, "ஆமா, சரிதான்.", True),
            payment("கடன் தொகையிலிருந்தே பிடிச்சுக்கிட்டாங்க.", "from_loan"),
            required("இல்லை, கட்டாயம் இல்லை, நானே விரும்பி எடுத்தேன்.", False),
            cover("3 லட்சம் கவர்.", "3 லட்சம்"),
            term("2 வருஷம்.", "2 வருஷம்"),
            cancel("ஆமா, 30 நாள் உள்ள ரத்து பண்ணலாம்னு சொன்னாங்க.", True, "30 நாள்"),
            features("இல்லை, அது இன்சூரன்ஸ், பணம் திரும்ப வராது.", ()),
            consent("இன்சூரன்ஸ்க்கு ஃபார்ம்ல கையெழுத்து போட்டேன்.", True, "signed_form"),
        ],
        "clear",
        "",
        "compliant customer",
    ),
    case(
        "ta-02",
        "ta",
        rec(premium=45000, cover=500000, term=60, required=True, consent=None),
        [
            recall(
                "நகைக்கடனுக்கு பாதுகாப்புன்னு ஒரு எஃப்டி போட்டாங்க, 45,000 ரூபாய்.",
                ("ஒரு எஃப்டி", "deposit", "45,000", P1),
            ),
            kind("எஃப்டி தான், பேங்க்ல அப்படித்தான் சொன்னாங்க.", "deposit"),
            premium("45,000.", "45,000"),
            readback(45000, "ஆமா.", True),
            payment("லோன் பணத்துல இருந்து கழிச்சுட்டாங்க.", "from_loan"),
            required("ஆமா, இது இல்லாம லோன் கிடைக்காதுன்னு சொன்னாங்க.", True),
            choice("வேற கம்பெனி பத்தி ஒண்ணும் சொல்லலை.", False),
            cover("கவர்னா என்னன்னே தெரியாது.", DK),
            term("5 வருஷம்.", "5 வருஷம்"),
            cancel("ரத்து பண்றது பத்தி யாரும் சொல்லலை.", False),
            features(
                "தேவைப்பட்டா எந்த நேரத்துலயும் பணத்த திரும்ப வாங்கிக்கலாம்னு சொன்னாங்க.",
                ("refundable_anytime",),
            ),
            consent("எஃப்டிக்குன்னு சொல்லி பேப்பர்ல கையெழுத்து வாங்கினாங்க.", True, "signed_form"),
        ],
        "flag_for_review",
        "kind cover cancel_window consent loan_funded bundling belief_mismatch",
        "customer believes the product is an FD they can take back at any time",
    ),
    case(
        "ta-03",
        "ta",
        rec(premium=9500, cover=100000, term=12, cancel_days=15, lender="nbfc", loan="personal"),
        [
            recall("ஒண்ணும் எடுக்கலை, லோன் மட்டும் தான்."),
            kind("அது என்னன்னு எனக்கு புரியலை, தெரியாது.", DK),
            premium("எவ்வளவுன்னு நினைவில்லை.", DK),
            payment("", UN),
            required("ஹலோ, கொஞ்சம் சத்தமா பேசுங்க.", UN),
            cover("தெரியாது.", DK),
            term("ஒரு வருஷம்னு நினைக்கிறேன், சரியா தெரியலை.", UN),
            cancel("அப்படி ஒண்ணும் சொல்லலை.", False),
            features("அத பத்தி எனக்கு எதுவும் தெரியாது.", DK),
            consent("லோனுக்கு மட்டும் தான் ஒத்துக்கிட்டேன், வேற எதுக்கும் இல்லை, OTP சொன்னேன்.", False, "otp"),
        ],
        "flag_for_review",
        "kind premium cover cancel_window recall consent belief_mismatch",
        "does not know; silence; says they agreed only to the loan",
    ),
    case(
        "ta-04",
        "ta",
        rec(premium=27500, cover=400000, term=36, from_loan=False, loan="personal"),
        [
            recall(
                "ஒரு இன்சூரன்ஸ் பாலிசி, 27,500 ரூபாய் கட்டினேன்.",
                ("ஒரு இன்சூரன்ஸ் பாலிசி", "insurance", "27,500", P1),
            ),
            kind("நான் தனியா கேஷ் கட்டினேன்.", UN),
            kind("இன்சூரன்ஸ் பாலிசி.", "insurance"),
            premium("27,000.", "27,000"),
            readback(27000, "இல்லை இல்லை, 27,500.", False, corrected="27,500"),
            readback(27500, "சரி, அதான்.", True),
            payment("நானே தனியா கட்டினேன், லோன்ல இருந்து இல்லை.", "separately"),
            required("கட்டாயம்னு சொல்லலை, என் விருப்பம் தான்.", False),
            cover("4 லட்சம்.", "4 லட்சம்"),
            term("3 வருஷம்.", "3 வருஷம்"),
            cancel("ஆமா, 30 நாள் டைம் இருக்கு, அதுக்குள்ள கேன்சல் பண்ணலாம்.", True, "30 நாள்"),
            features("திரும்ப கிடைக்காது, எனக்கு ஏதாவது ஆனா தான் குடும்பத்துக்கு பணம் வரும்.", ()),
            consent("இன்சூரன்ஸ்க்கு சம்மதிச்சேன், மொபைலுக்கு வந்த OTP நம்பர் சொன்னேன்.", True, "otp"),
        ],
        "clear",
        "",
        "answers a different question once; premium corrected at read-back",
    ),
    case(
        "ta-05",
        "ta",
        rec(premium=32000, cover=450000, term=48, consent="digital_click", lender="nbfc"),
        [
            recall(
                "இன்சூரன்ஸ்னு ஒண்ணு இருக்குன்னு லோன் வந்ததுக்கு அப்புறம் தான் தெரிஞ்சது, 32,000 பிடிச்சிருக்காங்க.",
                ("இன்சூரன்ஸ்னு ஒண்ணு", "insurance", "32,000", P1),
                concerns=[("learned_after_sale", "லோன் வந்ததுக்கு அப்புறம் தான் தெரிஞ்சது")],
            ),
            kind("இன்சூரன்ஸ்.", "insurance"),
            premium("32,000 ரூபாய்.", "32,000"),
            readback(32000, "ஆமா.", True),
            payment("லோன் தொகையில கழிச்சிட்டாங்க.", "from_loan"),
            required("இல்லை.", False),
            cover("2 லட்சம்.", "2 லட்சம்"),
            term("2 வருஷம்.", "2 வருஷம்"),
            cancel("கேன்சல் பண்ணலாம்னு சொன்னாங்க, ஆனா எத்தனை நாள்னு ஞாபகம் இல்லை.", True, DK),
            features("திரும்ப வராது.", ()),
            consent(
                "ஏஜென்ட் டேப்லெட்ல அழுத்த சொன்னார், அழுத்தினேன், எதுக்குன்னு சொல்லலை.",
                UN,
                "digital_click",
                concerns=[("signed_without_explanation", "எதுக்குன்னு சொல்லலை")],
            ),
            say(
                "close",
                "சரி. கால் வந்தா எல்லாத்துக்கும் ஆமான்னு சொல்லுங்கன்னு ஆபீஸ்ல சொன்னாங்க.",
                concerns=[("coached_answers", "கால் வந்தா எல்லாத்துக்கும் ஆமான்னு சொல்லுங்கன்னு ஆபீஸ்ல சொன்னாங்க")],
            ),
        ],
        "flag_for_review",
        "cover term cancel_window sale_conduct",
        "wrong cover and term; three sale concerns, one voiced at the close",
    ),
    # --- Kannada (not human-reviewed) -------------------------------------------------------
    case(
        "kn-01",
        "kn",
        rec(premium=21000, cover=300000, term=36, required=True, loan="personal"),
        [
            recall("ಸಾಲದ ಜೊತೆ ಒಂದು ವಿಮೆ ತಗೊಂಡೆ, 21,000 ರೂಪಾಯಿ.", ("ಒಂದು ವಿಮೆ", "insurance", "21,000", P1)),
            kind("ಅದು ವಿಮೆ, ಸಾಲಕ್ಕೆ ಸಂಬಂಧಿಸಿದ್ದು.", "insurance"),
            premium("21,000 ರೂಪಾಯಿ.", "21,000"),
            readback(21000, "ಹೌದು, ಸರಿ.", True),
            payment("ಸಾಲದ ಹಣದಲ್ಲೇ ಕಟ್ ಮಾಡಿದ್ರು.", "from_loan"),
            required("ಹೌದು, ಸಾಲಕ್ಕೆ ಇದು ಬೇಕೇ ಬೇಕು ಅಂತ ಹೇಳಿದ್ರು.", True),
            choice("ಹೌದು, ಬೇರೆ ಕಂಪನಿಯಲ್ಲೂ ಮಾಡಿಸಬಹುದು ಅಂತ ಹೇಳಿದ್ರು.", True),
            cover("3 ಲಕ್ಷ ಕವರ್ ಇದೆ.", "3 ಲಕ್ಷ"),
            term("3 ವರ್ಷ.", "3 ವರ್ಷ"),
            cancel("ಹೌದು, 30 ದಿನ ಒಳಗೆ ಕ್ಯಾನ್ಸಲ್ ಮಾಡಬಹುದು.", True, "30 ದಿನ"),
            features("ಇಲ್ಲ, ವಿಮೆ ಹಣ ವಾಪಸ್ ಬರಲ್ಲ.", ()),
            consent("ವಿಮೆಗೆ ಒಪ್ಪಿದ್ದೆ, ಮೊಬೈಲ್‌ಗೆ ಬಂದ OTP ಕೊಟ್ಟೆ.", True, "otp"),
        ],
        "clear",
        "",
        "compliant; required as a risk mitigant with a choice of provider",
    ),
    case(
        "kn-02",
        "kn",
        rec(
            premium=60000,
            cover=800000,
            term=60,
            required=True,
            choice=False,
            consent="signed_form",
            lender="nbfc",
        ),
        [
            recall(
                "ಚಿನ್ನದ ಸಾಲಕ್ಕೆ ಭದ್ರತೆ ಅಂತ ಒಂದು ಫಿಕ್ಸೆಡ್ ಡೆಪಾಸಿಟ್ ಇಟ್ಟಿದ್ದೀನಿ, 60,000.",
                ("ಒಂದು ಫಿಕ್ಸೆಡ್ ಡೆಪಾಸಿಟ್", "deposit", "60,000", P1),
            ),
            kind("ಡೆಪಾಸಿಟ್ ಅದು, ಮ್ಯಾನೇಜರ್ ಹಾಗೇ ಹೇಳಿದ್ರು.", "deposit"),
            premium("60,000.", "60,000"),
            readback(60000, "ಹೌದು.", True),
            payment("ಸಾಲದ ಮೊತ್ತದಿಂದಲೇ ಹಿಡ್ಕೊಂಡ್ರು.", "from_loan"),
            required("ಹೌದು, ಇದಿಲ್ಲದೆ ಸಾಲ ಕೊಡಲ್ಲ ಅಂದ್ರು.", True),
            choice("ಗೊತ್ತಿಲ್ಲ, ನೆನಪಿಲ್ಲ.", DK),
            cover("8 ಲಕ್ಷ.", "8 ಲಕ್ಷ"),
            term("5 ವರ್ಷ.", "5 ವರ್ಷ"),
            cancel("ಇಲ್ಲ, ಅದರ ಬಗ್ಗೆ ಯಾರೂ ಹೇಳಿಲ್ಲ.", False),
            features(
                "5 ವರ್ಷ ಆದ್ಮೇಲೆ ಬಡ್ಡಿ ಸೇರಿ ವಾಪಸ್ ಬರುತ್ತೆ.",
                ("withdrawable_after_period", "guaranteed_return"),
            ),
            consent("ಡೆಪಾಸಿಟ್‌ಗೆ ಅಂತ ಫಾರ್ಮ್‌ಗೆ ಸಹಿ ಹಾಕಿದೆ.", True, "signed_form"),
        ],
        "flag_for_review",
        "kind cancel_window bundling belief_mismatch",
        "customer believes the product is a deposit that returns with interest",
    ),
    case(
        "kn-03",
        "kn",
        rec(premium=14000, cover=200000, term=24, cancel_days=15, consent="verbal", loan="personal"),
        [
            recall("ಗೊತ್ತಿಲ್ಲ ಸರ್, ಸಾಲ ಮಾತ್ರ ತಗೊಂಡಿದ್ದು."),
            kind("ಏನು ಅಂತ ನನಗೆ ಗೊತ್ತಿಲ್ಲ.", DK),
            premium("ತಿಂಗಳ ಕಂತು 6,500 ಕಟ್ತಾ ಇದ್ದೀನಿ.", UN),
            premium("ನೆನಪಿಲ್ಲ.", DK),
            payment("ಅದು ನನಗೆ ತಿಳಿದಿಲ್ಲ.", DK),
            required("", UN),
            cover("ಗೊತ್ತಿಲ್ಲ.", DK),
            term("ನೆನಪಿಲ್ಲ.", DK),
            cancel("ಹೇಳಿದ್ರೋ ಇಲ್ವೋ ನೆನಪಿಲ್ಲ.", DK),
            features("ಗೊತ್ತಿಲ್ಲ, ಯಾರೂ ಏನೂ ಹೇಳಿಲ್ಲ.", DK),
            consent("ನಾನು ಸಾಲಕ್ಕೆ ಮಾತ್ರ ಒಪ್ಪಿದ್ದು, ಬೇರೆ ಯಾವುದಕ್ಕೂ ಇಲ್ಲ.", False),
        ],
        "flag_for_review",
        "kind premium cover term cancel_window recall consent loan_funded belief_mismatch",
        "does not know anything about the product; gives the EMI when asked the premium",
    ),
    case(
        "kn-04",
        "kn",
        rec(
            premium=16500,
            cover=250000,
            term=24,
            from_loan=False,
            cancel_days=None,
            consent="recorded_call",
            lender="nbfc",
            loan="personal",
        ),
        [
            recall(
                "ಒಂದು ಇನ್ಶೂರೆನ್ಸ್ ಪಾಲಿಸಿ ಮಾಡಿಸಿದೆ, 16,500 ಕಟ್ಟಿದೆ, ಜೊತೆಗೆ ಪ್ರೊಸೆಸಿಂಗ್ ಫೀ ಇತ್ತು.",
                ("ಒಂದು ಇನ್ಶೂರೆನ್ಸ್ ಪಾಲಿಸಿ", "insurance", "16,500", P1),
                ("ಪ್ರೊಸೆಸಿಂಗ್ ಫೀ", "fee", None, None),
            ),
            kind("ಎಫ್‌ಡಿ... ಅಲ್ಲ ಅಲ್ಲ, ಇನ್ಶೂರೆನ್ಸ್.", "insurance"),
            premium("16,500 ರೂಪಾಯಿ.", "16,500"),
            readback(16500, "ಹೌದು ಹೌದು.", True),
            payment("ಸಾಲದಿಂದ... ಇಲ್ಲ, ನಾನೇ ಬೇರೆಯಾಗಿ ಫೋನ್‌ಪೇ ಮಾಡಿದೆ.", "separately"),
            required("ಇಲ್ಲ, ಕಡ್ಡಾಯ ಇರಲಿಲ್ಲ.", False),
            cover("ಎರಡೂವರೆ ಲಕ್ಷ.", "ಎರಡೂವರೆ ಲಕ್ಷ"),
            term("2 ವರ್ಷ.", "2 ವರ್ಷ"),
            cancel("ರದ್ದು ಮಾಡಬಹುದು ಅಂತ ಯಾರೂ ತಿಳಿಸಿಲ್ಲ.", False),
            features("ವಾಪಸ್ ಸಿಗಲ್ಲ, ಇದು ಇನ್ಶೂರೆನ್ಸ್ ಅಲ್ವಾ.", ()),
            consent("ಇನ್ಶೂರೆನ್ಸ್‌ಗೆ ಫೋನ್‌ನಲ್ಲಿ ಹೌದು ಅಂದೆ, ಆ ಕಾಲ್ ರೆಕಾರ್ಡ್ ಆಗ್ತಿತ್ತು.", True, "recorded_call"),
        ],
        "clear",
        "",
        "self-corrections on kind and payment; a fee named in recall",
    ),
    case(
        "kn-05",
        "kn",
        rec(premium=25000, cover=300000, term=36, from_loan=False, features=(), consent="signed_form"),
        [
            recall(
                "ಒಂದು ಇನ್ಶೂರೆನ್ಸ್ ಕೊಟ್ಟಿದ್ದಾರೆ, 25,000 ಒಂದೇ ಸಲ ಕಟ್ಟಿದ್ರೆ ಸಾಕು ಅಂದ್ರು.",
                ("ಒಂದು ಇನ್ಶೂರೆನ್ಸ್", "insurance", "25,000", P1),
                claims=[("one_time_payment", "ಒಂದೇ ಸಲ ಕಟ್ಟಿದ್ರೆ ಸಾಕು")],
            ),
            kind("ಇನ್ಶೂರೆನ್ಸ್.", "insurance"),
            premium("25,000.", "25,000"),
            readback(25000, "ಸರಿ.", True),
            payment("ಸಾಲದ ದುಡ್ಡಲ್ಲೇ ಮುರ್ಕೊಂಡ್ರು.", "from_loan"),
            required("ಇಲ್ಲ.", False),
            cover("3 ಲಕ್ಷ.", "3 ಲಕ್ಷ"),
            term("3 ವರ್ಷ.", "3 ವರ್ಷ"),
            cancel("ಹೌದು, 15 ದಿನ ಅಂದ್ರು.", True, "15 ದಿನ"),
            features("ವಾಪಸ್ ಬರಲ್ಲ.", ()),
            consent("ಇನ್ಶೂರೆನ್ಸ್‌ಗೆ ಬಾಯಿ ಮಾತಲ್ಲಿ ಒಪ್ಪಿದೆ ಅಷ್ಟೇ, ಯಾವ ಸಹಿನೂ ಹಾಕಿಲ್ಲ.", True, "verbal"),
        ],
        "flag_for_review",
        "cancel_window consent loan_funded belief_mismatch",
        "volunteers a one-time-payment belief; says it was deducted though the record says paid separately",
    ),
)


# --- building transcripts and gold -----------------------------------------------------------


def _answer(value: object, reply: str, turn_id: int) -> dict:
    evidence = {"quote": reply, "turn_id": turn_id}
    if value == UN:
        return {"status": "unclear"}
    if value == DK:
        return {"status": "dont_know", "evidence": evidence}
    return {"status": "stated", "value": value, "evidence": evidence}


def build(c: Case) -> Scenario:
    loan_id = f"LN-DEV-{c.id.upper()}"
    record = LoanRecord.model_validate(
        c.record
        | {
            "loan_id": loan_id,
            "borrower": {"name": f"Dev Borrower {c.id}", "dob": "1988-01-01", "language": c.language},
        }
    )
    bot = BOT[c.language]
    steps = list(c.steps)
    if steps[0].key != "right_party":
        hello, go_on, year, _ = OPENING[c.language]
        steps = [
            say("right_party", hello), say("disclosure", go_on), say("second_check", year),
            say("context", None), *steps,
        ]  # fmt: skip
    if steps[-1].key != "close":
        steps.append(say("close", OPENING[c.language][3]))

    turns: list[dict] = []
    answers: dict[str, dict] = {}
    items, claims, concerns = [], [], []
    recall_answer = None
    asked_before: set[str] = set()
    for step in steps:
        text = bot[step.key]
        if step.key == "right_party":
            text = text.format(name="देव" if c.language in ("hi", "hi-en") else "Dev")
        if step.key == "readback":
            text = text.format(spoken=spoken_amount(step.amount, c.language), inr=format_inr(step.amount))
        elif step.key in asked_before:
            text = bot["again"] + text
        asked_before.add(step.key)
        turn = {
            "id": len(turns) + 1,
            "speaker": "bot",
            "step": _STEP.get(step.key, "teach_back"),
            "text": text,
        }
        if step.key in _ASKS:
            turn |= {"asks": step.key, "product_id": P1}
        elif step.key == "readback":
            turn |= {"asks": "premium", "product_id": P1}
        elif step.key == "consent":
            turn |= {"asks": "consent"}
        turns.append(turn)
        if step.reply is None:
            continue
        turn_id = len(turns) + 1
        turns.append({"id": turn_id, "speaker": "customer", "step": turn["step"], "text": step.reply})
        for name, value in step.gold.items():
            answers[name] = _answer(value, step.reply, turn_id)
        if step.key == "recall":
            recall_answer = {"quote": step.reply, "turn_id": turn_id}
        for span, item_kind, amount, product in step.items:
            items.append(
                {
                    "evidence": {"quote": span, "turn_id": turn_id},
                    "kind": item_kind,
                    "amount_text": amount,
                    "product_id": product,
                }
            )
        claims += [{"claim": k, "evidence": {"quote": span, "turn_id": turn_id}} for k, span in step.claims]
        concerns += [
            {"concern": k, "evidence": {"quote": span, "turn_id": turn_id}} for k, span in step.concerns
        ]

    call_id = f"dev-{c.id}"
    transcript = Transcript.model_validate(
        {"call_id": call_id, "loan_id": loan_id, "language": c.language, "turns": turns}
    )
    gold_raw = RawExtraction.model_validate(
        {
            "call_id": call_id,
            "recall": {"asked": True, "answer": recall_answer, "items": items},
            "products": [{"product_id": P1, "volunteered_claims": claims, **answers}],
            "sale_concerns": concerns,
        }
    )
    perfect = evaluate(record, to_beliefs(gold_raw, record, transcript))
    return Scenario(c.id, record, transcript, GoldLabels.of(perfect), gold_raw, perfect, c.note)


def scenarios() -> tuple[Scenario, ...]:
    return tuple(build(c) for c in CASES)


def expectations() -> dict[str, tuple[Verdict, frozenset[RuleId]]]:
    """What the author expects of each case, before the rule engine is asked."""
    return {c.id: (Verdict(c.verdict), frozenset(RuleId(f) for f in c.flags)) for c in CASES}
