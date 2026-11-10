"""Shared helpers for the dialogue tests: synthetic records, scripted customers, and a call runner."""

from __future__ import annotations

from dataclasses import dataclass

from samajh.dialogue import (
    PRODUCT_QUESTIONS,
    BotUtterance,
    CallState,
    EndOfCall,
    Limits,
    RuleInterpreter,
    TurnInterpreter,
    start,
    step,
)
from samajh.types import Language, LoanRecord, Question

LENDER = "Udaharan Bank"
LANGUAGES = tuple(Language)
RULES = RuleInterpreter()


def product(pid: str = "P1", **changes) -> dict:
    return {
        "id": pid,
        "kind": "credit_life",
        "provider": "Namoona Life (synthetic)",
        "premium_inr": 52000,
        "cover_inr": 500000,
        "term_months": 24,
        "paid_from_loan": True,
        "required_for_loan": False,
        "risk_mitigant": True,
        "provider_choice_offered": False,
        "cancel_window_days": 30,
        "features": [],
        "consent": None,
    } | changes


def record(*products: dict, name: str = "Ramesh Kalpit", dob: str = "1984-06-15") -> LoanRecord:
    return LoanRecord.model_validate(
        {
            "loan_id": "LN-TEST-0001",
            "lender_type": "bank",
            "borrower": {"name": name, "dob": dob, "language": "hi"},
            "loan_kind": "gold",
            "sanctioned_inr": 500000,
            "disbursed_inr": 448000,
            "disbursed_on": "2026-10-20",
            "products": list(products) if products else [product()],
        }
    )


@dataclass(frozen=True)
class Customer:
    """What a scripted customer says, in one language. Tamil and Kannada lines are not human-reviewed."""

    identity: str
    go_ahead: str
    year: str  # 1984
    recall: str
    answers: tuple[str, ...]  # one per PRODUCT_QUESTIONS entry; the premium answer is 52,000
    consent: str
    confirm: str
    reject: str  # "no" to a read-back, with no other figure
    correction: str  # "no, 55,000"
    corrected: str  # 55,000 said alone
    decline: str
    human: str
    wrong_person: str
    who: str
    repeat: str
    filler: str
    dont_know: str
    weak_stop: str  # might mean "stop the call": the bot asks before it ends

    def product_replies(self) -> list[str]:
        """One product's answers, with the read-back confirmed straight after the premium."""
        k = PRODUCT_QUESTIONS.index(Question.premium) + 1
        return [*self.answers[:k], self.confirm, *self.answers[k:]]

    def happy(self, products: int = 1) -> list[str]:
        """Replies for a whole call: every question answered once, every read-back confirmed."""
        return [self.identity, self.go_ahead, self.year, self.recall, *(self.product_replies() * products),
                self.consent]  # fmt: skip


CUSTOMERS: dict[Language, Customer] = {
    Language.hi: Customer(
        identity="हाँ जी, बोल रहा हूँ",
        go_ahead="हाँ, ठीक है",
        year="उन्नीस सौ चौरासी",
        recall="बस एक एफडी, लोन सिक्योरिटी के लिए, बावन हज़ार की",
        answers=(
            "एफडी है",
            "बावन हज़ार",
            "लोन में से कट गया",
            "एक बार दिया था बस",
            "हाँ, बोला था ज़रूरी है",
            "कुछ नहीं बताया",
            "पैसा सुरक्षित रहेगा",
            "दो साल",
            "नहीं बताया",
            "एक साल बाद निकाल सकते हैं",
        ),
        consent="फॉर्म पर साइन किया था बस",
        confirm="हाँ, सही है",
        reject="नहीं, गलत है",
        correction="नहीं, पचपन हज़ार",
        corrected="पचपन हज़ार",
        decline="मुझे बात नहीं करनी, कॉल बंद करो",
        human="किसी इंसान से बात कराइए",
        wrong_person="रॉन्ग नंबर है",
        who="कौन बोल रहा है?",
        repeat="क्या? फिर से बोलिए",
        filler="हम्म",
        dont_know="पता नहीं",
        weak_stop="रहने दो",
    ),
    Language.hi_en: Customer(
        identity="yes, speaking",
        go_ahead="हाँ okay",
        year="1984",
        recall="बस एक FD ली थी loan security के लिए, fifty two thousand की",
        answers=(
            "FD है",
            "fifty two thousand",
            "loan amount से cut हो गया",
            "one time payment थी",
            "हाँ, बोला था compulsory है",
            "कुछ नहीं बताया",
            "पैसा safe रहेगा",
            "two years",
            "नहीं बताया",
            "one year बाद withdraw कर सकते हैं",
        ),
        consent="form पर sign किया था बस",
        confirm="yes, correct",
        reject="no, wrong है",
        correction="नहीं, fifty five thousand",
        corrected="fifty five thousand",
        decline="I am not interested, please don't call",
        human="mujhe kisi agent se baat karni hai",
        wrong_person="wrong number",
        who="who is this?",
        repeat="sorry, repeat कीजिए",
        filler="hmm",
        dont_know="pata nahin",
        weak_stop="leave it",
    ),
    Language.ta: Customer(
        identity="ஆமா, நான்தான் பேசுறேன்",
        go_ahead="சரி, சொல்லுங்க",
        year="1984",
        recall="ஒரு எஃப்டி மட்டும், கடன் பாதுகாப்புக்கு, ஐம்பத்திரண்டாயிரம்",
        answers=(
            "அது எஃப்டி",
            "ஐம்பத்திரண்டாயிரம்",
            "கடன் தொகையிலிருந்து பிடித்தார்கள்",
            "ஒரு முறை தான் கொடுத்தேன்",
            "ஆமா, கட்டாயம் என்று சொன்னார்கள்",
            "எதுவும் சொல்லவில்லை",
            "பணம் பாதுகாப்பாக இருக்கும்",
            "இரண்டு வருடம்",
            "சொல்லவில்லை",
            "ஒரு வருடம் கழித்து எடுக்கலாம்",
        ),
        consent="படிவத்தில் கையெழுத்து போட்டேன்",
        confirm="ஆமா, சரி",
        reject="இல்லை, தவறு",
        correction="இல்லை, ஐம்பத்தைந்தாயிரம்",
        corrected="ஐம்பத்தைந்தாயிரம்",
        decline="எனக்கு பேச விருப்பம் இல்லை, கூப்பிடாதீங்க",
        human="ஒரு அதிகாரி கிட்ட பேசணும்",
        wrong_person="ராங் நம்பர்",
        who="யார் பேசுறீங்க?",
        repeat="புரியல, மறுபடியும் சொல்லுங்க",
        filler="ம்ம்",
        dont_know="தெரியாது",
        weak_stop="போதும்",
    ),
    Language.kn: Customer(
        identity="ಹೌದು, ನಾನೇ ಮಾತಾಡ್ತಿದ್ದೀನಿ",
        go_ahead="ಸರಿ, ಹೇಳಿ",
        year="1984",
        recall="ಒಂದು ಎಫ್‌ಡಿ ಮಾತ್ರ, ಸಾಲದ ಭದ್ರತೆಗೆ, ಐವತ್ತೆರಡು ಸಾವಿರ",
        answers=(
            "ಅದು ಎಫ್‌ಡಿ",
            "ಐವತ್ತೆರಡು ಸಾವಿರ",
            "ಸಾಲದ ಮೊತ್ತದಿಂದ ಕಡಿತ ಮಾಡಿದರು",
            "ಒಂದೇ ಸಲ ಕೊಟ್ಟೆ",
            "ಹೌದು, ಕಡ್ಡಾಯ ಅಂತ ಹೇಳಿದರು",
            "ಏನೂ ಹೇಳಲಿಲ್ಲ",
            "ಹಣ ಸುರಕ್ಷಿತವಾಗಿರುತ್ತದೆ",
            "ಎರಡು ವರ್ಷ",
            "ಹೇಳಲಿಲ್ಲ",
            "ಒಂದು ವರ್ಷದ ನಂತರ ತೆಗೆಯಬಹುದು",
        ),
        consent="ಫಾರ್ಮ್ ಮೇಲೆ ಸಹಿ ಮಾಡಿದೆ",
        confirm="ಹೌದು, ಸರಿ",
        reject="ಇಲ್ಲ, ತಪ್ಪು",
        correction="ಇಲ್ಲ, ಐವತ್ತೈದು ಸಾವಿರ",
        corrected="ಐವತ್ತೈದು ಸಾವಿರ",
        decline="ನನಗೆ ಮಾತಾಡಲು ಇಷ್ಟ ಇಲ್ಲ, ಕರೆ ಮಾಡಬೇಡಿ",
        human="ಒಬ್ಬ ಅಧಿಕಾರಿ ಜೊತೆ ಮಾತಾಡಬೇಕು",
        wrong_person="ರಾಂಗ್ ನಂಬರ್",
        who="ಯಾರು ಮಾತಾಡ್ತಿರೋದು?",
        repeat="ಅರ್ಥ ಆಗಲಿಲ್ಲ, ಮತ್ತೆ ಹೇಳಿ",
        filler="ಹ್ಮ್",
        dont_know="ಗೊತ್ತಿಲ್ಲ",
        weak_stop="ಸಾಕು",
    ),
}


@dataclass(frozen=True)
class Call:
    """A played call: every state and bot utterance in order, and the end if it was reached."""

    states: tuple[CallState, ...]
    utterances: tuple[BotUtterance, ...]
    end: EndOfCall | None

    @property
    def state(self) -> CallState:
        return self.states[-1]

    @property
    def lines(self):
        return tuple(line for utterance in self.utterances for line in utterance.lines)

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(line.key for line in self.lines)


def play(
    rec: LoanRecord,
    language: Language,
    replies: list[str | tuple[str, str]],
    *,
    interpreter: TurnInterpreter = RULES,
    limits: Limits | None = None,
    lender_name: str = LENDER,
) -> Call:
    """Feed `replies` to a call until they run out or the call ends.

    A reply given as a pair is one turn heard twice: (the first transcript, the second transcript).
    """
    state, said = start(rec, language, lender_name=lender_name, limits=limits)
    states, utterances, end = [state], [said], None
    for reply in replies:
        first, second = reply if isinstance(reply, tuple) else (reply, None)
        state, said = step(state, first, second_reading=second, interpreter=interpreter)
        states.append(state)
        if isinstance(said, EndOfCall):
            utterances.append(said.utterance)
            end = said
            break
        utterances.append(said)
    return Call(tuple(states), tuple(utterances), end)
