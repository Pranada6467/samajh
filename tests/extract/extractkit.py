"""A fake LLM for the extractor tests. It replays outputs keyed by schema, question and reply."""

import json
import re
from datetime import date
from functools import cache
from pathlib import Path

from samajh.clients.errors import LlmOutputInvalid
from samajh.clients.llm import LlmResult
from samajh.extract._wire import SCHEMA, SlotKind
from samajh.types import Borrower, CallStep, Consent, LoanRecord, Product, Question, Speaker, Transcript, Turn

RECORDED = Path(__file__).parent / "recorded" / "dev_gpt-6-luna.json"
_USER = re.compile(r"Assistant's question: <<<(.*?)>>>\nCustomer's reply: <<<(.*?)>>>", re.DOTALL)

Key = tuple[str, str, str]  # schema name, bot question, customer reply


@cache
def recorded_outputs() -> dict[Key, dict]:
    """The recorded outputs. They predate `RecallReply.took_nothing`, so a recall output without
    it is replayed with `took_nothing` false: no denial is read into a reply the model never judged."""
    calls = json.loads(RECORDED.read_text())["calls"]
    return {
        (c["schema"], c["question"], c["reply"]): (
            {"took_nothing": False} | c["output"] if c["schema"] == "RecallReply" else c["output"]
        )
        for c in calls
    }


class FakeLlm:
    """`outputs` maps a call to the JSON the model returns. `replies` overrides by reply text alone.

    A screening call with no recorded output returns no claims and no concerns. Any other call
    with no output fails the test. `errors` makes one call raise. `sent` keeps every request, so a test can read the prompts.
    """

    def __init__(self, outputs: dict[Key, dict] | None = None) -> None:
        self.outputs = dict(outputs or {})
        self.replies: dict[tuple[str, str], dict] = {}  # (schema name, reply) -> output
        self.invalid: set[str] = set()  # replies for which the model never returns valid output
        self.errors: dict[tuple[str, str], Exception] = {}  # (schema name, reply) -> what the call raises
        self.sent: list[list] = []

    def say(self, schema: str, reply: str, **output) -> None:
        """Change fields of the recorded output for one reply, or set a whole new output."""
        recorded = next((v for (s, _, r), v in self.outputs.items() if (s, r) == (schema, reply)), {})
        self.replies[(schema, reply)] = recorded | output

    def complete(self, schema, messages, *, model=None, max_tokens=1024):
        self.sent.append(list(messages))
        question, reply = _USER.search(messages[1].content).groups()
        if reply in self.invalid:
            raise LlmOutputInvalid(model="fake", attempts=3, last_error="not valid JSON")
        name = schema.__name__
        if (name, reply) in self.errors:
            raise self.errors[(name, reply)]
        output = self.replies.get((name, reply)) or self.outputs.get((name, question, reply))
        if output is None:
            if name != "ScreenReply":
                raise AssertionError(f"no output recorded for {name} / {reply!r}")
            output = {"claims": [], "concerns": []}
        return LlmResult(
            value=schema.model_validate(output), model=model or "fake", prompt_tokens=0, completion_tokens=0,
            usd=0.0, cache_hit=True, attempts=0, generation_id=None,
        )  # fmt: skip

    def prompts(self) -> str:
        return "\n".join(message.content for request in self.sent for message in request)


# --- a small synthetic call, built row by row --------------------------------------------------

PRODUCT = Product(
    id="P1", kind="credit_life", provider="Nakli Life", premium_inr=41300, cover_inr=350000, term_months=36,
    paid_from_loan=True, required_for_loan=False, risk_mitigant=True, provider_choice_offered=True,
    cancel_window_days=30, features=frozenset(), consent=Consent(method="otp", at=date(2026, 10, 1)),
)  # fmt: skip


def record(product: Product = PRODUCT) -> LoanRecord:
    return LoanRecord(
        loan_id="L-FAKE-0001", lender_type="bank",
        borrower=Borrower(name="Nakli Naam", dob=date(1990, 1, 1), language="hi"),
        loan_kind="personal", sanctioned_inr=350000, disbursed_inr=308700, disbursed_on=date(2026, 10, 1),
        products=(product,),
    )  # fmt: skip


Row = tuple[str, str | None, str, str, dict]  # step, asks, bot question, customer reply, model output

# An informed customer on a clean record, with the output a correct model gives.
BASE: list[Row] = [
    ("open_recall", None, "लोन के साथ आपने क्या-क्या लिया, और कितने का?", "एक बीमा लिया था।",
     {"items": [{"span": "एक बीमा", "kind": "insurance", "amount_span": None}], "took_nothing": False}),
    ("teach_back", "kind", "वह क्या है: बीमा, एफ़डी, या कुछ और?", "बीमा है।",
     {"status": "stated", "kind": "insurance", "clauses": [1]}),
    ("teach_back", "premium", "उसके लिए आपने कितने रुपये दिए?", "इकतालीस हज़ार तीन सौ रुपये।",
     {"status": "stated", "span": "इकतालीस हज़ार तीन सौ", "clauses": [1]}),
    ("teach_back", "payment_source", "वह रकम कैसे चुकाई गई?", "लोन में से कटा था।",
     {"status": "stated", "source": "from_loan", "clauses": [1]}),
    ("teach_back", "required_for_loan", "क्या लोन पाने के लिए उसे लेना ज़रूरी था?", "नहीं, मर्ज़ी से लिया।",
     {"status": "stated", "yes": False, "clauses": [1, 2]}),
    ("teach_back", "cover", "उसमें कितनी रकम का कवर है?", "साढ़े तीन लाख रुपये।",
     {"status": "stated", "span": "साढ़े तीन लाख", "clauses": [1]}),
    ("teach_back", "term", "वह कितने समय के लिए है?", "तीन साल।",
     {"status": "stated", "span": "तीन साल", "clauses": [1]}),
    ("teach_back", "cancel_window", "क्या बताया गया था कि कैंसल कर सकते हैं, और कब तक?", "हाँ, तीस दिन के अंदर।",
     {"allowed_status": "stated", "allowed": True, "allowed_clauses": [1], "window_status": "stated",
      "window_span": "तीस दिन", "window_clauses": [2]}),
    ("teach_back", "features", "अगर आप वह पैसा वापस चाहें, तो क्या मिल सकता है?", "नहीं, वापस नहीं मिलता।",
     {"status": "stated", "claims": [], "clauses": [1, 2]}),
    ("consent_check", "consent", "आपने क्या-क्या लेने के लिए हामी भरी थी, और कैसे?",
     "लोन और बीमा, बीमे का ओटीपी दिया था।",
     {"given_status": "stated", "given": True, "given_clauses": [1], "method_status": "stated", "method": "otp",
      "method_clauses": [2]}),
    ("read_back", "premium", "इकतालीस हज़ार तीन सौ, यानी 41,300 रुपये, सही है?", "हाँ, सही है।",
     {"status": "stated", "confirms": True, "clauses": [1, 2], "corrected_amount_span": None}),
]  # fmt: skip


def swap(rows: list[Row], asks: str | None, *replacements: Row) -> list[Row]:
    """The rows with the question `asks` (None: open recall) replaced by `replacements`. Never the read-back."""
    out: list[Row] = []
    for row in rows:
        out += replacements if row[1] == asks and row[0] != "read_back" else [row]
    return out


def answered(rows: list[Row], asks: str | None, reply: str, **output) -> list[Row]:
    """The rows with a new reply to one question and the fields of the model's output that change."""
    (old,) = [r for r in rows if r[1] == asks and r[0] != "read_back"]
    return swap(rows, asks, (old[0], old[1], old[2], reply, old[4] | output))


def build(rows: list[Row]) -> tuple[Transcript, FakeLlm]:
    """A Hindi call about `record()`: the two identity steps, then one exchange per row."""
    turns: list[Turn] = []
    outputs: dict[Key, dict] = {}

    def say(step: str, bot: str, customer: str, asks: str | None = None) -> None:
        product = "P1" if asks and asks != "consent" else None
        question = Question(asks) if asks else None
        turns.append(Turn(id=len(turns) + 1, speaker=Speaker.bot, step=CallStep(step), text=bot,
                          asks=question, product_id=product))  # fmt: skip
        turns.append(Turn(id=len(turns) + 1, speaker=Speaker.customer, step=CallStep(step), text=customer))

    say("right_party_check", "क्या मेरी बात नकली जी से हो रही है?", "हाँ।")
    say("second_check", "अपने जन्म का साल बताइए।", "उन्नीस सौ नब्बे।")
    for step, asks, bot, customer, output in rows:
        say(step, bot, customer, asks)
        schema = "RecallReply" if step == "open_recall" else SCHEMA[_kind(step, asks)].__name__
        outputs[(schema, bot, customer)] = output
    transcript = Transcript(call_id="c1", loan_id="L-FAKE-0001", language="hi", turns=tuple(turns))
    return transcript, FakeLlm(outputs)


def _kind(step: str, asks: str | None) -> SlotKind:
    return SlotKind.readback if step == "read_back" else SlotKind(asks)
