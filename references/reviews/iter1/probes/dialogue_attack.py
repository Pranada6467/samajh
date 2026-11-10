"""Verifier probe (iteration 1, part 2): attack samajh.dialogue with fresh inputs. Offline, no LLM.

    uv run python references/reviews/iter1/probes/dialogue_attack.py [section ...]

Sections: third_party, refusals, false_declines, yes_to_either_or, read_back, loops, differential.
Every sentence here was written by the verifier (an LLM), not said by a person. Tamil and Kannada
sentences are not human-reviewed. Counts are counts of probes, not rates.
"""

from __future__ import annotations

import random
import sys

from samajh.dialogue import EndOfCall, Limits, RuleInterpreter, expecting, start, step
from samajh.dialogue.machine import AtReadBack, AtStopCheck, AtTeachBack
from samajh.types import Language, LoanRecord

LENDER = "Namoona Bank"


def record(**product_changes) -> LoanRecord:
    product = {
        "id": "P1", "kind": "credit_life", "provider": "Namoona Life (synthetic)", "premium_inr": 52000,
        "cover_inr": 500000, "term_months": 24, "paid_from_loan": True, "required_for_loan": False,
        "risk_mitigant": True, "provider_choice_offered": False, "cancel_window_days": 30, "features": [],
        "consent": None,
    } | product_changes  # fmt: skip
    return LoanRecord.model_validate(
        {
            "loan_id": "LN-VERIFY-0001", "lender_type": "bank",
            "borrower": {"name": "Ramesh Namoona", "dob": "1984-06-15", "language": "hi"},
            "loan_kind": "gold", "sanctioned_inr": 500000, "disbursed_inr": 448000,
            "disbursed_on": "2026-10-20", "products": [product],
        }
    )  # fmt: skip


def play(language: Language, replies: list[str], rec: LoanRecord | None = None, **kwargs):
    """Run replies until they run out or the call ends. Returns (state, last said, bot line keys, bot texts)."""
    state, said = start(rec or record(), language, lender_name=LENDER, **kwargs)
    keys = [line.key for line in said.lines]
    texts = [line.text for line in said.lines]
    for reply in replies:
        if isinstance(said, EndOfCall):
            break
        state, said = step(state, reply)
        lines = said.utterance.lines if isinstance(said, EndOfCall) else said.lines
        keys += [line.key for line in lines]
        texts += [line.text for line in lines]
    return state, said, keys, texts


HAPPY = {
    Language.hi: ["हाँ जी, बोल रहा हूँ", "हाँ", "1984"],
    Language.hi_en: ["yes, speaking", "haan okay", "1984"],
    Language.ta: ["ஆமா, நான்தான்", "சரி", "1984"],
    Language.kn: ["ಹೌದು, ನಾನೇ", "ಸರಿ", "1984"],
}
RECALL = {
    Language.hi: "एक एफडी ली थी",
    Language.hi_en: "ek FD li thi",
    Language.ta: "ஒரு எஃப்டி வாங்கினேன்",
    Language.kn: "ಒಂದು ಎಫ್‌ಡಿ ತೆಗೆದುಕೊಂಡೆ",
}

# ------------------------------------------------------------------ third party

# (who is speaking, [identity reply, go-ahead reply, birth-year reply]). None of these speakers is
# the borrower, and each says so in ordinary words. The year is the borrower's (a relative knows it).
THIRD_PARTY = {
    Language.hi: [
        ("son", ["हाँ बोलिए", "हाँ", "पापा 1984 में पैदा हुए थे"]),
        ("wife", ["हाँ जी, रमेश की वाइफ़ बोल रही हूँ", "ठीक है", "1984"]),
        ("brother", ["जी मैं रमेश का भाई हूँ, बताइए", "हाँ", "चौरासी"]),
        ("wife", ["हाँ, वो मेरे हस्बैंड हैं", "जी", "1984"]),
        ("colleague", ["हाँ जी बताइए, रमेश सर की डेस्क से बोल रहा हूँ", "हाँ बताइए", "उन्नीस सौ चौरासी"]),
        ("wife, after the re-ask", ["कौन?", "हाँ हैं, बुलाती हूँ", "हाँ", "1984"]),
        ("son", ["जी, पापा अभी दुकान पर हैं, बोलिए", "हाँ जी", "डैडी का बर्थ ईयर 1984 है"]),
        ("daughter", ["हाँ जी, मैं रमेश जी की बेटी हूँ", "हाँ ठीक है", "सन चौरासी"]),
        ("mother", ["हाँ बेटा बोलो, रमेश तो खेत गया है", "हाँ", "1984"]),
        ("neighbour", ["जी, रमेश भैया का फ़ोन मेरे पास छूट गया है, बोलिए", "ठीक है बोलिए", "1984"]),
    ],
    Language.hi_en: [
        ("wife", ["yes this is Ramesh's wife", "ok", "1984"]),
        ("son", ["haan ji boliye, papa abhi shop pe hain", "yes", "papa ka birth year 1984 hai"]),
        ("colleague", ["yes tell me, Ramesh sir is in a meeting", "okay go ahead", "nineteen eighty four"]),
        ("wife", ["haan, main Ramesh ki wife bol rahi hoon", "theek hai", "1984"]),
        ("brother", ["yes, Ramesh's brother here", "sure", "84"]),
        ("assistant", ["yes, I am Ramesh sir's assistant, boliye", "okay", "1984"]),
        ("wife, after the re-ask", ["who is this?", "yes he is on the line, one minute", "yes", "1984"]),
        ("daughter", ["ji, daddy bahar gaye hain, aap bataiye", "haan", "1984"]),
    ],
    Language.ta: [
        ("wife", ["ஆமா, நான் அவர் மனைவி பேசுறேன்", "சரி", "அவர் 1984ல பிறந்தார்"]),
        ("wife", ["சொல்லுங்க, அவர் கடைக்கு போயிருக்கார்", "சரி சொல்லுங்க", "1984"]),
        ("wife", ["ஆமாங்க, அவர் என் வீட்டுக்காரர்", "ஆமா", "1984"]),
        ("child", ["அப்பா தூங்குறாங்க, சொல்லுங்க", "சரி", "1984"]),
        ("colleague", ["சார் மீட்டிங்ல இருக்காரு, சொல்லுங்க", "ஓகே", "1984"]),
        ("brother", ["ஆமா, நான் ரமேஷ் தம்பி பேசுறேன்", "சரிங்க", "1984"]),
        ("wife, after the re-ask", ["யாரு?", "ஆமா இருக்காரு, கூப்பிடுறேன்", "சரி", "1984"]),
        ("mother", ["ஆமா பா, ரமேஷ் வயலுக்கு போயிருக்கான், சொல்லு", "சரி", "1984"]),
    ],
    Language.kn: [
        ("wife", ["ಹೇಳಿ, ರಮೇಶ್ ಆಫೀಸಿಗೆ ಹೋಗಿದ್ದಾರೆ", "ಸರಿ", "1984"]),
        ("wife", ["ಹೌದು, ನಾನು ರಮೇಶ್ ಹೆಂಡತಿ ಮಾತಾಡ್ತಿದ್ದೀನಿ", "ಸರಿ ಹೇಳಿ", "1984"]),
        ("child", ["ಅಪ್ಪ ಮಲಗಿದ್ದಾರೆ, ಹೇಳಿ", "ಆಯ್ತು", "1984"]),
        ("colleague", ["ಸರ್ ಮೀಟಿಂಗ್‌ನಲ್ಲಿದ್ದಾರೆ, ಹೇಳಿ", "ಓಕೆ", "1984"]),
        ("brother", ["ಹೌದು, ನಾನು ರಮೇಶ್ ತಮ್ಮ", "ಸರಿ", "1984"]),
        ("wife, after the re-ask", ["ಯಾರು?", "ಹೌದು ಇದ್ದಾರೆ, ಕರೀತೀನಿ", "ಸರಿ", "1984"]),
        ("mother", ["ಹೌದಪ್ಪ ಹೇಳು, ರಮೇಶ ಹೊಲಕ್ಕೆ ಹೋಗಿದ್ದಾನೆ", "ಸರಿ", "1984"]),
        ("daughter", ["ಹೌದು, ನಾನು ರಮೇಶ್ ಮಗಳು", "ಹೂಂ", "1984"]),
    ],
}


def third_party() -> None:
    print("\n== third party: is the lender named (disclosure) or the loan named (context)?")
    for language, cases in THIRD_PARTY.items():
        lender = loan = 0
        for who, replies in cases:
            state, said, keys, texts = play(language, replies)
            got_lender = "disclosure.who" in keys
            got_loan = "context.loan" in keys
            lender += got_lender
            loan += got_loan
            outcome = said.outcome.value if isinstance(said, EndOfCall) else f"at {state.position.at}"
            mark = "LOAN NAMED" if got_loan else ("lender named" if got_lender else "nothing said")
            print(f"  [{language.value}] {mark:12s} {who:24s} {replies!r} -> {outcome}")
        print(f"  [{language.value}] lender named to {lender}/{len(cases)}, loan named to {loan}/{len(cases)}")


# ------------------------------------------------------------------ refusals

# Fresh ways of refusing or asking to stop, none copied from the lexicon. Said at a teach-back question.
REFUSALS = {
    Language.hi: [
        "मुझे इस बारे में कुछ नहीं कहना",
        "छोड़िए ये सब",
        "मैं गाड़ी चला रहा हूँ",
        "कल फ़ोन करना",
        "अभी नहीं हो पाएगा, मेहमान आए हैं",
        "आप लोग बार बार क्यों पूछ रहे हो, बस हो गया",
        "मुझे ये सब जवाब देने में कोई रुचि नहीं",
        "मैं फ़ोन काट रही हूँ",
        "इतने सवाल मत पूछो",
        "मैं ऑफिस में हूँ, बात नहीं हो सकती",
        "नहीं चाहिए ये कॉल वॉल",
        "आगे कुछ नहीं बताऊँगा मैं",
    ],
    Language.hi_en: [
        "I have to go now",
        "please don't ask me all this",
        "main drive kar raha hoon",
        "kal call karna please",
        "I am in a meeting",
        "mujhe aur questions nahi chahiye",
        "that's it, I'm done",
        "I'd rather not answer",
        "abhi possible nahi hai",
        "can we do this some other day",
    ],
    Language.ta: [
        "எனக்கு இப்ப பேச முடியல",
        "நான் வண்டி ஓட்டிட்டு இருக்கேன்",
        "நாளைக்கு கூப்பிடுங்க",
        "இதெல்லாம் எனக்கு சொல்ல விருப்பம் இல்லை",
        "போதும்ங்க, விடுங்க",
        "நான் வேலையில இருக்கேன், அப்புறம் பாக்கலாம்",
        "இனிமே கேள்வி கேக்காதீங்க",
        "நான் போனை கட் பண்றேன்",
        "எனக்கு இதுல இன்ட்ரஸ்ட் இல்ல",
        "வேண்டாங்க, விட்டுடுங்க",
    ],
    Language.kn: [
        "ನನಗೆ ಈಗ ಮಾತಾಡೋಕೆ ಆಗ್ತಿಲ್ಲ",
        "ನಾನು ಗಾಡಿ ಓಡಿಸ್ತಿದ್ದೀನಿ",
        "ನಾಳೆ ಫೋನ್ ಮಾಡಿ",
        "ಇದೆಲ್ಲ ಹೇಳೋಕೆ ನನಗೆ ಇಷ್ಟ ಇಲ್ಲ",
        "ಸಾಕು ಬಿಡಿ",
        "ನಾನು ಕೆಲಸದಲ್ಲಿದ್ದೀನಿ, ಆಮೇಲೆ ನೋಡೋಣ",
        "ಇನ್ನು ಪ್ರಶ್ನೆ ಕೇಳಬೇಡಿ",
        "ನಾನು ಫೋನ್ ಕಟ್ ಮಾಡ್ತೀನಿ",
        "ನನಗೆ ಇದರಲ್ಲಿ ಇಂಟ್ರೆಸ್ಟ್ ಇಲ್ಲ",
        "ಬೇಡ ರೀ, ಬಿಟ್ಟುಬಿಡಿ",
    ],
}


def _at_first_question(language: Language):
    state, said, _, _ = play(language, HAPPY[language] + [RECALL[language]])
    assert isinstance(state.position, AtTeachBack), state.position
    return state


def _effect(before, after, said) -> str:
    if isinstance(said, EndOfCall):
        return f"ended:{said.outcome.value}"
    if isinstance(after.position, AtStopCheck):
        return "stop_check"
    if getattr(after.position, "reasked", False) and not getattr(before.position, "reasked", False):
        return "re-asked"
    return "NEXT QUESTION"


def refusals() -> None:
    print("\n== refusals at a teach-back question: does the bot stop, ask, or carry on?")
    for language, lines in REFUSALS.items():
        tally: dict[str, int] = {}
        for text in lines:
            before = _at_first_question(language)
            after, said = step(before, text)
            effect = _effect(before, after, said)
            tally[effect] = tally.get(effect, 0) + 1
            print(f"  [{language.value}] {effect:16s} {text}")
        print(f"  [{language.value}] {tally}")
    print("\n-- a customer who repeats one unrecognised refusal to every question: how long does the bot go on?")
    for language, lines in REFUSALS.items():
        for text in lines:
            before = _at_first_question(language)
            after, said = step(before, text)
            if _effect(before, after, said) not in ("NEXT QUESTION", "re-asked"):
                continue
            state, said, questions = before, None, 0
            while not isinstance(said, EndOfCall):
                state, said = step(state, text)
                questions += 1
            print(
                f"  [{language.value}] {questions} more bot utterances after the first refusal, "
                f"ended {said.outcome.value}, unresolved {len(said.unresolved)}: {text}"
            )
            break


# ------------------------------------------------------------------ false declines

# Answers a misled customer gives. Each holds words that sound like a refusal or a request for a
# person, but the customer is describing the sale, not ending the call. Said at the kind question.
ACCOUNTS = {
    Language.hi: [
        "मुझे तो इसमें इंटरेस्ट नहीं है, फिर भी जोड़ दिया गया",
        "बैंक वाले बोलते हैं बाद में बात करेंगे, आज तक कोई नहीं आया",
        "मैनेजर से बात करनी है बोलो तो कोई सुनता नहीं वहाँ",
        "वो लोग हमेशा यही बोलते हैं कि अभी टाइम नहीं है",
        "जब भी पूछो तो फोन काट देते हैं ब्रांच वाले",
        "एजेंट बोलता है बिजी हूँ बाद में कॉल करना",
    ],
    Language.hi_en: [
        "branch wale hamesha bolte hain call later, koi nahi batata",
        "they always hang up when I ask about it",
        "the agent keeps saying I am busy call me later",
        "I am not interested in this thing but it is in my loan",
        "every time I want to talk to the manager nobody picks up",
    ],
    Language.ta: [
        "அவங்க அப்புறம் பேசலாம்னு சொல்லி அனுப்பிட்டாங்க",
        "எனக்கு ஆர்வம் இல்லை ஆனாலும் சேர்த்துட்டாங்க",
        "மேனேஜர் கிட்ட பேசணும்னு கேட்டேன், யாரும் கண்டுக்கல",
        "கேட்டா எனக்கு நேரம் இல்லை அப்புறம் கூப்பிடுங்க னு சொல்றாங்க",
        "வேண்டாம்னு சொன்னேன், கட்டாயம்னு சொல்லி போட்டாங்க",
    ],
    Language.kn: [
        "ಅವರು ಆಮೇಲೆ ಮಾತಾಡೋಣ ಅಂತ ಹೇಳಿ ಕಳಿಸಿದ್ರು",
        "ನನಗೆ ಆಸಕ್ತಿ ಇಲ್ಲ ಆದ್ರೂ ಸೇರಿಸಿದ್ರು",
        "ಮ್ಯಾನೇಜರ್ ಜೊತೆ ಮಾತಾಡಬೇಕು ಅಂತ ಕೇಳಿದೆ, ಯಾರೂ ಕೇಳಲಿಲ್ಲ",
        "ಕೇಳಿದ್ರೆ ಈಗ ಟೈಮ್ ಇಲ್ಲ ನಂತರ ಕರೆ ಮಾಡಿ ಅಂತಾರೆ",
        "ಬೇಡ ಅಂದೆ, ಕಡ್ಡಾಯ ಅಂತ ಹೇಳಿ ಹಾಕಿದ್ರು",
    ],
}


def false_declines() -> None:
    print("\n== accounts of the sale that hold refusal-like words: does the call end on them?")
    for language, lines in ACCOUNTS.items():
        ended = asked = 0
        for text in lines:
            before = _at_first_question(language)
            after, said = step(before, text)
            effect = _effect(before, after, said)
            ended += effect.startswith("ended")
            asked += effect == "stop_check"
            print(f"  [{language.value}] {effect:16s} {text}")
        print(f"  [{language.value}] call ended on {ended}/{len(lines)}, stop question on {asked}/{len(lines)}")


# ------------------------------------------------------------------ bare yes to an either/or question


def yes_to_either_or() -> None:
    print("\n== a bare yes/no to 'was it required, or your choice?' and to the cancel question")
    bare = {
        Language.hi: ["हाँ जी", "नहीं"],
        Language.hi_en: ["yes", "no"],
        Language.ta: ["ஆமா", "இல்லை"],
        Language.kn: ["ಹೌದು", "ಇಲ್ಲ"],
    }
    for language, words in bare.items():
        state = _at_first_question(language)
        # kind, premium ("don't know" is an answer), payment source -> required_for_loan
        for filler in (RECALL[language], {"hi": "पता नहीं", "hi-en": "pata nahi", "ta": "தெரியாது",
                                          "kn": "ಗೊತ್ತಿಲ್ಲ"}[language.value], RECALL[language]):  # fmt: skip
            state, said = step(state, filler)
        assert state.position.question.value == "required_for_loan", state.position
        for word in words:
            after, said = step(state, word)
            print(f"  [{language.value}] required-or-choice? {word!r} -> {_effect(state, after, said)}"
                  f" (bot asked: {state.turns[-1].text})")  # fmt: skip


# ------------------------------------------------------------------ read-back


def _at_read_back(language: Language, premium: str, rec: LoanRecord | None = None, second: str | None = None):
    state, said, _, _ = play(language, HAPPY[language] + [RECALL[language]], rec)
    state, said = step(state, RECALL[language])  # kind
    state, said = step(state, premium, second_reading=second)  # premium
    while not isinstance(said, EndOfCall) and not isinstance(state.position, AtReadBack):
        if state.position.at == "teach_back" and state.position.question.value == "premium":
            return state, said  # the premium was not taken
        state, said = step(state, RECALL[language])
    return state, said


def read_back() -> None:
    print("\n== read-back: whose figure is spoken, and what a yes/no disagreement between two readings does")
    rec = record(premium_inr=61000)
    for language, premium in [
        (Language.hi, "बावन हज़ार"), (Language.hi_en, "fifty two thousand"),
        (Language.ta, "ஐம்பத்திரண்டாயிரம்"), (Language.kn, "ಐವತ್ತೆರಡು ಸಾವಿರ"),
    ]:  # fmt: skip
        state, said = _at_read_back(language, premium, rec)
        last = said.lines[-1].text if not isinstance(said, EndOfCall) else "(call ended, no read-back)"
        print(f"  [{language.value}] record 61,000, customer said {premium!r}: bot says: {last}")
        print(f"       61,000 in any bot line: {any('61,000' in t.text for t in state.turns if t.speaker.value == 'bot')}")
    print("  -- the customer says no to the read-back in the first transcript; the second transcript says yes")
    for language, premium, no, yes in [
        (Language.hi, "बावन हज़ार", "नहीं", "हाँ"),
        (Language.hi_en, "fifty two thousand", "no", "yes"),
        (Language.ta, "ஐம்பத்திரண்டாயிரம்", "இல்லை", "ஆமா"),
        (Language.kn, "ಐವತ್ತೆರಡು ಸಾವಿರ", "ಇಲ್ಲ", "ಹೌದು"),
    ]:
        state, said = _at_read_back(language, premium)
        assert isinstance(state.position, AtReadBack), state.position
        after, said2 = step(state, no, second_reading=yes)
        kept = after.turns[-1 - len(said2.utterance.lines if isinstance(said2, EndOfCall) else said2.lines)].text
        result = said2.outcome.value if isinstance(said2, EndOfCall) else f"at {after.position.at}"
        print(f"  [{language.value}] first={no!r} second={yes!r} -> {result}; customer turn kept as {kept!r}; "
              f"unresolved {len(after.unresolved)}")  # fmt: skip
        after, said2 = step(state, no)
        result = said2.outcome.value if isinstance(said2, EndOfCall) else f"at {after.position.at}"
        print(f"  [{language.value}] first={no!r} alone -> {result}")
    print("  -- nothing in the read-back says which amount it is")
    state, said = _at_read_back(Language.hi, "बावन हज़ार")
    print(f"  [hi] {said.lines[-1].text}")


# ------------------------------------------------------------------ loops and limits


def loops() -> None:
    print("\n== does every call end? adversarial repeats, then random replies")
    adversarial = {
        "silence forever": [""],
        "what? forever": ["क्या?"],
        "leave it / no, alternating": ["रहने दो", "नहीं"],
        "yes forever": ["हाँ"],
        "figure ping-pong at read-back": ["बावन हज़ार", "नहीं, पचपन हज़ार"],
        "one emoji": ["🙂"],
        "5,000 words": ["हाँ " * 5000],
        "NUL and controls": ["\x00\x01\x02 हाँ ﻿"],
    }
    for name, cycle in adversarial.items():
        for opening in ([], HAPPY[Language.hi], HAPPY[Language.hi] + ["एक एफडी", "एफडी"]):
            state, said = start(record(), Language.hi, lender_name=LENDER)
            for reply in opening:
                state, said = step(state, reply)
            n = 0
            while not isinstance(said, EndOfCall):
                state, said = step(state, cycle[n % len(cycle)])
                n += 1
                if n > 500:
                    print(f"  NOT ENDED after 500 turns: {name}")
                    break
            else:
                print(f"  {name:32s} after {len(opening)} good replies: ended {said.outcome.value} "
                      f"in {state.bot_turns} bot utterances")  # fmt: skip
    rng = random.Random(20261110)
    pool = [r for cases in THIRD_PARTY.values() for _, rs in cases for r in rs]
    pool += [r for rs in REFUSALS.values() for r in rs] + [r for rs in ACCOUNTS.values() for r in rs]
    pool += ["", "हाँ", "नहीं", "पता नहीं", "बावन हज़ार", "52,000", "1984", "84", "क्या?", "रहने दो", "3,02,000",
             "तीन लाख दो सौ", "शायद पचपन हज़ार", "yes", "no", "ஆமா", "இல்லை", "ಹೌದು", "ಇಲ್ಲ"]  # fmt: skip
    worst, crashes, outcomes = 0, 0, {}
    for k in range(4000):
        language = list(Language)[k % 4]
        products = [dict(id=f"P{i + 1}") for i in range(rng.choice([0, 1, 1, 2, 3]))]
        rec = LoanRecord.model_validate(record().model_dump(mode="json") | {
            "products": [record().products[0].model_dump(mode="json") | p for p in products]})  # fmt: skip
        try:
            state, said = start(rec, language, lender_name=LENDER, limits=Limits(max_bot_turns=10_000))
            n = 0
            while not isinstance(said, EndOfCall):
                second = rng.choice(pool) if rng.random() < 0.3 else None
                state, said = step(state, rng.choice(pool), second_reading=second)
                n += 1
                assert n < 2000, "did not end"
        except Exception as error:  # noqa: BLE001 - the probe counts every failure
            crashes += 1
            print(f"  CRASH {type(error).__name__}: {error}")
            continue
        worst = max(worst, state.bot_turns)
        outcomes[said.outcome.value] = outcomes.get(said.outcome.value, 0) + 1
    print(f"  4,000 random calls (0 to 3 products, budget 10,000): crashes {crashes}, longest {worst} bot "
          f"utterances, outcomes {outcomes}")  # fmt: skip


# ------------------------------------------------------------------ differential (no record value in any line)


def differential() -> None:
    print("\n== two records that differ in every tested value: are the bot's lines identical?")
    a = record()
    b = record(kind="credit_life", provider="Doosra Jeevan (synthetic)", premium_inr=61000, cover_inr=750000,
               term_months=60, paid_from_loan=False, required_for_loan=True, risk_mitigant=False,
               provider_choice_offered=True, cancel_window_days=15,
               features=["one_time_payment"], consent={"method": "otp", "at": "2026-10-19"})  # fmt: skip
    rng = random.Random(7)
    pool = [r for rs in REFUSALS.values() for r in rs] + [r for rs in ACCOUNTS.values() for r in rs]
    # No reply in the pool holds a value of record b, so any such value in a bot line came from the record.
    pool += ["हाँ", "नहीं", "पता नहीं", "बावन हज़ार", "सत्तर हज़ार", "52,000", "क्या?", "मैसेज से", "साइन किया",
             "ज़रूरी था", "मर्ज़ी थी", "दस दिन", "तीस दिन", "तीन साल", "दो साल", "साढ़े चार लाख"]  # fmt: skip
    differ = leaks = calls = 0
    values = ["61,000", "61000", "इकसठ", "sixty one", "7,50,000", "750000", "Doosra", "Jeevan", "Namoona Life",
              "otp", "ओटीपी", "LN-VERIFY", "P1", "credit", "15", "60"]  # fmt: skip
    for k in range(800):
        language = list(Language)[k % 4]
        replies = HAPPY[language] + [rng.choice(pool) for _ in range(40)]
        _, _, keys_a, texts_a = play(language, replies, a)
        _, _, keys_b, texts_b = play(language, replies, b)
        calls += 1
        differ += texts_a != texts_b
        said_by_customer = " ".join(replies)
        for text in texts_b:
            for value in values:
                if value in text and value not in said_by_customer:
                    leaks += 1
                    print(f"  LEAK? {value!r} in {text!r}")
    print(f"  {calls} paired calls: bot lines differ in {differ}; record values found in bot lines: {leaks}")


SECTIONS = {
    "third_party": third_party, "refusals": refusals, "false_declines": false_declines,
    "yes_to_either_or": yes_to_either_or, "read_back": read_back, "loops": loops, "differential": differential,
}  # fmt: skip

if __name__ == "__main__":
    for name in sys.argv[1:] or list(SECTIONS):
        SECTIONS[name]()
    _ = (RuleInterpreter, expecting)
