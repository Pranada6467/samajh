"""Call v2 (iteration 2, package P2): the reviewers' findings and the new behaviour, pinned.

The probe sentences marked "verifier" and "judge" are copied from
references/reviews/iter1/probes/dialogue_attack.py and judge-probes/judge_goahead_probe.sh. The
"fresh" sets were written by the P2 builder before the word lists were changed, to check that the
fix is not fitted to the reviewers' sentences. All are LLM-written text, not speech. Tamil and
Kannada sentences are not human-reviewed.
"""

from __future__ import annotations

import pytest
from dialogue_kit import CUSTOMERS, LANGUAGES, LENDER, NO_CHECK, YEAR_POLICY, play, product, record

from samajh.amounts import parse_amount
from samajh.dialogue import (
    LINES,
    PRODUCT_QUESTIONS,
    EndOfCall,
    Expecting,
    Outcome,
    call_seconds,
    expecting,
    load_prompts,
    start,
    step,
)
from samajh.dialogue.machine import AtCallbackTime, AtReadBack, AtStopCheck, AtTeachBack
from samajh.types import Language, Question, Speaker

HI, HE, TA, KN = Language.hi, Language.hi_en, Language.ta, Language.kn

OPENING = {
    HI: ["हाँ जी, बोल रहा हूँ", "हाँ", "1984"],
    HE: ["yes, speaking", "haan okay", "1984"],
    TA: ["ஆமா, நான்தான்", "சரி", "1984"],
    KN: ["ಹೌದು, ನಾನೇ", "ಸರಿ", "1984"],
}
NAMED = {HI: "एक एफडी ली थी", HE: "ek FD li thi", TA: "ஒரு எஃப்டி வாங்கினேன்", KN: "ಒಂದು ಎಫ್‌ಡಿ ತೆಗೆದುಕೊಂಡೆ"}


def loan_named(call) -> bool:
    return "context.loan" in call.keys


# --- 1. who is believed at the opening ----------------------------------------------------------

VERIFIER_THIRD_PARTY = {
    HI: [
        ["हाँ बोलिए", "हाँ", "पापा 1984 में पैदा हुए थे"],
        ["हाँ जी, रमेश की वाइफ़ बोल रही हूँ", "ठीक है", "1984"],
        ["जी मैं रमेश का भाई हूँ, बताइए", "हाँ", "चौरासी"],
        ["हाँ, वो मेरे हस्बैंड हैं", "जी", "1984"],
        ["हाँ जी बताइए, रमेश सर की डेस्क से बोल रहा हूँ", "हाँ बताइए", "उन्नीस सौ चौरासी"],
        ["कौन?", "हाँ हैं, बुलाती हूँ", "हाँ", "1984"],
        ["जी, पापा अभी दुकान पर हैं, बोलिए", "हाँ जी", "डैडी का बर्थ ईयर 1984 है"],
        ["हाँ जी, मैं रमेश जी की बेटी हूँ", "हाँ ठीक है", "सन चौरासी"],
        ["हाँ बेटा बोलो, रमेश तो खेत गया है", "हाँ", "1984"],
        ["जी, रमेश भैया का फ़ोन मेरे पास छूट गया है, बोलिए", "ठीक है बोलिए", "1984"],
    ],
    HE: [
        ["yes this is Ramesh's wife", "ok", "1984"],
        ["haan ji boliye, papa abhi shop pe hain", "yes", "papa ka birth year 1984 hai"],
        ["yes tell me, Ramesh sir is in a meeting", "okay go ahead", "nineteen eighty four"],
        ["haan, main Ramesh ki wife bol rahi hoon", "theek hai", "1984"],
        ["yes, Ramesh's brother here", "sure", "84"],
        ["yes, I am Ramesh sir's assistant, boliye", "okay", "1984"],
        ["who is this?", "yes he is on the line, one minute", "yes", "1984"],
        ["ji, daddy bahar gaye hain, aap bataiye", "haan", "1984"],
    ],
    TA: [
        ["ஆமா, நான் அவர் மனைவி பேசுறேன்", "சரி", "அவர் 1984ல பிறந்தார்"],
        ["சொல்லுங்க, அவர் கடைக்கு போயிருக்கார்", "சரி சொல்லுங்க", "1984"],
        ["ஆமாங்க, அவர் என் வீட்டுக்காரர்", "ஆமா", "1984"],
        ["அப்பா தூங்குறாங்க, சொல்லுங்க", "சரி", "1984"],
        ["சார் மீட்டிங்ல இருக்காரு, சொல்லுங்க", "ஓகே", "1984"],
        ["ஆமா, நான் ரமேஷ் தம்பி பேசுறேன்", "சரிங்க", "1984"],
        ["யாரு?", "ஆமா இருக்காரு, கூப்பிடுறேன்", "சரி", "1984"],
        ["ஆமா பா, ரமேஷ் வயலுக்கு போயிருக்கான், சொல்லு", "சரி", "1984"],
    ],
    KN: [
        ["ಹೇಳಿ, ರಮೇಶ್ ಆಫೀಸಿಗೆ ಹೋಗಿದ್ದಾರೆ", "ಸರಿ", "1984"],
        ["ಹೌದು, ನಾನು ರಮೇಶ್ ಹೆಂಡತಿ ಮಾತಾಡ್ತಿದ್ದೀನಿ", "ಸರಿ ಹೇಳಿ", "1984"],
        ["ಅಪ್ಪ ಮಲಗಿದ್ದಾರೆ, ಹೇಳಿ", "ಆಯ್ತು", "1984"],
        ["ಸರ್ ಮೀಟಿಂಗ್‌ನಲ್ಲಿದ್ದಾರೆ, ಹೇಳಿ", "ಓಕೆ", "1984"],
        ["ಹೌದು, ನಾನು ರಮೇಶ್ ತಮ್ಮ", "ಸರಿ", "1984"],
        ["ಯಾರು?", "ಹೌದು ಇದ್ದಾರೆ, ಕರೀತೀನಿ", "ಸರಿ", "1984"],
        ["ಹೌದಪ್ಪ ಹೇಳು, ರಮೇಶ ಹೊಲಕ್ಕೆ ಹೋಗಿದ್ದಾನೆ", "ಸರಿ", "1984"],
        ["ಹೌದು, ನಾನು ರಮೇಶ್ ಮಗಳು", "ಹೂಂ", "1984"],
    ],
}

FRESH_THIRD_PARTY = {
    HI: [
        ["हाँ जी, मैं उनकी मिसेज़ बोल रही हूँ", "हाँ", "1984"],
        ["जी बताइए, वो नहा रहे हैं", "ठीक है", "1984"],
        ["हाँ, मैं रमेश का बेटा हूँ", "हाँ", "1984"],
        ["हेलो, हाँ, ये रमेश जी का नंबर है, आप बोलिए", "हाँ", "1984"],
        ["हाँ बोलिए, मैं उनके घर से बोल रहा हूँ", "हाँ", "1984"],
        ["अभी वो बाहर गए हैं, मुझे बता दीजिए", "हाँ", "1984"],
        ["जी मैं उनकी बहू हूँ, कहिए", "हाँ", "1984"],
        ["जी हाँ", "हाँ", "पति का जन्म 1984 में हुआ था"],
        ["हाँ", "जी", "उनका बर्थ ईयर चौरासी है"],
        ["कौन बोल रहा है?", "हम उनके पड़ोसी हैं, बताइए", "हाँ", "1984"],
        ["रमेश? वो तो दुकान गए", "अच्छा बोलिए", "हाँ", "1984"],
        ["हाँ जी, घर पर ही हैं, फ़ोन देती हूँ", "हाँ", "1984"],
        ["जी, मैं उनका ड्राइवर हूँ", "हाँ", "1984"],
        ["हाँ, बोलिए क्या काम है उनसे", "हाँ", "1984"],
    ],
    HE: [
        ["haan ji, Ramesh ji ke bhai bol raha hoon", "haan", "1984"],
        ["yes, his son here, tell me", "yes", "1984"],
        ["hello, this is Ramesh's office, go ahead", "ok", "1984"],
        ["haan bolo, papa so rahe hain", "haan", "1984"],
        ["yes he is my husband, tell me", "okay", "1984"],
        ["ji boliye, sir abhi busy hain", "haan", "1984"],
    ],
}


@pytest.mark.parametrize(
    "language, replies",
    [
        (lang, r)
        for sets in (VERIFIER_THIRD_PARTY, FRESH_THIRD_PARTY)
        for lang, rs in sets.items()
        for r in rs
    ],
)
def test_a_third_party_never_hears_the_loan(language, replies):
    call = play(record(), language, replies)
    assert not loan_named(call), call.keys


@pytest.mark.parametrize("language", [HI, HE])
def test_a_third_party_is_told_only_that_the_call_was_for_the_first_name(language):
    reply = {HI: "हाँ जी, मैं उनकी पत्नी बोल रही हूँ", HE: "yes, I am his wife"}[language]
    call = play(record(), language, [reply])
    assert call.end is not None and call.end.outcome is Outcome.wrong_party
    assert call.keys == ("right_party.ask", "end.third_party")
    text = call.end.utterance.text
    assert "Ramesh" in text and "Udaharan" not in text and "लोन" not in text


@pytest.mark.parametrize("language", [HI, HE])
def test_the_reask_asks_whether_the_speaker_is_the_borrower_not_whether_he_is_there(language):
    call = play(record(), language, ["कौन?"])
    reask = call.utterances[-1].text
    assert "लाइन पर" not in reask and "on the line" not in reask.casefold()
    assert call.keys[-1] == "right_party.reask"


# Round 3: a go-on reply after the re-ask is an ordinary confirmation (birth year, no lender); a reply
# that confirms nothing still ends the call at the second try.
@pytest.mark.parametrize("replies", [["कौन?", "बताइए"], ["कौन?", "okay go ahead"], ["हेलो?", "बोलिए बोलिए"]])
def test_a_go_on_reply_after_the_reask_asks_the_birth_year_and_never_names_the_lender(replies):
    call = play(record(), HI, replies)
    assert call.keys[-1] == "second_check.ask" and "disclosure.who" not in call.keys
    assert LENDER not in " ".join(line.text for line in call.lines)


@pytest.mark.parametrize("replies", [["आप कौन?", "हम्म"], ["हेलो?", "नमस्ते"]])
def test_a_reply_that_does_not_claim_to_be_the_borrower_is_never_a_yes(replies):
    call = play(record(), HI, replies)
    assert call.end is not None and call.end.outcome is Outcome.not_confirmed
    assert "disclosure.who" not in call.keys and call.keys[-1] == "end.third_party"


@pytest.mark.parametrize(
    "reply", ["जी हाँ, मैं ही हूँ", "हाँ, मैं ही बोल रहा हूँ", "yes, speaking", "हाँ जी, बोल रहा हूँ"]
)
def test_an_explicit_first_person_claim_goes_on(reply):
    call = play(record(), HI, [reply])
    assert call.keys[-1] == "disclosure.go_ahead"


# Round 3: an acknowledgement is an ordinary confirmation: the birth year next, the lender not named.
@pytest.mark.parametrize("ack", ["हाँ बोलिए", "जी कहिए", "जी", "हाँ जी", "haan boliye"])
def test_an_acknowledgement_goes_to_the_birth_year_without_naming_the_lender(ack):
    call = play(record(), HI, [ack])
    assert call.keys[-1] == "second_check.ask" and "disclosure.who" not in call.keys
    assert LENDER not in " ".join(line.text for line in call.lines)


@pytest.mark.parametrize("greeting", ["हेलो", "नमस्ते"])
def test_a_greeting_is_not_a_confirmation_and_twice_ends_the_call(greeting):
    call = play(record(), HI, [greeting, greeting])
    assert call.keys == ("right_party.ask", "right_party.reask", "end.third_party")
    assert call.end.outcome is Outcome.not_confirmed


@pytest.mark.parametrize(
    "reply", ["हाँ, मैं रमेश बोल रहा हूँ", "ji main Ramesh", "मैं सुरेश बोल रहा हूँ", "हाँ साहब बोलिए"]
)
def test_a_reply_outside_the_tight_patterns_never_takes_the_strong_path_without_the_classifier(reply):
    call = play(record(), HI, [reply])
    assert "disclosure.who" not in call.keys
    assert call.keys[-1] in ("right_party.reask", "end.third_party", "second_check.ask")


# --- 2. refusals and non-refusals ---------------------------------------------------------------

VERIFIER_REFUSALS = {
    HI: [
        "मुझे इस बारे में कुछ नहीं कहना", "छोड़िए ये सब", "मैं गाड़ी चला रहा हूँ", "कल फ़ोन करना",
        "अभी नहीं हो पाएगा, मेहमान आए हैं", "आप लोग बार बार क्यों पूछ रहे हो, बस हो गया",
        "मुझे ये सब जवाब देने में कोई रुचि नहीं", "मैं फ़ोन काट रही हूँ", "इतने सवाल मत पूछो",
        "मैं ऑफिस में हूँ, बात नहीं हो सकती", "नहीं चाहिए ये कॉल वॉल", "आगे कुछ नहीं बताऊँगा मैं",
    ],
    HE: [
        "I have to go now", "please don't ask me all this", "main drive kar raha hoon", "kal call karna please",
        "I am in a meeting", "mujhe aur questions nahi chahiye", "that's it, I'm done", "I'd rather not answer",
        "abhi possible nahi hai", "can we do this some other day",
    ],
    TA: [
        "எனக்கு இப்ப பேச முடியல", "நான் வண்டி ஓட்டிட்டு இருக்கேன்", "நாளைக்கு கூப்பிடுங்க",
        "இதெல்லாம் எனக்கு சொல்ல விருப்பம் இல்லை", "போதும்ங்க, விடுங்க", "நான் வேலையில இருக்கேன், அப்புறம் பாக்கலாம்",
        "இனிமே கேள்வி கேக்காதீங்க", "நான் போனை கட் பண்றேன்", "எனக்கு இதுல இன்ட்ரஸ்ட் இல்ல", "வேண்டாங்க, விட்டுடுங்க",
    ],
    KN: [
        "ನನಗೆ ಈಗ ಮಾತಾಡೋಕೆ ಆಗ್ತಿಲ್ಲ", "ನಾನು ಗಾಡಿ ಓಡಿಸ್ತಿದ್ದೀನಿ", "ನಾಳೆ ಫೋನ್ ಮಾಡಿ", "ಇದೆಲ್ಲ ಹೇಳೋಕೆ ನನಗೆ ಇಷ್ಟ ಇಲ್ಲ",
        "ಸಾಕು ಬಿಡಿ", "ನಾನು ಕೆಲಸದಲ್ಲಿದ್ದೀನಿ, ಆಮೇಲೆ ನೋಡೋಣ", "ಇನ್ನು ಪ್ರಶ್ನೆ ಕೇಳಬೇಡಿ", "ನಾನು ಫೋನ್ ಕಟ್ ಮಾಡ್ತೀನಿ",
        "ನನಗೆ ಇದರಲ್ಲಿ ಇಂಟ್ರೆಸ್ಟ್ ಇಲ್ಲ", "ಬೇಡ ರೀ, ಬಿಟ್ಟುಬಿಡಿ",
    ],
}  # fmt: skip

FRESH_REFUSALS = {
    HI: [
        "देखिए मुझे अभी ये सब नहीं बताना", "मैं खाना खा रहा हूँ अभी", "बाद में करना ये सब", "परसों फ़ोन कर लेना",
        "मुझसे ये सवाल मत करो", "बहुत हो गया, अब बंद करो", "मैं किसी और काम में हूँ", "नहीं करनी मुझे ये बातें",
        "बस, अब और नहीं", "मैं ट्रेन में हूँ, आवाज़ नहीं आ रही, बाद में", "ये सब मैं नहीं बताऊँगी",
    ],
    HE: [
        "please stop asking", "I don't have time for this", "not now yaar, baad mein", "call me tomorrow evening",
        "mujhe abhi baat nahi karni", "kisi insaan se baat karao", "I want to speak to a real person",
    ],
}  # fmt: skip


def at_first_question(language):
    call = play(record(), language, [*OPENING[language], NAMED[language]])
    assert isinstance(call.state.position, AtTeachBack), call.keys
    return call.state


def effect(state, text, **kwargs) -> str:
    after, said = step(state, text, **kwargs)
    if isinstance(said, EndOfCall):
        return f"ended:{said.outcome.value}"
    if isinstance(after.position, AtStopCheck):
        return "stop_check"
    if isinstance(after.position, AtCallbackTime):
        return "asked_when"
    return "carried_on"


@pytest.mark.parametrize(
    "language, text",
    [(lang, t) for sets in (VERIFIER_REFUSALS, FRESH_REFUSALS) for lang, ts in sets.items() for t in ts],
)
def test_a_refusal_never_gets_the_next_question(language, text):
    assert effect(at_first_question(language), text) != "carried_on"


VERIFIER_ACCOUNTS = {
    HI: [
        "मुझे तो इसमें इंटरेस्ट नहीं है, फिर भी जोड़ दिया गया", "बैंक वाले बोलते हैं बाद में बात करेंगे, आज तक कोई नहीं आया",
        "मैनेजर से बात करनी है बोलो तो कोई सुनता नहीं वहाँ", "वो लोग हमेशा यही बोलते हैं कि अभी टाइम नहीं है",
        "जब भी पूछो तो फोन काट देते हैं ब्रांच वाले", "एजेंट बोलता है बिजी हूँ बाद में कॉल करना",
    ],
    HE: [
        "branch wale hamesha bolte hain call later, koi nahi batata", "they always hang up when I ask about it",
        "the agent keeps saying I am busy call me later", "I am not interested in this thing but it is in my loan",
        "every time I want to talk to the manager nobody picks up",
    ],
    TA: [
        "அவங்க அப்புறம் பேசலாம்னு சொல்லி அனுப்பிட்டாங்க", "எனக்கு ஆர்வம் இல்லை ஆனாலும் சேர்த்துட்டாங்க",
        "மேனேஜர் கிட்ட பேசணும்னு கேட்டேன், யாரும் கண்டுக்கல", "கேட்டா எனக்கு நேரம் இல்லை அப்புறம் கூப்பிடுங்க னு சொல்றாங்க",
        "வேண்டாம்னு சொன்னேன், கட்டாயம்னு சொல்லி போட்டாங்க",
    ],
    KN: [
        "ಅವರು ಆಮೇಲೆ ಮಾತಾಡೋಣ ಅಂತ ಹೇಳಿ ಕಳಿಸಿದ್ರು", "ನನಗೆ ಆಸಕ್ತಿ ಇಲ್ಲ ಆದ್ರೂ ಸೇರಿಸಿದ್ರು",
        "ಮ್ಯಾನೇಜರ್ ಜೊತೆ ಮಾತಾಡಬೇಕು ಅಂತ ಕೇಳಿದೆ, ಯಾರೂ ಕೇಳಲಿಲ್ಲ", "ಕೇಳಿದ್ರೆ ಈಗ ಟೈಮ್ ಇಲ್ಲ ನಂತರ ಕರೆ ಮಾಡಿ ಅಂತಾರೆ",
        "ಬೇಡ ಅಂದೆ, ಕಡ್ಡಾಯ ಅಂತ ಹೇಳಿ ಹಾಕಿದ್ರು",
    ],
}  # fmt: skip

FRESH_ACCOUNTS = {
    HI: [
        "उन्होंने बोला बाद में बात करेंगे, फिर कभी फ़ोन नहीं आया", "मैंने मना किया था पर वो बोले बिना इसके लोन नहीं मिलेगा",
        "वो लोग फ़ोन ही नहीं उठाते, मैनेजर से बात कराने को बोलो तो टाल देते हैं", "मुझे इंटरेस्ट नहीं था, फिर भी एजेंट ने डाल दिया",
        "बैंक वाले कहते हैं ये ज़रूरी है, मैं क्या करता",
    ],
    HE: [
        "agent ne bola tha mujhe time nahi hai, sign karo bas", "they said they are busy and will call me later, nobody called",
        "branch mein bola tha mujhe nahi chahiye, phir bhi add kar diya",
    ],
}  # fmt: skip


@pytest.mark.parametrize(
    "language, text",
    [(lang, t) for sets in (VERIFIER_ACCOUNTS, FRESH_ACCOUNTS) for lang, ts in sets.items() for t in ts],
)
def test_an_account_of_the_sale_with_refusal_words_does_not_end_the_call(language, text):
    assert not effect(at_first_question(language), text).startswith("ended")


def at_go_ahead():
    return play(record(), HI, [OPENING[HI][0]]).state


@pytest.mark.parametrize(
    "text, wanted",
    [
        # the judge's six
        ("ठीक है, जल्दी बोलिए थोड़ा बिज़ी हूँ", "second_check.ask"),
        ("ये फ्रॉड कॉल तो नहीं है? आप कहाँ से बोल रहे हो?", "verify.before_loan"),
        ("मुझे हिंदी ठीक से नहीं आती, तमिल में बोलिए", "language.switched"),  # W4: Tamil has lines: a live switch
        ("अभी गाड़ी चला रहा हूँ, शाम को कॉल करना", Outcome.call_back_later),
        ("हाँ बोलो, पर लोन का पैसा तो मैंने भर दिया है", "second_check.ask"),
        ("किस चीज़ का फ़ीडबैक? मैंने तो कोई शिकायत नहीं की", "disclosure.reask"),
        # fresh
        ("हाँ पर जल्दी कीजिए, मुझे निकलना है", "second_check.ask"),
        ("ये असली कॉल है? मुझे कैसे पता चलेगा?", "verify.before_loan"),
        ("aap kaun bol rahe ho, bank se ho?", "verify.before_loan"),
        ("can you speak in English please", "language.switched"),  # W4: English goes to the Hinglish lines
        ("मराठी में बात कर सकते हैं?", Outcome.language_switch),
        ("अभी नहीं, एक घंटे बाद कॉल कीजिए", Outcome.call_back_later),
    ],
)
def test_a_reply_at_the_go_ahead_that_is_not_a_refusal_is_not_taken_as_one(text, wanted):
    _state, said = step(at_go_ahead(), text)
    if isinstance(wanted, Outcome):
        assert isinstance(said, EndOfCall) and said.outcome is wanted
    else:
        assert not isinstance(said, EndOfCall), said.outcome
        assert said.lines[-1].key in (wanted, "disclosure.go_ahead", "second_check.ask", "right_party.ask")
        assert wanted in [line.key for line in said.lines]


def test_a_stated_time_is_kept_as_the_customers_own_words():
    _state, said = step(at_go_ahead(), "अभी गाड़ी चला रहा हूँ, शाम को कॉल करना")
    assert said.callback_time == "अभी गाड़ी चला रहा हूँ, शाम को कॉल करना"
    assert said.utterance.lines[-1].key == "end.call_back"


def test_call_later_without_a_time_asks_when_and_keeps_the_answer():
    state, said = step(at_first_question(HI), "बाद में कॉल करना")
    assert isinstance(state.position, AtCallbackTime) and said.lines[-1].key == "callback.when"
    assert expecting(state.position) is Expecting.callback_time
    state, said = step(state, "संडे को सुबह")
    assert isinstance(said, EndOfCall) and said.outcome is Outcome.call_back_later
    assert said.callback_time == "संडे को सुबह"


def test_a_language_request_records_the_language():
    # W4: a language with no prompt file ends the call and records it; one with a file switches live (test_w4_language).
    _state, said = step(at_go_ahead(), "मुझे हिंदी ठीक से नहीं आती, मराठी में बोलिए")
    assert said.requested_language == "marathi" and said.utterance.lines[-1].key == "end.language"


def test_a_verification_question_after_the_loan_is_named_gets_the_papers_answer_then_the_question_again():
    state = at_first_question(HI)
    asked = state.turns[-1].text
    state, said = step(state, "रुकिए, ये कॉल असली है? आप कौन बोल रहे हो?")
    assert next(line.key for line in said.lines) == "verify.after_loan"
    assert said.lines[-1].text == asked


def test_side_answers_are_limited():
    state = at_go_ahead()
    keys = []
    for _ in range(4):
        state, said = step(state, "आप कौन बोल रहे हो?")
        if isinstance(said, EndOfCall):
            break
        keys += [line.key for line in said.lines]
    assert keys.count("verify.before_loan") == 2


@pytest.mark.parametrize("language", LANGUAGES)
def test_silence_twice_ends_the_call_as_no_response(language):
    state = at_first_question(language)
    state, said = step(state, "")
    assert not isinstance(said, EndOfCall)
    state, said = step(state, "")
    assert isinstance(said, EndOfCall) and said.outcome is Outcome.no_response
    assert said.utterance.lines[-1].key == "end.no_response"


def test_a_weak_stop_signal_asks_shall_i_continue_and_yes_goes_on():
    state = at_first_question(HI)
    state, said = step(state, "रहने दो")
    assert isinstance(state.position, AtStopCheck) and said.lines[-1].key == "stop_check.decline"
    after, said = step(state, "हाँ पूछिए")
    assert not isinstance(said, EndOfCall) and isinstance(after.position, AtTeachBack)
    after, said = step(state, "नहीं")
    assert isinstance(said, EndOfCall) and said.outcome is Outcome.declined


# --- 3. the opening -----------------------------------------------------------------------------

WORDS_PER_SECOND = 2.5  # assumed speaking rate for Hindi and Hinglish; no audio was timed


def spoken_seconds(*texts: str) -> float:
    return sum(len(t.split()) for t in texts) / WORDS_PER_SECOND


@pytest.mark.parametrize("language", [HI, HE])
def test_the_opening_is_under_twenty_seconds_before_the_second_customer_turn(language):
    call = play(record(), language, [OPENING[language][0]])
    assert call.keys == (
        "right_party.ask", "disclosure.who", "disclosure.not_sales", "disclosure.recording", "disclosure.go_ahead",
    )  # fmt: skip
    seconds = spoken_seconds(*(u.text for u in call.utterances), OPENING[language][0])
    assert seconds < 20, seconds


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_bot_utterance_fits_the_transport(language):
    lender = "Udaharan Small Finance Bank Limited Co"  # 38 characters
    customer = CUSTOMERS[language]
    rec = record(product("P1"), product("P2"))
    call = play(rec, language, customer.happy(2), lender_name=lender)
    assert call.end is not None
    for utterance in call.utterances:
        assert len(utterance.text) <= 600, (utterance.text, len(utterance.text))


@pytest.mark.parametrize("language", [HI, HE])
def test_an_informed_one_product_call_takes_at_most_150_seconds_by_word_count(language):
    # P8: measured on the default setting (no second check), so the scripted year reply is left out. With the
    # year of birth the same call is 151.6 s (hi) and 151.2 s (hi-en) by word count since iteration 3 added
    # the neutral acknowledgements and the named kind question.
    replies = [reply for k, reply in enumerate(CUSTOMERS[language].happy()) if k != 2]
    call = play(record(), language, replies, identity=NO_CHECK)
    assert call.end is not None and call.end.outcome is Outcome.completed
    seconds = call_seconds(call.end.transcript, words_per_second=WORDS_PER_SECOND)
    assert seconds <= 150, seconds


def test_call_seconds_uses_audio_times_where_they_are_set():
    call = play(record(), HI, CUSTOMERS[HI].happy())
    transcript = call.end.transcript
    timed = transcript.model_copy(
        update={"turns": tuple(t.model_copy(update={"start_s": 0.0, "end_s": 1.0}) for t in transcript.turns)}
    )
    assert call_seconds(timed) == pytest.approx(len(transcript.turns))


@pytest.mark.parametrize("language", [HI, HE])
def test_the_disclosures_that_left_the_opening_are_still_said(language):
    call = play(record(), language, CUSTOMERS[language].happy())
    keys = call.keys
    assert keys.index("disclosure.never_ask") < keys.index("context.loan")  # with the birth-year question
    assert keys.index("disclosure.rights") < keys.index("open_recall.ask")
    assert "close.verify" in keys[-4:]


# --- 4. the teach-back --------------------------------------------------------------------------

TOOK_NOTHING = {HI: "कुछ नहीं लिया, बस लोन लिया था", HE: "kuch nahi liya, sirf loan liya tha"}


@pytest.mark.parametrize("language", [HI, HE])
def test_a_customer_who_took_nothing_gets_one_follow_up_then_consent_then_the_close(language):
    nothing = TOOK_NOTHING[language]
    call = play(record(), language, [*OPENING[language], nothing, "नहीं, कुछ नहीं", "लोन के लिए हाँ की थी, फॉर्म पर साइन किया था"])  # W4: both halves
    assert call.end is not None and call.end.outcome is Outcome.completed
    asked = [line.key for line in call.lines if line.asks is not None or line.key.startswith("open_recall")]
    assert asked == ["open_recall.ask", "open_recall.nothing", "consent.ask"]
    assert not any(t.asks in PRODUCT_QUESTIONS for t in call.end.transcript.turns if t.speaker is Speaker.bot)


def test_a_follow_up_that_names_something_goes_on_to_the_questions():
    call = play(record(), HI, [*OPENING[HI], "कुछ नहीं", "हाँ, एक बीमा की बात हुई थी"])
    assert call.keys[-1] == "kind.ask_named"


def test_which_thing_then_took_nothing_at_a_question_stops_the_product_questions():
    state = at_first_question(HI)
    state, said = step(state, "कौन सी चीज़? मैंने तो कुछ नहीं लिया")
    assert said.lines[-1].key == "consent.ask"


def test_no_line_is_the_riddle():
    for language in (HI, HE):
        texts = load_prompts(language).templates.values()
        assert not any("वो चीज़ क्या है" in t or "हिसाब से वो चीज़" in t for t in texts)


def test_provider_choice_is_skipped_when_the_customer_says_it_was_their_own_choice():
    answers = list(CUSTOMERS[HI].answers)
    answers[PRODUCT_QUESTIONS.index(Question.required_for_loan)] = "नहीं, मेरी अपनी मर्ज़ी थी"
    del answers[PRODUCT_QUESTIONS.index(Question.provider_choice)]
    call = play(record(), HI, [*OPENING[HI], NAMED[HI], *answers[:2], "हाँ सही है", *answers[2:]])
    assert "provider_choice.ask" not in call.keys
    assert "cover.ask" in call.keys


def test_provider_choice_is_asked_when_the_customer_says_it_was_required():
    call = play(record(), HI, CUSTOMERS[HI].happy())
    assert "provider_choice.ask" in call.keys


@pytest.mark.parametrize("language", [HI, HE])
def test_payment_frequency_is_asked_and_tagged(language):
    call = play(record(), language, CUSTOMERS[language].happy())
    turns = [t for t in call.end.transcript.turns if t.asks is Question.payment_frequency]
    assert turns and all(t.product_id == "P1" for t in turns)


@pytest.mark.parametrize("bare", ["हाँ जी", "नहीं", "yes"])
def test_a_bare_yes_or_no_to_an_either_or_question_is_asked_again(bare):
    state = at_first_question(HI)
    for reply in ("एफडी है", "बावन हज़ार", "हाँ सही है", "लोन से", "एक बार देना था"):
        state, _ = step(state, reply)
    assert state.position.question is Question.required_for_loan
    assert expecting(state.position) is Expecting.either_or
    after, _ = step(state, bare)
    assert after.position.question is Question.required_for_loan and after.position.reasked


def test_dont_know_is_never_asked_again():
    state = at_first_question(HI)
    keys = []
    while True:
        state, said = step(state, "पता नहीं")
        if isinstance(said, EndOfCall):
            keys += [line.key for line in said.utterance.lines]
            break
        keys += [line.key for line in said.lines]
    assert not any(key.endswith(".reask") for key in keys), keys


# --- 5. amount turns ----------------------------------------------------------------------------


def at_premium():
    state, _said = step(at_first_question(HI), "एफडी है")
    assert state.position.question is Question.premium
    return state


def test_two_readings_that_agree_are_read_back_at_once():
    state, _said = step(at_premium(), "बावन हज़ार", second_reading="52,000")
    assert isinstance(state.position, AtReadBack) and state.position.amount_inr == 52000


@pytest.mark.parametrize("second", ["तीन लाख दो हज़ार", "", "पता नहीं"])
def test_readings_that_differ_or_one_missing_ask_for_the_amount_once_more(second):
    state, said = step(at_premium(), "तीन लाख दो सौ", second_reading=second)
    assert said.lines[-1].key == "premium.say_again"
    assert expecting(state.position) is Expecting.amount
    state, said = step(
        state, "तीन लाख दो सौ", second_reading="3,02,000"
    )  # still differ: read back, never ask a third time
    assert isinstance(state.position, AtReadBack) and state.position.amount_inr == 300200


def test_a_figure_only_one_reading_holds_is_never_read_back_on_the_first_try():
    _state, said = step(at_premium(), "पता नहीं", second_reading="बावन हज़ार")
    assert said.lines[-1].key == "premium.say_again"


def test_one_yes_and_one_no_at_a_read_back_says_it_again():
    state, _ = step(at_premium(), "बावन हज़ार", second_reading="बावन हज़ार")
    after, _ = step(state, "नहीं", second_reading="हाँ")
    assert isinstance(after.position, AtReadBack) and after.position.read_backs == 2
    after, _said = step(state, "हाँ", second_reading="हाँ")
    assert not isinstance(after.position, AtReadBack)


@pytest.mark.parametrize(
    "reply", ["कौन सा बावन हज़ार?", "बावन हज़ार तो लोन की किस्त है", "जी हाँ सही, बीस हज़ार तो मैंने अलग से दिए थे"]
)
def test_a_reply_that_repeats_or_adds_a_figure_is_not_a_confirmation(reply):
    state, _ = step(at_premium(), "बावन हज़ार")
    after, _ = step(state, reply)
    assert isinstance(after.position, AtReadBack) and after.position.read_backs == 2  # said again, not taken
    assert after.position.amount_inr == 52000 and after.premiums[0].amount_inr == 52000


def test_the_read_back_follows_the_premium_answer_and_says_what_the_figure_is():
    _state, said = step(at_premium(), "बावन हज़ार")
    line = said.lines[-1]
    assert line.key == "read_back.confirm" and line.asks is Question.premium and line.product_id == "P1"
    assert "दिए" in line.text


@pytest.mark.parametrize(
    "said_amount, low, high",
    [
        ("पचास बावन हज़ार के आसपास", 50000, 52000),
        ("करीब पचास हज़ार", 50000, 50000),
        ("50 से 52 हज़ार", 50000, 52000),
    ],
)
def test_an_approximate_amount_is_read_back_as_said(said_amount, low, high):
    from samajh.amounts import Approximate, parse_approx_amount

    state, said = step(at_premium(), said_amount)
    assert isinstance(state.position, AtReadBack), said.lines[-1].key
    line = said.lines[-1]
    assert line.key == "read_back.confirm_about"
    parsed = parse_approx_amount(line.text)
    assert isinstance(parsed, Approximate) and (parsed.low, parsed.high) == (low, high)


def test_a_correction_of_an_approximate_amount_is_read_back_exactly():
    state, _ = step(at_premium(), "पचास बावन हज़ार के आसपास")
    state, said = step(state, "नहीं, इक्यावन हज़ार")
    assert said.lines[-1].key == "read_back.confirm" and state.position.amount_inr == 51000


# --- the line set -------------------------------------------------------------------------------


def test_the_new_line_keys_exist():
    for key in (
        "open_recall.nothing", "payment_frequency.ask", "payment_frequency.reask", "premium.say_again",
        "read_back.confirm_about", "verify.before_loan", "verify.after_loan", "callback.when", "end.call_back",
        "end.language", "end.third_party", "end.no_response", "close.verify",
    ):  # fmt: skip
        assert key in LINES
    assert "disclosure.verify" not in LINES


def test_no_leak_holds_on_the_new_branches():
    a = record(product(required_for_loan=True, premium_inr=61000, cancel_window_days=15))
    b = record(
        product(
            required_for_loan=False, premium_inr=99000, cancel_window_days=30, features=["one_time_payment"]
        )
    )
    scripts = [
        [*OPENING[HI], "कुछ नहीं", "नहीं", "हाँ की थी"],
        [*OPENING[HI], "कुछ नहीं", "हाँ एक चीज़ की बात हुई थी", "पता नहीं", "पचास बावन हज़ार के आसपास", "हाँ"],
        [*OPENING[HI], NAMED[HI], "एफडी", "बावन हज़ार", "हाँ", "लोन से", "एक बार", "मेरी मर्ज़ी थी", "पता नहीं"],
        [OPENING[HI][0], "बाद में कॉल करना", "शाम को"],
    ]
    for script in scripts:
        bot_a = [line.text for line in play(a, HI, script).lines]
        bot_b = [line.text for line in play(b, HI, script).lines]
        assert bot_a == bot_b
        assert not any("61,000" in t or "99,000" in t for t in bot_a)
    _, first = start(a, HI, lender_name="Udaharan Bank", identity=YEAR_POLICY)
    assert first.lines[0].key == "right_party.ask"


# --- coordinator additions: cover read-back, re-asked amounts tagged alike ------------------------


def at_cover():
    state, _ = step(at_premium(), "बावन हज़ार")
    for reply in ("हाँ सही है", "लोन से", "एक बार", "मेरी मर्ज़ी थी"):
        state, _said = step(state, reply)
    assert state.position.question is Question.cover, state.position
    return state


def test_a_stated_cover_figure_is_read_back_and_confirmed():
    state, said = step(at_cover(), "पाँच लाख तक का कवर है")
    line = said.lines[-1]
    assert line.key == "read_back.cover_confirm" and line.step.value == "read_back"
    assert (
        line.asks is Question.cover and line.product_id == "P1" and parse_amount(line.text).rupees == 500000
    )
    after, said = step(state, "हाँ")
    assert after.position.question is Question.term


def test_a_cover_figure_can_be_corrected_and_the_record_is_never_read():
    rec = record(product(cover_inr=900000))
    call = play(rec, HI, [*OPENING[HI], NAMED[HI], "एफडी", "बावन हज़ार", "हाँ", "लोन से", "एक बार", "मेरी मर्ज़ी थी",
                          "पाँच लाख", "नहीं, चार लाख", "हाँ"])  # fmt: skip
    readbacks = [line.text for line in call.lines if line.key == "read_back.cover_confirm"]
    assert [parse_amount(t).rupees for t in readbacks] == [500000, 400000]
    assert not any("नौ लाख" in line.text for line in call.lines)
    assert call.keys[-1] == "term.ask" and call.state.premium_of(0) == 52000


def test_a_cover_answer_with_no_figure_is_not_read_back():
    _state, said = step(at_cover(), "पैसा सुरक्षित रहेगा")
    assert said.lines[-1].key == "term.ask"


def test_both_askings_of_a_re_asked_amount_are_tagged_with_the_same_question():
    state, _said = step(at_premium(), "तीन लाख दो सौ", second_reading="3,02,000")
    asked = [t for t in state.turns if t.speaker is Speaker.bot and t.asks is Question.premium]
    assert [t.step.value for t in asked] == ["teach_back", "teach_back"] and all(
        t.product_id == "P1" for t in asked
    )
